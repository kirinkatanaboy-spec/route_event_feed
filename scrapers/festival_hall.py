"""フェスティバルホール（festivalhall.jp/events/、2ページ目以降は /events/page/N/）。

WordPress・日付昇順のページ送り（1ページ10公演）。各公演は
`ul.performance-list > li`:
  タイトル `h2._title a`、日時 `table.tbl-perform-info` の「日時」行 td
  （\"2026年6月9日（火） 12:30\"＝開演日時）。
音楽・演劇ホールのため guess_genre が other の場合は concert に寄せる。
先読み4ヶ月を超えたら（昇順なので）打ち切る。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, GENRE_OTHER, GENRE_CONCERT, guess_genre
from venues import FESTIVAL_HALL
from .base import http_get, soup_of, flatten_ws

_BASE = "https://www.festivalhall.jp/events/"
_DT_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日.*?(\d{1,2}):(\d{2})")
_DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
_MAX_PAGES = 13


def fetch() -> list[Event]:
    today = _dt.date.today()
    cy, cm = _add_months(today.year, today.month, 4)
    cutoff = _dt.date(cy, cm, 1)  # この月1日以降は対象外
    events: list[Event] = []
    seen: set[tuple] = set()
    for page in range(1, _MAX_PAGES + 1):
        url = _BASE if page == 1 else f"{_BASE}page/{page}/"
        try:
            resp = http_get(url, accept="text/html,*/*")
        except Exception:
            break
        page_events, reached_cutoff = _parse(resp.text, today, cutoff)
        for ev in page_events:
            key = (ev.date, ev.title)
            if key in seen:
                continue
            seen.add(key)
            events.append(ev)
        if reached_cutoff:
            break
    return events


def _parse(html: str, today: _dt.date, cutoff: _dt.date):
    doc = soup_of(html)
    events: list[Event] = []
    reached_cutoff = False
    for li in doc.select("ul.performance-list > li"):
        ttl = li.select_one("h2._title a") or li.select_one("h2._title")
        title = flatten_ws(ttl.get_text() if ttl else "")
        if not title:
            continue
        when = _datetime_cell(li)
        if when is None:
            continue
        dm = _DT_RE.search(when)
        hh = mm = None
        if dm:
            y, mo, da = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
            hh, mm = int(dm.group(4)), int(dm.group(5))
        else:
            d2 = _DATE_RE.search(when)
            if not d2:
                continue
            y, mo, da = int(d2.group(1)), int(d2.group(2)), int(d2.group(3))
        try:
            d = _dt.date(y, mo, da)
        except ValueError:
            continue
        if d >= cutoff:
            reached_cutoff = True
            continue
        if d < today:
            continue
        genre = guess_genre(title)
        if genre == GENRE_OTHER:
            genre = GENRE_CONCERT  # 音楽・演劇ホール
        events.append(Event(
            venue=FESTIVAL_HALL, date=d, title=title,
            genre=genre, start_hour=hh, start_minute=mm,
        ))
    return events, reached_cutoff


def _datetime_cell(li) -> str | None:
    for tr in li.select("table.tbl-perform-info tr"):
        th = tr.select_one("th")
        if th is not None and "日時" in th.get_text():
            td = tr.select_one("td")
            return flatten_ws(td.get_text()) if td else None
    return None


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.start_hour, e.genre, e.title)
