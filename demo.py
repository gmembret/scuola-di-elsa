"""Portale finto (PORTAL_SCHOOL=demo).

Restituisce pagine HTML con la stessa struttura dell'Eltern-Portal, così l'app
e tutti i parser si possono provare senza credenziali. Conferme e voti vengono
ricordati in memoria.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urljoin

from .portal import PortalClient

T = date.today()


def d(days: int) -> str:
    return (T + timedelta(days=days)).strftime("%d.%m.%Y")


LETTERS = [
    ("412", "Einladung zum Elternsprechabend", "05.11.2026 17:42",
     "Liebe Eltern,<br />am Donnerstag, " + d(9) + ", findet von 17:00 bis 20:00 Uhr der Elternsprechabend statt. "
     "Bitte buchen Sie Ihre Termine über das Eltern-Portal unter „Buchung Sprechstunde“.<br />Mit freundlichen Grüßen<br />Die Schulleitung", True),
    ("409", "Wandertag der 7. Klassen", "03.11.2026 08:15",
     "Sehr geehrte Eltern,<br />der Wandertag findet am " + d(4) + " statt. Treffpunkt ist um 8:00 Uhr am Ostbahnhof. "
     "Bitte geben Sie Ihrem Kind wetterfeste Kleidung, Brotzeit und 5 € für die Fahrkarte mit.", True),
    ("401", "Unterrichtsfreier Tag am Buß- und Bettag", "28.10.2026 12:00",
     "Am Mittwoch, 18.11.2026, ist unterrichtsfrei. Die Mittagsbetreuung findet nicht statt.", False),
    ("395", "Informationen zur Schulaufgabenplanung", "15.10.2026 10:30",
     "Die Termine der Schulaufgaben finden Sie ab sofort im Eltern-Portal unter Service → Schulaufgaben / Weitere Termine.", False),
]

POLL_LIST = """
<div id="asam_content"><div class="row"><div class="col-xs-12">
<div class="row m_bot"><div class="col-xs-6"><a href="aktuelles/umfragen/31_0" class=" umf_list">Teilnahme am Wintersporttag</a></div>
<div class="col-xs-3 text-center"><span>{end1}</span></div><div class="col-xs-3 text-center">{voted1}</div></div>
<div class="row m_bot"><div class="col-xs-6"><a href="aktuelles/umfragen/27_0" class=" umf_list">Elternbeiratswahl 2026/27</a></div>
<div class="col-xs-3 text-center"><span>{end2}</span></div><div class="col-xs-3 text-center"><span>20.10.2026<img src='/includes/project/images/haken.png' /></span></div></div>
</div></div></div>
"""

POLL_DETAIL = """
<div id="asam_content">
<form class='form-horizontal' action='/includes/nachrichten_dir/umfragen_editor_db_ins.php' method='post'>
<input type='hidden' name='csrf' value='demo'>
<div class='form-group'><div class='col-xs-12'><h3><span>Teilnahme am Wintersporttag</span></h3><input type='hidden' name='UMF_ID' value='31'></div></div>
<div class='form-group'><div class='col-xs-12'>Liebe Eltern,<br />am {day} findet der Wintersporttag am Spitzingsee statt. Bitte teilen Sie uns mit, ob Ihr Kind teilnimmt und welche Aktivität es wählt.</div></div>
<div class='form-group'><label class='control-label'>Nimmt Ihr Kind teil?</label>
<div><label><input type='radio' name='frage_1' value='1' {dis}> Ja, mein Kind nimmt teil</label><br />
<label><input type='radio' name='frage_1' value='2' {dis}> Nein, mein Kind nimmt nicht teil</label></div></div>
<div class='form-group'><label class='control-label'>Gewünschte Aktivität</label>
<div><label><input type='checkbox' name='frage_2[]' value='ski' {dis}> Ski alpin</label><br />
<label><input type='checkbox' name='frage_2[]' value='rodeln' {dis}> Rodeln</label><br />
<label><input type='checkbox' name='frage_2[]' value='wandern' {dis}> Winterwanderung</label></div></div>
<div class='form-group'><label class='control-label'>Bemerkungen (z. B. Allergien)</label><textarea name='bemerkung' {dis}></textarea></div>
{submit}
</form></div>
"""

BLACKBOARD = """
<div id="asam_content"><div class="grid">
<div class="grid-item"><div class="well"><p>eingestellt am 06.11.2026 09:12:00</p><h4>Fundsachen vor den Herbstferien</h4>
<p>Alle Fundsachen liegen bis Freitag vor dem Sekretariat aus. Danach werden sie gespendet.</p></div></div>
<div class="grid-item"><div class="well"><p>eingestellt am 30.10.2026 14:00:00</p><h4>Neuer Speiseplan der Mensa</h4>
<p>Der Speiseplan für November ist online. Anmeldung zum Mittagessen bis Donnerstag 12 Uhr.</p>
<p><a href="aktuelles/get_file/?repo=77&csrf=demo">Speiseplan_November.pdf</a></p></div></div>
</div></div>
"""

MESSAGES = """
<table id="messages-fachlehrer-table"><tbody>
<tr class="message-row" onclick="showMessageFachlehrer(55, 3)"><td>Fr. Huber</td><td>Englisch</td><td>Vokabeltest am Montag</td><td>09.11.2026 16:20</td></tr>
</tbody></table>
"""

MESSAGE_DETAIL = """
<div id="message-thread-grid"><div class="row"><div>Betreff</div><div>Vokabeltest am Montag</div></div>
<div class="row"><div>Nachricht</div><div><div class="ui segment">Liebe Eltern,<br>am Montag schreiben wir einen kurzen Vokabeltest zu Unit 2. Bitte erinnern Sie Elsa daran, die Vokabeln S. 204–206 zu wiederholen.<br>Viele Grüße<br>K. Huber</div></div></div></div>
"""

EXAM_LIST = """
<div class="container"><div id="asam_content"><div class="row"><div class="no_padding_md">
<table class="table2"><tbody>
<tr><td>{d1}</td><td>08:00 - 09:30</td><td>SA in Mathematik</td></tr>
<tr><td>{d2}</td><td>09:45 - 11:15</td><td>SA in Englisch</td></tr>
<tr><td>{d3}</td><td></td><td>SA in Deutsch</td></tr>
<tr><td>{d4}</td><td>11:30 - 12:15</td><td>SA in Latein</td></tr>
<tr><td>{d0}</td><td>08:00 - 09:30</td><td>SA in Biologie</td></tr>
</tbody></table></div></div></div></div>
"""


def letters_html(confirmed: set[str]) -> str:
    rows = []
    for lid, title, stamp, body, new in LETTERS:
        is_new = new and lid not in confirmed
        status = "Empfang noch nicht bestätigt." if is_new else "Empfang bestätigt."
        rows.append(
            f"<table class='table_header'><tr><td>#{lid[-2:]}</td><td id='empf_{lid}'>{status}</td></tr>"
            f"<tr><td colspan='2'><span onclick='eb_bestaetigung({lid});' class='link_nachrichten'>"
            f"<h4>{title}</h4> (keine Datei - Empfang durch Klick auf Titel bestätigen) {stamp}</span><br />"
            f"<span style='font-size: 8pt;'>Klasse/n: 7a</span><br />{body}</td></tr></table>"
        )
    return "<div id='asam_content'>" + "".join(rows) + "</div>"


class _Resp:
    def __init__(self, text: str = "", data: Any = None):
        self.text = text
        self._data = data
        self.headers = {"Content-Type": "application/json" if data is not None else "text/plain"}

    def json(self) -> Any:
        return self._data

    def raise_for_status(self) -> None:
        return None


class DemoPortal(PortalClient):
    def __init__(self) -> None:
        super().__init__("demo", "", "", "Elsa")
        self.school_name = "Städtisches Käthe-Kollwitz-Gymnasium München (DEMO)"
        self.student = {"id": "1", "name": "Elsa Rossi (7a)"}
        self.confirmed: set[str] = set()
        self.voted: dict[str, Any] = {}

    def login(self) -> None:  # nessuna rete
        return None

    def _get(self, path: str, **kw: Any) -> Any:
        p = path.lstrip("/")
        if p.startswith("aktuelles/elternbriefe"):
            return _Resp(letters_html(self.confirmed))
        if p.startswith("api/elternbrief_bestaetigen.php"):
            self.confirmed.add(p.split("eb=")[1])
            return _Resp("ok")
        if p == "aktuelles/umfragen":
            voted1 = (
                f"<span>{date.today().strftime('%d.%m.%Y')}<img src='/includes/project/images/haken.png' /></span>"
                if "31_0" in self.voted else ""
            )
            return _Resp(POLL_LIST.format(end1=d(6), end2=d(-15), voted1=voted1))
        if p.startswith("aktuelles/umfragen/31_0"):
            locked = "31_0" in self.voted
            return _Resp(POLL_DETAIL.format(
                day=d(30), dis="disabled" if locked else "",
                submit="" if locked else "<button type='submit' class='btn btn-primary'>Absenden</button>",
            ))
        if p.startswith("aktuelles/umfragen/27_0"):
            return _Resp("<div id='asam_content'><p>Vielen Dank, Sie haben bereits abgestimmt.</p></div>")
        if p.startswith("aktuelles/schwarzes_brett"):
            return _Resp(BLACKBOARD)
        if p == "meldungen/kommunikation_fachlehrer":
            return _Resp(MESSAGES)
        if p.startswith("meldungen/kommunikation_fachlehrer/"):
            return _Resp(MESSAGE_DETAIL)
        if p == "meldungen/kommunikation":
            return _Resp("<table><tbody></tbody></table>")
        if p.startswith("service/termine/liste/schulaufgaben"):
            return _Resp(EXAM_LIST.format(d0=d(-12), d1=d(3), d2=d(8), d3=d(15), d4=d(22)))
        if p.startswith("api/ws_get_termine.php"):
            ts = int(datetime.combine(T + timedelta(days=5), datetime.min.time()).timestamp()) * 1000
            return _Resp(data={"success": 1, "result": [
                {"id": "id_9", "title": "kLN in Französisch", "title_short": "kLN in Französisch<br>",
                 "class": "event-warning", "start": str(ts), "end": str(ts)},
                {"id": "id_10", "title": "Elternsprechabend", "title_short": "Elternsprechabend<br>",
                 "class": "event-info", "start": str(ts), "end": str(ts)},
            ]})
        return _Resp("<div id='asam_content'></div>")

    def _post(self, url: str, data: Any) -> Any:
        if "umfragen_editor_db_ins" in url:
            self.voted["31_0"] = data
            return _Resp("<div>Vielen Dank für Ihre Teilnahme!</div>")
        return _Resp("")

    @property
    def base(self) -> str:
        return urljoin(self.base_url, "")


if __name__ == "__main__":  # piccolo controllo manuale
    p = DemoPortal()
    print(json.dumps([i.to_dict() for i in p.letters()], indent=1, ensure_ascii=False)[:800])
