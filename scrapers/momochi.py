"""SAWARAPIA（ももち文化センター・momochi-bunka.com/event/）。

event_service.dart の _fetchMomochi / _parseMomochiHtml を移植。
.article__item を走査し、開催日が無い記事（お知らせ等）はスキップ。
"""
from __future__ import annotations

import datetime as _dt

from model import Event, guess_genre
from venues import MOMOCHI_BUNKA
from .base import http_get, soup_of, flatten_ws, expand_jp_date_range


def fetch() -> list[Event]:
    resp = http_get("https://momochi-bunka.com/event/", accept="text/html,*/*")
    return _parse(resp.text)


def _parse(html: str) -> list[Event]:
    doc = soup_of(html)
    events: list[Event] = []
    today = _dt.date.today()
    for item in doc.select(".article__item"):
        date_el = item.select_one(".article__item__eventDate")
        if date_el is None:  # 開催日が無い記事はスキップ
            continue
        dates = expand_jp_date_range(date_el.get_text(), today)
        if not dates:
            continue
        title_el = item.select_one(".article__item__ttl")
        title = flatten_ws(title_el.get_text() if title_el else "")
        if not title:
            continue
        genre = guess_genre(title)
        for d in dates:
            events.append(Event(
                venue=MOMOCHI_BUNKA, date=d, title=title, genre=genre,
                start_hour=None, start_minute=None,
            ))
    return events
