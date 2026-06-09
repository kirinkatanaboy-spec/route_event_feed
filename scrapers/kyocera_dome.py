"""京セラドーム大阪（kyoceradome-osaka.jp/schedule/?yearId=YYYY&monthId=M）。

静的HTML・月別。各イベントは id="event2026-06-09" のブロック:
  カテゴリ `.top span`（野球 / コンサート / 販売・展示・その他）、
  タイトル `h2`、
  日時 `.btm li.date`（"…開始時間：18:00…"）。
野球→sports、コンサート→concert、展示系→exhibition、他は guess_genre。
"非公開イベント"（関係者のみ）は観客需要が無いため除外。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import (
    Event, GENRE_SPORTS, GENRE_CONCERT, GENRE_EXHIBITION, guess_genre,
)
from venues import KYOCERA_DOME
from .base import http_get, soup_of, flatten_ws

_ID_RE = re.compile(r"event(\d{4})-(\d{1,2})-(\d{1,2})")
_START_RE = re.compile(r"開始時間：(\d{1,2}):(\d{2})")


def fetch() -> list[Event]:
    today = _dt.date.today()
    events: list[Event] = []
    seen: set[tuple] = set()
    for month_offset in range(4):  # 今月〜+3ヶ月
        y, m = _add_months(today.year, today.month, month_offset)
        url = f"https://www.kyoceradome-osaka.jp/schedule/?yearId={y}&monthId={m}&cat="
        try:
            resp = http_get(url, accept="text/html,*/*")
        except Exception:
            continue
        for ev in _parse(resp.text, today):
            key = (ev.date, ev.title)
            if key in seen:
                continue
            seen.add(key)
            events.append(ev)
    return events


def _parse(html: str, today: _dt.date) -> list[Event]:
    doc = soup_of(html)
    events: list[Event] = []
    for block in doc.select('[id^="event"]'):
        m = _ID_RE.match(block.get("id", ""))
        if not m:
            continue
        try:
            d = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if d < today:
            continue
        h2 = block.select_one("h2")
        title = flatten_ws(h2.get_text() if h2 else "")
        if not title or "非公開" in title:
            continue
        cat_el = block.select_one(".top span")
        cat = flatten_ws(cat_el.get_text() if cat_el else "")
        if cat == "野球":
            genre = GENRE_SPORTS
        elif cat == "コンサート":
            genre = GENRE_CONCERT
        elif "展示" in cat:
            genre = GENRE_EXHIBITION
        else:
            genre = guess_genre(title)
        hh = mm = None
        dl = block.select_one(".btm li.date")
        if dl is not None:
            tm = _START_RE.search(dl.get_text())
            if tm:
                hh, mm = int(tm.group(1)), int(tm.group(2))
        events.append(Event(
            venue=KYOCERA_DOME, date=d, title=title,
            genre=genre, start_hour=hh, start_minute=mm,
        ))
    return events


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.start_hour, e.genre, e.title)
