"""福岡武道館（fukuokabudokan.jp / WordPress Event Organiser）。

event_service.dart の _fetchBudokan / _parseBudokanJson を移植。
FullCalendar 用 admin-ajax エンドポイントが会場全イベントを JSON で返す（nonce不要）:
  /wp-admin/admin-ajax.php?action=eventorganiser-fullcal
    &start=YYYY-MM-DD&end=YYYY-MM-DD&timeformat=HH:mm
    &category=tournament,event,meeting
レスポンスは FullCalendar イベント配列。allDay の end は排他的→[start,end)で展開。
"""
from __future__ import annotations

import datetime as _dt
import json
import re

from model import Event, GENRE_SPORTS
from venues import FUKUOKA_BUDOKAN
from .base import http_get, flatten_ws

_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


def fetch() -> list[Event]:
    today = _dt.date.today()
    end = today + _dt.timedelta(days=120)
    url = (
        "https://fukuokabudokan.jp/wp-admin/admin-ajax.php?action=eventorganiser-fullcal"
        f"&start={today.isoformat()}&end={end.isoformat()}&timeformat=HH:mm"
        "&category=tournament,event,meeting"
    )
    resp = http_get(url, accept="application/json,*/*")
    return _parse(resp.text, today)


def _parse(body: str, today: _dt.date) -> list[Event]:
    decoded = json.loads(body)
    if not isinstance(decoded, list):
        return []
    events: list[Event] = []
    for raw in decoded:
        if not isinstance(raw, dict):
            continue
        title = flatten_ws(str(raw.get("title", "")))
        if not title:
            continue
        start_str = str(raw.get("start", ""))
        start_dt = _parse_iso(start_str)
        if start_dt is None:
            continue
        all_day = raw.get("allDay") is True
        # 終日イベントは end が排他的 → [start, end) で日付展開（最大7日に制限）。
        dates: list[_dt.date] = []
        if all_day:
            end_dt = _parse_iso(str(raw.get("end", "")))
            if end_dt is not None and end_dt > start_dt:
                d = start_dt
                last = end_dt
                guard = 0
                while d < last and guard < 7:
                    dates.append(d)
                    d += _dt.timedelta(days=1)
                    guard += 1
            else:
                dates.append(start_dt)
        else:
            dates.append(start_dt)
        # 時刻指定イベントのみ開演時刻を採用（終日は None＝ジャンル既定）。
        hh = mm = None
        if not all_day:
            time_src = start_str.split("T", 1)[1] if "T" in start_str else start_str
            tm = _TIME_RE.search(time_src)
            if tm:
                hh, mm = int(tm.group(1)), int(tm.group(2))
        for d in dates:
            if d < today:
                continue
            events.append(Event(
                venue=FUKUOKA_BUDOKAN, date=d, title=title,
                genre=GENRE_SPORTS,  # 武道大会・体育館行事＝スポーツ需要曲線
                start_hour=hh, start_minute=mm,
            ))
    return events


def _parse_iso(s: str) -> _dt.date | None:
    """"2026-06-06T00:00:00" 形式から date を取り出す（時刻部は無視）。"""
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if not m:
        return None
    try:
        return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
