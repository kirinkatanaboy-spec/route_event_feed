# route_event_feed

全国のイベント情報を **会場公式サイトから収集 → 静的JSONに整形 → 無料ホスティングで配信** する
データ基盤。Flutterアプリ（route_timer_app）とは完全に別プロジェクト。

## なぜ別プロジェクトか

- スクレイパーは Python（GitHub Actions 無料枠で定期実行）。Flutterと無関係。
- アプリ側でスクレイプしない＝端末のCPU/メモリ負荷ゼロ（OOM対策）。
- 会場サイトが改修で壊れても、ここを直すだけで全ユーザーに即反映（アプリ更新不要）。
- 個人情報を一切扱わない（イベントは公開情報）。サーバー不要・コストほぼ¥0。

## 全体構成（3出力・1データ源）

```
route_event_feed/
  scrapers/          会場公式サイトを収集（福岡9会場から移植中）
  venues.py          会場マスタ（座標・地域・大箱フラグ）
  model.py           Event / Venue モデル＋JSONスキーマ
  build.py           収集→整形→ out/ に書き出し
  out/
    events_jp.json   ① アプリが取得する薄いJSON
    index.html       ② 公開サイト（独自分析＋将来AdSense）
  .github/workflows/
    build.yml        定期実行（cron）＋GitHub Pages デプロイ
  requirements.txt
```

1本のジョブが「アプリ用JSON」と「公開サイト」を同時に吐く。

## データ源のポリシー（重要）

- 収集元は **各会場の公式サイト/公式カレンダー/公式API/オープンデータのみ**。
- 商用集約サイト（ぴあ・Walkerplus 等）の無断スクレイプ→再配布はしない
  （広告で収益化する公開サイトでは規約・データベース権リスクが高いため）。
- 公開サイトは「事実（日時・会場・タイトル）＋独自のタクシー需要分析」に留め、
  各イベントから公式ページへ必ずリンク（出典明記）する。
  これにより AdSense の「独自価値」要件もクリアする。

## ローカル実行

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python build.py            # out/events_jp.json と out/index.html を生成
```

## 配信URL（GitHub Pages 設定後）

- アプリ用JSON: `https://<user>.github.io/route_event_feed/events_jp.json`
- 公開サイト:   `https://<user>.github.io/route_event_feed/`

## ステータス

- [x] 雛形・スキーマ・ビルドパイプライン
- [x] マリンメッセ系4会場（公式CMS API）移植
- [ ] サンパレス / PayPayドーム / 博多座 / 市民ホール / SAWARAPIA / 武道館 移植
- [ ] 全国の大箱（各地ドーム/アリーナ/スタジアム）追加
- [ ] 需要カーブ（タクシー視点）を各イベントに付与
- [ ] GitHub Pages 公開 → アクセスが育ってから AdSense 申請
