"""福岡市民ホール（fukuoka-civic-hall.jp/event/）。

event_service.dart の _fetchCivicHall / _parseCivicHallHtml を移植。
1〜3ページを取得し、日付＋タイトルで重複除去。年表記が無いため推定。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, guess_genre, resolve_year
from venues import FUKUOKA_CIVIC_HALL
from .base import http_get, soup_of, flatten_ws

_DATE_RE = re.compile(r"(\d{1,2})月\s*(\d{1,2})日")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*開演")


def fetch() -> list[Event]:
    out: list[Event] = []
    seen = set()
    for n in (1, 2, 3):
        url = ("https://www.fukuoka-civic-hall.jp/event/" if n == 1
               else f"https://www.fukuoka-civic-hall.jp/event/?paged={n}")
        try:
            resp = http_get(url, accept="text/html,*/*")
        except Exception:
            continue
        for e in _parse(resp.text):
            key = f"{e.date.isoformat()}|{e.title}"
            if key in seen:
                continue
            seen.add(key)
            out.append(e)
    return out


def _parse(html: str) -> list[Event]:
    doc = soup_of(html)
    events: list[Event] = []
    today = _dt.date.today()
    for item in doc.select(".event-item"):
        title_el = item.select_one("h2")
        title = flatten_ws(title_el.get_text() if title_el else "")
        if not title:
            continue
        date_text = None
        for dl in item.select("dl"):
            dt_el = dl.select_one("dt")
            if dt_el and "開催日" in dt_el.get_text():
                dd = dl.select_one("dd")
                date_text = dd.get_text() if dd else None
                break
        if date_text is None:
            info = item.select_one(".event-info")
            date_text = info.get_text() if info else None
        if date_text is None:
            continue
        dm = _DATE_RE.search(date_text)
        if not dm:
            continue
        date = resolve_year(int(dm.group(1)), int(dm.group(2)), today)
        if date < today:
            continue
        hh = mm = None
        tm = _TIME_RE.search(date_text)
        if tm:
            hh, mm = int(tm.group(1)), int(tm.group(2))
        events.append(Event(
            venue=FUKUOKA_CIVIC_HALL, date=date, title=title,
            genre=guess_genre(title), start_hour=hh, start_minute=mm,
        ))
    return events
