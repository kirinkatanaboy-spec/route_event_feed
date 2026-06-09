"""有明アリーナ（ariake-arena.tokyo/event/、翌月以降は /event/next/…）。

1ページ＝1ヶ月。`li.active .year` がそのページの年。各イベントは
`table.detail_table` の「公演時間」行 td に複数日が
"6.6 Sat 開場 15:00 / 開演 16:00"（<br>区切り）で並ぶ。タイトルは直前の
`.detail_top_content .event_name`（出演者名）を採用。特典会など日付の無い行は除外。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, GENRE_OTHER, GENRE_CONCERT, guess_genre
from venues import ARIAKE_ARENA
from .base import http_get, soup_of, flatten_ws

_BASE = "https://ariake-arena.tokyo/event/"
_LINE_DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})")
_KAIEN_RE = re.compile(r"開演[\s:：]*(\d{1,2})[:：](\d{2})")
_PAGES = 4  # 今月＋翌3ヶ月（/next/ を重ねる）


def fetch() -> list[Event]:
    today = _dt.date.today()
    events: list[Event] = []
    seen: set[tuple] = set()
    url = _BASE
    for _ in range(_PAGES):
        try:
            resp = http_get(url, accept="text/html,*/*")
        except Exception:
            break
        for ev in _parse(resp.text, today):
            key = (ev.date, ev.title)
            if key in seen:
                continue
            seen.add(key)
            events.append(ev)
        url = url.rstrip("/") + "/next/"
    return events


def _parse(html: str, today: _dt.date) -> list[Event]:
    doc = soup_of(html)
    year_el = doc.select_one("li.active .year")
    try:
        year = int(year_el.get_text(strip=True)) if year_el else today.year
    except ValueError:
        year = today.year
    events: list[Event] = []
    for tbl in doc.select("table.detail_table"):
        td = _time_cell(tbl)
        if td is None:
            continue
        title = _title_for(tbl)
        if not title:
            continue
        base_genre = guess_genre(title)
        for line in td.get_text("\n", strip=True).split("\n"):
            dm = _LINE_DATE_RE.search(line)
            if not dm:
                continue
            try:
                d = _dt.date(year, int(dm.group(1)), int(dm.group(2)))
            except ValueError:
                continue
            if d < today:
                continue
            hh = mm = None
            km = _KAIEN_RE.search(line)
            if km:
                hh, mm = int(km.group(1)), int(km.group(2))
            # アリーナの「開演」付き公演は概ねコンサート相当の需要（出演者名だけで
            # ジャンル判定できない場合のみ concert に寄せる。スポーツ等の判定は保持）。
            genre = base_genre
            if genre == GENRE_OTHER and km is not None:
                genre = GENRE_CONCERT
            events.append(Event(
                venue=ARIAKE_ARENA, date=d, title=title,
                genre=genre, start_hour=hh, start_minute=mm,
            ))
    return events


def _time_cell(tbl):
    for tr in tbl.select("tr"):
        th = tr.select_one("th")
        if th is not None and "公演時間" in th.get_text():
            return tr.select_one("td")
    return None


def _title_for(tbl) -> str:
    bottom = tbl.find_parent(class_="detail_bottom_content")
    top = bottom.find_previous(class_="detail_top_content") if bottom else None
    nm = top.select_one(".event_name") if top else None
    if nm is not None:
        t = flatten_ws(nm.get_text())
        if t:
            return t
    sub = bottom.select_one(".sub_title") if bottom else None
    return flatten_ws(sub.get_text()) if sub else ""


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.start_hour, e.genre, e.title)
