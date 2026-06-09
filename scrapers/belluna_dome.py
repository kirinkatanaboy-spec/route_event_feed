"""ベルーナドーム（bellunadome.seibulions.co.jp/schedule/YYYYMM/all/index.html）。

静的HTML・月別。各イベントは `div.event-item`（id=\"event_NNNN_YYYYMMDD\"）:
  日付は id 末尾の YYYYMMDD、
  ジャンルは `.news-label`（news-label-baseball=プロ野球 / news-label-concert=コンサート）、
  タイトル＋開始時刻は `.event-info` の自由文（\"…VS …(18::00）\" の様に時刻が括弧書き）。
貸切（ラベル無し）は需要に直結しないため除外。プロ野球=sports / コンサート=concert。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, GENRE_SPORTS, GENRE_CONCERT, guess_genre
from venues import BELLUNA_DOME
from .base import http_get, soup_of, flatten_ws

_ID_RE = re.compile(r"event_\d+_(\d{4})(\d{2})(\d{2})")
_TIME_RE = re.compile(r"(\d{1,2})[:：]+(\d{2})")


def fetch() -> list[Event]:
    today = _dt.date.today()
    events: list[Event] = []
    seen: set[tuple] = set()
    for month_offset in range(4):
        y, m = _add_months(today.year, today.month, month_offset)
        url = f"https://bellunadome.seibulions.co.jp/schedule/{y}{m:02d}/all/index.html"
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
    for item in doc.select("div.event-item"):
        m = _ID_RE.search(item.get("id", ""))
        if not m:
            continue
        try:
            d = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if d < today:
            continue
        info = item.select_one(".event-info")
        if info is None:
            continue
        label = info.select_one(".news-label")
        if label is None:
            continue  # 貸切などラベル無し＝需要対象外
        label_txt = flatten_ws(label.get_text())
        if "プロ野球" in label_txt:
            genre = GENRE_SPORTS
        elif "コンサート" in label_txt:
            genre = GENRE_CONCERT
        else:
            genre = None
        # タイトル＝event-info からラベルブロックと「詳細」リンクを除いた自由文
        for junk in info.select(".mb10, .btn-event-detail"):
            junk.extract()
        body = flatten_ws(info.get_text())
        hh = mm = None
        tm = _TIME_RE.search(body)
        if tm:
            hh, mm = int(tm.group(1)), int(tm.group(2))
            body = body[: tm.start()].rstrip(" (（")
        title = body.strip(" 　")
        if not title:
            continue
        if genre is None:
            genre = guess_genre(title)
        events.append(Event(
            venue=BELLUNA_DOME, date=d, title=title,
            genre=genre, start_hour=hh, start_minute=mm,
        ))
    return events


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.start_hour, e.genre, e.title)
