"""横浜アリーナ（yokohama-arena.co.jp/event/YYYYMM?_format=json）。

月別 JSON API。配列で各要素は
  {date1, date2, category, title, ev_open:[...], ev_start:[...], path, ...}。
date1〜date2 を日毎展開。ev_start は ["18:30"] または ["①12:30","②17:30"]
（丸数字付き＝昼夜2公演）→ 最初の時刻を採用。ジャンルは guess_genre。
"""
from __future__ import annotations

import datetime as _dt
import json
import re

from model import Event, guess_genre
from venues import YOKOHAMA_ARENA
from .base import http_get, flatten_ws

_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
_DATE_RE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
_MAX_SPAN_DAYS = 14


def fetch() -> list[Event]:
    today = _dt.date.today()
    events: list[Event] = []
    seen: set[tuple] = set()
    for month_offset in range(4):  # 今月〜+3ヶ月
        y, m = _add_months(today.year, today.month, month_offset)
        url = f"https://www.yokohama-arena.co.jp/event/{y}{m:02d}?_format=json"
        try:
            resp = http_get(url, accept="application/json,*/*")
        except Exception:
            continue
        for ev in _parse(resp.text, today):
            key = (ev.date, ev.title)
            if key in seen:
                continue
            seen.add(key)
            events.append(ev)
    return events


def _parse(body: str, today: _dt.date) -> list[Event]:
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError:
        return []
    if not isinstance(decoded, list):
        return []
    events: list[Event] = []
    for raw in decoded:
        if not isinstance(raw, dict):
            continue
        title = flatten_ws(str(raw.get("title", "")))
        if not title:
            continue
        start = _parse_date(str(raw.get("date1", "")))
        if start is None:
            continue
        end = _parse_date(str(raw.get("date2", ""))) or start
        if end < start:
            end = start
        if (end - start).days > _MAX_SPAN_DAYS:
            end = start
        hh = mm = None
        starts = raw.get("ev_start")
        if isinstance(starts, list) and starts:
            tm = _TIME_RE.search(str(starts[0]))
            if tm:
                hh, mm = int(tm.group(1)), int(tm.group(2))
        genre = guess_genre(title)
        d = start
        while d <= end:
            if d >= today:
                events.append(Event(
                    venue=YOKOHAMA_ARENA, date=d, title=title,
                    genre=genre, start_hour=hh, start_minute=mm,
                ))
            d += _dt.timedelta(days=1)
    return events


def _parse_date(s: str) -> _dt.date | None:
    m = _DATE_RE.match(s)
    if not m:
        return None
    try:
        return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.start_hour, e.genre, e.title)
