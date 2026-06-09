"""日産スタジアム（nissan-stadium.jp/calendar/）。

静的HTMLカレンダー（当月のみ公開）。`h3` が "2026年6月"。各 `tr` が1日で、
`th` 日番号、`img title`（サッカー/ラグビー/スポーツ以外のイベント…）、
`a[href^=detail]` タイトル、`td.sub2` 開催場所。複数イベント日は2行目以降の
日番号 th が空なので直前の日を引き継ぐ。サブ会場（日産フィールド小机等）は
需要が小さいため本スタジアム開催のみ採用。開演時刻は無いため None。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, GENRE_SPORTS, guess_genre
from venues import NISSAN_STADIUM
from .base import http_get, soup_of, flatten_ws

_MONTH_RE = re.compile(r"(\d{4})年(\d{1,2})月")
_MAIN_VENUE = "日産スタジアム"


def fetch() -> list[Event]:
    resp = http_get("https://www.nissan-stadium.jp/calendar/", accept="text/html,*/*")
    return _parse(resp.text)


def _parse(html: str) -> list[Event]:
    doc = soup_of(html)
    today = _dt.date.today()
    h3 = doc.find("h3")
    m = _MONTH_RE.search(h3.get_text()) if h3 else None
    if not m:
        return []
    year, month = int(m.group(1)), int(m.group(2))
    events: list[Event] = []
    last_day: int | None = None
    for tr in doc.select("tr"):
        th = tr.find("th")
        if th is not None:
            dtxt = re.sub(r"\D", "", th.get_text())
            if dtxt:
                last_day = int(dtxt)
        a = tr.select_one('a[href^="detail"]')
        if a is None or last_day is None:
            continue
        loc_el = tr.select_one("td.sub2")
        loc = flatten_ws(loc_el.get_text() if loc_el else "")
        if loc != _MAIN_VENUE:
            continue
        title = flatten_ws(a.get_text())
        if not title:
            continue
        try:
            d = _dt.date(year, month, last_day)
        except ValueError:
            continue
        if d < today:
            continue
        img = tr.find("img")
        icon = (img.get("title") if img else "") or ""
        if "スポーツ以外" in icon:
            genre = guess_genre(title)
        else:
            genre = GENRE_SPORTS  # サッカー/ラグビー/陸上 等
        events.append(Event(
            venue=NISSAN_STADIUM, date=d, title=title,
            genre=genre, start_hour=None, start_minute=None,
        ))
    return events


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.genre, e.title)
