"""東京国際フォーラム（t-i-forum.co.jp/visitors/event/?year=YYYY&month=M）。

静的HTML・月別カレンダー。各日付は `dl.p-news`:
  日付 `dt.p-news__pubdate`（aria-label=\"2026年6月1日\"）、
  その日の各イベントは `dd` 内の `div.p-eventTop_date_flex`:
    タイトル `.p-news__detail a span`（<br>区切りあり）。
\"※開催中止\"/\"※中止\" を含む公演は除外。開演時刻は一覧に無いため None。
多目的ホールのためジャンルは guess_genre 任せ。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, guess_genre
from venues import TOKYO_INTL_FORUM
from .base import http_get, soup_of, flatten_ws

_DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
_CANCEL_RE = re.compile(r"※\s*(開催中止|中止|開催延期)")


def fetch() -> list[Event]:
    today = _dt.date.today()
    events: list[Event] = []
    seen: set[tuple] = set()
    for month_offset in range(4):
        y, m = _add_months(today.year, today.month, month_offset)
        url = f"https://www.t-i-forum.co.jp/visitors/event/?year={y}&month={m}"
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
    for dl in doc.select("dl.p-news"):
        dt = dl.select_one(".p-news__pubdate")
        if dt is None:
            continue
        label = dt.get("aria-label", "") or dt.get_text()
        dm = _DATE_RE.search(label)
        if not dm:
            continue
        try:
            d = _dt.date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)))
        except ValueError:
            continue
        if d < today:
            continue
        for a in dl.select(".p-news__detail a"):
            span = a.select_one("span")
            title = flatten_ws(span.get_text(" ") if span else a.get_text(" "))
            if not title or _CANCEL_RE.search(title):
                continue
            events.append(Event(
                venue=TOKYO_INTL_FORUM, date=d, title=title,
                genre=guess_genre(title), start_hour=None, start_minute=None,
            ))
    return events


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.genre, e.title)
