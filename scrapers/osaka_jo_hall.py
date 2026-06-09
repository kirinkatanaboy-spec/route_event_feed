"""大阪城ホール（osaka-johall.com/event/?ym=YYYYMM）。

静的HTML・月別。年月は見出し `.box-center.event-box .event-date`（\"2026年6月\"）。
各イベントは `ul.event-list-wrap > li.event-detail`:
  日 `.event-date .date-num`、タイトル `.event-name .event-ttl a`、
  ジャンル `li.event-genre`（\"音楽・芸能\"/\"スポーツ\"/\"物販・展示\"/\"集会・式典\"）、
  開演時刻 `.event-schedule .inner-list li`（`.d-ttl`=\"開演\" の隣 `.d-txt`）。
ジャンルラベルでスポーツ/コンサート/展示を判定、他は guess_genre。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, GENRE_SPORTS, GENRE_CONCERT, GENRE_EXHIBITION, guess_genre
from venues import OSAKA_JO_HALL
from .base import http_get, soup_of, flatten_ws

_YM_RE = re.compile(r"(\d{4})年(\d{1,2})月")
_DAY_RE = re.compile(r"(\d{1,2})")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


def fetch() -> list[Event]:
    today = _dt.date.today()
    events: list[Event] = []
    seen: set[tuple] = set()
    for month_offset in range(4):
        y, m = _add_months(today.year, today.month, month_offset)
        url = f"https://www.osaka-johall.com/event/?ym={y}{m:02d}"
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
    box = doc.select_one(".event-box")
    if box is None:
        return []
    head = box.select_one(".event-date")
    ym = _YM_RE.search(head.get_text() if head else "")
    if not ym:
        return []
    year, month = int(ym.group(1)), int(ym.group(2))
    events: list[Event] = []
    for li in box.select("ul.event-list-wrap > li.event-detail"):
        day_el = li.select_one(".event-date .date-num")
        dm = _DAY_RE.search(day_el.get_text() if day_el else "")
        if not dm:
            continue
        try:
            d = _dt.date(year, month, int(dm.group(1)))
        except ValueError:
            continue
        if d < today:
            continue
        ttl = li.select_one(".event-name .event-ttl a") or li.select_one(".event-name .event-ttl")
        title = flatten_ws(ttl.get_text() if ttl else "")
        if not title:
            continue
        genre_el = li.select_one("li.event-genre")
        label = flatten_ws(genre_el.get_text() if genre_el else "")
        if "スポーツ" in label:
            genre = GENRE_SPORTS
        elif "音楽" in label or "芸能" in label:
            genre = GENRE_CONCERT
        elif "展示" in label or "展覧" in label:
            genre = GENRE_EXHIBITION
        else:
            genre = guess_genre(title)
        hh = mm = None
        for d_li in li.select(".event-schedule .inner-list li"):
            d_ttl = d_li.select_one(".d-ttl")
            if d_ttl is not None and "開演" in d_ttl.get_text():
                d_txt = d_li.select_one(".d-txt")
                tm = _TIME_RE.search(d_txt.get_text() if d_txt else "")
                if tm:
                    hh, mm = int(tm.group(1)), int(tm.group(2))
                break
        events.append(Event(
            venue=OSAKA_JO_HALL, date=d, title=title,
            genre=genre, start_hour=hh, start_minute=mm,
        ))
    return events


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.start_hour, e.genre, e.title)
