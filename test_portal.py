"""Test dei parser con HTML nel formato reale dell'Eltern-Portal.

Esegui con:  python -m pytest -q   (oppure  python tests/test_portal.py)
"""

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import portal as P  # noqa: E402
from app import translate as TR  # noqa: E402
from app.topics import topic_of  # noqa: E402

BASE = "https://kkgymuc.eltern-portal.org/"

# Formato reale (dalla demo ufficiale usata da pyelternportal)
LETTER_HTML = """<div id="asam_content">
<table class='table_header' width='100%' border='0'><tr><td>#1</td><td id='empf_1'>Empfang bestätigt.</td></tr>
<tr><td colspan='2'><span onclick='eb_bestaetigung(1);' class='link_nachrichten ' title='Empfang bestätigen'><h4>1. Klassenelternabend</h4> (keine Datei - Empfang durch Klick auf Titel bestätigen) 10.11.2026 18:05</span><br />
<span style='font-size: 8pt;'>Klasse/n: 5a</span><br />Erinnerung: Herzliche Einladung<br />Wir freuen uns auf Sie!</td></tr></table>
<table class='table_header'><tr><td>#2</td><td id='empf_77'>Empfang noch nicht bestätigt.</td></tr>
<tr><td colspan='2'><a href='aktuelles/get_file/?repo=77&csrf=abc' onclick='eb_bestaetigung(77);' class='link_nachrichten'><h4>Klassenfahrt 12.03.2027</h4> (Datei) 09.11.2026 07:30</a><br />
<span class='small text'>Klasse/n: 7a Klasse/n: 7b</span><br />Bitte lesen.</td></tr></table></div>"""


def test_letters():
    items = P.parse_letters(LETTER_HTML, BASE)
    assert [i.id for i in items] == ["1", "77"]
    a, b = items
    assert not a.new and a.title == "1. Klassenelternabend" and a.date == "2026-11-10T18:05:00"
    assert a.distribution == "5a" and "Herzliche Einladung" in a.body and "Wir freuen" in a.body
    assert b.new and b.can_confirm
    assert b.date == "2026-11-09T07:30:00"  # la data nel titolo non viene presa
    assert b.attachments[0]["href"] == BASE + "aktuelles/get_file/?repo=77&csrf=abc"


POLL_LIST = """<div id="asam_content"><div class="row m_bot">
<div class="col-xs-6"><a href="aktuelles/umfragen/2_0" class=" umf_list">Elternbeiratswahl</a></div>
<div class="col-xs-3 text-center"><span>01.01.2099</span></div>
<div class="col-xs-3 text-center"><span>05.11.2026<img src='/includes/project/images/haken.png' /></span></div></div>
<div class="row m_bot"><div class="col-xs-6"><a href="aktuelles/umfragen/5_0" class=" umf_list">Mensa</a></div>
<div class="col-xs-3 text-center"><span>01.01.2099</span></div><div class="col-xs-3 text-center"></div></div></div>"""


def test_polls():
    a, b = P.parse_polls(POLL_LIST, BASE)
    assert a.id == "2_0" and not a.new and a.extra["voted"] == "2026-11-05"
    assert b.id == "5_0" and b.new and b.extra["open"]


def test_poll_form_and_locked():
    html = """<div id='asam_content'><form class='form-horizontal' action='/includes/nachrichten_dir/umfragen_editor_db_ins.php' method='post'>
    <input type='hidden' name='csrf' value='x'><input type='hidden' name='UMF_ID' value='5'>
    <div class='form-group'><h3>Mensa</h3></div><div class='form-group'>Bitte abstimmen.</div>
    <div class='form-group'><label class='control-label'>Essen?</label><input type='radio' id='r1' name='a' value='1'><label for='r1'>Ja</label>
    <input type='radio' id='r2' name='a' value='0'><label for='r2'>Nein</label></div>
    <div class='form-group'><select name='s'><option value='x'>X</option></select></div>
    <button type='submit'>Absenden</button></form></div>"""
    f = P.parse_poll_form(html, BASE)
    assert f["action"].endswith("umfragen_editor_db_ins.php") and f["hidden"] == {"csrf": "x", "UMF_ID": "5"}
    assert f["fields"][0]["question"] == "Essen?" and [o["label"] for o in f["fields"][0]["options"]] == ["Ja", "Nein"]
    assert f["fields"][1]["type"] == "select" and not f["locked"] and "Bitte abstimmen" in f["description"]
    locked = P.parse_poll_form(html.replace("<button type='submit'>Absenden</button>", ""), BASE)
    assert locked["locked"]


def test_exams_list_and_json():
    html = """<div class="container"><div id="asam_content"><div class="row"><div class="no_padding_md"><table class="table2"><tbody>
    <tr><td>24.11.2026</td><td>08:00 - 09:30</td><td>SA in Mathematik</td></tr>
    <tr><td>Di., 01.12.2026</td><td></td><td>Schulaufgabe Deutsch</td></tr></tbody></table></div></div></div></div>"""
    e = P.parse_exam_list(html)
    assert [(x.date, x.time, x.subject, x.kind) for x in e] == [
        ("2026-11-24", "08:00", "Mathematik", "schulaufgabe"),
        ("2026-12-01", None, None, "schulaufgabe"),
    ]
    data = {"success": 1, "result": [
        {"id": "id_1", "title": "x", "title_short": "10:00 - 11:30<br />kLN in Englisch<br>", "class": "event-warning",
         "start": "1795161600000", "end": "1795161600000"},
        {"id": "id_2", "title": "Ferien", "title_short": "Ferien<br>", "class": "event-info", "start": "1795161600000", "end": "1"},
    ]}
    j = P.parse_exam_json(data)
    assert len(j) == 1 and j[0].kind == "test" and j[0].time == "10:00" and j[0].subject == "Englisch"


def test_messages_and_blackboard():
    msgs = P.parse_messages("""<table id="messages-fachlehrer-table"><tbody>
      <tr class="message-row" onclick="showMessageFachlehrer(12, 4)"><td>Hr. Maier</td><td>Mathe</td><td>Hausaufgaben</td><td>02.11.2026 13:10</td></tr>
      </tbody></table>""", "fachlehrer")
    assert msgs[0].sender == "Hr. Maier" and msgs[0].title == "Hausaufgaben" and msgs[0].extra["path_ids"] == ["12", "4"]
    bb = P.parse_blackboard("""<div id="asam_content"><div class="grid"><div class="grid-item"><div class="well">
      <p>eingestellt am 06.11.2026 09:12:00</p><h4>Fundsachen</h4><p>Bitte abholen.</p></div></div></div></div>""", BASE)
    assert len(bb) == 1 and bb[0].title == "Fundsachen" and bb[0].body == "Bitte abholen." and bb[0].date.startswith("2026-11-06")


def test_login_detection():
    assert P.parse_login_page("<form class='form-signin'><input name='csrf' value='abc'></form><h2 id='schule'>KKG</h2>") == ("abc", "KKG")
    assert P.parse_students("<div class='pupil-selector'><select><option value='9'>Elsa Rossi (7a)</option></select></div>") == [
        {"id": "9", "name": "Elsa Rossi (7a)"}]


def test_google_translate_response_format(tmp_path):
    TR._cache.clear()
    fake = mock.Mock()
    fake.json.return_value = [[["Cari genitori,\n", "Liebe Eltern,\n", None], ["grazie", "danke", None]], None, "de"]
    fake.raise_for_status.return_value = None
    with mock.patch.object(TR, "CACHE_FILE", tmp_path / "c.json"), mock.patch.object(TR.requests, "get", return_value=fake):
        assert TR.translate_many(["Liebe Eltern,\ndanke", ""], "it") == ["Cari genitori,\ngrazie", ""]


def test_topics():
    assert topic_of("Wandertag der 7. Klassen") == "gite"
    assert topic_of("Schulaufgabe Mathe verschoben") == "verifiche"
    assert topic_of("Fundsachen vor den Herbstferien") == "organizzazione"


if __name__ == "__main__":
    import tempfile
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(Path(tempfile.mkdtemp())) if "tmp_path" in fn.__code__.co_varnames else fn()
            print("ok", name)
