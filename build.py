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


def report_missing_sport_times(feed: dict) -> list[str]:
    """今後の試合（genre=sports）で開始時刻が欠落しているものを列挙。

    野球・サッカーの試合は公式に開始時刻が必ずあるため、未来の sports で
    startHour=None は「スクレイパーが時刻抽出に失敗している」静かな兆候。
    （アプリ側はジャンル別デフォルト時刻で埋めるため誤表示になるが画面に
    エラーは出ない。＝CIログでしか気付けないので、ここで明示警告する。）
    過去に PayPay ドームのホークス戦で時刻表記の正規表現がページ改変と
    逆順だったため全試合 None になった事故の再発防止。
    """
    today = _dt.date.today().isoformat()
    bad: list[str] = []
    for e in feed.get("events", []):
        if e.get("genre") != "sports":
            continue
        if (e.get("date") or "") < today:
            continue
        if e.get("startHour") is None:
            bad.append(f"{e.get('date')} {e.get('venueKey')} {e.get('title')!r}")
    return bad


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

    missing_times = report_missing_sport_times(feed)
    if missing_times:
        print(f"[WARN] 開始時刻が欠落した今後の試合 {len(missing_times)} 件"
              "（スクレイパーの時刻抽出失敗の疑い）:", file=sys.stderr)
        for m in missing_times:
            print(f"  - {m}", file=sys.stderr)


def render_site(feed: dict) -> str:
    """公開サイト（単一HTML）。out/events_jp.json を読み込んで表示する。

    フェーズD：独自価値＝「タクシー需要分析」を各イベントに付与する。
      - 終演予測（開演＋ジャンル別標準所要。アプリ event_service.dart と同思想）
      - 終演後の乗車ピーク時間帯
      - 需要★（大箱／終電後で加点）
    これにより単なる転載ではなくなり、AdSense の独自コンテンツ要件を満たす。
    各イベントには会場公式へのリンク（出典）を必ず付ける。

    AdSense は中身とアクセスが育ってから申請する。設置位置の枠コメントを置き、
    審査通過後に <head> へ広告スクリプト、本文へ ins タグを差し込めるようにしておく。
    """
    # 単一HTML。データは events_jp.json から fetch。f-string ではなく素の文字列
    # （CSS/JS の { } を二重化しなくて済むようにするため）。
    return _SITE_HTML


# 公開サイト本体（静的）。out/events_jp.json を読み込んで描画する。
_SITE_HTML = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>全国イベント × タクシー需要予測｜終演時刻と乗車ピークを会場公式情報から分析</title>
<meta name="description" content="全国の大型会場（ドーム・アリーナ・スタジアム）のイベントを会場公式サイトから集約し、終演予測と終演後のタクシー乗車ピーク時間帯・需要レベルを独自分析。会場公式リンク付き。">
<!-- ▼ AdSense（審査通過後にコメントを外す）
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX" crossorigin="anonymous"></script>
   ▲ -->
<style>
  :root { --bg:#13131f; --card:#1e1e30; --sec:#252538; --amber:#ffc107; --fg:#fff; --sub:#9a9ab0; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font-family:-apple-system,"Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif;
         line-height:1.5; }
  a { color:#6ab0ff; }
  header { padding:16px; background:var(--card); position:sticky; top:0; z-index:10;
            border-bottom:1px solid var(--sec); }
  header h1 { margin:0; font-size:17px; }
  header .meta { color:var(--sub); font-size:12px; margin-top:4px; }
  .lead { padding:12px 16px 0; color:var(--sub); font-size:13px; }
  .lead b { color:var(--fg); }
  details.about { margin:12px 16px 0; background:var(--card); border:1px solid var(--sec);
                  border-radius:10px; padding:0 14px; }
  details.about > summary { cursor:pointer; padding:12px 0; font-size:13px; font-weight:700; color:var(--amber); }
  details.about .body { font-size:12.5px; color:#c9c9d8; padding-bottom:14px; }
  details.about .body h3 { font-size:13px; color:var(--fg); margin:14px 0 6px; }
  details.about .body ul { margin:6px 0; padding-left:18px; }
  details.about .body .note { color:var(--sub); font-size:11.5px; margin-top:10px; }
  .controls { display:flex; gap:8px; flex-wrap:wrap; align-items:center; padding:12px 16px 4px; }
  .controls .label { color:var(--sub); font-size:12px; margin-right:2px; }
  .controls button { background:var(--sec); color:var(--fg); border:none; border-radius:16px;
                     padding:6px 14px; font-size:13px; cursor:pointer; }
  .controls button.on { background:var(--amber); color:#000; font-weight:700; }
  .controls .sep { width:1px; height:18px; background:var(--sec); margin:0 4px; }
  main { padding:8px 16px 40px; }
  .day { margin-top:18px; }
  .day h2 { font-size:14px; color:var(--amber); margin:0 0 8px;
             border-bottom:1px solid var(--sec); padding-bottom:4px; }
  .ev { background:var(--card); border-radius:10px; padding:12px 14px; margin-bottom:8px; }
  .ev .row1 { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }
  .ev .t { font-size:14px; font-weight:600; }
  .ev .v { font-size:12px; color:var(--sub); margin-top:3px; }
  .ev .time { font-size:13px; color:var(--amber); white-space:nowrap; padding-top:1px; }
  .ev .demand { margin-top:8px; padding-top:8px; border-top:1px dashed var(--sec);
                font-size:12px; color:#cfcfe0; display:flex; flex-wrap:wrap;
                gap:6px 12px; align-items:center; }
  .ev .demand .stars { color:var(--amber); font-size:13px; letter-spacing:1px; }
  .ev .demand .peak { color:#ffd866; }
  .ev .tag { font-size:10.5px; padding:1px 7px; border-radius:9px; background:var(--sec); color:#cfcfe0; }
  .ev .tag.late { background:#7a1f1f; color:#ffd5d5; }
  .ev .tag.big { background:#13405a; color:#bfe6ff; }
  .badge { font-size:11px; padding:2px 8px; border-radius:10px; margin-right:6px; }
  .g-concert { background:#5a2a6a; } .g-sports { background:#1b5e20; }
  .g-exhibition { background:#b26a00; } .g-other { background:#3a3a55; }
  .empty { color:var(--sub); padding:40px 0; text-align:center; }
  footer { border-top:1px solid var(--sec); margin-top:24px; padding:18px 16px 40px;
           color:var(--sub); font-size:11.5px; }
  footer a { color:#8ab8e0; }
</style>
</head>
<body>
<header>
  <h1>全国イベント × タクシー需要予測</h1>
  <div class="meta">会場公式サイトの公開情報を集約・自動更新：<span id="gen"></span></div>
</header>

<div class="lead">
  全国の大型会場（ドーム・アリーナ・スタジアム）のイベントを会場公式サイトから集め、
  <b>終演予測</b>と<b>終演後の乗車ピーク時間帯・需要レベル</b>を独自に分析して表示します。
  タクシー乗務・配車の参考にどうぞ。各イベントに会場公式リンク（出典）付き。
</div>

<details class="about">
  <summary>このサイトと需要分析について（読みもの）</summary>
  <div class="body">
    <p>イベントは終演直後に多数の来場者が一斉に移動を始めるため、会場周辺で短時間にタクシー需要が跳ね上がります。
       本サイトは会場公式の公演情報から、その「いつ・どれくらい」を見積もって表示します。</p>
    <h3>終演時刻の予測</h3>
    <p>開演時刻に、ジャンル別の標準的な所要時間を足して終演を見積もります。</p>
    <ul>
      <li>プロ野球：約3時間30分</li>
      <li>サッカー（J1）：約2時間（90分＋ハーフタイム＋ロスタイム）</li>
      <li>ライブ・コンサート：約2時間30分</li>
      <li>展示・その他：終日開催（需要は時間帯に分散）</li>
    </ul>
    <h3>乗車ピーク時間帯</h3>
    <p>終演の直後から約60分が乗車のピークです（特に終演＋10〜20分が最も集中）。本サイトでは
       <span class="peak">終演＋15分〜終演＋60分</span>をピーク帯として表示します。</p>
    <h3>需要レベル（★）の付け方</h3>
    <ul>
      <li>会場規模：ドーム／アリーナ／スタジアムなどの大箱は来場者が多く需要大（加点）</li>
      <li>終電後：終演が22:30以降だと電車での帰宅が難しくなり、タクシー需要が跳ねる（加点）</li>
      <li>展示・終日イベントは時間帯に分散するため、急なピークは小さめに評価</li>
    </ul>
    <p class="note">※ 予測はあくまで参考値です。実際の需要は公演の長さ・天候・交通状況・他イベントとの重なりで変動します。
       開演時刻が未公表の公演は終演予測を省略し、会場規模から需要レベルのみ示します。</p>
  </div>
</details>

<div class="controls" id="controls"></div>
<main id="list"><div class="empty">読み込み中...</div></main>

<footer>
  <p><b>データについて：</b>本サイトは各会場の公式サイトが公開している公演情報のみを集約しています。
     各イベントの「公式」リンクから一次情報（会場公式）をご確認ください。情報は1日3回自動更新しています。</p>
  <p><b>免責：</b>タクシー需要の予測値は独自分析による参考情報であり、正確性・実需要を保証するものではありません。
     掲載情報の利用により生じたいかなる損害についても責任を負いません。最新・正確な情報は必ず会場公式でご確認ください。</p>
  <p>© <span id="yr"></span> 全国イベント × タクシー需要予測</p>
</footer>

<script>
const GENRE_LABEL = {concert:"ライブ", sports:"スポーツ", exhibition:"展示", other:"その他"};
const GENRE_CLASS = {concert:"g-concert", sports:"g-sports", exhibition:"g-exhibition", other:"g-other"};

// 終演予測の所要分（アプリ event_service.dart _estimateDurationMinutes と同思想）
const BASEBALL = new Set(["paypay_dome","tokyo_dome","kyocera_dome","vantelin_dome",
  "sapporo_dome","belluna_dome","meiji_jingu","yokohama_stadium","zozo_marine","koshien"]);
const SOCCER = new Set(["best_denki_stadium","nissan_stadium","ajinomoto_stadium","nagai_stadium"]);
const DUR = {concert:150, sports:180, exhibition:480, other:150};

let DATA = null, region = "ALL", sort = "date";

function durationMin(e) {
  if (e.genre === "sports") {
    if (BASEBALL.has(e.venueKey)) return 210;
    if (SOCCER.has(e.venueKey)) return 120;
    return 180;
  }
  return DUR[e.genre] || 150;
}
function endTotal(e) {
  if (e.startHour == null) return null;
  return e.startHour * 60 + (e.startMinute || 0) + durationMin(e);
}
function fmtMin(total) {
  const h = Math.floor(total / 60), m = total % 60;
  return String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0");
}
function fmtDay(iso) {
  const d = new Date(iso + "T00:00:00");
  const w = "日月火水木金土"[d.getDay()];
  return (d.getMonth() + 1) + "/" + d.getDate() + "（" + w + "）";
}
function fmtTime(h, m) {
  return h == null ? "" : String(h).padStart(2, "0") + ":" + String(m || 0).padStart(2, "0");
}

// 需要分析: {stars, late, big, end, peakFrom, peakTo, dispersed}
function analyze(e, v) {
  const big = !!(v && v.bigBox);
  const dispersed = e.genre === "exhibition";
  const end = endTotal(e);
  let stars = big ? 2 : 1;
  let late = false;
  if (end != null && end >= 22 * 60 + 30) { stars += 1; late = true; }
  if (dispersed) stars = Math.max(1, stars - 1);
  stars = Math.max(1, Math.min(3, stars));
  return {
    stars, late, big, dispersed,
    end,
    peakFrom: end == null ? null : end + 15,
    peakTo: end == null ? null : end + 60,
  };
}

function demandHtml(a) {
  const stars = '<span class="stars">' + "★".repeat(a.stars) + "☆".repeat(3 - a.stars) + "</span>";
  const tags = [];
  if (a.big) tags.push('<span class="tag big">大箱</span>');
  if (a.late) tags.push('<span class="tag late">終電後</span>');
  const tagHtml = tags.join("");
  if (a.dispersed) {
    return '<div class="demand">' + stars + "<span>終日開催・需要は時間帯に分散</span>" + tagHtml + "</div>";
  }
  if (a.end == null) {
    return '<div class="demand">' + stars + "<span>開演時刻未公表（終演後にピーク）</span>" + tagHtml + "</div>";
  }
  const peak = '<span class="peak">乗車ピーク ' + fmtMin(a.peakFrom) + "〜" + fmtMin(a.peakTo) + "</span>";
  return '<div class="demand">' + stars + "<span>終演予測 " + fmtMin(a.end) + "</span>" + peak + tagHtml + "</div>";
}

function render() {
  const venues = Object.fromEntries(DATA.venues.map(v => [v.key, v]));
  const evs = DATA.events.filter(e => {
    if (region === "ALL") return true;
    const v = venues[e.venueKey];
    return v && v.region === region;
  });
  const byDay = {};
  for (const e of evs) (byDay[e.date] ||= []).push(e);
  const days = Object.keys(byDay).sort();
  const list = document.getElementById("list");
  if (!days.length) { list.innerHTML = '<div class="empty">該当するイベントがありません</div>'; return; }
  list.innerHTML = days.map(day => {
    const rows = byDay[day].map(e => {
      const v = venues[e.venueKey] || { name: e.venueKey, officialUrl: "#" };
      return { e, v, a: analyze(e, v) };
    });
    if (sort === "demand") {
      rows.sort((x, y) => (y.a.stars - x.a.stars) || ((x.e.startHour ?? 99) - (y.e.startHour ?? 99)));
    } else {
      rows.sort((x, y) => ((x.e.startHour ?? 99) - (y.e.startHour ?? 99)));
    }
    const items = rows.map(({ e, v, a }) => {
      const t = fmtTime(e.startHour, e.startMinute);
      const official = v.officialUrl
        ? ' ・ <a href="' + v.officialUrl + '" target="_blank" rel="noopener">公式</a>' : "";
      return '<div class="ev"><div class="row1"><div>' +
        '<div class="t"><span class="badge ' + (GENRE_CLASS[e.genre] || "g-other") + '">' +
        (GENRE_LABEL[e.genre] || "その他") + "</span>" + e.title + "</div>" +
        '<div class="v">' + v.name + official + "</div></div>" +
        '<div class="time">' + t + "</div></div>" +
        demandHtml(a) + "</div>";
    }).join("");
    return '<div class="day"><h2>' + fmtDay(day) + "</h2>" + items + "</div>";
  }).join("");
}

function buildControls() {
  const regions = ["ALL", ...new Set(DATA.venues.map(v => v.region).filter(Boolean))];
  const box = document.getElementById("controls");
  const regBtns = regions.map(r =>
    '<button data-r="' + r + '" class="' + (r === region ? "on" : "") + '">' +
    (r === "ALL" ? "すべて" : r) + "</button>").join("");
  const sortBtns =
    '<span class="label">並び</span>' +
    '<button data-s="date" class="' + (sort === "date" ? "on" : "") + '">時刻順</button>' +
    '<button data-s="demand" class="' + (sort === "demand" ? "on" : "") + '">需要順</button>';
  box.innerHTML = '<span class="label">地域</span>' + regBtns +
    '<span class="sep"></span>' + sortBtns;
  box.querySelectorAll("button[data-r]").forEach(b => b.onclick = () => {
    region = b.dataset.r;
    box.querySelectorAll("button[data-r]").forEach(x => x.classList.toggle("on", x === b));
    render();
  });
  box.querySelectorAll("button[data-s]").forEach(b => b.onclick = () => {
    sort = b.dataset.s;
    box.querySelectorAll("button[data-s]").forEach(x => x.classList.toggle("on", x === b));
    render();
  });
}

document.getElementById("yr").textContent = new Date().getFullYear();
fetch("events_jp.json").then(r => r.json()).then(d => {
  DATA = d;
  document.getElementById("gen").textContent = new Date(d.generatedAt).toLocaleString("ja-JP");
  buildControls();
  render();
}).catch(e => {
  document.getElementById("list").innerHTML = '<div class="empty">データを読み込めませんでした</div>';
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
