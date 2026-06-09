"""アビスパ福岡 ホーム試合（ベスト電器スタジアム）。

event_service.dart の _fetchAvispaHomeGames / _parseAvispaHtml を移植。
テーブルの6列目に「ベススタ」を含む行（ホーム試合）のみ採用。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, resolve_year, GENRE_SPORTS
from venues import BEST_DENKI_STADIUM
from .base import http_get, soup_of, flatten_ws

_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})\s*[（(]\s*[月火水木金土日]\s*[)）]")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


def fetch() -> list[Event]:
    resp = http_get("https://www.avispa.co.jp/game_practice/event",
                    accept="text/html,*/*")
    return _parse(resp.text)


def _parse(html: str) -> list[Event]:
    doc = soup_of(html)
    events: list[Event] = []
    today = _dt.date.today()
    for tr in doc.select("tr"):
        cells = tr.select("td")
        if len(cells) < 6:
            continue
        td = [flatten_ws(c.get_text()) for c in cells]
        if "ベススタ" not in td[5] and "ベスト電器" not in td[5]:
            continue
        dm = _DATE_RE.search(td[1])
        if not dm:
            continue
        date = resolve_year(int(dm.group(1)), int(dm.group(2)), today)
        if date < today:
            continue
        hh = mm = None
        tm = _TIME_RE.search(td[2])
        if tm:
            hh, mm = int(tm.group(1)), int(tm.group(2))
        opponent = td[3]
        title = f"アビスパ vs {opponent}" if opponent else "アビスパ ホーム試合"
        events.append(Event(
            venue=BEST_DENKI_STADIUM, date=date, title=title,
            genre=GENRE_SPORTS, start_hour=hh, start_minute=mm,
        ))
    return events
