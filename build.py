"""収集 → 整形 → out/ に events_jp.json と index.html を書き出す。

  python build.py

各スクレイパーは個別に try で囲み、1つ落ちても他の会場は出力する。
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys

from model import build_feed, GENRES
from venues import ALL_VENUES
import scrapers

OUT_DIR = os.path.join(os.path.dirname(__file__), "out")

# ─── サニティゲート閾値（壊れたスクレイパーで空/激減JSONを全端末へ配信しない） ───
# 違反すると JSON を書かず exit(1)。CI はデプロイを止め、直前の正常デプロイが残る。
MIN_TOTAL_EVENTS = 200       # 総イベントの絶対下限（現状 ~1170）
MAX_FAILED_SCRAPERS = 5      # 例外で落ちたスクレイパー数の上限（構造崩壊の検知）
MIN_RETENTION_RATIO = 0.6    # 前回比でこの割合を下回る急減は異常とみなす


def _required_event_keys() -> set:
    return {"venueKey", "date", "title", "genre", "startHour", "startMinute"}


def _required_venue_keys() -> set:
    return {"key", "name", "lat", "lng", "region", "bigBox", "officialUrl"}


def validate_schema(feed: dict) -> list[str]:
    """アプリが必ずパースできる形か検証。問題点のリストを返す（空＝OK）。"""
    problems: list[str] = []
    vkeys = {v.get("key") for v in feed.get("venues", [])}
    for v in feed.get("venues", []):
        if set(v) != _required_venue_keys():
            problems.append(f"venue keys mismatch: {v.get('key')}")
            break
    ev_keys = _required_event_keys()
    for e in feed.get("events", []):
        if set(e) != ev_keys:
            problems.append(f"event keys mismatch: {e.get('title')!r}")
            break
        if e.get("genre") not in GENRES:
            problems.append(f"bad genre {e.get('genre')!r}: {e.get('title')!r}")
            break
        if e.get("venueKey") not in vkeys:
            problems.append(f"unknown venueKey {e.get('venueKey')!r}")
            break
        try:
            _dt.date.fromisoformat(e.get("date"))
        except (TypeError, ValueError):
            problems.append(f"bad date {e.get('date')!r}: {e.get('title')!r}")
            break
    return problems


def _previous_total() -> int | None:
    """直前ビルドの events_jp.json の件数（無ければ None）。急減検知のベースライン。"""
    path = os.path.join(OUT_DIR, "events_jp.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return len(json.load(f).get("events", []))
    except Exception:  # noqa: BLE001 - 壊れた前回ファイルは無視
        return None


def sanity_gate(feed: dict, errors: list[str], prev_total: int | None) -> list[str]:
    """配信してよいデータか判定。違反理由のリストを返す（空＝合格）。"""
    reasons: list[str] = []
    reasons.extend(validate_schema(feed))
    total = len(feed.get("events", []))
    if total < MIN_TOTAL_EVENTS:
        reasons.append(f"total events {total} < floor {MIN_TOTAL_EVENTS}")
    if len(errors) > MAX_FAILED_SCRAPERS:
        reasons.append(f"{len(errors)} scrapers failed > {MAX_FAILED_SCRAPERS}")
    if prev_total is not None and total < prev_total * MIN_RETENTION_RATIO:
        reasons.append(
            f"sudden drop: {total} < {prev_total}×{MIN_RETENTION_RATIO:.0%} "
            f"(={int(prev_total * MIN_RETENTION_RATIO)})")
    return reasons


def collect():
    events = []
    errors = []
    for mod in scrapers.ALL_SCRAPERS:
        name = mod.__name__.split(".")[-1]
        try:
            got = mod.fetch()
            events.extend(got)
            print(f"[ok] {name}: {len(got)} events")
        except Exception as e:  # noqa: BLE001 - 1会場の失敗で全体を止めない
            errors.append(f"{name}: {e}")
            print(f"[fail] {name}: {e}", file=sys.stderr)
    # 重複除去（会場+日付+タイトル）
    seen = set()
    uniq = []
    for e in events:
        k = e.dedup_key()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(e)
    return uniq, errors


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    force = "--force" in sys.argv  # 意図的な大変更時のみゲートを迂回
    prev_total = _previous_total()
    events, errors = collect()
    feed = build_feed(events, ALL_VENUES)

    # ★サニティゲート: 違反したら JSON を書かずに exit(1)。
    # CI ではデプロイが止まり、直前の正常な Pages 配信がそのまま残る
    # （壊れたスクレイパーで空/激減データを全端末へ配信しない）。
    reasons = sanity_gate(feed, errors, prev_total)
    if reasons and not force:
        print("[GATE FAILED] 出力を中止しました（直前の正常データを保持）:",
              file=sys.stderr)
        for r in reasons:
            print(f"  - {r}", file=sys.stderr)
        if errors:
            print("scraper errors:\n  " + "\n  ".join(errors), file=sys.stderr)
        sys.exit(1)
    if reasons and force:
        print("[GATE BYPASSED via --force]", file=sys.stderr)
        for r in reasons:
            print(f"  - {r}", file=sys.stderr)

    json_path = os.path.join(OUT_DIR, "events_jp.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {json_path} ({len(feed['events'])} events, "
          f"{len(feed['venues'])} venues)")

    html_path = os.path.join(OUT_DIR, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(render_site(feed))
    print(f"wrote {html_path}")

    if errors:
        print("errors:\n  " + "\n  ".join(errors), file=sys.stderr)


def render_site(feed: dict) -> str:
    """公開サイト（単一HTML）。out/events_jp.json を読み込んで表示する。

    AdSenseは中身とアクセスが育ってから申請するため、ここでは枠コメントのみ置く。
    各イベントには会場公式へのリンク（出典）を必ず付ける。
    """
    generated = feed.get("generatedAt", "")
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>全国イベント × タクシー需要マップ</title>
<!-- AdSense: 独自価値（タクシー需要分析）が育ってから申請・設置する -->
<style>
  :root {{ --bg:#13131f; --card:#1e1e30; --sec:#252538; --amber:#ffc107; --fg:#fff; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
         font-family:-apple-system,"Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif; }}
  header {{ padding:16px; background:var(--card); position:sticky; top:0; z-index:10;
            border-bottom:1px solid var(--sec); }}
  header h1 {{ margin:0; font-size:18px; }}
  header .meta {{ color:#9a9ab0; font-size:12px; margin-top:4px; }}
  .filters {{ display:flex; gap:8px; flex-wrap:wrap; padding:12px 16px; }}
  .filters button {{ background:var(--sec); color:var(--fg); border:none; border-radius:16px;
                     padding:6px 14px; font-size:13px; cursor:pointer; }}
  .filters button.on {{ background:var(--amber); color:#000; font-weight:700; }}
  main {{ padding:0 16px 40px; }}
  .day {{ margin-top:18px; }}
  .day h2 {{ font-size:14px; color:var(--amber); margin:0 0 8px;
             border-bottom:1px solid var(--sec); padding-bottom:4px; }}
  .ev {{ background:var(--card); border-radius:10px; padding:12px 14px; margin-bottom:8px;
         display:flex; justify-content:space-between; gap:12px; align-items:center; }}
  .ev .t {{ font-size:14px; font-weight:600; }}
  .ev .v {{ font-size:12px; color:#9a9ab0; margin-top:2px; }}
  .ev .time {{ font-size:13px; color:var(--amber); white-space:nowrap; }}
  .ev a {{ color:#6ab0ff; font-size:12px; text-decoration:none; }}
  .badge {{ font-size:11px; padding:2px 8px; border-radius:10px; margin-right:6px; }}
  .g-concert {{ background:#5a2a6a; }} .g-sports {{ background:#1b5e20; }}
  .g-exhibition {{ background:#b26a00; }} .g-other {{ background:#3a3a55; }}
  .empty {{ color:#9a9ab0; padding:40px 0; text-align:center; }}
</style>
</head>
<body>
<header>
  <h1>全国イベント × タクシー需要マップ</h1>
  <div class="meta">会場公式サイトの公開情報を集約・更新: <span id="gen"></span></div>
</header>
<div class="filters" id="filters"></div>
<main id="list"><div class="empty">読み込み中...</div></main>
<script>
const GENRE_LABEL = {{concert:"ライブ", sports:"スポーツ", exhibition:"展示", other:"その他"}};
const GENRE_CLASS = {{concert:"g-concert", sports:"g-sports", exhibition:"g-exhibition", other:"g-other"}};
let DATA = null, region = "ALL";

function fmtDay(iso) {{
  const d = new Date(iso + "T00:00:00");
  const w = "日月火水木金土"[d.getDay()];
  return `${{d.getMonth()+1}}/${{d.getDate()}}（${{w}}）`;
}}
function fmtTime(h, m) {{ return h==null ? "" : `${{String(h).padStart(2,"0")}}:${{String(m||0).padStart(2,"0")}}`; }}

function render() {{
  const venues = Object.fromEntries(DATA.venues.map(v => [v.key, v]));
  const evs = DATA.events.filter(e => {{
    if (region === "ALL") return true;
    const v = venues[e.venueKey];
    return v && v.region === region;
  }});
  const byDay = {{}};
  for (const e of evs) (byDay[e.date] ||= []).push(e);
  const days = Object.keys(byDay).sort();
  const list = document.getElementById("list");
  if (!days.length) {{ list.innerHTML = '<div class="empty">該当するイベントがありません</div>'; return; }}
  list.innerHTML = days.map(day => {{
    const items = byDay[day].map(e => {{
      const v = venues[e.venueKey] || {{name:e.venueKey, officialUrl:"#"}};
      const t = fmtTime(e.startHour, e.startMinute);
      return `<div class="ev">
        <div>
          <div class="t"><span class="badge ${{GENRE_CLASS[e.genre]||"g-other"}}">${{GENRE_LABEL[e.genre]||"その他"}}</span>${{e.title}}</div>
          <div class="v">${{v.name}}${{v.officialUrl ? ` ・ <a href="${{v.officialUrl}}" target="_blank" rel="noopener">公式</a>` : ""}}</div>
        </div>
        <div class="time">${{t}}</div>
      </div>`;
    }}).join("");
    return `<div class="day"><h2>${{fmtDay(day)}}</h2>${{items}}</div>`;
  }}).join("");
}}

function buildFilters() {{
  const regions = ["ALL", ...new Set(DATA.venues.map(v => v.region).filter(Boolean))];
  const box = document.getElementById("filters");
  box.innerHTML = regions.map(r =>
    `<button data-r="${{r}}" class="${{r===region?"on":""}}">${{r==="ALL"?"すべて":r}}</button>`).join("");
  box.querySelectorAll("button").forEach(b => b.onclick = () => {{
    region = b.dataset.r;
    box.querySelectorAll("button").forEach(x => x.classList.toggle("on", x===b));
    render();
  }});
}}

fetch("events_jp.json").then(r => r.json()).then(d => {{
  DATA = d;
  document.getElementById("gen").textContent = new Date(d.generatedAt).toLocaleString("ja-JP");
  buildFilters();
  render();
}}).catch(e => {{
  document.getElementById("list").innerHTML = '<div class="empty">データを読み込めませんでした</div>';
}});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
