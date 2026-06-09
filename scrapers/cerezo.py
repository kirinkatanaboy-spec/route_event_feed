"""セレッソ大阪 ホーム戦（ヤンマースタジアム長居 / ヨドコウ桜スタジアム）。

公式 `https://www.cerezo.jp/matches/` は Next.js。`__NEXT_DATA__` 内
`props.pageProps.games[]` に試合一覧があり、各試合の `api.hv`（ホーム/アウェー）、
`api.stadium_s`（球場短縮名）、`api.kickoff`（"1600"）を持つ。
ホーム戦のみ採用し、両長居スタジアム（ヨドコウ/ヤンマー/ハナサカ）は長居公園内で
隣接するため1会場 NAGAI_STADIUM にまとめる。球場未定（stadium_s=None）の
ホーム戦もセレッソ本拠地＝長居として採用する。
"""
from __future__ import annotations

import datetime as _dt
import json
import re

from model import Event, GENRE_SPORTS
from venues import NAGAI_STADIUM
from .base import http_get

_NEXT_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
_KO_RE = re.compile(r"^\d{3,4}$")
# 長居公園内の本拠地系の球場短縮名（これ以外＝中立地/特別開催は除外）
_HOME_STADIUMS = {None, "ヨドコウ", "ヤンマー", "ハナサカ"}


def fetch() -> list[Event]:
    resp = http_get("https://www.cerezo.jp/matches/", accept="text/html,*/*")
    m = _NEXT_RE.search(resp.text)
    if not m:
        return []
    data = json.loads(m.group(1))
    games = (
        data.get("props", {}).get("pageProps", {}).get("games", []) or []
    )
    today = _dt.date.today()
    events: list[Event] = []
    seen: set[tuple] = set()
    for g in games:
        api = g.get("api") or {}
        if api.get("hv") != "ホーム":
            continue
        if api.get("stadium_s") not in _HOME_STADIUMS:
            continue
        ds = g.get("date") or api.get("date")
        if not ds:
            continue
        try:
            date = _dt.date.fromisoformat(str(ds)[:10])
        except ValueError:
            continue
        if date < today:
            continue
        hh = mm = None
        ko = str(api.get("kickoff") or "")
        if _KO_RE.match(ko):
            ko = ko.zfill(4)
            hh, mm = int(ko[:2]), int(ko[2:])
        ev = Event(
            venue=NAGAI_STADIUM, date=date, title="セレッソ大阪 ホームゲーム",
            genre=GENRE_SPORTS, start_hour=hh, start_minute=mm,
        )
        key = ev.dedup_key()
        if key in seen:
            continue
        seen.add(key)
        events.append(ev)
    return events


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.start_hour, e.venue.key, e.title)
