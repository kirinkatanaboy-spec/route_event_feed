"""Kアリーナ横浜（k-arena.com/schedule/）。

静的HTML・1ページに全公演。各 `.schedule-list-item`:
  日付 `.schedule-list-item__date`（"2026.06.02.Tue."）、
  タイトル `.schedule-list-item__title`、
  時刻 `.schedule-list-item__open-start`（"OPEN 17:30 / START 19:00"）→ START を採用。
ジャンルは guess_genre（大半がコンサート）。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, guess_genre
from venues import K_ARENA
from .base import http_get, soup_of, flatten_ws

_DATE_RE = re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})")
_START_RE = re.compile(r"START\s*(\d{1,2}):(\d{2})")


def fetch() -> list[Event]:
    resp = http_get("https://k-arena.com/schedule/", accept="text/html,*/*")
    return _parse(resp.text)


def _parse(html: str) -> list[Event]:
    doc = soup_of(html)
    events: list[Event] = []
    today = _dt.date.today()
    for item in doc.select(".schedule-list-item"):
        date_el = item.select_one(".schedule-list-item__date")
        if date_el is None:
            continue
        m = _DATE_RE.search(date_el.get_text())
        if not m:
            continue
        try:
            d = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if d < today:
            continue
        title_el = item.select_one(".schedule-list-item__title")
        title = flatten_ws(title_el.get_text() if title_el else "")
        if not title:
            continue
        hh = mm = None
        os_el = item.select_one(".schedule-list-item__open-start")
        if os_el is not None:
            tm = _START_RE.search(os_el.get_text())
            if tm:
                hh, mm = int(tm.group(1)), int(tm.group(2))
        events.append(Event(
            venue=K_ARENA, date=d, title=title,
            genre=guess_genre(title), start_hour=hh, start_minute=mm,
        ))
    return events


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.start_hour, e.genre, e.title)
