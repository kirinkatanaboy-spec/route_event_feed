"""IGアリーナ（愛知国際アリーナ・ig-arena.jp/events/）。

Next.js のストリーム payload 内に `initialEvents` がエスケープされた JSON で埋め込まれる。
各要素: {id, date:"2026年6月1日（月）"（・区切りで複数日）, title, monthKey:"2026-06", ...}。
HTML の \\" を " に戻してから正規表現で date/title/monthKey を抽出する。
開演時刻は無いため None。ジャンルは guess_genre。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, guess_genre
from venues import IG_ARENA
from .base import http_get

_OBJ_RE = re.compile(
    r'"date":"(?P<date>.*?)","title":"(?P<title>.*?)",'
    r'.*?"monthKey":"(?P<y>\d{4})-(?P<m>\d{2})"'
)
_YEAR_RE = re.compile(r"(\d{4})年")
_MD_RE = re.compile(r"(\d{1,2})月(\d{1,2})日")


def fetch() -> list[Event]:
    resp = http_get("https://www.ig-arena.jp/events/", accept="text/html,*/*")
    return _parse(resp.text)


def _parse(html: str) -> list[Event]:
    text = html.replace('\\"', '"').replace("\\\\", "\\")
    events: list[Event] = []
    today = _dt.date.today()
    seen: set[tuple] = set()
    for mo in _OBJ_RE.finditer(text):
        title = mo.group("title").strip()
        if not title:
            continue
        date_src = mo.group("date")
        fb_year = int(mo.group("y"))
        ym = _YEAR_RE.search(date_src)
        year = int(ym.group(1)) if ym else fb_year
        genre = guess_genre(title)
        for md in _MD_RE.finditer(date_src):
            try:
                d = _dt.date(year, int(md.group(1)), int(md.group(2)))
            except ValueError:
                continue
            if d < today:
                continue
            key = (d, title)
            if key in seen:
                continue
            seen.add(key)
            events.append(Event(
                venue=IG_ARENA, date=d, title=title,
                genre=genre, start_hour=None, start_minute=None,
            ))
    return events


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.genre, e.title)
