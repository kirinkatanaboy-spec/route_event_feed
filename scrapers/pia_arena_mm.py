"""ぴあアリーナMM（横浜みなとみらい）公式イベントカレンダー。

月別ページ `https://pia-arena-mm.jp/event@p1=YYYY&p2=MM.html` の静的HTML。
各公演は `a.event-list` で、テキストは "MM.DD WD タイトル"（WD=曜日3文字）。
"PRIVATE"（非公開貸切・公演名なし）は除外する。今月から数ヶ月先まで巡回。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, guess_genre
from venues import PIA_ARENA_MM
from .base import http_get, soup_of, flatten_ws

_ITEM_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\s+[A-Z]{3}\s+(.+)$")


def fetch() -> list[Event]:
    today = _dt.date.today()
    events: list[Event] = []
    seen: set[tuple] = set()
    for offset in range(5):
        y, m = _add_months(today.year, today.month, offset)
        url = f"https://pia-arena-mm.jp/event@p1={y}&p2={m:02d}.html"
        try:
            resp = http_get(url, accept="text/html,*/*")
        except Exception:
            continue
        for ev in _parse(resp.text, y, m, today):
            key = ev.dedup_key()
            if key in seen:
                continue
            seen.add(key)
            events.append(ev)
    return events


def _parse(html: str, year: int, page_month: int, today: _dt.date) -> list[Event]:
    doc = soup_of(html)
    events: list[Event] = []
    for a in doc.select("a.event-list"):
        text = flatten_ws(a.get_text(" ", strip=True))
        mm = _ITEM_RE.match(text)
        if not mm:
            continue
        month, day = int(mm.group(1)), int(mm.group(2))
        title = mm.group(3).strip()
        if not title or title.upper().startswith("PRIVATE"):
            continue
        # ページ月と項目月が食い違う場合（年跨ぎ）は年を補正
        yr = year
        if month < page_month:
            yr = year + 1
        try:
            date = _dt.date(yr, month, day)
        except ValueError:
            continue
        if date < today:
            continue
        events.append(Event(
            venue=PIA_ARENA_MM, date=date, title=title,
            genre=guess_genre(title), start_hour=None, start_minute=None,
        ))
    return events


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.venue.key, e.title)
