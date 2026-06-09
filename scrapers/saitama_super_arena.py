"""さいたまスーパーアリーナ（saitama-arena.co.jp/schedule/YYYY/MM/）。

静的HTML・月別。各イベントは `dl.date > dd`（"2026/06/05(金) ～ 2026/07/05(日)"）
と `h3 > a`（タイトル）を持つ。ブロックの class は [ジャンル, 場所] の形:
  ジャンル= concert-show / exhibition / meeting-ceremony / sports / other
  場所= keyaki-plaza（屋外けやき広場）/ toiro（シェアオフィス）/ 無し（アリーナ本体）
けやき広場・TOIRO は需要分散・常設のため除外し、アリーナ本体の催事のみ採用する。
開演時刻はページに無いため None。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import (
    Event, GENRE_CONCERT, GENRE_EXHIBITION, GENRE_SPORTS, GENRE_OTHER,
    guess_genre,
)
from venues import SAITAMA_SUPER_ARENA
from .base import http_get, soup_of, flatten_ws

_DATE_RE = re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})")
_EXCLUDE_LOCATIONS = {"keyaki-plaza", "toiro"}
_GENRE_BY_CLASS = {
    "concert-show": GENRE_CONCERT,
    "exhibition": GENRE_EXHIBITION,
    "sports": GENRE_SPORTS,
    "meeting-ceremony": GENRE_OTHER,
}
_MAX_SPAN_DAYS = 40  # これを超える長期催事は開始日のみ（常設・展示の全日展開を防ぐ）


def fetch() -> list[Event]:
    today = _dt.date.today()
    events: list[Event] = []
    seen: set[tuple] = set()
    for month_offset in range(4):  # 今月〜+3ヶ月
        y, m = _add_months(today.year, today.month, month_offset)
        url = f"https://www.saitama-arena.co.jp/schedule/{y}/{m:02d}/"
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
    for dl in doc.select("dl.date"):
        block = dl.find_parent("li") or dl.find_parent("div")
        if block is None:
            continue
        classes = block.get("class") or []
        if any(c in _EXCLUDE_LOCATIONS for c in classes):
            continue
        dd = dl.select_one("dd")
        if dd is None:
            continue
        dates = _expand_slash_range(dd.get_text(), today)
        if not dates:
            continue
        h3 = block.find("h3")
        title = flatten_ws(h3.get_text() if h3 else "")
        if not title:
            continue
        genre = None
        for c in classes:
            if c in _GENRE_BY_CLASS:
                genre = _GENRE_BY_CLASS[c]
                break
        if genre is None:
            genre = guess_genre(title)
        for d in dates:
            events.append(Event(
                venue=SAITAMA_SUPER_ARENA, date=d, title=title,
                genre=genre, start_hour=None, start_minute=None,
            ))
    return events


def _expand_slash_range(src: str, today: _dt.date) -> list[_dt.date]:
    """\"YYYY/MM/DD(曜) ～ YYYY/MM/DD(曜)\" を日付リストへ展開。"""
    found = _DATE_RE.findall(src)
    if not found:
        return []
    try:
        start = _dt.date(int(found[0][0]), int(found[0][1]), int(found[0][2]))
    except ValueError:
        return []
    if len(found) >= 2:
        try:
            end = _dt.date(int(found[1][0]), int(found[1][1]), int(found[1][2]))
        except ValueError:
            end = start
    else:
        end = start
    if end < start:
        end = start
    if (end - start).days > _MAX_SPAN_DAYS:
        end = start  # 長期催事は開始日のみ
    out: list[_dt.date] = []
    d = start
    while d <= end:
        if d >= today:
            out.append(d)
        d += _dt.timedelta(days=1)
    return out


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.genre, e.title)
