"""会場マスタ。

福岡9会場はアプリ(event_service.dart)の Venue 定数と key/座標を一致させる。
全国の大箱は需要インパクト大の会場をシード（スクレイパーは順次追加）。
"""
from model import Venue

# ─── 福岡（アプリと同一） ───────────────────────────────────────────────────
MARINE_MESSE_A = Venue(
    key="marine_messe_a", name="マリンメッセ福岡A館",
    lat=33.608276, lng=130.402028, region="福岡", big_box=True,
    official_url="https://www.marinemesse.or.jp/messe/event/",
)
MARINE_MESSE_B = Venue(
    key="marine_messe_b", name="マリンメッセ福岡B館",
    lat=33.606532, lng=130.403585, region="福岡", big_box=True,
    official_url="https://www.marinemesse.or.jp/messe-b/event/",
)
FUKUOKA_CONGRESS = Venue(
    key="fukuoka_congress", name="福岡国際会議場",
    lat=33.604404, lng=130.403444, region="福岡",
    official_url="https://www.marinemesse.or.jp/congress/event/",
)
FUKUOKA_KOKUSAI_CENTER = Venue(
    key="fukuoka_kokusai_center", name="福岡国際センター",
    lat=33.603178, lng=130.401333, region="福岡",
    official_url="https://www.marinemesse.or.jp/kokusai/event/",
)
FUKUOKA_SUNPALACE = Venue(
    key="fukuoka_sunpalace", name="福岡サンパレス",
    lat=33.603445, lng=130.402727, region="福岡",
    official_url="https://www.f-sunpalace.com/hall/",
)
PAYPAY_DOME = Venue(
    key="paypay_dome", name="みずほPayPayドーム福岡",
    lat=33.5957, lng=130.3621, region="福岡", big_box=True,
    official_url="https://www.softbankhawks.co.jp/stadium/",
)
BEST_DENKI_STADIUM = Venue(
    key="best_denki_stadium", name="ベスト電器スタジアム",
    lat=33.593722, lng=130.467500, region="福岡", big_box=True,
    official_url="https://www.avispa.co.jp/",
)
HAKATAZA = Venue(
    key="hakataza", name="博多座",
    lat=33.595734, lng=130.406395, region="福岡",
    official_url="https://www.hakataza.co.jp/lineup/",
)
FUKUOKA_CIVIC_HALL = Venue(
    key="fukuoka_civic_hall", name="福岡市民ホール",
    lat=33.598389, lng=130.398918, region="福岡",
    official_url="https://www.fukuoka-civic-hall.jp/event/",
)
MOMOCHI_BUNKA = Venue(
    key="momochi_bunka", name="SAWARAPIA(ももち文化センター)",
    lat=33.582418, lng=130.347089, region="福岡",
    official_url="https://momochi-bunka.com/event/",
)
FUKUOKA_BUDOKAN = Venue(
    key="fukuoka_budokan", name="福岡武道館",
    lat=33.603306, lng=130.416168, region="福岡",
    official_url="https://fukuokabudokan.jp/",
)

# ─── 全国の大箱（座標シード・スクレイパーは順次追加） ───────────────────────
# まずは「終演後にタクシー需要が大きく出る」大規模アリーナ/ドーム/スタジアムから。
TOKYO_DOME = Venue(
    key="tokyo_dome", name="東京ドーム",
    lat=35.705622, lng=139.751853, region="東京", big_box=True,
    official_url="https://www.tokyo-dome.co.jp/dome/",
)
SAITAMA_SUPER_ARENA = Venue(
    key="saitama_super_arena", name="さいたまスーパーアリーナ",
    lat=35.894940, lng=139.630700, region="埼玉", big_box=True,
    official_url="https://www.saitama-arena.co.jp/",
)
YOKOHAMA_ARENA = Venue(
    key="yokohama_arena", name="横浜アリーナ",
    lat=35.512200, lng=139.617000, region="神奈川", big_box=True,
    official_url="https://www.yokohama-arena.co.jp/",
)
K_ARENA = Venue(
    key="k_arena", name="Kアリーナ横浜",
    lat=35.466400, lng=139.630300, region="神奈川", big_box=True,
    official_url="https://k-arena.com/schedule/",
)
ARIAKE_ARENA = Venue(
    key="ariake_arena", name="有明アリーナ",
    lat=35.642000, lng=139.793700, region="東京", big_box=True,
    official_url="https://ariake-arena.tokyo/event/",
)
NISSAN_STADIUM = Venue(
    key="nissan_stadium", name="日産スタジアム",
    lat=35.509900, lng=139.606200, region="神奈川", big_box=True,
    official_url="https://www.nissan-stadium.jp/calendar/",
)
AJINOMOTO_STADIUM = Venue(
    key="ajinomoto_stadium", name="味の素スタジアム",
    lat=35.664500, lng=139.527500, region="東京", big_box=True,
    official_url="https://www.ajinomotostadium.com/schedule/",
)
BELLUNA_DOME = Venue(
    key="belluna_dome", name="ベルーナドーム",
    lat=35.759500, lng=139.421600, region="埼玉", big_box=True,
    official_url="https://bellunadome.seibulions.co.jp/",
)
TOKYO_INTL_FORUM = Venue(
    key="tokyo_intl_forum", name="東京国際フォーラム",
    lat=35.677200, lng=139.763700, region="東京", big_box=True,
    official_url="https://www.t-i-forum.co.jp/visitors/event/",
)
OSAKA_JO_HALL = Venue(
    key="osaka_jo_hall", name="大阪城ホール",
    lat=34.687300, lng=135.532000, region="大阪", big_box=True,
    official_url="https://www.osaka-johall.com/event/",
)
FESTIVAL_HALL = Venue(
    key="festival_hall", name="フェスティバルホール",
    lat=34.693800, lng=135.494400, region="大阪", big_box=True,
    official_url="https://www.festivalhall.jp/events/",
)
IG_ARENA = Venue(
    key="ig_arena", name="IGアリーナ",
    lat=35.184600, lng=136.899000, region="愛知", big_box=True,
    official_url="https://www.ig-arena.jp/events/",
)
KYOCERA_DOME = Venue(
    key="kyocera_dome", name="京セラドーム大阪",
    lat=34.669358, lng=135.476056, region="大阪", big_box=True,
    official_url="https://www.kyoceradome-osaka.jp/",
)
NAGOYA_DOME = Venue(
    key="vantelin_dome", name="バンテリンドーム ナゴヤ",
    lat=35.186500, lng=136.947500, region="愛知", big_box=True,
    official_url="https://www.nagoya-dome.co.jp/",
)
SAPPORO_DOME = Venue(
    key="sapporo_dome", name="札幌ドーム",
    lat=43.015100, lng=141.409800, region="北海道", big_box=True,
    official_url="https://www.sapporo-dome.co.jp/",
)
PIA_ARENA_MM = Venue(
    key="pia_arena_mm", name="ぴあアリーナMM",
    lat=35.461300, lng=139.629600, region="神奈川", big_box=True,
    official_url="https://pia-arena-mm.jp/event/",
)
# ヤンマースタジアム長居 と ヨドコウ桜スタジアムは長居公園内で隣接（約150m）。
# セレッソ大阪のホーム戦をまとめて1会場として扱う（タクシー需要上は同一エリア）。
NAGAI_STADIUM = Venue(
    key="nagai_stadium", name="ヤンマースタジアム長居（長居公園）",
    lat=34.614900, lng=135.517800, region="大阪", big_box=True,
    official_url="https://www.cerezo.jp/matches/",
)
# ─── プロ野球（npb.jp の月別カレンダーから取得） ───────────────────────────
MEIJI_JINGU = Venue(
    key="meiji_jingu", name="明治神宮野球場",
    lat=35.674700, lng=139.717200, region="東京", big_box=True,
    official_url="https://npb.jp/games/2026/",
)
YOKOHAMA_STADIUM = Venue(
    key="yokohama_stadium", name="横浜スタジアム",
    lat=35.443300, lng=139.640000, region="神奈川", big_box=True,
    official_url="https://npb.jp/games/2026/",
)
ZOZO_MARINE = Venue(
    key="zozo_marine", name="ZOZOマリンスタジアム",
    lat=35.645200, lng=140.031200, region="千葉", big_box=True,
    official_url="https://npb.jp/games/2026/",
)
KOSHIEN = Venue(
    key="koshien", name="阪神甲子園球場",
    lat=34.721100, lng=135.361700, region="兵庫", big_box=True,
    official_url="https://npb.jp/games/2026/",
)

# 全会場リスト（build.py から参照）
ALL_VENUES = [
    MARINE_MESSE_A, MARINE_MESSE_B, FUKUOKA_CONGRESS, FUKUOKA_KOKUSAI_CENTER,
    FUKUOKA_SUNPALACE, PAYPAY_DOME, BEST_DENKI_STADIUM, HAKATAZA,
    FUKUOKA_CIVIC_HALL, MOMOCHI_BUNKA, FUKUOKA_BUDOKAN,
    TOKYO_DOME, SAITAMA_SUPER_ARENA, YOKOHAMA_ARENA, KYOCERA_DOME,
    NAGOYA_DOME, SAPPORO_DOME,
    K_ARENA, ARIAKE_ARENA, NISSAN_STADIUM, AJINOMOTO_STADIUM,
    BELLUNA_DOME, TOKYO_INTL_FORUM, OSAKA_JO_HALL, FESTIVAL_HALL, IG_ARENA,
    PIA_ARENA_MM, NAGAI_STADIUM,
    MEIJI_JINGU, YOKOHAMA_STADIUM, ZOZO_MARINE, KOSHIEN,
]

# マリンメッセ系: CMS会場ID → Venue
MARINE_MESSE_VENUE_ID_MAP = {
    "rhPkRp7kYFiu7CuFjFaW": MARINE_MESSE_A,
    "1uLqpDJwQBdRWOuFnLUm": MARINE_MESSE_B,
    "M1a4HXq8jUU5bnAKafsY": FUKUOKA_CONGRESS,
    "ZxskZD69QFYho9rXNUZl": FUKUOKA_KOKUSAI_CENTER,
}
