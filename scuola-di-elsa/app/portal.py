"""Client per l'Eltern-Portal (eltern-portal.org).

Parla con il portale come farebbe un browser: login con csrf, scelta del figlio,
lettura delle pagine HTML e invio dei moduli. Gli indirizzi e la struttura HTML
sono quelli usati anche dalle librerie open source pyelternportal ed
elternportal-api.
"""

from __future__ import annotations

import hashlib
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

PARSER = "html.parser"
UA = (
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36"
)


class PortalError(Exception):
    """Errore generico del portale."""


class LoginError(PortalError):
    """Credenziali errate o login non riuscito."""


# ---------------------------------------------------------------------------
# Modelli
# ---------------------------------------------------------------------------
@dataclass
class Item:
    """Una comunicazione di qualsiasi categoria."""

    id: str
    category: str  # elternbriefe | schwarzes_brett | umfragen | klassenleitung | fachlehrer
    title: str
    body: str = ""
    date: str | None = None  # ISO
    new: bool = False
    can_confirm: bool = False
    sender: str | None = None
    distribution: str | None = None
    attachments: list[dict[str, str]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Exam:
    id: str
    date: str  # ISO date
    time: str | None
    title: str
    kind: str  # schulaufgabe | test | altro
    subject: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Utilità di parsing
# ---------------------------------------------------------------------------
_DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _text_with_breaks(tag: Tag | None) -> str:
    """Testo di un elemento, con <br> e blocchi trasformati in a capo."""
    if tag is None:
        return ""
    tag = BeautifulSoup(str(tag), PARSER)
    for br in tag.find_all("br"):
        br.replace_with("\n")
    for block in tag.find_all(["p", "div", "li", "tr", "h1", "h2", "h3", "h4"]):
        block.insert_after("\n")
    return _clean(tag.get_text())


def _parse_date(text: str | None) -> date | None:
    m = _DATE_RE.search(text or "")
    if not m:
        return None
    try:
        return date(int(m[3]), int(m[2]), int(m[1]))
    except ValueError:
        return None


def _parse_datetime(text: str | None) -> datetime | None:
    d = _parse_date(text)
    if d is None:
        return None
    rest = (text or "")[_DATE_RE.search(text).end():]
    t = _TIME_RE.search(rest)
    if t:
        return datetime(d.year, d.month, d.day, int(t[1]), int(t[2]))
    return datetime(d.year, d.month, d.day)


def _stable_id(*parts: Any) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def _attachments(tag: Tag, base_url: str) -> list[dict[str, str]]:
    out = []
    seen = set()
    for a in tag.select("a[href*='get_file']"):
        href = urljoin(base_url, a.get("href", "").lstrip("/"))
        if href in seen:
            continue
        seen.add(href)
        name = _clean(a.get_text()) or a.get("title") or "Allegato"
        out.append({"name": name, "href": href})
    return out


# ---------------------------------------------------------------------------
# Parser delle singole pagine (puri, testabili senza rete)
# ---------------------------------------------------------------------------
def parse_login_page(html: str) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html, PARSER)
    csrf = soup.find("input", {"name": "csrf"})
    school = soup.find("h2", {"id": "schule"})
    return (
        csrf.get("value") if csrf else None,
        school.get_text(strip=True) if school else None,
    )


def parse_students(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, PARSER)
    return [
        {"id": opt.get("value", ""), "name": _clean(opt.get_text())}
        for opt in soup.select(".pupil-selector select option")
    ]


def is_logged_in(html: str) -> bool:
    soup = BeautifulSoup(html, PARSER)
    if soup.select_one(".pupil-selector"):
        return True
    return soup.find("form", class_="form-signin") is None and "logout" in html


def parse_letters(html: str, base_url: str) -> list[Item]:
    """aktuelles/elternbriefe"""
    soup = BeautifulSoup(html, PARSER)
    items: list[Item] = []
    for link in soup.select(".link_nachrichten"):
        m = re.search(r"eb_bestaetigung\((\d+)\)", link.get("onclick") or "")
        m = m or re.search(r"\d+", link.get("onclick") or "")
        if not m:
            continue
        letter_id = m[1] if m.lastindex else m[0]

        h4 = link.find("h4")
        title = _clean(h4.get_text()) if h4 else _clean(link.get_text())

        # data: testo del link escluso il titolo
        stamp_text = " ".join(
            s for s in link.find_all(string=True) if s.find_parent("h4") is None
        )
        sent = _parse_datetime(stamp_text)

        status_cell = soup.find("td", {"id": f"empf_{letter_id}"})
        status = _clean(status_cell.get_text()) if status_cell else ""
        new = "noch nicht" in status.lower() or (status_cell is None)
        number = ""
        if status_cell is not None:
            prev = status_cell.find_previous_sibling("td")
            number = _clean(prev.get_text()) if prev else ""

        cell = link.find_parent("td") or link.parent
        distribution = None
        body = ""
        if cell is not None:
            cell_copy = BeautifulSoup(str(cell), PARSER)
            first = cell_copy.find(class_="link_nachrichten")
            if first is not None:
                first.decompose()
            dist = cell_copy.select_one("span.small, span[style*='8pt']")
            if dist is not None:
                distribution = _clean(dist.get_text()).replace("Klasse/n:", "").strip(" ,")
                dist.decompose()
            body = _text_with_breaks(cell_copy)

        attachments = []
        if link.name == "a" and link.get("href"):
            attachments.append(
                {"name": "PDF", "href": urljoin(base_url, link["href"].lstrip("/"))}
            )

        items.append(
            Item(
                id=letter_id,
                category="elternbriefe",
                title=title,
                body=body,
                date=sent.isoformat() if sent else None,
                new=new,
                can_confirm=new,
                distribution=distribution,
                attachments=attachments,
                extra={"number": number, "status": status},
            )
        )
    return items


def parse_blackboard(html: str, base_url: str) -> list[Item]:
    """aktuelles/schwarzes_brett"""
    soup = BeautifulSoup(html, PARSER)
    items: list[Item] = []
    for well in soup.select("#asam_content .grid-item .well, #asam_content .well"):
        h4 = well.find("h4")
        if h4 is None:
            continue
        title = _clean(h4.get_text())
        full = _text_with_breaks(well)
        sent = _parse_datetime(full)
        copy = BeautifulSoup(str(well), PARSER)
        for tag in copy.find_all("h4"):
            tag.decompose()
        for p in copy.find_all("p"):
            if "eingestellt am" in p.get_text():
                p.decompose()
        body = _text_with_breaks(copy)
        items.append(
            Item(
                id=_stable_id("sb", title, sent),
                category="schwarzes_brett",
                title=title,
                body=body,
                date=sent.isoformat() if sent else None,
                attachments=_attachments(well, base_url),
            )
        )
    # deduplica (alcuni temi annidano .well dentro .grid-item)
    uniq: dict[str, Item] = {}
    for it in items:
        uniq.setdefault(it.id, it)
    return list(uniq.values())


def parse_polls(html: str, base_url: str) -> list[Item]:
    """aktuelles/umfragen: elenco."""
    soup = BeautifulSoup(html, PARSER)
    items: list[Item] = []
    today = date.today()
    for row in soup.select("#asam_content div.row.m_bot"):
        a = row.select_one("a.umf_list")
        if a is None:
            continue
        href = a.get("href", "")
        cols = row.find_all("div", recursive=False)
        end = _parse_date(cols[1].get_text()) if len(cols) > 1 else None
        voted = _parse_date(cols[2].get_text()) if len(cols) > 2 else None
        if len(cols) > 2 and cols[2].find("img", src=re.compile("haken")):
            voted = voted or end or today
        open_ = end is None or end >= today
        poll_id = re.sub(r"[^0-9_]", "", href.rsplit("/", 1)[-1]) or _stable_id(href)
        items.append(
            Item(
                id=poll_id,
                category="umfragen",
                title=_clean(a.get_text()),
                date=end.isoformat() if end else None,
                new=open_ and voted is None,
                attachments=_attachments(row, base_url),
                extra={
                    "href": href,
                    "end": end.isoformat() if end else None,
                    "voted": voted.isoformat() if voted else None,
                    "open": open_,
                },
            )
        )
    return items


def parse_poll_form(html: str, base_url: str) -> dict[str, Any]:
    """Pagina di dettaglio di un sondaggio → testo + campi del modulo.

    I sondaggi dell'Eltern-Portal sono moduli HTML liberi (radio, checkbox,
    testo, select). Invece di indovinare la struttura, li leggiamo in modo
    generico e li rimandiamo identici con le scelte dell'utente.
    """
    soup = BeautifulSoup(html, PARSER)
    form = soup.select_one("#asam_content form") or soup.find("form")
    if form is None:
        return {"description": _text_with_breaks(soup.select_one("#asam_content")),
                "fields": [], "hidden": {}, "action": None, "locked": True}

    action = urljoin(base_url, (form.get("action") or "").lstrip("/")) if form.get("action") else None
    hidden = {
        i.get("name"): i.get("value", "")
        for i in form.find_all("input", {"type": "hidden"})
        if i.get("name")
    }

    title_tag = form.find("h3")
    title = _clean(title_tag.get_text()) if title_tag else ""

    # descrizione: blocchi di testo senza campi
    desc_parts: list[str] = []
    fields: list[dict[str, Any]] = []
    groups: dict[str, dict[str, Any]] = {}
    any_disabled = False

    def label_for(inp: Tag) -> str:
        if inp.get("id"):
            lab = form.find("label", {"for": inp["id"]})
            if lab:
                return _clean(lab.get_text())
        parent_label = inp.find_parent("label")
        if parent_label:
            return _clean(parent_label.get_text())
        # testo subito dopo l'input
        texts = []
        for sib in inp.next_siblings:
            if isinstance(sib, Tag) and sib.name in ("input", "br", "select", "textarea"):
                break
            texts.append(sib.get_text() if isinstance(sib, Tag) else str(sib))
        return _clean(" ".join(texts)) or inp.get("value", "")

    def question_for(inp: Tag) -> str:
        group = inp.find_parent(class_="form-group")
        if group is None:
            return ""
        lab = group.find(class_=re.compile("control-label")) or group.find(["label", "strong", "b"])
        if lab and not lab.find("input"):
            return _clean(lab.get_text())
        return ""

    for group in form.find_all(class_="form-group") or [form]:
        if group.find(["input", "select", "textarea"], type=lambda t: t != "hidden") is None:
            if group.find("h3") is None:
                t = _text_with_breaks(group)
                if t:
                    desc_parts.append(t)

    for inp in form.find_all(["input", "select", "textarea"]):
        itype = (inp.get("type") or inp.name).lower()
        name = inp.get("name")
        if not name or itype in ("hidden", "submit", "button", "reset", "image"):
            continue
        disabled = inp.has_attr("disabled") or inp.has_attr("readonly")
        any_disabled = any_disabled or disabled
        if itype in ("radio", "checkbox"):
            g = groups.get(name)
            if g is None:
                g = {
                    "name": name,
                    "type": itype,
                    "question": question_for(inp),
                    "options": [],
                    "disabled": disabled,
                }
                groups[name] = g
                fields.append(g)
            g["options"].append(
                {
                    "value": inp.get("value", "on"),
                    "label": label_for(inp),
                    "checked": inp.has_attr("checked"),
                }
            )
        elif inp.name == "select":
            fields.append(
                {
                    "name": name,
                    "type": "select",
                    "question": question_for(inp),
                    "options": [
                        {
                            "value": o.get("value", _clean(o.get_text())),
                            "label": _clean(o.get_text()),
                            "checked": o.has_attr("selected"),
                        }
                        for o in inp.find_all("option")
                    ],
                    "disabled": disabled,
                }
            )
        else:
            fields.append(
                {
                    "name": name,
                    "type": "textarea" if inp.name == "textarea" else "text",
                    "question": question_for(inp) or inp.get("placeholder", ""),
                    "value": inp.get_text() if inp.name == "textarea" else inp.get("value", ""),
                    "disabled": disabled,
                }
            )

    has_submit = form.find(["button", "input"], type="submit") is not None or form.find("button") is not None
    page_text = soup.get_text(" ").lower()
    already = "bereits abgestimmt" in page_text or "bereits teilgenommen" in page_text or "ihre antwort wurde" in page_text

    return {
        "title": title,
        "description": "\n\n".join(desc_parts),
        "fields": fields,
        "hidden": hidden,
        "action": action,
        "locked": (not fields) or any_disabled or not has_submit or already,
        "attachments": _attachments(form, base_url),
    }


def parse_messages(html: str, category: str) -> list[Item]:
    """meldungen/kommunikation_fachlehrer e meldungen/kommunikation (elenco)."""
    soup = BeautifulSoup(html, PARSER)
    items: list[Item] = []
    for row in soup.select("tr.message-row, table tbody tr[onclick]"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 3:
            continue
        onclick = row.get("onclick", "")
        nums = re.findall(r"\d+", onclick)
        texts = [_clean(c.get_text()) for c in cells]
        sent = None
        for t in reversed(texts):
            sent = _parse_datetime(t)
            if sent:
                break
        sender = texts[0]
        subject = texts[2] if len(texts) > 3 else texts[1]
        unread = bool(row.find(class_=re.compile("unread|neu|new", re.I))) or "font-weight: bold" in (row.get("style") or "")
        items.append(
            Item(
                id=_stable_id(category, *nums) if nums else _stable_id(category, sender, subject, sent),
                category=category,
                title=subject,
                sender=sender,
                date=sent.isoformat() if sent else None,
                new=unread,
                extra={"path_ids": nums},
            )
        )
    return items


def parse_message_detail(html: str) -> str:
    soup = BeautifulSoup(html, PARSER)
    parts = [_text_with_breaks(seg) for seg in soup.select("#message-thread-grid div.ui.segment")]
    if not parts:
        parts = [_text_with_breaks(soup.select_one("#asam_content"))]
    return "\n\n———\n\n".join(p for p in parts if p)


_SUBJECT_RE = re.compile(r"\bin\s+([A-Za-zÄÖÜäöüß/ \-]+?)\s*(\(|$)")
_TEST_RE = re.compile(r"^(kLN|KA|StA|Ex|Test|Kurzarbeit|Stegreif)", re.I)


def exam_kind(title: str, css: str | None = None) -> str:
    css = (css or "").lower()
    if "important" in css:
        return "schulaufgabe"
    if "warning" in css:
        return "test"
    if re.match(r"^(SA|Schulaufgabe)\b", title.strip(), re.I) or "schulaufgabe" in title.lower():
        return "schulaufgabe"
    if _TEST_RE.match(title.strip()):
        return "test"
    return "altro"


def exam_subject(title: str) -> str | None:
    m = _SUBJECT_RE.search(title or "")
    return m[1].strip() if m else None


def parse_exam_list(html: str) -> list[Exam]:
    """service/termine/liste/schulaufgaben: tabella data | ora | titolo."""
    soup = BeautifulSoup(html, PARSER)
    exams: list[Exam] = []
    rows = soup.select("#asam_content .table2 tbody tr") or soup.select("#asam_content table tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        raw_date, raw_time, title = (_clean(c.get_text(" ")) for c in cells[:3])
        d = _parse_date(raw_date)
        if d is None or not title:
            continue
        t = _TIME_RE.search(raw_time or "")
        exams.append(
            Exam(
                id=_stable_id("sa", d, title),
                date=d.isoformat(),
                time=f"{int(t[1]):02d}:{t[2]}" if t else None,
                title=title,
                kind=exam_kind(title) if exam_kind(title) != "altro" else "schulaufgabe",
                subject=exam_subject(title),
            )
        )
    return exams


def parse_exam_json(data: dict[str, Any]) -> list[Exam]:
    """api/ws_get_termine.php → solo compiti (event-important / event-warning)."""
    exams: list[Exam] = []
    if not data or not data.get("success"):
        return exams
    for r in data.get("result", []):
        css = r.get("class", "")
        if "important" not in css and "warning" not in css:
            continue
        try:
            start = datetime.fromtimestamp(int(str(r["start"])[:10]))
        except (KeyError, ValueError):
            continue
        raw = (r.get("title_short") or r.get("title") or "").replace("<br />", "<br>")
        parts = [p for p in re.split(r"<br\s*/?>", raw) if p.strip()]
        time_txt = None
        if parts and _TIME_RE.match(parts[0].strip()):
            time_txt = _TIME_RE.match(parts[0].strip())
            parts = parts[1:]
        title = _clean(BeautifulSoup(" ".join(parts) or raw, PARSER).get_text())
        exams.append(
            Exam(
                id=_stable_id("sa", start.date(), title),
                date=start.date().isoformat(),
                time=f"{int(time_txt[1]):02d}:{time_txt[2]}" if time_txt else (
                    start.strftime("%H:%M") if (start.hour or start.minute) else None
                ),
                title=title,
                kind=exam_kind(title, css),
                subject=exam_subject(title),
            )
        )
    return exams


# ---------------------------------------------------------------------------
# Client con sessione
# ---------------------------------------------------------------------------
class PortalClient:
    def __init__(self, school: str, username: str, password: str, child: str = "") -> None:
        school = school.lower().strip().removeprefix("https://").removeprefix("http://")
        school = school.split("/")[0].removesuffix(".eltern-portal.org")
        self.school = school
        self.base_url = f"https://{school}.eltern-portal.org/"
        self.username = username.strip()
        self.password = password
        self.child_hint = child.strip().lower()
        self.school_name: str | None = None
        self.students: list[dict[str, str]] = []
        self.student: dict[str, str] | None = None
        self._session: requests.Session | None = None
        self._logged_at = 0.0
        self._lock = threading.RLock()

    # -- sessione -----------------------------------------------------------
    def _new_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9"})
        return s

    def login(self) -> None:
        with self._lock:
            s = self._new_session()
            r = s.get(self.base_url, timeout=20)
            r.raise_for_status()
            if "existiert nicht" in r.text:
                raise PortalError(f"Il portale {self.base_url} non esiste")
            csrf, school_name = parse_login_page(r.text)
            if not csrf:
                raise PortalError("Pagina di login senza token csrf (portale in manutenzione?)")
            self.school_name = school_name
            r = s.post(
                urljoin(self.base_url, "includes/project/auth/login.php"),
                data={"csrf": csrf, "username": self.username, "password": self.password, "go_to": ""},
                timeout=20,
            )
            r.raise_for_status()
            students = parse_students(r.text)
            if not students:
                raise LoginError("Login non riuscito: controlla email e password del portale")
            self.students = students
            chosen = students[0]
            if self.child_hint:
                for st in students:
                    if self.child_hint in st["name"].lower():
                        chosen = st
                        break
            self.student = chosen
            s.post(urljoin(self.base_url, f"api/set_child.php?id={chosen['id']}"), timeout=20)
            self._session = s
            self._logged_at = time.time()

    def _ensure(self) -> requests.Session:
        # le sessioni PHP scadono: rifacciamo il login ogni 15 minuti
        if self._session is None or time.time() - self._logged_at > 15 * 60:
            self.login()
        return self._session  # type: ignore[return-value]

    def _get(self, path: str, **kw: Any) -> requests.Response:
        with self._lock:
            s = self._ensure()
            r = s.get(urljoin(self.base_url, path.lstrip("/")), timeout=25, **kw)
            is_page = not path.lstrip("/").startswith(("api/", "aktuelles/get_file"))
            if is_page and r.headers.get("Content-Type", "").startswith("text/html") and not is_logged_in(r.text):
                self.login()
                r = self._session.get(urljoin(self.base_url, path.lstrip("/")), timeout=25, **kw)  # type: ignore[union-attr]
            r.raise_for_status()
            return r

    def _post(self, url: str, data: Any) -> requests.Response:
        with self._lock:
            s = self._ensure()
            r = s.post(url, data=data, timeout=25)
            r.raise_for_status()
            return r

    # -- lettura -----------------------------------------------------------
    def letters(self) -> list[Item]:
        return parse_letters(self._get("aktuelles/elternbriefe").text, self.base_url)

    def blackboard(self) -> list[Item]:
        return parse_blackboard(self._get("aktuelles/schwarzes_brett").text, self.base_url)

    def polls(self) -> list[Item]:
        return parse_polls(self._get("aktuelles/umfragen").text, self.base_url)

    def messages(self) -> list[Item]:
        out: list[Item] = []
        for path, cat in (
            ("meldungen/kommunikation", "klassenleitung"),
            ("meldungen/kommunikation_fachlehrer", "fachlehrer"),
        ):
            try:
                items = parse_messages(self._get(path).text, cat)
            except requests.HTTPError:
                continue
            for it in items[:15]:
                ids = it.extra.get("path_ids") or []
                if len(ids) >= 2:
                    try:
                        it.body = parse_message_detail(self._get(f"{path}/{ids[0]}/{ids[1]}").text)
                    except requests.HTTPError:
                        pass
            out.extend(items)
        return out

    def exams(self, months_ahead: int = 6) -> list[Exam]:
        found: dict[str, Exam] = {}
        try:
            for e in parse_exam_list(self._get("service/termine/liste/schulaufgaben").text):
                found[e.id] = e
        except requests.HTTPError:
            pass
        # API del calendario: copre anche i "kleine Leistungsnachweise"
        today = date.today()
        start_year = today.year if today.month >= 8 else today.year - 1
        frm = int(datetime(start_year, 8, 1).timestamp() * 1000)
        to = int((datetime.now() + timedelta(days=31 * months_ahead)).timestamp() * 1000)
        try:
            r = self._get("api/ws_get_termine.php", params={"from": frm, "to": to, "utc_offset": -60})
            for e in parse_exam_json(r.json()):
                if e.id not in found and not any(
                    x.date == e.date and (x.subject and x.subject == e.subject) for x in found.values()
                ):
                    found[e.id] = e
        except (requests.HTTPError, ValueError):
            pass
        return sorted(found.values(), key=lambda e: (e.date, e.time or ""))

    def poll_form(self, href: str) -> dict[str, Any]:
        return parse_poll_form(self._get(href).text, self.base_url)

    # -- azioni ------------------------------------------------------------
    def confirm_letter(self, letter_id: str) -> bool:
        if not re.fullmatch(r"\d+", letter_id):
            raise PortalError("id lettera non valido")
        self._get(f"api/elternbrief_bestaetigen.php?eb={letter_id}")
        # verifica sullo stato reale
        for it in self.letters():
            if it.id == letter_id:
                return not it.new
        return True

    def submit_poll(self, href: str, answers: dict[str, Any]) -> dict[str, Any]:
        form = self.poll_form(href)
        if form["locked"] or not form["action"]:
            raise PortalError("Questo sondaggio non accetta più risposte")
        allowed = {f["name"]: f for f in form["fields"]}
        data: list[tuple[str, str]] = list(form["hidden"].items())
        for name, value in answers.items():
            f = allowed.get(name)
            if f is None:
                continue
            values = value if isinstance(value, list) else [value]
            if f["type"] in ("radio", "checkbox", "select"):
                valid = {o["value"] for o in f["options"]}
                values = [v for v in values if v in valid]
            for v in values:
                data.append((name, str(v)))
        r = self._post(form["action"], data)
        text = BeautifulSoup(r.text, PARSER).get_text(" ")
        return {"ok": True, "message": _clean(text)[:300]}
