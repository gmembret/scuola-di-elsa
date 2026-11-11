"""Argomento di una comunicazione, dedotto da parole chiave tedesche.

Si aggiunge alla sezione del portale (Elternbriefe, Schwarzes Brett, …) per
poter filtrare, ad esempio, tutto ciò che riguarda gite o verifiche.
"""

from __future__ import annotations

import re

TOPICS: list[tuple[str, str]] = [
    ("organizzazione", r"fundsach|verloren"),
    ("verifiche", r"schulaufgabe|klausur|prüfung|leistungsnachweis|stegreif|kurzarbeit|test\b|zeugnis|noten"),
    ("gite", r"ausflug|sporttag|wintersport|exkursion|klassenfahrt|fahrt|wandertag|skilager|schullandheim|austausch|museum|theater"),
    ("eventi", r"elternabend|elternsprech|sprechtag|sprechstunde|fest|feier|konzert|tag der offenen|veranstaltung|einladung|gottesdienst"),
    ("pagamenti", r"zahlung|bezahl|überweis|kosten|euro|€|beitrag|geld"),
    ("salute", r"krank|gesundheit|corona|impf|läuse|allerg|attest|erste hilfe"),
    ("orari", r"unterrichtsfrei|ferien|stundenplan|unterrichtsausfall|unterrichtsschluss|beginn|vertretung|streik|unterricht entfällt"),
    ("elezioni", r"wahl|elternbeirat|abstimmung|umfrage"),
    ("mensa", r"mensa|essen|verpflegung|kiosk"),
]

_COMPILED = [(name, re.compile(pat, re.I)) for name, pat in TOPICS]


def topic_of(title: str, body: str = "") -> str:
    head = title or ""
    for name, rx in _COMPILED:
        if rx.search(head):
            return name
    text = (body or "")[:1500]
    for name, rx in _COMPILED:
        if rx.search(text):
            return name
    return "organizzazione"
