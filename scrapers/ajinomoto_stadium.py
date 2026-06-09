"""味の素スタジアム（ajinomotostadium.com/schedule/YYYY/MM/）。

静的HTML・月別。各 `.scheduleBox`:
  日付 `.columnBlock01`（"06.06 土"、同日2件目以降は空→直前を引き継ぐ）、
  タイトル `.columnBlock03 h3`、
  アイコン `ul.icon li`（icon01=味の素スタジアム本体 / icon02=アミノバイタル
  フィールド〔サブ会場〕、iconA=競技/カテゴリ）。本スタジアム開催のみ採用。
開演時刻は基本無いため None。スポーツ系カテゴリは sports、他は guess_genre。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, GENRE_SPORTS, guess_genre
from venues import AJINOMOTO_STADIUM
from .base import http_get, soup_of, flatten_ws

_DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})")
_SPORTS_CATS = {"サッカー", "アメフト", "フットサル", "スポーツ", "ラグビー", "陸上", "野球"}


def fetch() -> list[Event]:
    today = _dt.date.today()
    events: list[Event] = []
    seen: set[tuple] = set()
    for month_offset in range(4):
        y, m = _add_months(today.year, today.month, month_offset)
        url = f"https://www.ajinomotostadium.com/schedule/{y}/{m:02d}/"
        try:
            resp = http_get(url, accept="text/html,*/*")
        except Exception:
            continue
        for ev in _parse(resp.text, y, m, today):
            key = (ev.date, ev.title)
            if key in seen:
                continue
            seen.add(key)
            events.append(ev)
    return events


def _parse(html: str, year: int, month: int, today: _dt.date) -> list[Event]:
    doc = soup_of(html)
    events: list[Event] = []
    last_day: int | None = None
    for box in doc.select(".scheduleBox"):
        col1 = box.select_one(".columnBlock01")
        if col1 is not None:
            dm = _DATE_RE.search(col1.get_text())
            if dm:
                last_day = int(dm.group(2))
        if last_day is None:
            continue
        # 場所アイコン: icon01=本スタジアム のみ採用
        if box.select_one("ul.icon li.icon01") is None:
            continue
        h3 = box.select_one(".columnBlock03 h3")
        title = flatten_ws(h3.get_text() if h3 else "")
        if not title:
            continue
        try:
            d = _dt.date(year, month, last_day)
        except ValueError:
            continue
        if d < today:
            continue
        cat_el = box.select_one("ul.icon li.iconA")
        cat = flatten_ws(cat_el.get_text() if cat_el else "")
        genre = GENRE_SPORTS if cat in _SPORTS_CATS else guess_genre(title)
        events.append(Event(
            venue=AJINOMOTO_STADIUM, date=d, title=title,
            genre=genre, start_hour=None, start_minute=None,
        ))
    return events


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.genre, e.title)
