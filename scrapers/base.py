"""スクレイパー共通ユーティリティ。

event_service.dart の _flattenWhitespace / _expandJpDateRange /
_extractOrderedLines を Python へ移植。
"""
from __future__ import annotations

import datetime as _dt
import re

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

UA = (
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36"
)


def http_get(url: str, *, referer: str = "", accept: str = "application/json,*/*",
             timeout: int = 15) -> requests.Response:
    headers = {"User-Agent": UA, "Accept": accept}
    if referer:
        headers["Referer"] = referer
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp


def soup_of(text: str) -> BeautifulSoup:
    return BeautifulSoup(text, "html.parser")


def flatten_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


_JP_START_RE = re.compile(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日")
_JP_END_RE = re.compile(r"(?:(\d{4})年\s*)?(?:(\d{1,2})月\s*)?(\d{1,2})日")
_JP_SEP_RE = re.compile(r"[～〜~]")


def expand_jp_date_range(src: str, today: _dt.date) -> list[_dt.date]:
    """「YYYY年M月D日(曜)」形式（範囲「～」対応）を日付リストへ展開。

    終了側は年・月の省略を許容。today より前は除外。
    範囲が40日超なら開催日スパイクでないため開始日のみ採用。
    """
    sm = _JP_START_RE.search(src)
    if not sm:
        return []
    start = _dt.date(int(sm.group(1)), int(sm.group(2)), int(sm.group(3)))
    end = start
    sep = _JP_SEP_RE.search(src)
    if sep:
        tail = src[sep.end():]
        em = _JP_END_RE.search(tail)
        if em:
            emo = int(em.group(2)) if em.group(2) else start.month
            ed = int(em.group(3))
            year = int(em.group(1)) if em.group(1) else start.year
            if em.group(1) is None and emo < start.month:
                year = start.year + 1
            cand = _dt.date(year, emo, ed)
            if cand >= start:
                end = cand
    if (end - start).days > 40:
        end = start
    out = []
    dt = start
    while dt <= end:
        if dt >= today:
            out.append(dt)
        dt += _dt.timedelta(days=1)
    return out


_BLOCK_TAGS = {
    "p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "tr", "td", "th", "section", "article",
}


def extract_ordered_lines(root: Tag | None) -> list[str]:
    """DOM ノードからテキストを行単位で順序保持で抽出。

    ブロック要素境界で改行を区切り、インラインテキストは1行にまとめる。
    """
    if root is None:
        return []
    out: list[str] = []
    buf: list[str] = []

    def flush():
        if buf:
            out.append("".join(buf))
            buf.clear()

    def walk(node):
        if isinstance(node, NavigableString):
            buf.append(str(node))
            return
        if isinstance(node, Tag):
            is_block = node.name in _BLOCK_TAGS
            if is_block:
                flush()
            for c in node.children:
                walk(c)
            if is_block:
                flush()

    walk(root)
    flush()
    return out
