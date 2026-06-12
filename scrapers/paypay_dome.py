"""みずほPayPayドーム福岡。

event_service.dart の _fetchPayPayDome（イベントスケジュール）と
_fetchHawksHomeGames（ホークス公式戦）を移植。両ソースを結合して返す。
"""
from __future__ import annotations

import datetime as _dt
import re

from model import Event, guess_genre, GENRE_SPORTS
from venues import PAYPAY_DOME
from .base import http_get, soup_of, extract_ordered_lines

# ── イベントスケジュール ──────────────────────────────────────────────────
_DATE_RE = re.compile(r"^(20\d{2})/(\d{1,2})/(\d{1,2})")
_KAIEN_RE = re.compile(r"開演\s*(\d{1,2}):(\d{2})")
_HEAD_RE = re.compile(r"^(イベント|コンサート|試合|公演|ライブ)$")
_TEL_RE = re.compile(r"TEL[:：]|問い合わせ|お問合せ")

# ── ホークス試合 ──────────────────────────────────────────────────────────
_HREF_RE = re.compile(r"/gamelive/result/(\d{4})(\d{2})(\d{2})\d{2}/?")
# ページ表記は「試合開始 18:00」（"試合開始" が時刻の前）。
_GAME_TIME_RE = re.compile(r"試合開始\s*(\d{1,2}):(\d{2})")
_LOGO_ID_RE = re.compile(r"logo_(\d+)_")
_HAWKS_TEAM_ID = "2005001"
_TEAM_ID_TO_NAME = {
    "2005001": "ホークス",
    # パ・リーグ
    "2005002": "バファローズ",
    "2005003": "イーグルス",
    "2008001": "ライオンズ",
    "1992001": "マリーンズ",
    "2004001": "ファイターズ",
    # セ・リーグ（交流戦の対戦相手）
    "1954001": "ドラゴンズ",
    "2012001": "ベイスターズ",
    "1961001": "タイガース",
    "2006001": "スワローズ",
}


def fetch() -> list[Event]:
    out: list[Event] = []
    year = _dt.date.today().year
    try:
        resp = http_get(
            f"https://www.softbankhawks.co.jp/stadium/event_schedule/{year}/",
            accept="text/html,*/*")
        out.extend(_parse_events(resp.text))
    except Exception:
        pass
    try:
        resp = http_get("https://www.softbankhawks.co.jp/game/schedule/",
                        accept="text/html,*/*")
        out.extend(_parse_games(resp.text))
    except Exception:
        pass
    return out


def _parse_events(html: str) -> list[Event]:
    doc = soup_of(html)
    lines = extract_ordered_lines(doc.body)
    events: list[Event] = []
    today = _dt.date.today()
    cur_date = None
    cur_title = None
    cur_hh = cur_mm = None

    def flush():
        nonlocal cur_title, cur_hh, cur_mm
        if cur_date and cur_title and cur_date >= today:
            events.append(Event(
                venue=PAYPAY_DOME, date=cur_date, title=cur_title,
                genre=guess_genre(cur_title, is_dome=True),
                start_hour=cur_hh, start_minute=cur_mm,
            ))
        cur_title = None
        cur_hh = cur_mm = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        dm = _DATE_RE.match(line)
        if dm:
            flush()
            try:
                cur_date = _dt.date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)))
            except ValueError:
                cur_date = None
            continue
        if cur_date is None:
            continue
        tm = _KAIEN_RE.search(line)
        if tm:
            cur_hh, cur_mm = int(tm.group(1)), int(tm.group(2))
            continue
        if len(line) <= 6 and _HEAD_RE.match(line):
            continue
        if _TEL_RE.search(line):
            continue
        if cur_title is None:
            cur_title = line
    flush()
    return events


def _parse_games(html: str) -> list[Event]:
    doc = soup_of(html)
    events: list[Event] = []
    today = _dt.date.today()
    seen = set()
    for a in doc.select("a"):
        href = a.get("href", "")
        m = _HREF_RE.search(href)
        if not m:
            continue
        try:
            date = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if date < today:
            continue
        # 親方向に c-calendar-list-day を探す
        p = a.parent
        day_card = None
        for _ in range(10):
            if p is None:
                break
            cls = " ".join(p.get("class", [])) if hasattr(p, "get") else ""
            if "c-calendar-list-day" in cls:
                day_card = p
                break
            p = p.parent
        if day_card is None:
            continue
        text = day_card.get_text()
        if "PayPay" not in text:
            continue
        key = date.isoformat()
        if key in seen:
            continue
        seen.add(key)
        hh = mm = None
        tm = _GAME_TIME_RE.search(text)
        if tm:
            hh, mm = int(tm.group(1)), int(tm.group(2))
        opponent = "対戦相手"
        for img in day_card.select(".c-calendar-list-game-vs-teams-team img"):
            src = img.get("data-src") or img.get("src") or ""
            lm = _LOGO_ID_RE.search(src)
            if not lm:
                continue
            tid = lm.group(1)
            if tid == _HAWKS_TEAM_ID:
                continue
            opponent = _TEAM_ID_TO_NAME.get(tid, "対戦相手")
            break
        events.append(Event(
            venue=PAYPAY_DOME, date=date, title=f"ホークス vs {opponent}",
            genre=GENRE_SPORTS, start_hour=hh, start_minute=mm,
        ))
    return events
