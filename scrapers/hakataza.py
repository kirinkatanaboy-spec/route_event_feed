"""博多座（hakataza.co.jp/lineup/）。

event_service.dart の _fetchHakataza / _parseHakatazaHtml を移植。
ロングラン公演は日毎に展開。開演時刻はページに無いため None。
"""
from __future__ import annotations

import datetime as _dt

from model import Event, GENRE_CONCERT
from venues import HAKATAZA
from .base import http_get, soup_of, flatten_ws, expand_jp_date_range


def fetch() -> list[Event]:
    resp = http_get("https://www.hakataza.co.jp/lineup/", accept="text/html,*/*")
    return _parse(resp.text)


def _parse(html: str) -> list[Event]:
    doc = soup_of(html)
    events: list[Event] = []
    today = _dt.date.today()
    for box in doc.select(".showcase__box"):
        sched = box.select_one(".showcase__schedule")
        if sched is None:
            continue
        dates = expand_jp_date_range(sched.get_text(), today)
        if not dates:
            continue
        main_el = box.select_one(".showcase__title-main")
        title_el = box.select_one(".showcase__title")
        title = flatten_ws(
            (main_el.get_text() if main_el else (title_el.get_text() if title_el else "")))
        if not title:
            continue
        for d in dates:
            events.append(Event(
                venue=HAKATAZA, date=d, title=title,
                genre=GENRE_CONCERT, start_hour=None, start_minute=None,
            ))
    return events
