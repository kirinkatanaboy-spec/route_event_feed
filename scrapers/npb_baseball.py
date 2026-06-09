"""プロ野球 4球場（npb.jp の月別カレンダー schedule_MM.html）。

明治神宮野球場(ヤクルト)/横浜スタジアム(DeNA)/ZOZOマリン(ロッテ)/阪神甲子園(阪神)
の本拠地開催を npb.jp の公式日程から一括取得する。
（PayPayドーム/バンテリンD/京セラD/ベルーナD/東京Dは各専用スクレイパーが担当。）

カレンダーの1日セルは `td > div.date`（日番号）＋`a.link_block`（1試合）。
各 link_block は:
  `td.team1 img[alt]`=ホーム、`td.team2 img[alt]`=ビジター、
  1つ目 `td.state`=開始時刻("18:00")、2つ目 `td.state`=開催球場名("神宮"/"横浜"/
  "ZOZOマリン"/"甲子園"、地方開催時は"盛岡"等)。
2つ目 state の球場名が対象4球場と完全一致した試合だけ採用（地方開催・予備日は除外）。
npb.jp は UTF-8 だが requests が latin-1 と誤判定するため content を明示デコードする。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, GENRE_SPORTS
from venues import MEIJI_JINGU, YOKOHAMA_STADIUM, ZOZO_MARINE, KOSHIEN
from .base import http_get, soup_of, flatten_ws

# 2つ目 td.state の球場名（空白除去後）→ Venue
_VENUE_BY_LABEL = {
    "神宮": MEIJI_JINGU,
    "横浜": YOKOHAMA_STADIUM,
    "ZOZOマリン": ZOZO_MARINE,
    "甲子園": KOSHIEN,
}
# チーム正式名(img alt)→短縮名
_SHORT = {
    "読売ジャイアンツ": "巨人",
    "東京ヤクルトスワローズ": "ヤクルト",
    "阪神タイガース": "阪神",
    "中日ドラゴンズ": "中日",
    "横浜DeNAベイスターズ": "DeNA",
    "広島東洋カープ": "広島",
    "北海道日本ハムファイターズ": "日本ハム",
    "オリックス・バファローズ": "オリックス",
    "東北楽天ゴールデンイーグルス": "楽天",
    "千葉ロッテマリーンズ": "ロッテ",
    "福岡ソフトバンクホークス": "ソフトバンク",
    "埼玉西武ライオンズ": "西武",
}
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


def fetch() -> list[Event]:
    today = _dt.date.today()
    events: list[Event] = []
    seen: set[tuple] = set()
    for month_offset in range(4):
        y, m = _add_months(today.year, today.month, month_offset)
        url = f"https://npb.jp/games/{y}/schedule_{m:02d}.html"
        try:
            resp = http_get(url, accept="text/html,*/*")
        except Exception:
            continue
        html = resp.content.decode("utf-8", "replace")
        for ev in _parse(html, y, m, today):
            key = (ev.venue.key, ev.date, ev.title)
            if key in seen:
                continue
            seen.add(key)
            events.append(ev)
    return events


def _parse(html: str, year: int, month: int, today: _dt.date) -> list[Event]:
    doc = soup_of(html)
    events: list[Event] = []
    for a in doc.select("a.link_block"):
        states = a.select("td.state")
        if len(states) < 2:
            continue
        label = re.sub(r"\s", "", states[1].get_text())
        venue = _VENUE_BY_LABEL.get(label)
        if venue is None:
            continue  # 対象4球場以外（地方開催・他球場・予備日）
        cell = a.find_parent("td")
        date_el = cell.select_one("div.date") if cell else None
        if date_el is None:
            continue
        dm = re.search(r"(\d{1,2})", date_el.get_text())
        if not dm:
            continue
        try:
            d = _dt.date(year, month, int(dm.group(1)))
        except ValueError:
            continue
        if d < today:
            continue
        t1 = a.select_one("td.team1 img")
        t2 = a.select_one("td.team2 img")
        home = _SHORT.get((t1.get("alt") if t1 else "") or "", flatten_ws(t1.get("alt")) if t1 else "")
        away = _SHORT.get((t2.get("alt") if t2 else "") or "", flatten_ws(t2.get("alt")) if t2 else "")
        if not home or not away:
            continue
        hh = mm = None
        tm = _TIME_RE.search(states[0].get_text())
        if tm:
            hh, mm = int(tm.group(1)), int(tm.group(2))
        events.append(Event(
            venue=venue, date=d, title=f"{home} vs {away}",
            genre=GENRE_SPORTS, start_hour=hh, start_minute=mm,
        ))
    return events


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.start_hour, e.venue.key, e.title)
