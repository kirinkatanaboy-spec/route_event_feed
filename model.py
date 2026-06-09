"""Event / Venue モデルと出力JSONスキーマ。

アプリ(route_timer_app)側の event_service.dart の VenueEvent / Venue / EventGenre
を Python へ移植したもの。出力JSONはアプリが直接パースできる形に整える。
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional

# ─── ジャンル ───────────────────────────────────────────────────────────────
# アプリ側 EventGenre { concert, sports, exhibition, other } と文字列で一致させる。
GENRE_CONCERT = "concert"
GENRE_SPORTS = "sports"
GENRE_EXHIBITION = "exhibition"
GENRE_OTHER = "other"
GENRES = (GENRE_CONCERT, GENRE_SPORTS, GENRE_EXHIBITION, GENRE_OTHER)


@dataclass(frozen=True)
class Venue:
    """会場マスタ1件。"""

    key: str          # アプリ側 Venue.key と一致させる（例 "marine_messe_a"）
    name: str
    lat: float
    lng: float
    region: str = ""  # 地域フィルタ用（例 "福岡", "東京"）。全国化で使用。
    big_box: bool = False  # ドーム/アリーナ等の大箱か（需要インパクト大）
    official_url: str = ""  # 出典リンク（公開サイトで明記）

    def to_json(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "region": self.region,
            "bigBox": self.big_box,
            "officialUrl": self.official_url,
        }


@dataclass
class Event:
    """イベント1件（特定日の1公演）。"""

    venue: Venue
    date: _dt.date
    title: str
    genre: str = GENRE_OTHER
    start_hour: Optional[int] = None    # 開演時刻（不明なら None）
    start_minute: Optional[int] = None

    def to_json(self) -> dict:
        return {
            "venueKey": self.venue.key,
            "date": self.date.isoformat(),  # "YYYY-MM-DD"
            "title": self.title,
            "genre": self.genre,
            # 開演時刻は不明なら null（アプリ側でジャンル別デフォルトを使う）
            "startHour": self.start_hour,
            "startMinute": self.start_minute,
        }

    def dedup_key(self) -> tuple:
        return (self.venue.key, self.date.isoformat(), self.title.strip())


# ─── ジャンル推定（event_service.dart の _guessGenre 移植） ──────────────────
import re as _re

_SPORTS_RE = _re.compile(
    r"野球|サッカー|バスケ|バレー|相撲|格闘技|ボクシング|プロレス|ラグビー|"
    r"フットボール|ホークス|アビスパ|試合|vs|VS"
)
_CONCERT_RE = _re.compile(
    r"LIVE|ライブ|ツアー|TOUR|コンサート|CONCERT|公演|フェス|FES",
    _re.IGNORECASE,
)
_EXHIBITION_RE = _re.compile(r"展|博|EXPO|見本市|フェア|展示")


def guess_genre(title: str, is_dome: bool = False) -> str:
    if _SPORTS_RE.search(title):
        return GENRE_SPORTS
    if _CONCERT_RE.search(title):
        return GENRE_CONCERT
    if _EXHIBITION_RE.search(title):
        return GENRE_EXHIBITION
    if is_dome:
        return GENRE_CONCERT
    return GENRE_OTHER


# ─── 年推定（_resolveYear 移植） ────────────────────────────────────────────
def resolve_year(month: int, day: int, today: _dt.date) -> _dt.date:
    """月日のみから年を推定。1ヶ月以上前の日付は翌年とみなす。"""
    year = today.year
    candidate = _dt.date(year, month, day)
    if candidate < today - _dt.timedelta(days=30):
        year += 1
    return _dt.date(year, month, day)


def build_feed(events: list[Event], venues: list[Venue]) -> dict:
    """出力JSON全体を組み立てる。"""
    events_sorted = sorted(
        events,
        key=lambda e: (e.date, e.start_hour or 0, e.start_minute or 0),
    )
    used_keys = {e.venue.key for e in events_sorted}
    return {
        "schemaVersion": 1,
        "generatedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "venues": [v.to_json() for v in venues if v.key in used_keys],
        "events": [e.to_json() for e in events_sorted],
    }
