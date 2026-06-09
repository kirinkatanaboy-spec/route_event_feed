"""バンテリンドームナゴヤ（nagoya-dome.co.jp/enjoy/index.php?ym=YYYYMM）。

1ページに全月分が `.events`（id="tabs-N"）として並ぶ。tabs-N は
連続する月（tabs-0 が基準月）。空月の `.calAttn`（"2026年10月は予定がありません"）
から基準月を逆算して各タブの年月を確定する。
各月の `table.event_01` 内、`p.eventname` を含む行が1イベント:
  先頭td群= 日(M/D) / 開場 / 開始 / 終了、最後に イベント名。
ジャンルは行頭アイコン（icon1/icon4=スポーツ、icon2=コンサート、icon3=祭事）で判定。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, GENRE_SPORTS, GENRE_CONCERT, guess_genre
from venues import NAGOYA_DOME
from .base import http_get, soup_of, flatten_ws

_TAB_RE = re.compile(r"tabs-(\d+)")
_ATTN_RE = re.compile(r"(20\d\d)年(\d{1,2})月")
_DAY_RE = re.compile(r"(\d{1,2})/(\d{1,2})")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
_ICON_RE = re.compile(r"/icon(\d+)\.png")
_LOOKAHEAD_MONTHS = 4


def fetch() -> list[Event]:
    today = _dt.date.today()
    url = f"https://www.nagoya-dome.co.jp/enjoy/index.php?ym={today.year}{today.month:02d}"
    resp = http_get(url, accept="text/html,*/*")
    return _parse(resp.text, today)


def _parse(html: str, today: _dt.date) -> list[Event]:
    doc = soup_of(html)
    tabs = doc.select(".events")
    base = _anchor_base_month(tabs)
    if base is None:
        return []
    events: list[Event] = []
    cutoff = _add_months(today.year, today.month, _LOOKAHEAD_MONTHS)
    for tab in tabs:
        m = _TAB_RE.search(tab.get("id", ""))
        if not m:
            continue
        idx = int(m.group(1))
        year, month = _add_months(base[0], base[1], idx)
        # 当月より前 / 先読み上限より後 はスキップ
        if (year, month) < (today.year, today.month):
            continue
        if (year, month) > cutoff:
            continue
        events.extend(_parse_month(tab, year, month, today))
    return events


def _parse_month(tab, year: int, month: int, today: _dt.date) -> list[Event]:
    out: list[Event] = []
    for tr in tab.select("table.event_01 tr"):
        name_p = tr.select_one(".eventname")
        if name_p is None:
            continue
        tds = tr.find_all("td", recursive=False)
        # イベント名tdの手前が 日/開場/開始/終了
        lead: list = []
        for td in tds:
            if td.select_one(".eventname") is not None:
                break
            lead.append(td)
        if not lead:
            continue
        dm = _DAY_RE.search(lead[0].get_text())
        if not dm:
            continue
        try:
            d = _dt.date(year, month, int(dm.group(2)))
        except ValueError:
            continue
        if d < today:
            continue
        hh = mm = None
        if len(lead) >= 3:  # lead[2] = 開始
            tm = _TIME_RE.search(lead[2].get_text())
            if tm:
                hh, mm = int(tm.group(1)), int(tm.group(2))
        title = flatten_ws(name_p.get_text())
        if not title:
            continue
        out.append(Event(
            venue=NAGOYA_DOME, date=d, title=title,
            genre=_genre_of(name_p, title), start_hour=hh, start_minute=mm,
        ))
    return out


def _genre_of(name_p, title: str) -> str:
    img = name_p.find("img")
    if img is not None:
        m = _ICON_RE.search(img.get("src", ""))
        if m:
            n = m.group(1)
            if n in ("1", "4"):  # 野球 / スポーツ
                return GENRE_SPORTS
            if n == "2":  # コンサート
                return GENRE_CONCERT
    return guess_genre(title)


def _anchor_base_month(tabs) -> tuple[int, int] | None:
    """空月の calAttn ラベルから tabs-0 の年月を逆算する。"""
    for tab in tabs:
        m = _TAB_RE.search(tab.get("id", ""))
        if not m:
            continue
        idx = int(m.group(1))
        attn = tab.select_one(".calAttn")
        if attn is None:
            continue
        a = _ATTN_RE.search(attn.get_text())
        if not a:
            continue
        return _add_months(int(a.group(1)), int(a.group(2)), -idx)
    return None


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.start_hour, e.genre, e.title)
