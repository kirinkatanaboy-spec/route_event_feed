"""東京ドーム（tokyo-dome.co.jp/dome/event/schedule.html）。

静的HTMLのカレンダー。月ごとに `.c-mod-tab__body` があり、見出し
`.c-ttl-set-calender`（"2026年06月"）で年月が確定する。各日は
`tr.c-mod-calender__item`、日番号は最初の `.c-mod-calender__day`。
1日に複数イベントがあり各 `.c-mod-calender__detail-in` が1件:
  タグ `.c-txt-tag__item`（野球/コンサート/イベント）、
  タイトル `.c-mod-calender__links a`、
  時刻 `.c-txt-caption-01`（"開場 15:00／開演 17:00"）。
"TOKYO DOME TOUR"（/dome/visit/）は常設の見学案内バナーなので除外。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, GENRE_SPORTS, GENRE_CONCERT, guess_genre
from venues import TOKYO_DOME
from .base import http_get, soup_of, flatten_ws

_MONTH_RE = re.compile(r"(\d{4})年(\d{1,2})月")
_START_RE = re.compile(r"(?:開演|開始)\s*(\d{1,2}):(\d{2})")
_BANNER_TITLES = {"TOKYO DOME TOUR"}


def fetch() -> list[Event]:
    resp = http_get(
        "https://www.tokyo-dome.co.jp/dome/event/schedule.html",
        accept="text/html,*/*",
    )
    return _parse(resp.text)


def _parse(html: str) -> list[Event]:
    doc = soup_of(html)
    events: list[Event] = []
    today = _dt.date.today()
    for body in doc.select(".c-mod-tab__body"):
        ttl = body.select_one(".c-ttl-set-calender")
        if ttl is None:
            continue
        m = _MONTH_RE.search(ttl.get_text())
        if not m:
            continue
        year, month = int(m.group(1)), int(m.group(2))
        for tr in body.select("tr.c-mod-calender__item"):
            day_el = tr.select_one(".c-mod-calender__day")
            if day_el is None:
                continue
            try:
                day = int(re.sub(r"\D", "", day_el.get_text()) or "0")
            except ValueError:
                continue
            try:
                d = _dt.date(year, month, day)
            except ValueError:
                continue
            if d < today:
                continue
            for block in tr.select(".c-mod-calender__detail-in"):
                link = block.select_one(".c-mod-calender__links a")
                title = flatten_ws(link.get_text() if link else "")
                if not title or title in _BANNER_TITLES:
                    continue
                tag_el = block.select_one(".c-txt-tag__item")
                tag = flatten_ws(tag_el.get_text() if tag_el else "")
                if tag == "野球":
                    genre = GENRE_SPORTS
                elif tag == "コンサート":
                    genre = GENRE_CONCERT
                else:
                    genre = guess_genre(title, is_dome=True)
                hh = mm = None
                for cap in block.select(".c-txt-caption-01"):
                    tm = _START_RE.search(cap.get_text())
                    if tm:
                        hh, mm = int(tm.group(1)), int(tm.group(2))
                        break
                events.append(Event(
                    venue=TOKYO_DOME, date=d, title=title,
                    genre=genre, start_hour=hh, start_minute=mm,
                ))
    return events


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.start_hour, e.genre, e.title)
