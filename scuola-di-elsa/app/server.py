"""Scuola di Elsa — server (connettore) + app per il telefono.

Variabili d'ambiente:
  PORTAL_SCHOOL    kkgymuc                (sottodominio dell'Eltern-Portal; "demo" = dati finti)
  PORTAL_USER      email di accesso all'Eltern-Portal
  PORTAL_PASSWORD  password dell'Eltern-Portal
  CHILD_NAME       Elsa                   (se nel portale ci sono più figli)
  APP_PIN          codice per aprire l'app (obbligatorio)
  SECRET_KEY       stringa casuale lunga per firmare il cookie di accesso
  DEEPL_API_KEY    facoltativa: traduzioni con DeepL invece di Google
"""

from __future__ import annotations

import hmac
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from .portal import Exam, Item, LoginError, PortalClient, PortalError
from .topics import topic_of
from .translate import translate_many

STATIC = Path(__file__).parent / "static"
COOKIE = "elsa_session"
MAX_AGE = 180 * 24 * 3600

SCHOOL = os.environ.get("PORTAL_SCHOOL", "kkgymuc")
APP_PIN = os.environ.get("APP_PIN", "")
SECRET = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
signer = URLSafeTimedSerializer(SECRET, salt="elsa")

if SCHOOL == "demo":
    from .demo import DemoPortal

    portal: Any = DemoPortal()
else:
    portal = PortalClient(
        SCHOOL,
        os.environ.get("PORTAL_USER", ""),
        os.environ.get("PORTAL_PASSWORD", ""),
        os.environ.get("CHILD_NAME", "Elsa"),
    )

_cache: dict[str, Any] = {"at": 0.0, "raw": None}
_cache_lock = threading.Lock()
CACHE_SECONDS = 300


# ---------------------------------------------------------------------------
# Accesso all'app
# ---------------------------------------------------------------------------
def authed(request: Request) -> bool:
    token = request.cookies.get(COOKIE)
    if not token:
        return False
    try:
        signer.loads(token, max_age=MAX_AGE)
        return True
    except BadSignature:
        return False


def require(fn):
    async def wrapper(request: Request) -> Response:
        if not authed(request):
            return JSONResponse({"error": "login"}, status_code=401)
        try:
            return await fn(request)
        except LoginError as e:
            return JSONResponse({"error": "portal_login", "detail": str(e)}, status_code=502)
        except PortalError as e:
            return JSONResponse({"error": "portal", "detail": str(e)}, status_code=502)
        except Exception as e:  # noqa: BLE001
            return JSONResponse({"error": "network", "detail": f"{type(e).__name__}: {e}"}, status_code=502)

    return wrapper


_attempts: dict[str, list[float]] = {}


async def login(request: Request) -> Response:
    ip = request.client.host if request.client else "?"
    now = time.time()
    recent = [t for t in _attempts.get(ip, []) if now - t < 600]
    if len(recent) >= 8:
        return JSONResponse({"error": "too_many"}, status_code=429)
    body = await request.json()
    pin = str(body.get("pin", ""))
    if not APP_PIN:
        return JSONResponse({"error": "no_pin_configured"}, status_code=500)
    if not hmac.compare_digest(pin, APP_PIN):
        _attempts[ip] = recent + [now]
        return JSONResponse({"error": "wrong_pin"}, status_code=403)
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        COOKIE, signer.dumps("ok"), max_age=MAX_AGE, httponly=True, secure=request.url.scheme == "https", samesite="lax"
    )
    return resp


async def logout(request: Request) -> Response:
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE)
    return resp


# ---------------------------------------------------------------------------
# Dati
# ---------------------------------------------------------------------------
def _fetch_raw() -> dict[str, Any]:
    items: list[Item] = []
    errors: list[str] = []
    for name, fn in (
        ("elternbriefe", portal.letters),
        ("schwarzes_brett", portal.blackboard),
        ("umfragen", portal.polls),
        ("messaggi", portal.messages),
    ):
        try:
            items.extend(fn())
        except LoginError:
            raise
        except Exception as e:  # noqa: BLE001 - una sezione rotta non blocca le altre
            errors.append(f"{name}: {e}")
    try:
        exams = portal.exams()
    except LoginError:
        raise
    except Exception as e:  # noqa: BLE001
        exams = []
        errors.append(f"schulaufgaben: {e}")
    return {
        "items": items,
        "exams": exams,
        "errors": errors,
        "school": portal.school_name,
        "student": (portal.student or {}).get("name"),
        "updated": time.time(),
    }


def get_raw(force: bool = False) -> dict[str, Any]:
    with _cache_lock:
        if force or _cache["raw"] is None or time.time() - _cache["at"] > CACHE_SECONDS:
            _cache["raw"] = _fetch_raw()
            _cache["at"] = time.time()
        return _cache["raw"]


def invalidate() -> None:
    with _cache_lock:
        _cache["at"] = 0.0


def localize(raw: dict[str, Any], lang: str) -> dict[str, Any]:
    items: list[Item] = raw["items"]
    exams: list[Exam] = raw["exams"]
    texts = [i.title for i in items] + [i.body for i in items] + [e.title for e in exams]
    tr = translate_many(texts, lang) if lang != "de" else texts
    n = len(items)
    out_items = []
    for idx, it in enumerate(items):
        d = it.to_dict()
        d["title_de"], d["body_de"] = it.title, it.body
        d["title"], d["body"] = tr[idx], tr[n + idx]
        d["topic"] = topic_of(it.title, it.body)
        d.get("extra", {}).pop("path_ids", None)
        out_items.append(d)
    out_exams = []
    for idx, e in enumerate(exams):
        d = e.to_dict()
        d["title_de"] = e.title
        d["title"] = tr[2 * n + idx]
        out_exams.append(d)
    return {
        "school": raw["school"],
        "student": raw["student"],
        "updated": raw["updated"],
        "errors": raw["errors"],
        "items": out_items,
        "exams": out_exams,
        "lang": lang,
    }


def _lang(request: Request) -> str:
    lang = request.query_params.get("lang", "it")
    return lang if lang in ("it", "en", "de") else "it"


@require
async def overview(request: Request) -> Response:
    force = request.query_params.get("refresh") == "1"
    lang = _lang(request)
    raw = await run_in_threadpool(get_raw, force)
    data = await run_in_threadpool(localize, raw, lang)
    return JSONResponse(data)


@require
async def confirm_letter(request: Request) -> Response:
    letter_id = request.path_params["letter_id"]
    ok = await run_in_threadpool(portal.confirm_letter, letter_id)
    invalidate()
    return JSONResponse({"ok": ok})


def _find_poll(poll_id: str) -> Item:
    for it in get_raw()["items"]:
        if it.category == "umfragen" and it.id == poll_id:
            return it
    raise PortalError("Sondaggio non trovato")


def _poll_localized(poll_id: str, lang: str) -> dict[str, Any]:
    poll = _find_poll(poll_id)
    form = portal.poll_form(poll.extra["href"])
    texts = [form.get("title") or poll.title, form.get("description", "")]
    for f in form["fields"]:
        texts.append(f.get("question", ""))
        for o in f.get("options", []):
            texts.append(o.get("label", ""))
    tr = translate_many(texts, lang) if lang != "de" else texts
    it = iter(tr)
    out = {
        "id": poll_id,
        "title": next(it),
        "title_de": texts[0],
        "description": next(it),
        "description_de": texts[1],
        "locked": form["locked"],
        "voted": poll.extra.get("voted"),
        "end": poll.extra.get("end"),
        "attachments": form.get("attachments", []) or poll.attachments,
        "fields": [],
    }
    for f in form["fields"]:
        nf = {k: v for k, v in f.items() if k != "options"}
        nf["question_de"] = f.get("question", "")
        nf["question"] = next(it)
        if "options" in f:
            nf["options"] = []
            for o in f["options"]:
                no = dict(o)
                no["label_de"] = o.get("label", "")
                no["label"] = next(it)
                nf["options"].append(no)
        out["fields"].append(nf)
    return out


@require
async def poll_detail(request: Request) -> Response:
    data = await run_in_threadpool(_poll_localized, request.path_params["poll_id"], _lang(request))
    return JSONResponse(data)


@require
async def poll_submit(request: Request) -> Response:
    poll = await run_in_threadpool(_find_poll, request.path_params["poll_id"])
    body = await request.json()
    answers = body.get("answers") or {}
    if not isinstance(answers, dict) or not answers:
        return JSONResponse({"error": "empty"}, status_code=400)
    result = await run_in_threadpool(portal.submit_poll, poll.extra["href"], answers)
    invalidate()
    return JSONResponse(result)


@require
async def file_proxy(request: Request) -> Response:
    """Scarica un allegato dal portale con la sessione del connettore."""
    url = request.query_params.get("u", "")
    if not url.startswith(portal.base_url) or "get_file" not in url:
        return JSONResponse({"error": "bad_url"}, status_code=400)
    r = await run_in_threadpool(portal._get, url[len(portal.base_url):])
    ctype = r.headers.get("Content-Type", "application/octet-stream")
    headers = {"Cache-Control": "private, max-age=3600"}
    disp = r.headers.get("Content-Disposition")
    if disp:
        headers["Content-Disposition"] = disp.replace("attachment", "inline")
    content = getattr(r, "content", r.text.encode())
    return Response(content, media_type=ctype, headers=headers)


async def me(request: Request) -> Response:
    return JSONResponse({"authed": authed(request), "school": SCHOOL})


async def health(request: Request) -> Response:
    return JSONResponse({"ok": True})


async def index(request: Request) -> Response:
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


async def service_worker(request: Request) -> Response:
    return FileResponse(STATIC / "sw.js", media_type="application/javascript", headers={"Cache-Control": "no-cache"})


app = Starlette(
    routes=[
        Route("/", index),
        Route("/sw.js", service_worker),
        Route("/api/health", health),
        Route("/api/me", me),
        Route("/api/login", login, methods=["POST"]),
        Route("/api/logout", logout, methods=["POST"]),
        Route("/api/overview", overview),
        Route("/api/letters/{letter_id}/confirm", confirm_letter, methods=["POST"]),
        Route("/api/polls/{poll_id}", poll_detail),
        Route("/api/polls/{poll_id}", poll_submit, methods=["POST"]),
        Route("/api/file", file_proxy),
        Mount("/static", StaticFiles(directory=STATIC), name="static"),
    ],
    middleware=[Middleware(GZipMiddleware, minimum_size=800)],
)
