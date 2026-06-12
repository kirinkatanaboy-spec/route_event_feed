"""PayPayドーム（ホークス戦）スクレイパーの回帰テスト。

2026-06-12 の事故の再発防止:
  ① ホークス公式の試合カードは「試合開始 18:00」（"試合開始" が時刻の前）表記
     だが、正規表現が逆順 "(HH):(MM)試合開始" を期待していたため全試合で
     開始時刻が None になり、アプリ側デフォルト時刻で誤表示していた。
  ② 交流戦のセ・リーグ対戦相手IDが未登録で「対戦相手」と表示されていた。

ネットワーク非依存（実HTML断片に対する純パーステスト）。CIで build 前に実行する。
失敗時は exit(1)。
"""
from __future__ import annotations

import sys

from scrapers.paypay_dome import _GAME_TIME_RE, _TEAM_ID_TO_NAME, _LOGO_ID_RE

# ホークス公式 game/schedule の試合カード get_text() の実サンプル（2026-06）。
_CARD_DAY_GAME = " 試合開始 14:00 みずほPayPay 勝敗(分) 先発 本塁打 チケット購入 "
_CARD_NIGHT_GAME = " 試合開始 18:00 みずほPayPay 勝敗(分) 0-0 先発 前田純 本塁打 "


def _check(name: str, cond: bool) -> bool:
    print(("[ok] " if cond else "[NG] ") + name)
    return cond


def main() -> int:
    ok = True

    # ① 開始時刻が「試合開始 HH:MM」順で抽出できる（逆順regexだと None になる）
    m = _GAME_TIME_RE.search(_CARD_DAY_GAME)
    ok &= _check("デーゲーム 14:00 を抽出",
                 bool(m) and (int(m.group(1)), int(m.group(2))) == (14, 0))
    m = _GAME_TIME_RE.search(_CARD_NIGHT_GAME)
    ok &= _check("ナイター 18:00 を抽出",
                 bool(m) and (int(m.group(1)), int(m.group(2))) == (18, 0))

    # ② 交流戦のセ・リーグ6球団＋パ・リーグ5球団が対戦相手として解決できる
    pacific = {"2005002", "2005003", "2008001", "1992001", "2004001"}
    central = {"1954001", "2012001", "1961001", "2006001"}  # 中日/DeNA/阪神/ヤクルト
    for tid in pacific | central:
        ok &= _check(f"対戦相手ID {tid} が登録済み", tid in _TEAM_ID_TO_NAME)

    # ③ ロゴURLから球団IDを取り出せる（opponent抽出の前提）
    lm = _LOGO_ID_RE.search("/media/sites/7/common/teamlogo/2026/logo_2006001_s.png")
    ok &= _check("ロゴURLからID抽出", bool(lm) and lm.group(1) == "2006001")

    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
