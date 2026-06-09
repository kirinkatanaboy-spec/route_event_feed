"""マリンメッセ系4会場（公式CMS API: studiodesignapp Firestore）。

event_service.dart の _fetchMarineMesseGroup / _parseMarineMesseRecords /
_expandMarineMesseSchedule を Python へ移植。

1回の API 呼び出しで A館 / B館 / 福岡国際会議場 / 福岡国際センター 全イベントを取得し、
各レコードの zu0OnEpi.document.name で会場を分類する。
"""
from __future__ import annotations

import base64
import datetime as _dt
import re

from model import Event, guess_genre, resolve_year
from venues import MARINE_MESSE_VENUE_ID_MAP
from .base import http_get

_QUERY_JSON = (
    '{"uid":"20260515043559","project_id":"gjliOqGf6PL86iEKnjya",'
    '"schema_key":"rMR9xdMj","orders":"order","offset":0,"limit":200}'
)

_RANGE_RE = re.compile(
    r"(\d{1,2})\.(\d{1,2})(?:\([月火水木金土日]\))?\s*[～〜~]\s*"
    r"(\d{1,2})\.(\d{1,2})(?:\([月火水木金土日]\))?"
)
_SINGLE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})(?:\([月火水木金土日]\))?")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)


def fetch() -> list[Event]:
    qb64 = base64.b64encode(_QUERY_JSON.encode("utf-8")).decode("ascii")
    from urllib.parse import quote
    url = f"https://api.cms.studiodesignapp.com/v2/search?q={quote(qb64)}"
    resp = http_get(url, referer="https://www.marinemesse.or.jp/")
    decoded = resp.json()
    if isinstance(decoded, dict):
        records = list(decoded.values())
    elif isinstance(decoded, list):
        records = decoded
    else:
        raise ValueError(f"unexpected shape: {type(decoded)}")
    return _parse_records(records)


def _parse_records(raw) -> list[Event]:
    events: list[Event] = []
    today = _dt.date.today()
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        fields = _dig_fields(entry)
        if fields is None:
            continue
        title = _fs_string(fields.get("title"))
        date_string = _fs_string(fields.get("RIeOyB9L"))
        if not title or not date_string:
            continue
        venue_id = _dig_reference_name(fields.get("zu0OnEpi"))
        venue = MARINE_MESSE_VENUE_ID_MAP.get(venue_id)
        if venue is None:
            continue  # 未登録会場はスキップ
        genre = guess_genre(title)
        for occ_date, hh, mm in _expand_schedule(date_string, today):
            events.append(Event(
                venue=venue, date=occ_date, title=title, genre=genre,
                start_hour=hh, start_minute=mm,
            ))
    return events


def _dig_reference_name(field):
    try:
        return field["document"]["name"]
    except (KeyError, TypeError):
        return None


def _dig_fields(record):
    try:
        return dict(record["document"]["fields"]["default"]["mapValue"]["fields"])
    except (KeyError, TypeError):
        return None


def _fs_string(field):
    if isinstance(field, dict) and isinstance(field.get("stringValue"), str):
        return field["stringValue"]
    return None


def _expand_schedule(date_string: str, today: _dt.date):
    """日程文字列を (date, hour, minute) のリストへ展開。

    "6.16(火) 19:00～ <br>6.17(水) 18:00～"  → 2件
    "5.20(水)～5.22(金)<br>10:00～17:00"     → 3件（時刻は全日に適用）
    "6.14(日)"                              → 1件（時刻 None）
    """
    out = []
    normalized = _BR_RE.sub("\n", date_string)
    lines = [s.strip() for s in normalized.split("\n")]

    range_dates: list[_dt.date] = []
    global_time = None  # (hour, minute) or None

    for line in lines:
        if not line:
            continue
        r = _RANGE_RE.search(line)
        if r:
            m1, d1, m2, d2 = (int(r.group(i)) for i in range(1, 5))
            start = resolve_year(m1, d1, today)
            end = resolve_year(m2, d2, today)
            dt = start
            while dt <= end:
                range_dates.append(dt)
                dt += _dt.timedelta(days=1)
            tm = _TIME_RE.search(line)
            if tm:
                global_time = (int(tm.group(1)), int(tm.group(2)))
            continue
        s = _SINGLE_RE.search(line)
        if s:
            m, d = int(s.group(1)), int(s.group(2))
            dt = resolve_year(m, d, today)
            tm = _TIME_RE.search(line)
            t = (int(tm.group(1)), int(tm.group(2))) if tm else None
            if dt >= today:
                out.append((dt, t[0] if t else None, t[1] if t else None))
            continue
        tm = _TIME_RE.search(line)
        if tm and range_dates:
            global_time = (int(tm.group(1)), int(tm.group(2)))

    for dt in range_dates:
        if dt < today:
            continue
        hh = global_time[0] if global_time else None
        mm = global_time[1] if global_time else None
        out.append((dt, hh, mm))
    return out


if __name__ == "__main__":
    for e in fetch():
        print(e.date, e.venue.name, e.title, e.start_hour, e.start_minute)
