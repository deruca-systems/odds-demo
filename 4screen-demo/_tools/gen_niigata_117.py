"""
新潟 1R-12R 比較ビュー (monitor=117) 用データ生成スクリプト
2026-04-30 session3 追加。

目的:
  - monitor=117 の 4分割比較ビューを「全部新潟・1R〜12R」で構成する（ユーザー要望）。
  - 12 レースを 4 分割 × 3 列に展開し、各列で異なるパターン (NORMAL/A/B/C/D/E/F/G/H +
    出走表 18頭 + 出走表 10頭+出走取消) を比較表示する。

実行:
  python -X utf8 _tools/gen_niigata_117.py
  （gen_data.py 実行後に必ず本スクリプトを実行すること。
   gen_data.py 側の extra_monitors からは 117 を除外済 (session3 の修正)。）

出力:
  - results/{TODAY}/JRA_04_01..10.json   (10 レースの確定成績)
  - odds/{TODAY}/JRA_04_11.json          (出走表 18頭、entries モード fallback 用)
  - odds/{TODAY}/JRA_04_12.json          (出走表 10頭+出走取消、entries モード)
  - schedules/{TODAY}/117.json           (4-split 比較ビュー)
  - schedules/{TODAY}/117_fast.json      (同上、fast=1 専用)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import importlib.util
from datetime import timedelta
from pathlib import Path

# gen_data.py を import（同じ _tools/ ディレクトリ内）
# REPO_ROOT = 本スクリプトのある _tools/ の親ディレクトリ (= 4screen-demo/)
REPO_ROOT = Path(__file__).resolve().parent.parent
GEN_DATA_PATH = REPO_ROOT / "_tools" / "gen_data.py"

spec = importlib.util.spec_from_file_location("gen_data", str(GEN_DATA_PATH))
gen = importlib.util.module_from_spec(spec)
sys.modules["gen_data"] = gen
spec.loader.exec_module(gen)

NOW = gen.NOW
NOW_ISO = gen.NOW_ISO
TODAY = gen.TODAY_YYYYMMDD

# ============================================================
# 新潟競走馬名・騎手プール（JRA 関東所属イメージ）
# ============================================================
NIIGATA_NAMES = [
    "ヤマトクラウン", "シナノキング", "エチゴサファイア", "ミナトブリーズ",
    "サドノカガヤキ", "ホッカイファイア", "ユキグニロード", "アガノストリーム",
    "イイヤマブレイブ", "ジョウエツプライド", "カミシバラオー", "ナエバノヒカリ",
    "シンガタモミジ", "アサヒマウント", "ナガオカパール", "コシヒカリスター",
    "サンセイブロッサム", "ニイガタメロディー",
]

# ============================================================
# 新潟結果データ生成 (1R〜10R)
# ============================================================
RESULTS_PLAN = [
    # (rr, pattern, race_name, distance, surface, condition, weather, post_offset_min)
    (1,  "NORMAL", "サラ系3歳新馬",    1200, "芝", "良", "sunny",  -180),
    (2,  "B",      "サラ系3歳未勝利",  1400, "ダ", "良", "sunny",  -160),
    (3,  "E",      "サラ系3歳1勝クラス",1600, "芝", "良", "sunny",  -140),
    (4,  "A",      "サラ系3歳500万下", 1200, "ダ", "稍重","sunny",  -120),
    (5,  "C",      "サラ系3歳上1勝",   1800, "芝", "良", "cloudy", -100),
    (6,  "D",      "サラ系2歳新馬",    1400, "ダ", "稍重","cloudy", -80),
    (7,  "F",      "サラ系3歳上1勝",   1600, "芝", "良", "cloudy", -60),
    (8,  "G",      "メイクデビュー新潟",1200, "ダ", "良", "sunny",  -40),
    (9,  "H",      "サラ系3歳上2勝",   1800, "芝", "良", "sunny",  -20),
    (10, "NORMAL", "新潟記念(GIII)",   2000, "芝", "良", "sunny",   0),
]

# 各レースのオプション: 特払・返還の有無を散らす（実演用）
SPECIAL_PAY = {
    1: ("place", 0),   # 1Rの複勝1着目を特払
}
REFUND_MANUAL = {
    # gen_refund() は pattern=E のときだけ自動返還を生成する。
    # 4R(A) と 7R(F) にも返還を仮挿入して「返還帯」表示の比較材料にする。
    4: {"horse_no_bitmap": "0" * 17 + "1",  # 18番返還
        "bracket_no_bitmap": "0" * 7 + "1", # 8枠返還
        "same_bracket_bitmap": None},
    7: {"horse_no_bitmap": "0" * 6 + "1" + "0" * 11,  # 7番返還
        "bracket_no_bitmap": "0" * 8,
        "same_bracket_bitmap": None},
}


def gen_one_result(rr: int, pattern: str, race_name: str, distance: int,
                    surface: str, condition: str, weather: str,
                    post_offset_min: int) -> dict:
    """1 レース分の結果 JSON を gen_data.gen_results_json 準拠で生成。"""
    race_spec = {
        "organizer_type": "JRA",
        "place_cd": "04",
        "place_name": "新潟",
        "rr": rr,
        "race_id": f"JRA_04_{rr:02d}",
        "race_key": f"新潟{rr}R",
    }
    seed = 4000 + rr
    special = SPECIAL_PAY.get(rr)
    if special:
        data = gen.gen_results_json(race_spec, pattern, seed,
                                     special_pay_bet=special[0],
                                     special_pay_idx=special[1])
    else:
        data = gen.gen_results_json(race_spec, pattern, seed)
    # 返還を手動上書き（指定があれば）
    if rr in REFUND_MANUAL:
        data["refund"] = REFUND_MANUAL[rr]
    # post_time を NOW + offset で設定（参考表示）
    pt = NOW + timedelta(minutes=post_offset_min)
    data["post_time"] = pt.strftime("%H:%M")
    data["post_time_iso"] = pt.strftime("%Y-%m-%dT%H:%M:%S+09:00")
    data["weather"] = weather
    data["surface"] = surface
    data["condition"] = condition
    data["distance"] = distance
    data["race_name"] = race_name
    return data


# ============================================================
# 新潟出走表データ生成 (11R 18頭 / 12R 10頭+出走取消)
# ============================================================
def gen_one_odds(rr: int, horses_n: int, post_offset_min: int,
                 race_name: str, scratched: dict = None,
                 apprentice: dict = None) -> dict:
    """make_race を流用して出走表用 odds JSON を生成。

    apprentice: { horse_no: 減量記号 } で見習・女性騎手減量サンプルを注入。
                記号は ★/▲/△/◇/☆ の 5 種 (JSON 仕様書 v0.6.2 §A.12 準拠)。
    """
    return gen.make_race(
        organizer_type="JRA",
        place_cd="04",
        place_name="新潟",
        rr=rr,
        race_name=race_name,
        weather="sunny", weather_label="晴",
        surface="芝", condition="良", distance=2000, direction="左",
        post_time_offset_min=post_offset_min, horses_n=horses_n,
        name_pool=NIIGATA_NAMES, jockey_pool=gen.JOCKEYS_JRA,
        seed=4000 + rr,
        scratched_horse_nos=(scratched or {}),
        apprentice_horse_nos=(apprentice or {}),
    )


# ============================================================
# 117 schedule 構築
# ============================================================
def build_screen(position: str, races: list) -> dict:
    """4-split の 1 panel（3 races）を構築。"""
    return {
        "position": position,
        "layout_section": position,
        "template": "templates/entries-results-3r.html",
        "place_cd": "04",
        "organizer_type": "JRA",
        "display_pattern_id": 10,
        "display_pattern_name": "3R出走成績",
        "is_auto_extend": False,
        "back_color_code": None,
        "races": [
            {
                "race_id": f"JRA_04_{rr:02d}",
                "race_key": f"新潟{rr}R",
                "post_time_iso": NOW_ISO,
                "data_source": data_source,
            }
            for (rr, data_source) in races
        ],
    }


def build_117_schedule(monitor_id: int, fast: bool) -> dict:
    """monitor=117 4-split 比較ビューのスケジュールを構築。

    Layout:
      P1 = 1R, 2R, 3R (NORMAL, B, E)
      P2 = 4R, 5R, 6R (A, C, D)
      P3 = 7R, 8R, 9R (F, G, H)
      P4 = 10R 結果再掲, 11R 出走表 18頭, 12R 出走表 10頭+取消
    """
    end_minutes = 5 if fast else 480   # fast=5min, normal=8h
    end_iso = (NOW + timedelta(minutes=end_minutes)).strftime("%Y-%m-%dT%H:%M:%S+09:00")

    # 結果は results/、出走表 (11R, 12R) は odds/ を参照
    results_path = lambda rr: f"results/{TODAY}/JRA_04_{rr:02d}.json"
    odds_path    = lambda rr: f"odds/{TODAY}/JRA_04_{rr:02d}.json"

    p1_races = [(1, results_path(1)),  (2, results_path(2)),  (3, results_path(3))]
    p2_races = [(4, results_path(4)),  (5, results_path(5)),  (6, results_path(6))]
    p3_races = [(7, results_path(7)),  (8, results_path(8)),  (9, results_path(9))]
    p4_races = [(10, results_path(10)), (11, odds_path(11)),  (12, odds_path(12))]

    return {
        "server_time": NOW_ISO,
        "monitor_id": monitor_id,
        "display_date": TODAY,
        "slots": [{
            "slot_id": "slot1",
            "start_time": NOW_ISO,
            "end_time": end_iso,
            "layout": "4split",
            "display_pattern_id": 10,
            "display_pattern_name": "3R出走成績比較",
            "screens": [
                build_screen("P1", p1_races),
                build_screen("P2", p2_races),
                build_screen("P3", p3_races),
                build_screen("P4", p4_races),
            ],
        }],
    }


# ============================================================
# Main
# ============================================================
def main():
    results_dir = REPO_ROOT / "results" / TODAY
    odds_dir    = REPO_ROOT / "odds"    / TODAY
    sched_dir   = REPO_ROOT / "schedules" / TODAY
    results_dir.mkdir(parents=True, exist_ok=True)
    odds_dir.mkdir(parents=True, exist_ok=True)
    sched_dir.mkdir(parents=True, exist_ok=True)

    # 結果 1R〜10R
    for plan in RESULTS_PLAN:
        rr = plan[0]
        data = gen_one_result(*plan)
        fname = f"JRA_04_{rr:02d}.json"
        (results_dir / fname).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote results/{TODAY}/{fname}: pattern={plan[1]} entries={len(data['entries'])}")

    # 出走表 11R (18頭) — 5 記号サンプル全種を含む
    # 馬番 3=★ / 5=▲ / 8=△ / 12=◇ / 15=☆ で 5 記号すべて jockey 行内に表示
    odds_11 = gen_one_odds(11, 18, post_offset_min=20,
                            race_name="新潟記念ステークス(オープン)",
                            apprentice={3: '★', 5: '▲', 8: '△',
                                        12: '◇', 15: '☆'})
    (odds_dir / "JRA_04_11.json").write_text(
        json.dumps(odds_11, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote odds/{TODAY}/JRA_04_11.json: 18頭出走表 (5記号サンプル: 3★/5▲/8△/12◇/15☆)")

    # 出走表 12R (10頭、馬番7に出走取消、馬番2に ◇ 女性騎手サンプル)
    odds_12 = gen_one_odds(12, 10, post_offset_min=40,
                            race_name="関屋記念(GIII)",
                            scratched={7: 1},
                            apprentice={2: '◇'})
    (odds_dir / "JRA_04_12.json").write_text(
        json.dumps(odds_12, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote odds/{TODAY}/JRA_04_12.json: 10頭出走表+出走取消(7番)+◇(2番)")

    # 117 schedule
    sched = build_117_schedule(117, fast=False)
    (sched_dir / "117.json").write_text(
        json.dumps(sched, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote schedules/{TODAY}/117.json: 4-split 新潟1R-12R 比較ビュー")

    sched_fast = build_117_schedule(117, fast=True)
    (sched_dir / "117_fast.json").write_text(
        json.dumps(sched_fast, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote schedules/{TODAY}/117_fast.json: fast版")


if __name__ == "__main__":
    main()
