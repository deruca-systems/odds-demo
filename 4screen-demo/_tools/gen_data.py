"""
odds-demo 用サンプルJSONジェネレータ

「ある1日の開催」を静的JSONだけで再現する。
- NOW を基準に post_time を「実行時刻 + N分」の絶対時刻で配置
- 3スロット分の schedule を slots[] 配列で出力（通常60分間隔版 + 短縮5分間隔版）
- 9レース分のオッズJSONを生成

実行: python src/odds-demo/_tools/gen_data.py
"""
import json
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

# path-date-folder (2026-04-20): v0.5 §1.5 ファイル配置規約に準拠し、
#   スケジュール・オッズ・変更情報を {種別}/{YYYYMMDD}/ 配下に統一配置する。
SCHEDULES_OUT_BASE = Path(__file__).resolve().parent.parent / "schedules"
ODDS_OUT_BASE      = Path(__file__).resolve().parent.parent / "odds"
CHANGES_OUT_BASE   = Path(__file__).resolve().parent.parent / "changes"

# 旧 data/ 配下（移行元、main() 冒頭で schedule_*.json / odds_*.json を掃除）
LEGACY_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# --- 時刻基準 ---
JST = timezone(timedelta(hours=9))
NOW = datetime.now(JST)
NOW_ISO = NOW.strftime("%Y-%m-%dT%H:%M:%S+09:00")
TODAY_YYYYMMDD = NOW.strftime("%Y%m%d")  # 日付フォルダ名・display_date 値の双方に使用

# --- field-rename-v0.5 (2026-04-20): 表示文字列 → v0.5 §4.3 INT コード変換 ---
# v0.5 付録A.7〜A.10 の値体系に準拠。プロト RACE_DEFINITIONS は可読性重視で
# string（"sunny"/"芝"/"良"/"右"）で記述されているため、make_race 内で INT 化して
# JSON に出力する。本番バッチは直接 INT 生成するため本マップ不要。
WEATHER_STR_TO_CD = {
    "sunny": 1, "cloudy": 2, "light-rain": 3, "rain": 4,
    "light-snow": 5, "snow": 6,
}
TRACK_STR_TO_CD = {
    "ダ": 0, "芝": 1, "サ": 2, "障": 3,
}
TRACK_COND_STR_TO_CD = {
    "良": 1, "稍重": 2, "重": 3, "不良": 4,
}
COURSE_DIRECTION_STR_TO_CD = {
    "右": 1, "左": 2, "直線": 3,
}

# --- 3R-entries-results-phase2 (2026-04-21): 出走成績 3R 表示 ---
# Phase 1 設計提案書 付録 A: 着差コード → 表示名変換（NAR 別紙1-20-1 項目512 / JRA 項番2102）
# Phase 1 設計提案書 付録 B: 異常区分コード → accident_type（JRA 項番2101）
MARGIN_CD_TO_NAME_NAR = {
    "01": "1", "02": "2", "03": "3", "04": "4", "05": "5",
    "06": "6", "07": "7", "08": "8", "09": "9",
    "10": "大差", "11": "同着", "12": "ハナ", "13": "アタマ", "14": "クビ",
    "15": "1/2", "16": "3/4", "17": "1 1/2", "18": "2 1/2",
    # "19": 空き
    "20": "レコード", "21": "1/4", "22": "1 1/4", "23": "1 3/4",
    "24": "3 1/2", "25": "10",
}
MARGIN_CD_TO_NAME_JRA = {
    "_12": "1/2", "_34": "3/4",
    "1__": "1", "112": "1 1/2", "114": "1 1/4", "134": "1 3/4",
    "2__": "2", "212": "2 1/2",
    "3__": "3", "312": "3 1/2",
    "4__": "4", "5__": "5", "6__": "6", "7__": "7", "8__": "8", "9__": "9",
    "A__": "アタマ", "D__": "同着", "H__": "ハナ", "K__": "クビ",
    "T__": "大差", "Z__": "10",
}

def margin_cd_to_name(organizer_type: str, cd):
    """着差コード → 表示文字列。None・未定義は None 返却。"""
    if cd is None:
        return None
    cd = str(cd)
    if organizer_type == "NAR":
        return MARGIN_CD_TO_NAME_NAR.get(cd)
    elif organizer_type == "JRA":
        if cd.strip() == "":
            return None  # "sp"（海外・地方既定値）
        return MARGIN_CD_TO_NAME_JRA.get(cd.replace(" ", "_"))
    return None

# 異常区分コード（JRA 項番2101）→ accident_type
ACCIDENT_TYPE_JRA = {
    0: None, 1: "出走取消", 2: "発走除外", 3: "競走除外",
    4: "競走中止", 5: "失格", 6: "落馬再騎乗", 7: "降着",
}
def accident_type_from_jra(code):
    return ACCIDENT_TYPE_JRA.get(code)

def accident_type_from_nar(is_scratched: int):
    """NAR 暫定マッピング（R-5: Phase 2 で内山様確認予定）"""
    if is_scratched == 1: return "出走取消"
    if is_scratched == 2: return "競走除外"
    return None


def now_plus_min(minutes: int) -> str:
    """NOW から minutes 分後の ISO 8601 (+09:00) 文字列"""
    return (NOW + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S+09:00")


def now_plus_hhmm(minutes: int) -> str:
    """NOW から minutes 分後の HH:MM 文字列（日跨ぎは考慮せず表示用）"""
    return (NOW + timedelta(minutes=minutes)).strftime("%H:%M")


# --- 枠割 ---
def frame_assign(n: int) -> list:
    """N頭 → 枠番（1..8）のリスト。日本競馬標準。"""
    assert 1 <= n <= 18
    counts = [1] * 8 if n >= 8 else [1] * n + [0] * (8 - n)
    remaining = max(0, n - 8)
    i = 7
    while remaining > 0 and any(c < 2 for c in counts):
        if counts[i] < 2:
            counts[i] += 1
            remaining -= 1
        i -= 1
        if i < 0:
            break
    i = 7
    while remaining > 0:
        counts[i] += 1
        remaining -= 1
        i -= 1
    result = []
    for fi, c in enumerate(counts, start=1):
        result.extend([fi] * c)
    return result


# ========================================================================
# H-01/H-02/H-08 (2026-04-17): JSONスキーマ拡張用の定数・ヘルパ
# ========================================================================

# H-02: 取消・除外の事由名称（NAR 実運用を参考に抜粋）
SCRATCH_REASONS_CANCEL = [  # is_scratched=1（出走取消）用
    "感冒のため", "フレグモーネのため", "故障のため", "疾病のため",
    "けいれんのため", "跛行のため",
]
SCRATCH_REASON_EXCLUDE = "競走除外"  # is_scratched=2（競走除外）固定

# H-02/H-08: 騎手変更事由コード表（NAR 実運用、2026-04-17 及川共有）
CHG_REASON_MAP = {
    "00": "（誤入力の取消）",
    "01": "公正保持",
    "02": "疾病",
    "03": "事故",
    "04": "騎乗停止",
    "05": "騎手負傷",
    "06": "検査",
    "07": "家事都合",
    "08": "変更命令",
    "09": "その他",
}

# H-02: 調教師名プール（サンプル、日本人名風）
TRAINER_NAMES = [
    "山田厩舎", "佐藤厩舎", "鈴木厩舎", "田中厩舎", "高橋厩舎",
    "渡辺厩舎", "伊藤厩舎", "小林厩舎", "中村厩舎", "加藤厩舎",
    "斎藤厩舎", "吉田厩舎", "山本厩舎", "松本厩舎", "井上厩舎",
    "木村厩舎", "林厩舎", "清水厩舎",
]

# H-08: chg_type（変更種別）コード表
CHG_TYPE_MAP = {
    1: "騎手変更",
    2: "出走取消",
    3: "競走除外",
    4: "発走時刻変更",
}

# H-02: 減量記号（見習騎手用）
GENRYOKIGO_POOL = ["★", "▲", "△", "☆"]


def _default_fwt(sex: str, age: int, rng: random.Random) -> float:
    """性別・馬齢に応じた斤量（fwt、小数形式）を生成。牝馬は2kg軽減。"""
    if age <= 3:
        base = 54.0 + rng.uniform(0.0, 2.0)
    else:
        base = 55.0 + rng.uniform(0.0, 3.0)
    if sex == "牝":
        base -= 2.0
    return round(base, 1)


# --- 馬データ ---
def make_horses(n: int, name_pool: list, jockey_pool: list, seed: int,
                scratched_horse_nos: dict = None,
                jockey_change_horse_no: int = None,
                apprentice_horse_nos: dict = None):
    """
    scratched_horse_nos: { horse_no: is_scratched値 } の dict
      - 1 = 出走取消（NAR: SU1取消 / JRA: A301）
      - 2 = 競走除外（JRA: A302）
      未指定の馬は is_scratched=0（正常出走）となる。
    指示書08: 表示側は is_scratched=1/2 を「取消」「除外」ラベルで区別し、
    どちらも人気・次点算出・マトリクス表示からは同じ扱いで除外する。
    オッズ値自体は通常通り生成し、表示側でラベル差替・空白化する。

    H-02 (2026-04-17): 以下の拡張項目を追加
      sex / age / fwt / cnm / wt2 / scratch_reason / jockey_changed /
      org_jockey_nm / new_jockey_nm / chg_reason_cd / org_genryokigo / new_genryokigo
      （v0.5 §4.4.3 命名統一: 2026-04-20 json-v05-align にて chg_jockey_nm → new_jockey_nm。
        ローカル変数は chg_jockey_nm のまま DB 対応 crc.chg_jockey_nm を反映、JSON 出力時のみ new_ へ変換）

    jockey_change_horse_no: 騎手変更を発生させる馬番（None=発生なし）
    apprentice_horse_nos: { horse_no: 減量記号 } の dict（見習騎手サンプル）
    """
    rng = random.Random(seed)
    frames = frame_assign(n)
    odds_win = [round(rng.uniform(1.8, 180.0), 1) for _ in range(n)]
    sorted_by_odds = sorted(range(n), key=lambda i: odds_win[i])
    is_popular_set = set(sorted_by_odds[:3])
    is_secondary_set = set(sorted_by_odds[3:5])
    scratched = scratched_horse_nos or {}
    apprentices = apprentice_horse_nos or {}
    horses = []
    for i in range(n):
        wmin = round(odds_win[i] * rng.uniform(0.25, 0.45), 1)
        wmax = round(odds_win[i] * rng.uniform(0.5, 0.8), 1)
        wmin = max(1.1, wmin)
        wmax = max(wmin + 0.1, wmax)
        horse_no = i + 1

        # --- H-02 拡張項目の生成 ---
        # 性別: 牡60% / 牝35% / セ5%
        r = rng.random()
        sex = "牡" if r < 0.60 else ("牝" if r < 0.95 else "セ")
        # 馬齢: 3〜6歳中心
        age = rng.choices([3, 4, 5, 6], weights=[30, 40, 20, 10])[0]
        # 斤量（小数形式 kg）
        fwt = _default_fwt(sex, age, rng)
        # 調教師名
        cnm = TRAINER_NAMES[(i + seed) % len(TRAINER_NAMES)]
        # 前走馬体重（現weight ±10kg）
        weight = 440 + rng.randint(0, 80)
        wt2 = weight + rng.randint(-10, 10)

        # 取消・除外事由
        is_sc = int(scratched.get(horse_no, 0))
        if is_sc == 1:
            scratch_reason = SCRATCH_REASONS_CANCEL[(i + seed) % len(SCRATCH_REASONS_CANCEL)]
        elif is_sc == 2:
            scratch_reason = SCRATCH_REASON_EXCLUDE
        else:
            scratch_reason = None

        # 騎手変更情報（指示書 §3.4: サンプルレース1レース程度で発生）
        current_jockey = jockey_pool[i % len(jockey_pool)]
        if jockey_change_horse_no == horse_no and is_sc == 0:
            # 別の騎手を変更後の名前として選択
            new_idx = (i + 7) % len(jockey_pool)
            if jockey_pool[new_idx] == current_jockey:
                new_idx = (new_idx + 1) % len(jockey_pool)
            jockey_changed = True
            org_jockey_nm = current_jockey
            chg_jockey_nm = jockey_pool[new_idx]
            chg_reason_cd = "05"  # 騎手負傷（NAR実運用）
            displayed_jockey = chg_jockey_nm
        else:
            jockey_changed = False
            org_jockey_nm = None
            chg_jockey_nm = None
            chg_reason_cd = None
            displayed_jockey = current_jockey

        # 減量記号
        apprentice_mark = apprentices.get(horse_no)
        org_genryokigo = apprentice_mark if apprentice_mark else None
        # 騎手変更発生時は新騎手側の記号（サンプルでは None）、変更なしなら同値
        new_genryokigo = org_genryokigo if not jockey_changed else None
        # 2026-04-30 session3 追加: JSON 仕様書 v0.6.2 §4.5.4 entries[] 用の単一 `genryokigo` フィールド。
        # crc.new_genryokigo を優先、なければ crc.org_genryokigo （仕様書の定義どおり）。
        genryokigo = new_genryokigo if new_genryokigo else org_genryokigo

        horses.append({
            "frame_no": frames[i],
            "horse_no": horse_no,
            "horse_name": name_pool[i % len(name_pool)],
            "jockey": displayed_jockey,
            "weight": weight,
            "weight_diff": rng.randint(-8, 10),
            "win_odds": odds_win[i],
            "place_odds_min": wmin,
            "place_odds_max": wmax,
            "is_popular": i in is_popular_set,
            "is_secondary": i in is_secondary_set,
            "is_scratched": is_sc,
            # --- H-02 拡張項目（SCR-INF-001/003 で使用予定、現状テンプレは未参照）---
            "sex": sex,
            "age": age,
            "fwt": fwt,
            "cnm": cnm,
            "wt2": wt2,
            "scratch_reason": scratch_reason,
            "jockey_changed": jockey_changed,
            "org_jockey_nm": org_jockey_nm,
            # json-v05-align (2026-04-20): v0.5 §4.4.3 命名統一（案A）。
            #   DB 対応 crc.chg_jockey_nm は不変、JSON 出力時のみ new_jockey_nm に変換。
            "new_jockey_nm": chg_jockey_nm,
            "chg_reason_cd": chg_reason_cd,
            "org_genryokigo": org_genryokigo,
            "new_genryokigo": new_genryokigo,
            # JSON 仕様書 v0.6.2 §4.5.4: entries[].genryokigo (単一フィールド) を追加
            "genryokigo": genryokigo,
        })
    return horses


def make_frame_odds(horses, seed: int):
    rng = random.Random(seed + 100)
    frame_has = {}
    for h in horses:
        frame_has.setdefault(h["frame_no"], []).append(h["horse_no"])
    out = []
    for a in range(1, 9):
        for b in range(a, 9):
            if a not in frame_has or b not in frame_has:
                continue
            if a == b and len(frame_has[a]) < 2:
                continue
            out.append({
                "frame_a": a, "frame_b": b,
                "odds": round(rng.uniform(3.0, 300.0), 1)
            })
    out.sort(key=lambda e: e["odds"])
    for e in out[:5]:
        e["is_popular"] = True
    for e in out[5:]:
        e["is_popular"] = False
    out.sort(key=lambda e: (e["frame_a"], e["frame_b"]))
    return out


def make_matrices(horses, seed: int):
    rng = random.Random(seed + 200)
    n = len(horses)
    um, wd = [], []
    for i in range(n):
        for j in range(i + 1, n):
            a = horses[i]["horse_no"]
            b = horses[j]["horse_no"]
            ao = horses[i]["win_odds"]
            bo = horses[j]["win_odds"]
            umaren = round(ao * bo * rng.uniform(0.25, 0.50), 1)
            wmin = round(umaren * rng.uniform(0.15, 0.30), 1)
            wmax = round(umaren * rng.uniform(0.35, 0.55), 1)
            wmin = max(1.1, wmin)
            wmax = max(wmin + 0.2, wmax)
            um.append({"a": a, "b": b, "odds": umaren})
            wd.append({"a": a, "b": b, "min": wmin, "max": wmax})
    return um, wd


# H-03 (2026-04-19): 枠単（frame_utan）オッズ生成
# field-rename-utan (2026-04-20): 旧 gen_frame_umatan から改名。
#   命名注: `utan` = waku-tan（枠単）の短縮形。
#   馬単（uma-tan）は umatan_matrix / umatan_popular 側に格納。混同注意。
# 仕様（2026-04-19 及川指示で改訂）:
#   - `enabled=False` のレースは空配列（枠単発売なし）。親 index.html はページング停止
#   - 同枠組合せ（frame_a == frame_b）は、その枠が2頭以上のときのみ出力
#     例: 8頭立て = 1〜8枠に1頭ずつ → 同枠組合せは全て存在しない
#     例: 10頭立て = 7-8枠が2頭ずつ → 7-7, 8-8 は存在、1-1〜6-6 は存在しない
#   - 相手枠が出走頭数ゼロの枠は組合せ自体が存在しない（通常、8頭以上立てなら全枠使われる）
def gen_frame_utan(horses: list, seed: int, enabled: bool = True, num_frames: int = 8):
    if not enabled:
        return []
    # 枠ごとの頭数
    frame_count = {i: 0 for i in range(1, num_frames + 1)}
    for h in horses:
        fn = h.get("frame_no")
        if fn in frame_count:
            frame_count[fn] += 1
    rng = random.Random(seed + 600)
    entries = []
    for fa in range(1, num_frames + 1):
        if frame_count[fa] == 0:
            continue
        for fb in range(1, num_frames + 1):
            if frame_count[fb] == 0:
                continue
            if fa == fb and frame_count[fa] < 2:
                continue  # 同枠1頭のみの場合は同枠組合せなし
            odds = round(rng.uniform(4.5, 1500.0), 1)
            entries.append({
                "frame_a": fa,
                "frame_b": fb,
                "odds": odds,
                "is_popular": odds < 10.0,
            })
    return entries


def make_umatan_matrix(horses, seed: int):
    """
    馬単オッズ行列: 順序のある全組合せ (a, b) where a != b
    a = 1着の馬番, b = 2着の馬番。サイズは N*(N-1)。
    馬連オッズの約2倍レンジで分散させる（1着・2着の順序に応じて強弱）。
    """
    rng = random.Random(seed + 500)
    n = len(horses)
    out = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a = horses[i]["horse_no"]
            b = horses[j]["horse_no"]
            ao = horses[i]["win_odds"]
            bo = horses[j]["win_odds"]
            odds = round(ao * bo * rng.uniform(0.40, 0.90), 1)
            out.append({"a": a, "b": b, "odds": odds})
    return out


def make_popular_list(horses, comb_size: int, count: int, seed: int):
    # H-06 (2026-04-17): 取消・除外馬（is_scratched != 0）を含む組合せは人気順に含めない。
    # サンプリング元（ranked / top / 全馬）から取消馬インデックスを除外することで、
    # 生成段階で「取消馬を含むエントリ」が絶対に作られない → rank/is_popular も連番で正しく付与される。
    # 表示側の filterScratchedFromPopular（common.js）は防御的二重対策として残置する。
    rng = random.Random(seed + 300 + comb_size)
    valid_indices = [i for i, h in enumerate(horses) if not h.get("is_scratched")]
    n_valid = len(valid_indices)
    if n_valid < comb_size:
        return []
    ranked = sorted(valid_indices, key=lambda i: horses[i]["win_odds"])
    top = ranked[: min(n_valid, 8)]
    seen = set()
    entries = []
    max_unique = 1
    for k in range(comb_size):
        max_unique *= (n_valid - k)
    for k in range(1, comb_size + 1):
        max_unique //= k
    count = min(count, max_unique)
    while len(entries) < count:
        picks = tuple(sorted(rng.sample(top if rng.random() < 0.7 else valid_indices, comb_size)))
        if picks in seen:
            continue
        seen.add(picks)
        entries.append(picks)
    out = []
    for idx, picks in enumerate(entries, start=1):
        nums = [horses[i]["horse_no"] for i in picks]
        odds = round(6.0 + idx * rng.uniform(2.0, 8.0), 1)
        e = {"rank": idx, "a": nums[0], "b": nums[1]}
        if comb_size >= 3:
            e["c"] = nums[2]
        e["odds"] = odds
        e["is_popular"] = idx <= 3
        out.append(e)
    return out


def make_ordered_popular_list(horses, comb_size: int, count: int, seed: int):
    # H-06 (2026-04-17): make_popular_list と同じ方針で、サンプリング元から取消馬を除外する。
    rng = random.Random(seed + 400 + comb_size)
    valid_indices = [i for i, h in enumerate(horses) if not h.get("is_scratched")]
    n_valid = len(valid_indices)
    if n_valid < comb_size:
        return []
    ranked = sorted(valid_indices, key=lambda i: horses[i]["win_odds"])
    top = ranked[: min(n_valid, 8)]
    seen = set()
    entries = []
    max_unique = 1
    for k in range(comb_size):
        max_unique *= (n_valid - k)
    count = min(count, max_unique)
    while len(entries) < count:
        size = comb_size
        if rng.random() < 0.7 and len(top) >= size:
            picks = rng.sample(top, size)
        else:
            picks = rng.sample(valid_indices, size)
        key = tuple(picks)
        if key in seen:
            continue
        seen.add(key)
        entries.append(picks)
    out = []
    for idx, picks in enumerate(entries, start=1):
        nums = [horses[i]["horse_no"] for i in picks]
        odds = round(8.0 + idx * rng.uniform(3.0, 15.0), 1)
        e = {"rank": idx, "a": nums[0], "b": nums[1]}
        if comb_size >= 3:
            e["c"] = nums[2]
        e["odds"] = odds
        e["is_popular"] = idx <= 3
        out.append(e)
    return out


def make_race(
    *,
    # field-rename-v0.5 (2026-04-20): v0.5 §4.3 命名に統一
    organizer_type: str,
    place_cd: str,            # 場コード（例: "09"=阪神, "45"=船橋）
    place_name: str,          # 場名（例: "阪神"）
    rr: int,                  # レース番号
    race_name: str,
    weather: str,             # 入力は可読文字列、出力時に weather_cd (INT) に変換
    weather_label: str,
    surface: str,             # 入力は "芝"/"ダ"/..、出力時に track_cd (INT) に変換
    condition: str,           # 入力は "良"/"稍重"/..、出力時に track_cond_cd (INT) に変換
    distance: int,
    direction: str,           # 入力は "右"/"左"/"直線"、出力時に course_direction (INT) に変換
    post_time_offset_min: int,
    horses_n: int,
    name_pool: list,
    jockey_pool: list,
    seed: int,
    is_previous_day: bool = False,
    scratched_horse_nos: dict = None,
    odds_status: int = 0,             # H-01: 0=発売中 / 1=確定 / 2=レース中止 / 3=開催中止
    jockey_change_horse_no: int = None, # H-02
    apprentice_horse_nos: dict = None,  # H-02: {horse_no: genryokigo}
    has_frame_utan: bool = True,      # H-03 (2026-04-19): False で枠単発売なしサンプル
    grade: str = None,                  # json-v05-align (2026-04-20): v0.5 §4.3 grade（G1/G2/G3/D/L/None）
):
    assert organizer_type in ("JRA", "NAR"), f"organizer_type must be 'JRA' or 'NAR', got {organizer_type!r}"
    assert odds_status in (0, 1, 2, 3), f"odds_status must be 0-3, got {odds_status}"
    horses = make_horses(horses_n, name_pool, jockey_pool, seed,
                         scratched_horse_nos=scratched_horse_nos,
                         jockey_change_horse_no=jockey_change_horse_no,
                         apprentice_horse_nos=apprentice_horse_nos)
    fo = make_frame_odds(horses, seed)
    um, wd = make_matrices(horses, seed)
    post_time_hhmm = now_plus_hhmm(post_time_offset_min)
    post_time_iso = now_plus_min(post_time_offset_min)
    # deadline_min は参考値（発走2分前想定）。実運用はクライアント側で post_time から動的算出。
    reference_deadline = max(0, post_time_offset_min - 2)
    # json-v05-align (2026-04-20): v0.5 §4.3 の deadline（HH:MM）/ deadline_iso（ISO 8601）を追加。
    #   プロトでは締切 = 発走 2 分前として算出（本番は DB csc.ct を参照）。
    deadline_offset_min = post_time_offset_min - 2
    deadline_hhmm = now_plus_hhmm(deadline_offset_min)
    deadline_iso = now_plus_min(deadline_offset_min)
    return {
        "server_time": NOW_ISO,
        "race": {
            # field-rename-v0.5 (2026-04-20): v0.5 §4.3 命名統一
            "organizer_type": organizer_type,
            "place_cd": place_cd,
            "place_name": place_name,
            "rr": rr,
            "race_name": race_name,
            "race_class": "",
            # json-v05-align (2026-04-20): v0.5 §4.3 grade（null 許容、重賞以外は None）
            "grade": grade,
            # deadline_min は参考値、後方互換のため残存（common.js 内部算出とは独立）
            "deadline_min": reference_deadline,
            # json-v05-align (2026-04-20): v0.5 §4.3 deadline（HH:MM）/ deadline_iso（ISO 8601）追加
            "deadline": deadline_hhmm,
            "deadline_iso": deadline_iso,
            "post_time": post_time_hhmm,
            "post_time_iso": post_time_iso,
            # field-rename-v0.5 (2026-04-20): 文字列 → INT コード変換
            "weather_cd": WEATHER_STR_TO_CD.get(weather, 1),
            "weather_label": weather_label,
            "track_cd": TRACK_STR_TO_CD.get(surface, 0),
            "track_cond_cd": TRACK_COND_STR_TO_CD.get(condition, 1),
            "track_cond_dirt_cd": None,   # JRA 限定・本プロトでは全 null
            "distance": distance,
            "course_direction": COURSE_DIRECTION_STR_TO_CD.get(direction, 1),
            "pn": horses_n,               # v0.5 §4.3 出走頭数（取消・除外含む予定頭数）
            "is_previous_day": is_previous_day,
            "odds_status": odds_status,  # H-01 追加
            # H-03 (2026-04-19): 枠単オッズ。race オブジェクト内に配置（指示書準拠）。
            # 仕様改訂 (2026-04-19): 同枠組合せは2頭以上の枠のみ、発売なしは空配列。
            "frame_utan": gen_frame_utan(horses, seed, enabled=has_frame_utan),
        },
        "horses": horses,
        "frame_odds": fo,
        "umaren_matrix": um,
        "umatan_matrix": make_umatan_matrix(horses, seed),
        "wide_matrix": wd,
        "umaren_popular":    make_popular_list(horses, 2, 30, seed),
        "umatan_popular":    make_ordered_popular_list(horses, 2, 30, seed),
        "trio_popular":      make_popular_list(horses, 3, 30, seed),
        "trifecta_popular":  make_ordered_popular_list(horses, 3, 30, seed),
    }


# --- 馬名/騎手プール ---
FUNABASHI_NAMES = [
    "カイロス", "プロミネント", "ドリームボート", "シルバーアロー",
    "アズラエル", "エテルニタス", "ブルーグレイス", "サンライズゲート",
    "リバーダンス", "ファルコンハート", "ノーブルスター", "グランドフィナーレ",
]
NAGOYA_NAMES = [
    "ミスティックトレイル", "コスモサンダー", "ファーストライト", "アビスクィーン",
    "ベガサスワン", "テンペストルーラー", "セレスティアル", "ロイヤルサテライト",
    "ウィンディゲイル", "エクリプスランナー", "ノクターンビート", "オーロラブライト",
    "シルバーブレイズ", "ゴールデンディスク", "クリムゾンレイヴン", "アクアマリンボーイ",
]
TOKYO_NAMES = [
    "ロードトレイル", "フリートストリートダンサー", "エコロマーズ", "ハートホイップ",
    "レオテミス", "アミーラトアルザマーン", "ベイビーキッス", "ミルテンベルク",
    "シュヴェルトライテ", "エマヌエーレ", "ナムラローズマリー", "ブリックワーク",
    "ハピネスアゲン", "フォルテム", "トーラスシャイン", "ジャスパーディビネ",
    "スコーピオン", "ジュンヴァンケット",
]
NAKAYAMA_NAMES = [
    "ゼウスオブジャパン", "アクロポリス", "ミネルヴァ", "アポロンアロー",
    "ヘラクレスキング", "ディオニュソス", "アテナプライム", "アルテミスムーン",
    "ヘスティアフレイム", "ポセイドンウェーブ", "ヘパイストス", "アフロディーテ",
    "クロノスライズ", "レトーオブライト", "タイタンズフィスト", "エウロパストーム",
]
HANSHIN_NAMES = [
    "ローレルブレイブ", "シルヴァンレジェンド", "ミラージュエクセル", "セレクトブルーム",
    "アストラルフォース", "イグナイトソード", "ベルナデッタ", "クリスタルノート",
    "ヴェンデッタロア", "ノースサファイア", "ブライトリベラル", "カスケードエコー",
    "グランリヴァージュ", "テンペラメント", "フォルトゥナリオ", "マリアージュ",
    "プレシャスリオン", "アンセムフレイム",
]
SAGA_NAMES = [
    "ウィンフォルテ", "サクラノホシ", "ラッキーフジ", "キタノキセキ",
    "テイオーブライト", "フジノメイカ", "ハナビシルーン", "ツキノコエ",
    "ミヤビノホシ", "シンザンブレイブ", "タケルオーザ", "コウリュウキング",
]
# 指示書09 T6: L字レイアウト+動画デモ（monitor_id=0102）用の門別馬名プール
# 2026-04-17: 18頭立てに対応するため 12→18 個に拡張
MONBETSU_NAMES = [
    "ノーザンクラウド", "アイスフィヨルド", "スノーラプソディ", "ポラリスブレーブ",
    "オホーツクスプリンター", "ベイウィンド", "シラカバコート", "マリンサファイア",
    "ウェーブブリッジ", "ミラーレイク", "ハルニレチャンプ", "フロストムーン",
    "タンチョウスカイ", "ブリザードローズ", "オーロラマジック", "シラハマタイド",
    "エゾノカゼ", "ユキシラベ",
]
JOCKEYS_NAR = [
    "山本聡哉", "森泰斗", "本田正重", "町田直希",
    "笹川翼", "張田京", "和田譲治", "御神本訓史",
    "矢野貴之", "吉原寛人", "左海誠二", "野畑凌",
    "張田昂", "真島大輔", "山中悠希", "赤岡修次",
]
JOCKEYS_JRA = [
    "武豊", "C.ルメール", "川田将雅", "横山武史",
    "戸崎圭太", "松山弘平", "D.レーン", "岩田望来",
    "M.デムーロ", "池添謙一", "福永祐一", "北村友一",
    "三浦皇成", "横山和生", "浜中俊", "松若風馬",
    "丹内祐次", "亀田温心",
]


# --- レース定義 ---
# 各レース: (file, race定義) のタプル
# post_time_offset_min は NOW からの分数
RACE_DEFINITIONS = [
    # ---- slot 1: 午前の部 ----
    # 船橋1R: カットイン CUT-001/CUT-002 実演用に「発走直前」設定。
    #   NOW+3分 発走 → 表示締切 NOW+30秒 → slot1 開始直後に CUT-001 発火、30秒後に CUT-002 発火
    # 船橋2R/3R: オッズ画面を十分見せるため「発走時刻 HH:MM」表示のまま slot1 を過ごす長めの余裕。
    #   fast モード slot1 = 5分 の範囲外なので、slot1 中はずっと pre モード（発走時刻表示）。
    # レース番号順と発走時刻順が一致するよう 1R < 2R < 3R で並べる。
    ("odds_NAR_45_01.json", dict(
        organizer_type="NAR", place_cd="45",
        place_name="船橋", rr=1, race_name="サラ系3歳未勝利",
        weather="sunny", weather_label="晴",
        surface="ダ", condition="良", distance=1200, direction="左",
        post_time_offset_min=3, horses_n=8,
        name_pool=FUNABASHI_NAMES, jockey_pool=JOCKEYS_NAR, seed=101,
    )),
    ("odds_NAR_45_02.json", dict(
        organizer_type="NAR", place_cd="45",
        place_name="船橋", rr=2, race_name="サラ系3歳新馬",
        weather="sunny", weather_label="晴",
        surface="ダ", condition="良", distance=1400, direction="左",
        post_time_offset_min=10, horses_n=11,
        name_pool=FUNABASHI_NAMES, jockey_pool=JOCKEYS_NAR, seed=102,
        # H-02 (2026-04-17): 見習騎手サンプル（馬番4に減量記号 ★）
        apprentice_horse_nos={4: "★"},
    )),
    ("odds_NAR_45_03.json", dict(
        organizer_type="NAR", place_cd="45",
        place_name="船橋", rr=3, race_name="サラ系3歳1勝クラス",
        weather="cloudy", weather_label="曇",
        surface="ダ", condition="稍重", distance=1600, direction="左",
        post_time_offset_min=15, horses_n=12,
        name_pool=FUNABASHI_NAMES, jockey_pool=JOCKEYS_NAR, seed=103,
    )),
    # 指示書08: 取消馬デモ用 8頭レース（5番を出走取消）
    #   slot1 内で「既存4テンプレ（単勝複勝枠連 / 馬連ワイド / 人気1-15 / 人気16-30）」を
    #   取消馬入りで見せる。post_time は 1R(3分)と 2R(10分)の間に配置。
    ("odds_NAR_45_04.json", dict(
        organizer_type="NAR", place_cd="45",
        place_name="船橋", rr=4, race_name="サラ系3歳500万下",
        weather="cloudy", weather_label="曇",
        surface="ダ", condition="良", distance=1200, direction="左",
        post_time_offset_min=8, horses_n=8,
        name_pool=FUNABASHI_NAMES, jockey_pool=JOCKEYS_NAR, seed=104,
        scratched_horse_nos={5: 1},  # 5番: 出走取消
    )),
    # ---- slot 2: 午後の部 ----
    ("odds_NAR_49_02.json", dict(
        organizer_type="NAR", place_cd="49",
        place_name="名古屋", rr=2, race_name="サラ系2歳新馬",
        weather="cloudy", weather_label="曇",
        surface="ダ", condition="稍重", distance=1200, direction="右",
        post_time_offset_min=60, horses_n=13,
        name_pool=NAGOYA_NAMES, jockey_pool=JOCKEYS_NAR, seed=202,
    )),
    ("odds_NAR_49_07.json", dict(
        organizer_type="NAR", place_cd="49",
        place_name="名古屋", rr=7, race_name="サラ系2歳未勝利",
        weather="light-rain", weather_label="小雨",
        surface="ダ", condition="重", distance=1400, direction="右",
        post_time_offset_min=63, horses_n=14,
        name_pool=NAGOYA_NAMES, jockey_pool=JOCKEYS_NAR, seed=207,
        # H-02: 見習騎手サンプル（馬番7に減量記号 ▲）
        apprentice_horse_nos={7: "▲"},
    )),
    ("odds_NAR_49_08.json", dict(
        organizer_type="NAR", place_cd="49",
        place_name="名古屋", rr=8, race_name="サラ系3歳オープン",
        weather="rain", weather_label="雨",
        surface="ダ", condition="不良", distance=1800, direction="右",
        post_time_offset_min=66, horses_n=16,
        name_pool=NAGOYA_NAMES, jockey_pool=JOCKEYS_NAR, seed=208,
    )),
    ("odds_NAR_49_09.json", dict(
        organizer_type="NAR", place_cd="49",
        place_name="名古屋", rr=9, race_name="サラ系3歳2勝クラス",
        weather="rain", weather_label="雨",
        surface="ダ", condition="不良", distance=1200, direction="右",
        post_time_offset_min=69, horses_n=10,
        name_pool=NAGOYA_NAMES, jockey_pool=JOCKEYS_NAR, seed=209,
        # H-03 (2026-04-19): 枠単発売なしサンプル。single-screen.html のページング停止確認用
        has_frame_utan=False,
    )),
    # ---- NAR_41 佐賀（changes-info デモ用: 騎手変更・出走取消を含む） ----
    # changes-info 画面が参照する changes/{YYYYMMDD}/NAR_41.json を自動生成するためのテンプレート。
    # post_time は slot2 末尾〜slot3 前半に配置（offset 72〜78 分）。
    ("odds_NAR_41_02.json", dict(
        organizer_type="NAR", place_cd="41",
        place_name="佐賀", rr=2, race_name="サラ系3歳未勝利",
        weather="sunny", weather_label="晴",
        surface="ダ", condition="良", distance=900, direction="右",
        post_time_offset_min=72, horses_n=9,
        name_pool=SAGA_NAMES, jockey_pool=JOCKEYS_NAR, seed=4102,
        jockey_change_horse_no=3,  # 3番騎手変更（changes-info デモ用）
    )),
    ("odds_NAR_41_03.json", dict(
        organizer_type="NAR", place_cd="41",
        place_name="佐賀", rr=3, race_name="サラ系3歳500万下",
        weather="sunny", weather_label="晴",
        surface="ダ", condition="稍重", distance=1400, direction="右",
        post_time_offset_min=75, horses_n=10,
        name_pool=SAGA_NAMES, jockey_pool=JOCKEYS_NAR, seed=4103,
        scratched_horse_nos={7: 1},  # 7番出走取消（changes-info デモ用）
    )),
    ("odds_NAR_41_06.json", dict(
        organizer_type="NAR", place_cd="41",
        place_name="佐賀", rr=6, race_name="サラ系3歳1勝クラス",
        weather="cloudy", weather_label="曇",
        surface="ダ", condition="良", distance=1200, direction="右",
        post_time_offset_min=78, horses_n=8,
        name_pool=SAGA_NAMES, jockey_pool=JOCKEYS_NAR, seed=4106,
    )),
    # ---- slot 3: メインレースの部 ----
    ("odds_JRA_05_11.json", dict(
        organizer_type="JRA", place_cd="05",
        place_name="東京", rr=11, race_name="フェブラリーステークス",
        weather="sunny", weather_label="晴",
        surface="芝", condition="良", distance=2400, direction="左",
        post_time_offset_min=123, horses_n=18,
        name_pool=TOKYO_NAMES, jockey_pool=JOCKEYS_JRA, seed=311,
        is_previous_day=True,
    )),
    ("odds_JRA_06_11.json", dict(
        organizer_type="JRA", place_cd="06",
        place_name="中山", rr=11, race_name="スプリングステークス",
        weather="sunny", weather_label="晴",
        surface="芝", condition="良", distance=1600, direction="右",
        post_time_offset_min=126, horses_n=16,
        name_pool=NAKAYAMA_NAMES, jockey_pool=JOCKEYS_JRA, seed=312,
    )),
    # 指示書08: 取消馬デモ用 18頭レース（5/10番 出走取消・15番 競走除外）
    #   slot3 に追加、MATRIX_VARIANT_FILES に含めてマトリクス4枚テンプレで表示。
    #   マトリクス first/second の両方で取消・除外のブロック/セルが空白＋薄くなる挙動を検証。
    ("odds_JRA_09_11.json", dict(
        organizer_type="JRA", place_cd="09",
        place_name="阪神", rr=11, race_name="大阪杯",
        # json-v05-align (2026-04-20): v0.5 §8.3 サンプル対応（G1 重賞例）
        grade="G1",
        weather="cloudy", weather_label="曇",
        surface="芝", condition="良", distance=2000, direction="右",
        post_time_offset_min=129, horses_n=18,
        name_pool=HANSHIN_NAMES, jockey_pool=JOCKEYS_JRA, seed=411,
        scratched_horse_nos={5: 1, 10: 1, 15: 2},  # 5/10: 出走取消、15: 競走除外
        # H-02 (2026-04-17): 騎手変更サンプル（馬番3、取消馬以外）chg_reason_cd=05（騎手負傷）
        jockey_change_horse_no=3,
    )),
    # 指示書09 T6: monitor_id=0102（L字+1画面デモ）用の門別7R
    #   org=NAR、場コード=30（門別）。
    #   2026-04-17: 18頭立てで side-entries/wide-popular のフル可変挙動を検証するため
    #   horses_n を 8→18 に拡張。--row-count: max(10, 18) = 18 行で縦分割される。
    ("odds_NAR_30_07.json", dict(
        organizer_type="NAR", place_cd="30",
        place_name="門別", rr=7, race_name="サラ系3歳B2",
        weather="sunny", weather_label="晴",
        surface="ダ", condition="良", distance=1200, direction="右",
        post_time_offset_min=10, horses_n=18,
        name_pool=MONBETSU_NAMES, jockey_pool=JOCKEYS_NAR, seed=307,
    )),
    # ---- H-01 中止サンプル（schedule_0106/0107 用、2026-04-17）----
    # schedule_0106: レース中止（odds_status=2）— 中山8R
    ("odds_JRA_06_08.json", dict(
        organizer_type="JRA", place_cd="06",
        place_name="中山", rr=8, race_name="中山8R（中止想定）",
        weather="rain", weather_label="雨",
        surface="芝", condition="不良", distance=1800, direction="右",
        post_time_offset_min=30, horses_n=10,
        name_pool=NAKAYAMA_NAMES, jockey_pool=JOCKEYS_JRA, seed=608,
        odds_status=2,  # レース中止
    )),
    # schedule_0107: 開催中止（odds_status=3）— 船橋5R（場全体中止想定）
    ("odds_NAR_45_05.json", dict(
        organizer_type="NAR", place_cd="45",
        place_name="船橋", rr=5, race_name="船橋5R（開催中止想定）",
        weather="rain", weather_label="雨",
        surface="ダ", condition="不良", distance=1200, direction="左",
        post_time_offset_min=40, horses_n=10,
        name_pool=FUNABASHI_NAMES, jockey_pool=JOCKEYS_NAR, seed=4505,
        odds_status=3,  # 開催中止
    )),
]


# ========================================================================
# H-04 (2026-04-17): 新スケジュールJSON構造 `slot.screens[].races[]`
# ========================================================================
# display_pattern_id → {layout, screens} マッピング表（M-01 同時解決）。
# screens 各要素は (position, template) のタプル。type='video' は video_config 付き。
# Phase 1 設計提案 §3.1 の内容を実装。
# display-pattern-id-numeric (2026-04-20): v0.5 §1.3.1 display_pattern_id は INT。
#   プロト内部は可読性重視で文字列 ID を保持しつつ、JSON 出力時に INT + 表示名へ変換する。
#   DB 側の正式 INT 値は v0.5 付録B 確定待ち、本暫定値（1〜5）は確定時に差替え可能。
#   フロント側（index.html）は slot.screens[].template を直接使うため本マップ非依存。
#   新メンバー参照用に assets/js/config.js にも同等の lookup を配置。
DISPLAY_PATTERN_NUMERIC_IDS = {
    "PAT-4SPLIT-STD":               (1, "4分割標準"),
    "PAT-4SPLIT-UMATAN":            (2, "4分割馬連馬単"),
    "PAT-LSHAPE-VIDEO":             (3, "L字+動画"),
    "PAT-1SCREEN-VIDEO":            (4, "1画面動画"),
    "PAT-4SPLIT-RIGHTBOTTOM-VIDEO": (5, "4分割右下動画"),
    # 3R-entries-results-phase2 (2026-04-21): 出走成績 3R 表示追加
    "PAT-3R-ENTRIES-RESULTS":       (10, "3R出走成績"),
    # v0.6 追加（2026-04-22）: 仕様書 v0.6 §3.8 / 付録B 暫定採番。DB 正式値確定時に差替え
    "PAT-6R-ENTRIES-RESULTS":       (11, "6R出走成績"),
    "PAT-CHANGES-INFO":             (12, "変更情報"),
}

DISPLAY_PATTERN_MAP = {
    "PAT-4SPLIT-STD": {
        "layout": "4split",
        "screens": [
            {"position": "P1", "template": "templates/single-screen.html"},
            {"position": "P2", "template": "templates/single-umaren-wide.html"},
            {"position": "P3", "template": "templates/single-popular.html"},
            {"position": "P4", "template": "templates/single-popular-second.html"},
        ],
    },
    "PAT-4SPLIT-UMATAN": {
        "layout": "4split",
        "screens": [
            {"position": "P1", "template": "templates/single-umaren-first.html"},
            {"position": "P2", "template": "templates/single-umaren-second.html"},
            {"position": "P3", "template": "templates/single-umatan-first.html"},
            {"position": "P4", "template": "templates/single-umatan-second.html"},
        ],
    },
    "PAT-LSHAPE-VIDEO": {
        "layout": "lshape",
        "screens": [
            {"position": "P1", "template": "templates/side-entries.html"},
            {"position": "P2", "template": "templates/video-frame.html", "type": "video"},
            {"position": "P3", "template": "templates/wide-popular.html"},
        ],
    },
    "PAT-1SCREEN-VIDEO": {
        "layout": "1screen",
        "screens": [
            {"position": "P1", "template": "templates/video-frame.html", "type": "video"},
        ],
    },
    "PAT-4SPLIT-RIGHTBOTTOM-VIDEO": {
        "layout": "4split",
        "screens": [
            {"position": "P1", "template": "templates/single-screen.html"},
            {"position": "P2", "template": "templates/single-umaren-wide.html"},
            {"position": "P3", "template": "templates/single-popular.html"},
            {"position": "P4", "template": "templates/video-frame.html", "type": "video"},
        ],
    },
    # 3R-entries-results-phase2 (2026-04-21): 1画面内 3レース成績表示。
    #   1列 (P1) のみ、子テンプレ側が 3 レース並列で render する。
    "PAT-3R-ENTRIES-RESULTS": {
        "layout": "1screen",
        "screens": [
            {"position": "P1", "template": "templates/entries-results-3r.html"},
        ],
    },
}


# ============================================================================
# 3R-entries-results-phase2 (2026-04-21): 出走成績 3R 表示用の生成ロジック群
# ============================================================================
# 根拠:
#   - Phase 1 設計提案書 CC設計提案_3R-entries-results_20260421.md
#   - 画面仕様書 v0.03 §SCR-INF-001
#   - 同着時払戻パターン定義書 v1.1
# ============================================================================

# パターン別の rank 分布（1-indexed、(rank, count) のリスト）
# 同着定義書 §4 の「1着/2着/3着数」欄から決定
PATTERN_RANK_PLAN = {
    # 同着パターン定義書 v1.1 §5 「成績行数」欄に厳密に合致させる。
    # 2026-04-30 session3 改訂2 修正:
    #   B は旧 `(6,1)` 1 エントリ余分 → 5 エントリに修正
    #   F は旧 `(5,1)` 不足 → 5 エントリに修正（5着1頭追加）
    "NORMAL": [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1)],   # 5 エントリ（通常時 1〜5着表示）
    "A":      [(1, 3)],                                    # 3 エントリ（1着3頭同着のみ / screen5 race-record3 準拠）
    "B":      [(1, 2), (3, 3)],                            # 5 エントリ（1着2頭 + 3着3頭、4着・5着なし）
    "C":      [(1, 2), (3, 2), (5, 1)],                    # 5 エントリ（1着2頭 + 3着2頭 + 5着）
    "D":      [(1, 2), (3, 1), (4, 1), (5, 1)],            # 5 エントリ（1着2頭 + 3〜5着）
    "E":      [(1, 1), (2, 3)],                            # 4 エントリ（2着3頭同着）
    "F":      [(1, 1), (2, 2), (4, 1), (5, 1)],            # 5 エントリ（2着2頭同着 + 4着 + 5着）
    "G":      [(1, 1), (2, 1), (3, 3)],                    # 5 エントリ（3着3頭同着）
    "H":      [(1, 1), (2, 1), (3, 2), (5, 1)],            # 5 エントリ（3着2頭同着 + 5着、4着なし）
}

# 各パターンごとの賭式件数（同着定義書 §4 表より転記）
# key = (pattern, bet_type), value = 件数
PAYOUT_COUNT_TABLE = {
    # NORMAL: 単1 複3 枠連1 枠単1 馬連1 馬単1 ワイド3 三連複1 三連単1 = 計13
    ("NORMAL", "win"): 1, ("NORMAL", "place"): 3,
    ("NORMAL", "frame_quinella"): 1, ("NORMAL", "frame_exacta"): 1,
    ("NORMAL", "quinella"): 1, ("NORMAL", "exacta"): 1,
    ("NORMAL", "wide"): 3, ("NORMAL", "trio"): 1, ("NORMAL", "trifecta"): 1,

    # A: 単3 複3 枠連3 枠単6 馬連3 馬単3 ワイド3 三連複3 三連単6 = 計33 (+返還1=34)
    ("A", "win"): 3, ("A", "place"): 3,
    ("A", "frame_quinella"): 3, ("A", "frame_exacta"): 6,
    ("A", "quinella"): 3, ("A", "exacta"): 3,
    ("A", "wide"): 3, ("A", "trio"): 3, ("A", "trifecta"): 6,

    # B: 単2 複5 枠連1 枠単2 馬連1 馬単1 ワイド7 三連複3 三連単6 = 計28 (+返還1=29)
    ("B", "win"): 2, ("B", "place"): 5,
    ("B", "frame_quinella"): 1, ("B", "frame_exacta"): 2,
    ("B", "quinella"): 1, ("B", "exacta"): 1,
    ("B", "wide"): 7, ("B", "trio"): 3, ("B", "trifecta"): 6,

    # C: 単2 複4 枠連1 枠単2 馬連1 馬単1 ワイド5 三連複3 三連単3 = 計22 (+返還1=23)
    ("C", "win"): 2, ("C", "place"): 4,
    ("C", "frame_quinella"): 1, ("C", "frame_exacta"): 2,
    ("C", "quinella"): 1, ("C", "exacta"): 1,
    ("C", "wide"): 5, ("C", "trio"): 3, ("C", "trifecta"): 3,

    # D: 単2 複3 枠連1 枠単2 馬連1 馬単2 ワイド3 三連複1 三連単2 = 計17 (+返還1=18)
    ("D", "win"): 2, ("D", "place"): 3,
    ("D", "frame_quinella"): 1, ("D", "frame_exacta"): 2,
    ("D", "quinella"): 1, ("D", "exacta"): 2,
    ("D", "wide"): 3, ("D", "trio"): 1, ("D", "trifecta"): 2,

    # E: 単1 複4 枠連3 枠単3 馬連3 馬単3 ワイド6 三連複3 三連単6 = 計32
    ("E", "win"): 1, ("E", "place"): 4,
    ("E", "frame_quinella"): 3, ("E", "frame_exacta"): 3,
    ("E", "quinella"): 3, ("E", "exacta"): 3,
    ("E", "wide"): 6, ("E", "trio"): 3, ("E", "trifecta"): 6,

    # F: 単1 複3 枠連2 枠単2 馬連3 馬単1 ワイド3 三連複1 三連単2 = 計18
    ("F", "win"): 1, ("F", "place"): 3,
    ("F", "frame_quinella"): 2, ("F", "frame_exacta"): 2,
    ("F", "quinella"): 3, ("F", "exacta"): 1,
    ("F", "wide"): 3, ("F", "trio"): 1, ("F", "trifecta"): 2,

    # G: 単1 複5 枠連1 枠単1 馬連1 馬単1 ワイド6 三連複3 三連単3 = 計22 (+返還1=23)
    ("G", "win"): 1, ("G", "place"): 5,
    ("G", "frame_quinella"): 1, ("G", "frame_exacta"): 1,
    ("G", "quinella"): 1, ("G", "exacta"): 1,
    ("G", "wide"): 6, ("G", "trio"): 3, ("G", "trifecta"): 3,

    # H: 単1 複4 枠連1 枠単1 馬連1 馬単1 ワイド4 三連複2 三連単2 = 計17 (+返還1=18)
    ("H", "win"): 1, ("H", "place"): 4,
    ("H", "frame_quinella"): 1, ("H", "frame_exacta"): 1,
    ("H", "quinella"): 1, ("H", "exacta"): 1,
    ("H", "wide"): 4, ("H", "trio"): 2, ("H", "trifecta"): 2,
}

BET_TYPE_TO_CODE = {
    "win": "wn", "place": "pe",
    "frame_quinella": "bq", "frame_exacta": "be",
    "quinella": "qa", "exacta": "ea",
    "wide": "wd", "trio": "to", "trifecta": "ta",
}


def determine_dead_heat_pattern(entries: list) -> str:
    """entries[] (rank 付き) から同着パターンを判定。想定外は ValueError。"""
    rank_counts = {}
    for e in entries:
        r = e.get("rank")
        if r in (1, 2, 3):
            rank_counts[r] = rank_counts.get(r, 0) + 1
    n1 = rank_counts.get(1, 0)
    n2 = rank_counts.get(2, 0)
    n3 = rank_counts.get(3, 0)
    patterns = {
        (1, 1, 1): "NORMAL",
        (3, 0, 0): "A",
        (2, 0, 3): "B", (2, 0, 2): "C", (2, 0, 1): "D",
        (1, 3, 0): "E", (1, 2, 0): "F",
        (1, 1, 3): "G", (1, 1, 2): "H",
    }
    key = (n1, n2, n3)
    if key not in patterns:
        raise ValueError(f"想定外の同着組合せ: 1着{n1}件 / 2着{n2}件 / 3着{n3}件")
    return patterns[key]


# 枠番カラークラス名のマッピング（common.js FRAME_NUMBER_CLASS と同期）
_FRAME_COLOR_CLASSES = [
    "number-white", "number-black", "number-red", "number-blue",
    "number-yellow", "number-green", "number-orange", "number-pink",
]


def _frame_color_class(frame_no: int) -> str:
    if 1 <= frame_no <= 8:
        return _FRAME_COLOR_CLASSES[frame_no - 1]
    return "number-white"


# ダミー馬名・騎手名プール（パターン別生成で使う）
_RESULTS_HORSE_POOL = [
    ("ロードトレイル", "小沢大仁"),
    ("フリートストリートダンサー", "丸山元気"),
    ("エコロマーズ", "菊澤一樹"),
    ("ハートホイップ", "黛弘人"),
    ("レオテミス", "石田拓郎"),
    ("アミーラトアルザマーン", "松若風馬"),
    ("ベイビーキッス", "小林脩斗"),
    ("ミルテンベルク", "Ｌ．ヒュ"),
    ("シュヴェルトライテ", "亀田温心"),
    ("エマヌエーレ", "横山琉人"),
    ("ナムラローズマリー", "長岡禎仁"),
    ("ブリックワーク", "斎藤新"),
]


def gen_entries_for_pattern(organizer_type: str, pattern: str, seed: int) -> list:
    """パターン別の同着分布に基づき entries を生成。"""
    rng = random.Random(seed + 700)
    plan = PATTERN_RANK_PLAN[pattern]
    entries = []
    # ダミー馬番（1 から順、同枠 2 頭の枠割を想定し枠1-8 に収める）
    horse_nos = list(range(1, 13))  # 1〜12 番馬
    frame_map = frame_assign(12)  # 12頭の枠割を算出（既存関数）
    # プラン上のエントリ数上限まで使用
    horse_idx = 0
    # 着差コード候補（NAR / JRA）
    margin_cd_iter_nar = iter(["14", "15", "17", "22"])  # クビ / 1/2 / 1 1/2 / 1 1/4
    margin_cd_iter_jra = iter(["K__", "_12", "112", "114"])
    for (rank, count) in plan:
        for i in range(count):
            if horse_idx >= len(horse_nos):
                break
            hn = horse_nos[horse_idx]
            horse_idx += 1
            fn = frame_map[hn - 1]
            (hname, jname) = _RESULTS_HORSE_POOL[(hn - 1) % len(_RESULTS_HORSE_POOL)]
            # 1着は time を入れる、同着は "同着"
            time_val = f"5:{34 + rng.randint(0, 30):02d}.{rng.randint(0, 9)}" if rank == 1 and i == 0 else None
            if count >= 2 and i > 0:
                # 同着 i 頭目以降は着差表示「同着」で固定
                margin_name = "同着"
            elif rank == 1:
                margin_name = None  # 1着単独は着差なし
            else:
                # 2着以降: コード候補から選択
                try:
                    if organizer_type == "NAR":
                        cd = next(margin_cd_iter_nar)
                    else:
                        cd = next(margin_cd_iter_jra)
                except StopIteration:
                    cd = "14" if organizer_type == "NAR" else "K__"
                margin_name = margin_cd_to_name(organizer_type, cd) or "クビ"
            entries.append({
                "rank": rank,
                "frame_no": fn,
                "horse_no": hn,
                "horse_name": hname,
                "jockey": jname,
                "genryokigo": None,
                "time": time_val,
                "margin_name": margin_name,
                "frame_color_class": _frame_color_class(fn),
                "is_dead_heat": count >= 2,
                "accident_type": None,
            })
    return entries


def _gen_combination(bet_type: str, idx: int, entries: list, rng) -> str:
    """賭式別のダミー組合せ文字列を生成（馬番・枠番ベース）"""
    horse_nos = sorted(set(e["horse_no"] for e in entries))
    frame_nos = sorted(set(e["frame_no"] for e in entries))
    if bet_type in ("win", "place"):
        return str(horse_nos[idx % len(horse_nos)])
    if bet_type in ("frame_quinella", "frame_exacta"):
        if len(frame_nos) < 2:
            return f"{frame_nos[0]}-{frame_nos[0]}"
        a = frame_nos[idx % len(frame_nos)]
        b = frame_nos[(idx + 1) % len(frame_nos)]
        return f"{a}-{b}"
    if bet_type in ("quinella", "exacta", "wide"):
        a = horse_nos[idx % len(horse_nos)]
        b = horse_nos[(idx + 1) % len(horse_nos)]
        return f"{a}-{b}"
    if bet_type in ("trio", "trifecta"):
        a = horse_nos[idx % len(horse_nos)]
        b = horse_nos[(idx + 1) % len(horse_nos)]
        c = horse_nos[(idx + 2) % len(horse_nos)]
        return f"{a}-{b}-{c}"
    return ""


def _gen_payout_entry(bet_type: str, idx: int, entries: list, rng, pattern: str,
                       is_special_idx_target: int = -1) -> dict:
    """1 件分の払戻エントリを生成。
    is_special_idx_target: 特払いに指定する idx（-1 = 特払いなし）"""
    # 賭式別の金額レンジ
    amount_ranges = {
        "win": (100, 1000), "place": (100, 500),
        "frame_quinella": (200, 2000), "frame_exacta": (400, 4000),
        "quinella": (300, 3000), "exacta": (600, 6000),
        "wide": (150, 800), "trio": (1000, 50000),
        "trifecta": (5000, 500000),
    }
    lo, hi = amount_ranges.get(bet_type, (100, 1000))
    is_special = (idx == is_special_idx_target)
    amount = 70 if is_special else round(rng.randint(lo, hi) / 10) * 10
    place_label = None
    if bet_type == "place":
        # 同着時は同じ rank が複数行並ぶ
        # パターン別の着順ラベル（NORMAL = 1着/2着/3着、E = 1着/2着/2着/2着 等）
        place_labels_table = {
            "NORMAL": ["1着", "2着", "3着"],
            "A":      ["1着", "1着", "1着"],           # 1着3頭同着
            "B":      ["1着", "1着", "3着", "3着", "3着"],
            "C":      ["1着", "1着", "3着", "3着"],
            "D":      ["1着", "1着", "3着"],
            "E":      ["1着", "2着", "2着", "2着"],    # スクショ該当
            "F":      ["1着", "2着", "2着"],
            "G":      ["1着", "2着", "3着", "3着", "3着"],
            "H":      ["1着", "2着", "3着", "3着"],
        }
        labels = place_labels_table.get(pattern, ["1着", "2着", "3着"])
        place_label = labels[idx] if idx < len(labels) else labels[-1]
    return {
        "combination": _gen_combination(bet_type, idx, entries, rng),
        "combination_type": BET_TYPE_TO_CODE[bet_type],
        "amount": amount,
        "is_special_pay": is_special,
        "is_void": False,
        "place_label": place_label,
    }


def gen_payouts(pattern: str, entries: list, seed: int,
                 special_pay_bet: str = None, special_pay_idx: int = -1) -> dict:
    """payouts オブジェクト生成。
    special_pay_bet / special_pay_idx で特払いサンプルを指定。"""
    rng = random.Random(seed + 800)
    bet_order = ["win", "place", "frame_quinella", "frame_exacta",
                 "quinella", "exacta", "wide", "trio", "trifecta"]
    result = {"bet_order": bet_order}
    for bt in bet_order:
        count = PAYOUT_COUNT_TABLE.get((pattern, bt), 0)
        target_idx = special_pay_idx if bt == special_pay_bet else -1
        result[bt] = [
            _gen_payout_entry(bt, i, entries, rng, pattern, target_idx)
            for i in range(count)
        ]
    return result


def gen_refund(pattern: str) -> dict:
    """返還情報のサンプル生成。E パターンのみ返還あり（設計提案書 §3.7.2）。"""
    if pattern == "E":
        # 馬番16返還 + 枠番8返還（スクショ再現、ビットマップは左=1番 の 1-indexed）
        horse = "0" * 15 + "1" + "00"    # 16 ビット目 = 1（18桁）
        bracket = "0" * 7 + "1"          # 8 ビット目 = 1（8桁）
        return {
            "horse_no_bitmap": horse,
            "bracket_no_bitmap": bracket,
            "same_bracket_bitmap": None,
        }
    return {
        "horse_no_bitmap": "0" * 18,
        "bracket_no_bitmap": "0" * 8,
        "same_bracket_bitmap": None,
    }


def gen_results_json(race_spec: dict, pattern: str, seed: int,
                      special_pay_bet: str = None, special_pay_idx: int = -1) -> dict:
    """1 レース分の出走成績 JSON を生成。

    race_spec: {"organizer_type":"NAR", "place_cd":"49", "place_name":"名古屋",
                "rr":1, "race_id":"NAR_49_01", "race_key":"名古屋1R"}
    """
    entries = gen_entries_for_pattern(race_spec["organizer_type"], pattern, seed)
    # 自己整合性チェック
    detected = determine_dead_heat_pattern(entries)
    assert detected == pattern, f"想定 {pattern} vs 判定 {detected} 不一致"
    return {
        "server_time": NOW_ISO,
        "race_id": race_spec["race_id"],
        "race_key": race_spec["race_key"],
        "organizer_type": race_spec["organizer_type"],
        "place_cd": race_spec["place_cd"],
        "place_name": race_spec["place_name"],
        "rr": race_spec["rr"],
        "display_date": TODAY_YYYYMMDD,
        "odds_status": 1,   # 確定（成績モード想定）
        "dead_heat_pattern": pattern,
        "entries": entries,
        "payouts": gen_payouts(pattern, entries, seed, special_pay_bet, special_pay_idx),
        "refund": gen_refund(pattern),
    }


def _venue_name(org: str, pp: str) -> str:
    table = {
        ("NAR", "03"): "帯広",   # Phase 3 (2026-04-21): ばんえい競馬
        ("NAR", "30"): "門別", ("NAR", "45"): "船橋", ("NAR", "49"): "名古屋",
        ("JRA", "05"): "東京", ("JRA", "06"): "中山", ("JRA", "09"): "阪神",
    }
    return table.get((org, pp), "？")


# ==========================================================================
# Phase 3 (2026-04-21): ばんえい競馬（帯広）用データ生成
# --------------------------------------------------------------------------
# 特徴（注意事項 docx §2.2 / §6 参照）:
#   - 全馬 time を設定、margin_name は null 固定（着差の概念なし）
#   - time 形式は平地と同じ M:SS.S（例 "2:03.0"）
#   - 馬体重 4 桁（800-1200kg）、負担重量 3-4 桁（200-1000kg）
#   - 馬場水分フィールド track_water_pct（race 直下）
#   - 9 頭立てまでは 8 枠 2 頭入り（9 番馬 frame_no=8）
# ==========================================================================

_BANEI_HORSE_POOL = [
    ("エムトップ", "臼杵龍"),      ("カイロルーラー", "西謙一"),
    ("ブラックチャーム", "林康文"), ("ガオノチカラ", "長澤幸"),
    ("ヤマトリキ", "中原蓮"),      ("ダイコウシン", "西将太"),
    ("ツガルアマゾン", "村上章"),  ("トヨミヒラリ", "渡来心"),
    ("ハートエース", "島津新"),
]

_BANEI_RACE_NAMES = {
    1: "ばんえい競馬C1-5",
    2: "ばんえい競馬B2-8",
    3: "河内山夫妻初ばんえい競馬杯C2-10",
    4: "ばんえい競馬A1-3",
    5: "ばんえい競馬B2-7",
    6: "ばんえい競馬B3-8",
}


def gen_banei_entries(pattern: str, seed: int, horse_count: int = 5) -> list:
    """ばんえい用エントリ生成。全馬 time 設定、margin_name は null 固定。
    同着/返還は既存 PATTERN_RANK_PLAN を再利用（entries 数をばんえい向けに圧縮）。"""
    rng = random.Random(seed + 900)
    # ばんえい固有の「同着は margin_name=null、全馬 time」を満たすため、
    # PATTERN_RANK_PLAN（平地）と同じ着順分布を採用しつつ time/margin を上書き
    plan = PATTERN_RANK_PLAN.get(pattern, PATTERN_RANK_PLAN["NORMAL"])
    # entries 数を horse_count で truncate
    entries = []
    horse_idx = 0
    base_tenths = 1200    # 2:00.0 の tenths 換算（120 秒 × 10 = 1200 tenths）
    for (rank, count) in plan:
        for _ in range(count):
            if horse_idx >= horse_count:
                break
            hn = horse_idx + 1
            # 9 番目は 8 枠 2 頭入り
            if hn == 9:
                fn = 8
            elif horse_count <= 8:
                fn = hn
            else:
                fn = min(hn, 8)
            (hname, jname) = _BANEI_HORSE_POOL[horse_idx % len(_BANEI_HORSE_POOL)]
            base_tenths += rng.randint(5, 30)
            mins = base_tenths // 600
            secs = (base_tenths % 600) // 10
            tenths = base_tenths % 10
            entries.append({
                "rank": rank,
                "frame_no": fn,
                "horse_no": hn,
                "horse_name": hname,
                "jockey": jname,
                "genryokigo": None,
                "time": f"{mins}:{secs:02d}.{tenths}",
                "margin_name": None,              # ばんえいは着差なし
                "frame_color_class": _frame_color_class(fn),
                "is_dead_heat": count >= 2,
                "accident_type": None,
            })
            horse_idx += 1
    return entries


def gen_banei_results_json(rr: int, pattern: str = "NORMAL",
                            track_water_pct: float = 1.8,
                            horse_count: int = 5,
                            with_refund: bool = False) -> dict:
    """ばんえい results JSON（帯広 rr レース分）を生成。"""
    seed = (hash(("NAR", "03", rr)) % 10000) + 1
    entries = gen_banei_entries(pattern, seed, horse_count)
    refund = {"horse_no_bitmap": None, "bracket_no_bitmap": None, "same_bracket_bitmap": None}
    if with_refund:
        # ばんえい 10 頭立て返還サンプル: 馬番 9 返還、枠番 8 返還
        refund = {
            "horse_no_bitmap": "0" * 8 + "1" + "0",   # 9 番（10 桁）
            "bracket_no_bitmap": "0" * 7 + "1",       # 8 枠（8 桁）
            "same_bracket_bitmap": None,
        }
    return {
        "server_time": NOW_ISO,
        "race_id": f"NAR_03_{rr:02d}",
        "race_key": f"帯広{rr}R",
        "organizer_type": "NAR",
        "place_cd": "03",
        "place_name": "帯広",
        "rr": rr,
        "race_name": _BANEI_RACE_NAMES.get(rr, f"ばんえい競馬{rr}R"),
        "display_date": TODAY_YYYYMMDD,
        "odds_status": 1,
        "track_water_pct": track_water_pct,
        "dead_heat_pattern": pattern,
        "entries": entries,
        "payouts": gen_payouts(pattern, entries, seed),
        "refund": refund,
    }


def gen_banei_odds_json(rr: int, track_water_pct: float = 1.8,
                         horse_count: int = 9) -> dict:
    """ばんえい odds JSON（帯広 rr レース、出走表モード）を生成。"""
    rng = random.Random((hash(("NAR", "03", rr, "odds")) % 10000) + 1)
    horses = []
    for i in range(horse_count):
        hn = i + 1
        # 9 番目は 8 枠 2 頭入り
        fn = hn if hn <= 8 else 8
        (hname, jname) = _BANEI_HORSE_POOL[i % len(_BANEI_HORSE_POOL)]
        weight = 900 + rng.randint(-50, 150)   # 850-1050 相当の 4 桁
        weight_diff = rng.choice([-27, -15, -3, -1, 0, 1, 2, 9, 27])
        fwt = rng.choice([550, 560, 570, 580])
        horses.append({
            "frame_no": fn, "horse_no": hn,
            "horse_name": hname, "jockey": jname,
            "weight": weight, "weight_diff": weight_diff,
            "win_odds": round(rng.uniform(2.0, 30.0), 1),
            "place_odds_min": round(rng.uniform(1.0, 10.0), 1),
            "place_odds_max": round(rng.uniform(1.5, 15.0), 1),
            "is_popular": False, "is_secondary": False,
            "is_scratched": 0,
            "sex": rng.choice(["牡", "牝"]),
            "age": rng.choice([3, 4, 5]),
            "fwt": fwt, "cnm": "",
            "wt2": weight + rng.randint(-20, 20),
            "scratch_reason": None, "jockey_changed": False,
            "org_jockey_nm": None, "new_jockey_nm": None,
            "chg_reason_cd": None,
            "org_genryokigo": None, "new_genryokigo": None,
        })
    # 枠連オッズ matrix など（表示検証用ダミー、枠 1-8 のみ）
    frame_utan = [
        {"frame_a": a, "frame_b": b,
         "odds": round(rng.uniform(3, 300), 1), "is_popular": False}
        for a in range(1, 9) for b in range(1, 9) if a != b
    ]
    horse_nos = list(range(1, horse_count + 1))
    umaren_matrix = [
        {"a": a, "b": b, "odds": round(rng.uniform(3, 500), 1), "is_popular": False}
        for a in horse_nos for b in horse_nos if a < b
    ]
    umatan_matrix = [
        {"a": a, "b": b, "odds": round(rng.uniform(3, 500), 1), "is_popular": False}
        for a in horse_nos for b in horse_nos if a != b
    ]
    wide_matrix = [
        {"a": a, "b": b,
         "odds_min": round(rng.uniform(1.5, 30), 1),
         "odds_max": round(rng.uniform(30, 120), 1),
         "is_popular": False}
        for a in horse_nos for b in horse_nos if a < b
    ]
    frame_odds = [
        {"frame_a": a, "frame_b": b,
         "odds": round(rng.uniform(3, 200), 1), "is_popular": False}
        for a in range(1, 9) for b in range(a + 1, 9)
    ]
    return {
        "server_time": NOW_ISO,
        "race": {
            "organizer_type": "NAR", "place_cd": "03", "place_name": "帯広",
            "rr": rr, "race_name": _BANEI_RACE_NAMES.get(rr, f"ばんえい競馬{rr}R"),
            "race_class": "", "grade": None,
            "deadline_min": 1, "deadline": "14:13",
            "deadline_iso": "2026-04-21T14:13:44+09:00",
            "post_time": f"15:{(rr * 10) % 60:02d}",
            "post_time_iso": "2026-04-21T15:45:44+09:00",
            "weather_cd": 1, "weather_label": "晴",
            "track_cd": 0, "track_cond_cd": None,
            "track_water_pct": track_water_pct,
            "distance": 200, "course_direction": 0,
            "pn": horse_count, "is_previous_day": False,
            "odds_status": 0,
            "frame_utan": frame_utan,
        },
        "horses": horses,
        "frame_odds": frame_odds,
        "umaren_matrix": umaren_matrix,
        "umatan_matrix": umatan_matrix,
        "wide_matrix": wide_matrix,
        "umaren_popular": [],
        "umatan_popular": [],
        "trio_popular": [],
        "trifecta_popular": [],
    }


def _race_spec_for_results(org: str, pp: str, rr: int) -> dict:
    return {
        "organizer_type": org,
        "place_cd": pp,
        "place_name": _venue_name(org, pp),
        "rr": rr,
        "race_id": f"{org}_{pp}_{rr:02d}",
        "race_key": _venue_name(org, pp) + f"{rr}R",
    }


def _race_spec_results_for_schedule(org: str, pp: str, rr: int) -> dict:
    """schedule JSON の races[] エントリ生成（data_source は results/ 配下）"""
    return {
        "race_id": f"{org}_{pp}_{rr:02d}",
        "race_key": _venue_name(org, pp) + f"{rr}R",
        "post_time_iso": now_plus_min(0),   # 既に確定レース想定
        "data_source": f"results/{TODAY_YYYYMMDD}/{org}_{pp}_{rr:02d}.json",
    }


# パターン × 3 レース（monitor_id 108〜116）の割当
PATTERN_TO_RACES = {
    "NORMAL": [("NAR", "49", 1), ("NAR", "49", 2), ("NAR", "49", 3)],
    "A":      [("NAR", "49", 4), ("NAR", "49", 5), ("NAR", "49", 6)],
    "B":      [("NAR", "49", 7), ("NAR", "49", 8), ("NAR", "49", 9)],
    "C":      [("NAR", "49", 10), ("NAR", "49", 11), ("NAR", "49", 12)],
    "D":      [("NAR", "30", 1), ("NAR", "30", 2), ("NAR", "30", 3)],
    "E":      [("NAR", "30", 4), ("NAR", "30", 5), ("NAR", "30", 6)],
    "F":      [("NAR", "30", 7), ("NAR", "30", 8), ("NAR", "30", 9)],
    "G":      [("NAR", "30", 10), ("NAR", "30", 11), ("NAR", "30", 12)],
    "H":      [("JRA", "09", 10), ("JRA", "09", 11), ("JRA", "09", 12)],
}

# monitor_id → pattern 対応
MONITOR_TO_PATTERN = {
    108: "NORMAL", 109: "A", 110: "B", 111: "C", 112: "D",
    113: "E", 114: "F", 115: "G", 116: "H",
}


def build_schedule_entries_results(monitor_id: int, fast: bool = False) -> dict:
    """display_pattern_id=10 (PAT-3R-ENTRIES-RESULTS) 用スケジュール JSON を生成。"""
    s1_start, s1_end = (0, 60) if not fast else (0, 5)
    pattern = MONITOR_TO_PATTERN[monitor_id]
    race_triples = PATTERN_TO_RACES[pattern]
    races = [_race_spec_results_for_schedule(org, pp, rr) for (org, pp, rr) in race_triples]
    screen_races = {"P1": races}
    slots = [
        build_slot("slot1", s1_start, s1_end, "PAT-3R-ENTRIES-RESULTS", screen_races),
    ]
    return {
        "server_time": NOW_ISO,
        "monitor_id": monitor_id,
        "display_date": TODAY_YYYYMMDD,
        "slots": slots,
    }


def _race_id_from_file(fname: str) -> str:
    """'odds_NAR_45_01.json' → 'NAR_45_01'."""
    return fname.replace("odds_", "").replace(".json", "")


def _race_key_from_odds(fname: str) -> str:
    """生成済みオッズJSONから venue+race_no を読み取って race_key を返す（失敗時は race_id 相当）。

    path-date-folder (2026-04-20): オッズ JSON の配置が
        odds/{YYYYMMDD}/{ORG}_{PP}_{RR}.json
    に変わったため、参照先を odds_dir 経由に変更。入力 fname は旧命名
    ("odds_XXX.json") を許容し、プレフィックスを剥がして参照する。
    """
    default = _race_id_from_file(fname)
    basename = fname.replace("odds_", "")
    path = ODDS_OUT_BASE / TODAY_YYYYMMDD / basename
    if not path.exists():
        return default
    try:
        j = json.loads(path.read_text(encoding="utf-8"))
        # field-rename-v0.5 (2026-04-20): v0.5 §4.3 命名で読む
        place_name = j.get("race", {}).get("place_name", "")
        rr = j.get("race", {}).get("rr", "")
        if place_name and rr:
            return f"{place_name}{rr}R"
    except Exception:
        pass
    return default


def _race_spec(odds_file: str, post_offset_min: int) -> dict:
    """new 構造 (H-04) の race エントリを作る。
    odds_file: 'odds_NAR_45_01.json'（旧命名の入力を許容、出力は v0.5 形式）
    post_offset_min: NOW からの発走時刻オフセット（分）

    path-date-folder (2026-04-20): data_source を v0.5 §1.5 形式に対応。
        "data/odds_NAR_45_01.json" → "odds/{YYYYMMDD}/NAR_45_01.json"
    """
    odds_basename = odds_file.replace("odds_", "")  # "NAR_45_01.json"
    return {
        "race_id": _race_id_from_file(odds_file),
        "race_key": _race_key_from_odds(odds_file),
        "post_time_iso": now_plus_min(post_offset_min),
        "data_source": f"odds/{TODAY_YYYYMMDD}/{odds_basename}",
    }


def _video_config(venue_code: str, video_source_override: str = None) -> dict:
    """video screen の構成辞書を生成。"""
    cfg = {
        "venue_code": venue_code,
        "quality_mode": "auto",
        "quality_cap": 4,
        "audio_muted": True,
        "volume": 0.7,
    }
    if video_source_override:
        cfg["video_source_override"] = video_source_override
    return cfg


def build_slot(
    slot_id: str,
    start_offset_min: int,
    end_offset_min: int,
    display_pattern_id: str,
    screen_races: dict,           # {position: [race_spec, ...]} ※ video screen は {} で可
    video_config_by_pos: dict = None,
) -> dict:
    """H-04 Phase 2: `slot.screens[].races[]` 構造で slot を生成。

    display_pattern_id から layout と screens のテンプレを解決し、
    screen_races[pos] に指定された race リストを各画面に割り当てる。
    type='video' の画面は video_config_by_pos[pos] で設定。

    Args:
        slot_id: 文字列ID（例: "slot1"）。H-04 で number→string 化（Phase 1 §9.5 承認済）
        start_offset_min / end_offset_min: NOW からのオフセット分
        display_pattern_id: DISPLAY_PATTERN_MAP のキー
        screen_races: {position: [race_spec]}  video screen は省略可
        video_config_by_pos: {position: {venue_code, quality_mode, ...}}
    """
    pattern = DISPLAY_PATTERN_MAP[display_pattern_id]
    pat_id_int = DISPLAY_PATTERN_NUMERIC_IDS[display_pattern_id][0]
    pat_id_name = DISPLAY_PATTERN_NUMERIC_IDS[display_pattern_id][1]
    screens_out = []
    # v0.6 §3.5 準拠: 各 screen に DB `monitor_schedules_detail` のフィールドを出力。
    #   - layout_section (CHAR(2), P1/P2/P3/P4): position のエイリアス
    #   - place_cd / organizer_type: 先頭 race から推定（NULL 許容）
    #   - display_pattern_id / display_pattern_name: slot 単位と同値（DB は screen 毎に
    #     display_pattern_id_01..04 を持つが、プロト 1 slot = 1 pattern で統一）
    #   - is_auto_extend: BIT NOT NULL、プロトでは false 固定
    #   - back_color_code: CHAR(6) NULL、プロトでは null 固定（124 は手動注入）
    #   C-CC-2（v0.6 → v0.7 解消）対応。
    for s in pattern["screens"]:
        pos = s["position"]
        races_for_screen = [] if s.get("type") == "video" else screen_races.get(pos, [])
        # 先頭 race の race_id から place_cd / organizer_type を推定
        first_race_id = races_for_screen[0].get("race_id") if races_for_screen else None
        place_cd_val = None
        organizer_type_val = None
        if first_race_id and isinstance(first_race_id, str):
            parts = first_race_id.split("_")
            if len(parts) >= 2:
                organizer_type_val = parts[0] if parts[0] in ("JRA", "NAR") else None
                place_cd_val = parts[1] if len(parts[1]) == 2 else None
        screen_entry = {
            "position": pos,
            "layout_section": pos,                 # v0.6 §3.5 DB 対応
            "template": s["template"],
            "place_cd": place_cd_val,              # v0.6 §3.5
            "organizer_type": organizer_type_val,  # v0.6 §3.5
            "display_pattern_id": pat_id_int,      # v0.6 §3.5（slot と同値）
            "display_pattern_name": pat_id_name,   # v0.6 §3.5
            "is_auto_extend": False,               # v0.6 §3.5 プロト既定値
            "back_color_code": None,               # v0.6 §3.5.3
        }
        if s.get("type") == "video":
            screen_entry["type"] = "video"
            if video_config_by_pos and pos in video_config_by_pos:
                screen_entry.update(video_config_by_pos[pos])
            screen_entry["races"] = []  # video は races[] を空配列固定（Phase 1 §9.3 案V1）
        else:
            screen_entry["races"] = races_for_screen
        screens_out.append(screen_entry)
    return {
        "slot_id": slot_id,
        "start_time": now_plus_min(start_offset_min),
        "end_time": now_plus_min(end_offset_min),
        "layout": pattern["layout"],
        # display-pattern-id-numeric (2026-04-20): v0.5 §1.3.1 INT 化 + display_pattern_name 追加。
        #   引数 display_pattern_id は文字列 ID（内部可読性）、JSON 出力は INT + 表示名。
        "display_pattern_id": DISPLAY_PATTERN_NUMERIC_IDS[display_pattern_id][0],
        "display_pattern_name": DISPLAY_PATTERN_NUMERIC_IDS[display_pattern_id][1],
        "screens": screens_out,
    }


# ========================================================================
# 旧構造（`slot.races[].frames[]`）は H-04 で完全廃止。frames_of / build_lshape_slot /
# build_1screen_slot / build_4split_with_video_slot は削除した。
# ========================================================================


def _broadcast_races(odds_files_with_offsets: list, positions: list) -> dict:
    """同一のレース列を複数画面に割当てる（全画面同一場合の便利ヘルパ）。
    odds_files_with_offsets: [(odds_file, post_offset_min), ...]
    positions: ['P1', 'P2', 'P3', 'P4']
    """
    races = [_race_spec(f, m) for (f, m) in odds_files_with_offsets]
    return {p: races for p in positions}


def build_schedule(fast: bool = False) -> dict:
    """schedule_0101 を H-04 新構造で生成。
    案C採用により、display_pattern_id は slot単位で切替（レース毎テンプレ変化は廃止）。

    構成:
      slot1 = PAT-4SPLIT-STD, 船橋1R/2R/4R（取消デモ含む）
      slot2 = PAT-4SPLIT-UMATAN, 船橋3R/名古屋8R/東京11R/阪神11R（マトリクス実演）
      slot3 = PAT-4SPLIT-STD, 名古屋2R/7R/9R/中山11R

    fast=False: 各60分
    fast=True:  slot1=5分 / slot2=10分 / slot3=15分
    """
    if fast:
        s1_start, s1_end = 0, 5
        s2_start, s2_end = 5, 15
        s3_start, s3_end = 15, 30
        # fast モード時の post_time オフセット（NOW 起点の分）
        # ?next_race_sec=5 等と組合せて「遷移が見える」間隔に短縮する
        post = {
            # slot1（0〜5分、3レース）: 1分間隔
            "odds_NAR_45_01.json": 2,
            "odds_NAR_45_02.json": 3,
            "odds_NAR_45_04.json": 4,
            # slot2（5〜15分、4レース）: 2分間隔
            "odds_NAR_45_03.json": 6,
            "odds_NAR_49_08.json": 8,
            "odds_JRA_05_11.json": 10,
            "odds_JRA_09_11.json": 12,
            # slot3（15〜30分、4レース）: 3分間隔
            "odds_NAR_49_02.json": 16,
            "odds_NAR_49_07.json": 19,
            "odds_NAR_49_09.json": 22,
            "odds_JRA_06_11.json": 25,
        }
    else:
        s1_start, s1_end = 0, 60
        s2_start, s2_end = 60, 120
        s3_start, s3_end = 120, 180
        # 本番相当: 各レースの実 post_time_offset_min を使う
        # slot1 (0〜60分): 船橋1R(+3), 2R(+10), 4R(+15)
        post = {
            "odds_NAR_45_01.json": 3,
            "odds_NAR_45_02.json": 10,
            "odds_NAR_45_04.json": 15,
            # slot2 (60〜120分): 船橋3R は時間外のため slot2 中に再配置（+70〜+100）
            "odds_NAR_45_03.json": 70,
            "odds_NAR_49_08.json": 80,
            "odds_JRA_05_11.json": 90,
            "odds_JRA_09_11.json": 100,
            # slot3 (120〜180分): 名古屋2R/7R/9R/中山11R
            "odds_NAR_49_02.json": 130,
            "odds_NAR_49_07.json": 140,
            "odds_NAR_49_09.json": 150,
            "odds_JRA_06_11.json": 160,
        }

    # slot1: 船橋1R, 2R, 4R（4split-STD）
    slot1_files = [("odds_NAR_45_01.json", post["odds_NAR_45_01.json"]),
                   ("odds_NAR_45_02.json", post["odds_NAR_45_02.json"]),
                   ("odds_NAR_45_04.json", post["odds_NAR_45_04.json"])]
    slot1_races = _broadcast_races(slot1_files, ["P1", "P2", "P3", "P4"])

    # slot2: 船橋3R, 名古屋8R, 東京11R, 阪神11R（4split-UMATAN マトリクス）
    slot2_files = [("odds_NAR_45_03.json", post["odds_NAR_45_03.json"]),
                   ("odds_NAR_49_08.json", post["odds_NAR_49_08.json"]),
                   ("odds_JRA_05_11.json", post["odds_JRA_05_11.json"]),
                   ("odds_JRA_09_11.json", post["odds_JRA_09_11.json"])]
    slot2_races = _broadcast_races(slot2_files, ["P1", "P2", "P3", "P4"])

    # slot3: 名古屋2R, 7R, 9R, 中山11R（4split-STD）
    slot3_files = [("odds_NAR_49_02.json", post["odds_NAR_49_02.json"]),
                   ("odds_NAR_49_07.json", post["odds_NAR_49_07.json"]),
                   ("odds_NAR_49_09.json", post["odds_NAR_49_09.json"]),
                   ("odds_JRA_06_11.json", post["odds_JRA_06_11.json"])]
    slot3_races = _broadcast_races(slot3_files, ["P1", "P2", "P3", "P4"])

    slots = [
        build_slot("slot1", s1_start, s1_end, "PAT-4SPLIT-STD", slot1_races),
        build_slot("slot2", s2_start, s2_end, "PAT-4SPLIT-UMATAN", slot2_races),
        build_slot("slot3", s3_start, s3_end, "PAT-4SPLIT-STD", slot3_races),
    ]
    return {
        "server_time": NOW_ISO,
        "monitor_id": 101,                  # path-date-folder: v0.5 §1.3.1 INT 化
        "display_date": TODAY_YYYYMMDD,     # path-date-folder: v0.5 §3.3 必須
        "slots": slots,
    }


# === 指示書09 T6: monitor_id=0102 用 L字+1画面デモ schedule ===
# 2026-04-16 ユーザー要望 #4: 本番 NAR 門別の HLS を実URLで使用する。
# → video_source_override は使わず、VENUE_CODE_MAP + VIDEO_URL_BASE の組合せに戻す。
# gen_data.py 側の DEV_VIDEO_SOURCE 定数は残すが、build_schedule_0102 では参照しない。
# 門別以外の場コードを試す場合のみ手動で venue_code を差し替える。
DEV_VIDEO_SOURCE = None  # 参照しない（過去互換のため変数のみ残す）


def build_lshape_slot(slot_id: int, start_offset_min: int, end_offset_min: int,
                      race_key: str, odds_file: str, venue_code: str,
                      rotation_sec: int,
                      video_source_override: str = None) -> dict:
    """
    L字レイアウト（layout=lshape）のスロットを1レース分構築。
    position 1 = side-entries.html（出走表）
    position 2 = video-frame.html（HLSライブ）
    position 3 = wide-popular.html（3カラム人気順）
    """
    video_frame = {
        "position": 2,
        "type": "video",
        "venue_code": venue_code,
        "quality_mode": "auto",
        "quality_cap": 4,
        "audio_muted": True,
        "volume": 0.7,
    }
    if video_source_override:
        video_frame["video_source_override"] = video_source_override
    return {
        "slot_id": slot_id,
        "start_time": now_plus_min(start_offset_min),
        "end_time": now_plus_min(end_offset_min),
        "layout": "lshape",
        "race_rotation_seconds": rotation_sec,
        "races": [{
            "race_key": race_key,
            "frames": [
                {
                    "position": 1,
                    "type": "odds",
                    "template": "templates/side-entries.html",
                    "data_source": "data/" + odds_file,
                },
                video_frame,
                {
                    "position": 3,
                    "type": "odds",
                    "template": "templates/wide-popular.html",
                    "data_source": "data/" + odds_file,
                },
            ],
        }],
    }


def build_1screen_slot(slot_id: int, start_offset_min: int, end_offset_min: int,
                       race_key: str, venue_code: str,
                       rotation_sec: int,
                       video_source_override: str = None) -> dict:
    """
    1画面レイアウト（layout=1screen）のスロット。position 1 のみ video-frame.html。
    """
    video_frame = {
        "position": 1,
        "type": "video",
        "venue_code": venue_code,
        "quality_mode": "auto",
        "quality_cap": 4,
        "audio_muted": True,
        "volume": 0.7,
    }
    if video_source_override:
        video_frame["video_source_override"] = video_source_override
    return {
        "slot_id": slot_id,
        "start_time": now_plus_min(start_offset_min),
        "end_time": now_plus_min(end_offset_min),
        "layout": "1screen",
        "race_rotation_seconds": rotation_sec,
        "races": [{
            "race_key": race_key,
            "frames": [video_frame],
        }],
    }


def build_4split_with_video_slot(slot_id: int, start_offset_min: int, end_offset_min: int,
                                 race_key: str, odds_file: str, venue_code: str,
                                 rotation_sec: int,
                                 video_source_override: str = None) -> dict:
    """
    2026-04-17 ユーザー要望: 4分割レイアウトで右下に動画を配置するパターン。
      position 1 = 単勝・複勝・枠連（single-screen.html）
      position 2 = 馬連・ワイド（single-umaren-wide.html）
      position 3 = 人気順 1-15（single-popular.html）
      position 4 = 動画（video-frame.html）← 既存4分割の single-popular-second の代わり
    """
    video_frame = {
        "position": 4,
        "type": "video",
        "venue_code": venue_code,
        "quality_mode": "auto",
        "quality_cap": 4,
        "audio_muted": True,
        "volume": 0.7,
    }
    if video_source_override:
        video_frame["video_source_override"] = video_source_override
    return {
        "slot_id": slot_id,
        "start_time": now_plus_min(start_offset_min),
        "end_time": now_plus_min(end_offset_min),
        "layout": "4split",
        "race_rotation_seconds": rotation_sec,
        "races": [{
            "race_key": race_key,
            "frames": [
                {
                    "position": 1,
                    "type": "odds",
                    "template": "templates/single-screen.html",
                    "data_source": "data/" + odds_file,
                },
                {
                    "position": 2,
                    "type": "odds",
                    "template": "templates/single-umaren-wide.html",
                    "data_source": "data/" + odds_file,
                },
                {
                    "position": 3,
                    "type": "odds",
                    "template": "templates/single-popular.html",
                    "data_source": "data/" + odds_file,
                },
                video_frame,
            ],
        }],
    }


def build_schedule_0102(fast: bool = False) -> dict:
    """schedule_0102 を H-04 新構造で生成（monitor_id=0102）。
    slot1 = PAT-LSHAPE-VIDEO（出走表 + ライブ映像 + 3カラム人気順）
    slot2 = PAT-1SCREEN-VIDEO（ライブ映像のみ）
    slot3 = PAT-4SPLIT-RIGHTBOTTOM-VIDEO（P1-P3オッズ + P4動画）
    """
    if fast:
        s1_start, s1_end = 0, 1
        s2_start, s2_end = 1, 2
        s3_start, s3_end = 2, 3
        post_offset = 1  # 1分後発走
    else:
        s1_start, s1_end = 0, 60
        s2_start, s2_end = 60, 120
        s3_start, s3_end = 120, 180
        post_offset = 10

    # 浦和ライブ（odds は 門別7R ダミーを流用。2026-04-19 に大井→浦和へ切替、浦和開催日のため）
    race = _race_spec("odds_NAR_30_07.json", post_offset)

    slots = [
        # slot1: L字
        build_slot(
            "slot1", s1_start, s1_end, "PAT-LSHAPE-VIDEO",
            {"P1": [race], "P3": [race]},
            video_config_by_pos={"P2": _video_config(venue_code="urawa")},
        ),
        # slot2: 1画面動画のみ
        build_slot(
            "slot2", s2_start, s2_end, "PAT-1SCREEN-VIDEO",
            {},
            video_config_by_pos={"P1": _video_config(venue_code="urawa")},
        ),
        # slot3: 4分割（P4=動画）
        build_slot(
            "slot3", s3_start, s3_end, "PAT-4SPLIT-RIGHTBOTTOM-VIDEO",
            {"P1": [race], "P2": [race], "P3": [race]},
            video_config_by_pos={"P4": _video_config(venue_code="urawa")},
        ),
    ]
    return {
        "server_time": NOW_ISO,
        "monitor_id": 102,                  # path-date-folder: v0.5 §1.3.1 INT 化
        "display_date": TODAY_YYYYMMDD,     # path-date-folder: v0.5 §3.3 必須
        "slots": slots,
    }


def build_schedule_0103(fast: bool = False) -> dict:
    """schedule_0103: 複数場混在（H-04 新規）。
    P1=名古屋, P2=大井(門別流用), P3=中山, P4=阪神 の4場を同時表示。
    各画面が異なる post_time で独立遷移することを検証。
    """
    if fast:
        s1_start, s1_end = 0, 10
        post = {"P1": [2, 5], "P2": [3, 6], "P3": [4, 7], "P4": [5, 8]}  # 各画面2レース
    else:
        s1_start, s1_end = 0, 120
        post = {"P1": [30, 90], "P2": [45, 105], "P3": [60, 110], "P4": [75, 115]}

    screen_races = {
        "P1": [_race_spec("odds_NAR_49_02.json", post["P1"][0]),
               _race_spec("odds_NAR_49_07.json", post["P1"][1])],
        "P2": [_race_spec("odds_NAR_30_07.json", post["P2"][0]),
               _race_spec("odds_NAR_45_01.json", post["P2"][1])],
        "P3": [_race_spec("odds_JRA_06_11.json", post["P3"][0]),
               _race_spec("odds_JRA_05_11.json", post["P3"][1])],
        "P4": [_race_spec("odds_JRA_09_11.json", post["P4"][0]),
               _race_spec("odds_NAR_49_09.json", post["P4"][1])],
    }

    slots = [
        build_slot("slot1", s1_start, s1_end, "PAT-4SPLIT-STD", screen_races),
    ]
    return {
        "server_time": NOW_ISO,
        "monitor_id": 103,                  # path-date-folder: v0.5 §1.3.1 INT 化
        "display_date": TODAY_YYYYMMDD,     # path-date-folder: v0.5 §3.3 必須
        "slots": slots,
    }


def build_schedule_0104(fast: bool = False) -> dict:
    """schedule_0104: 1レース固定（H-04 新規）。
    全画面で同一レース1つだけを表示、締切後も継続表示（遷移しない）。
    """
    if fast:
        s1_start, s1_end = 0, 5
        post_offset = 1  # 1分後発走 → 数分で締切超過するが遷移しないことを検証
    else:
        s1_start, s1_end = 0, 60
        post_offset = 30

    race = _race_spec("odds_JRA_06_11.json", post_offset)  # 中山11R
    screen_races = {p: [race] for p in ["P1", "P2", "P3", "P4"]}

    slots = [
        build_slot("slot1", s1_start, s1_end, "PAT-4SPLIT-STD", screen_races),
    ]
    return {
        "server_time": NOW_ISO,
        "monitor_id": 104,                  # path-date-folder: v0.5 §1.3.1 INT 化
        "display_date": TODAY_YYYYMMDD,     # path-date-folder: v0.5 §3.3 必須
        "slots": slots,
    }


def build_schedule_0105(fast: bool = False) -> dict:
    """schedule_0105: slot遷移（H-04 新規）。
    slot1 = デイ開催 (PAT-4SPLIT-STD, 船橋カード)
    slot2 = ナイター (PAT-4SPLIT-UMATAN, マトリクス)
    display_pattern_id の変化も含む slot境界遷移を検証。
    """
    if fast:
        s1_start, s1_end = 0, 3
        s2_start, s2_end = 3, 8
        p1 = [1, 2]   # slot1 post offsets
        p2 = [4, 5, 6, 7]  # slot2 post offsets
    else:
        s1_start, s1_end = 0, 60
        s2_start, s2_end = 60, 180
        p1 = [15, 35]
        p2 = [75, 90, 105, 135]

    slot1_races = _broadcast_races(
        [("odds_NAR_45_01.json", p1[0]), ("odds_NAR_45_02.json", p1[1])],
        ["P1", "P2", "P3", "P4"],
    )
    slot2_races = _broadcast_races(
        [("odds_NAR_45_03.json", p2[0]), ("odds_NAR_49_08.json", p2[1]),
         ("odds_JRA_05_11.json", p2[2]), ("odds_JRA_09_11.json", p2[3])],
        ["P1", "P2", "P3", "P4"],
    )

    slots = [
        build_slot("slot1", s1_start, s1_end, "PAT-4SPLIT-STD", slot1_races),
        build_slot("slot2", s2_start, s2_end, "PAT-4SPLIT-UMATAN", slot2_races),
    ]
    return {
        "server_time": NOW_ISO,
        "monitor_id": 105,                  # path-date-folder: v0.5 §1.3.1 INT 化
        "display_date": TODAY_YYYYMMDD,     # path-date-folder: v0.5 §3.3 必須
        "slots": slots,
    }


# ========================================================================
# H-08 (2026-04-17): cchg 変更情報JSON生成（場単位）
# ========================================================================
def make_changes_json_for_place(organizer_type: str, place_cd: str, place_name: str,
                                 odds_entries: list) -> dict:
    """指定場に属する全オッズJSONから changes エントリを逆引き生成する。

    field-rename-v0.5 (2026-04-20): v0.5 §5 命名統一（organizer_type / place_cd / rr）。

    Args:
        organizer_type: "JRA" | "NAR"
        place_cd: 場コード文字列（例: "09"）
        place_name: 表示用場名（例: "阪神"）
        odds_entries: [(rr, race_data_dict), ...]（post_time_iso 昇順）

    Returns:
        changes JSON dict（v0.5 §5 スキーマに準拠）
    """
    changes = []
    seq = 0
    # post_time 昇順でイテレート（chg_time も発走前の妥当な時刻に割り当て）
    for (rr, data) in sorted(odds_entries, key=lambda x: x[1]["race"]["post_time_iso"]):
        post_iso = data["race"]["post_time_iso"]
        post_dt = datetime.strptime(post_iso, "%Y-%m-%dT%H:%M:%S+09:00").replace(tzinfo=JST)
        horses = data.get("horses", [])

        # chg_type=1 騎手変更
        for h in horses:
            if h.get("jockey_changed"):
                seq += 1
                # 変更時刻: 発走の約90分前
                chg_dt = post_dt - timedelta(minutes=90)
                reason_cd = h.get("chg_reason_cd") or "09"
                changes.append({
                    "chg_seq": seq,
                    "chg_time": chg_dt.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
                    "rr": rr,                           # field-rename-v0.5: v0.5 §5.4.1
                    "chg_type": 1,
                    "chg_type_name": CHG_TYPE_MAP[1],
                    "horse_no": h["horse_no"],
                    "horse_name": h["horse_name"],
                    "detail": {
                        "org_jockey_nm": h.get("org_jockey_nm"),
                        # json-v05-align (2026-04-20): v0.5 §5.4.2 命名統一。
                        #   horses[] 側で new_jockey_nm に変換済のため、そのキー名を参照。
                        "new_jockey_nm": h.get("new_jockey_nm"),
                        "chg_reason_cd": reason_cd,
                        "chg_reason_name": CHG_REASON_MAP.get(reason_cd, ""),
                    },
                })

        # chg_type=2 出走取消 / chg_type=3 競走除外
        for h in horses:
            is_sc = h.get("is_scratched", 0)
            if is_sc == 1 or is_sc == 2:
                seq += 1
                chg_dt = post_dt - timedelta(minutes=60 if is_sc == 1 else 45)
                changes.append({
                    "chg_seq": seq,
                    "chg_time": chg_dt.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
                    "rr": rr,                           # field-rename-v0.5: v0.5 §5.4.1
                    "chg_type": 2 if is_sc == 1 else 3,
                    "chg_type_name": CHG_TYPE_MAP[2 if is_sc == 1 else 3],
                    "horse_no": h["horse_no"],
                    "horse_name": h["horse_name"],
                    "detail": {
                        "scratch_reason": h.get("scratch_reason") or (
                            "競走除外" if is_sc == 2 else "感冒のため"
                        ),
                    },
                })

    # chg_seq は発生時刻順で振り直し（chg_time 昇順）
    changes.sort(key=lambda c: c["chg_time"])
    for i, c in enumerate(changes, start=1):
        c["chg_seq"] = i

    return {
        "server_time": NOW_ISO,
        # field-rename-v0.5 (2026-04-20): v0.5 §5.2 命名統一
        "organizer_type": organizer_type,
        "place_cd": place_cd,
        "place_name": place_name,
        "display_date": TODAY_YYYYMMDD,
        "changes": changes,
    }


def _group_odds_by_place(odds_by_file: dict) -> dict:
    """odds_by_file: {filename: data_dict} → {(organizer_type, place_cd, place_name): [(rr, data), ...]}

    field-rename-v0.5 (2026-04-20): v0.5 §4.3 命名で読み出す。
    """
    out = {}
    for fn, data in odds_by_file.items():
        r = data.get("race", {})
        key = (r.get("organizer_type"), r.get("place_cd"), r.get("place_name"))
        out.setdefault(key, []).append((r.get("rr"), data))
    return out


# ========================================================================
# H-01 (2026-04-17): schedule_0106 / 0107（中止サンプル）
# ========================================================================
def build_schedule_0106(fast: bool = False) -> dict:
    """schedule_0106: レース中止サンプル。中山8R (odds_status=2) を全画面に表示。"""
    if fast:
        s1_start, s1_end = 0, 5
        post_offset = 30
    else:
        s1_start, s1_end = 0, 360
        post_offset = 30

    race = _race_spec("odds_JRA_06_08.json", post_offset)
    screen_races = {p: [race] for p in ["P1", "P2", "P3", "P4"]}

    slots = [
        build_slot("slot1", s1_start, s1_end, "PAT-4SPLIT-STD", screen_races),
    ]
    return {
        "server_time": NOW_ISO,
        "monitor_id": 106,                  # path-date-folder: v0.5 §1.3.1 INT 化
        "display_date": TODAY_YYYYMMDD,     # path-date-folder: v0.5 §3.3 必須
        "slots": slots,
    }


def build_schedule_0107(fast: bool = False) -> dict:
    """schedule_0107: 開催中止サンプル。船橋5R (odds_status=3) を全画面に表示。"""
    if fast:
        s1_start, s1_end = 0, 5
        post_offset = 40
    else:
        s1_start, s1_end = 0, 360
        post_offset = 40

    race = _race_spec("odds_NAR_45_05.json", post_offset)
    screen_races = {p: [race] for p in ["P1", "P2", "P3", "P4"]}

    slots = [
        build_slot("slot1", s1_start, s1_end, "PAT-4SPLIT-STD", screen_races),
    ]
    return {
        "server_time": NOW_ISO,
        "monitor_id": 107,                  # path-date-folder: v0.5 §1.3.1 INT 化
        "display_date": TODAY_YYYYMMDD,     # path-date-folder: v0.5 §3.3 必須
        "slots": slots,
    }


def main():
    # path-date-folder (2026-04-20): v0.5 §1.5 に従い、出力先を日付フォルダ配下に統一。
    #   schedules/{YYYYMMDD}/{monitor_id}.json
    #   odds/{YYYYMMDD}/{ORG}_{PP}_{RR}.json
    #   changes/{YYYYMMDD}/{ORG}_{PP}.json（既存と整合）
    schedules_dir = SCHEDULES_OUT_BASE / TODAY_YYYYMMDD
    odds_dir      = ODDS_OUT_BASE / TODAY_YYYYMMDD
    changes_dir   = CHANGES_OUT_BASE / TODAY_YYYYMMDD
    schedules_dir.mkdir(parents=True, exist_ok=True)
    odds_dir.mkdir(parents=True, exist_ok=True)
    changes_dir.mkdir(parents=True, exist_ok=True)

    # 同日分の既存 JSON を掃除（再生成で差替え）
    for p in schedules_dir.glob("*.json"): p.unlink()
    for p in odds_dir.glob("*.json"): p.unlink()
    for p in changes_dir.glob("*.json"): p.unlink()

    # 旧 data/ 配下の schedule_*.json / odds_*.json を削除（path-date-folder 移行）。
    #   data/ ディレクトリ自体は残す（空になるが、将来の用途のため削除しない）。
    if LEGACY_DATA_DIR.exists():
        legacy_removed = 0
        for p in LEGACY_DATA_DIR.glob("schedule_*.json"):
            p.unlink(); legacy_removed += 1
        for p in LEGACY_DATA_DIR.glob("odds_*.json"):
            p.unlink(); legacy_removed += 1
        if legacy_removed:
            print(f"[path-date-folder] removed {legacy_removed} legacy file(s) from data/")

    # 各レースを書き出し（ファイル名から "odds_" を剥がして新配置へ）
    for fname, params in RACE_DEFINITIONS:
        data = make_race(**params)
        new_fname = fname.replace("odds_", "")  # "NAR_45_01.json"
        (odds_dir / new_fname).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"wrote odds/{TODAY_YYYYMMDD}/{new_fname}: "
              f"{len(data['horses'])}頭 post={data['race']['post_time']} "
              f"um={len(data['umaren_matrix'])} um_pop={len(data['umaren_popular'])}")

    def _write_schedule(monitor_id: int, fast: bool, sched: dict, desc: str):
        """スケジュール JSON を schedules/{YYYYMMDD}/{monitor_id}[_fast].json に書き出す。"""
        suffix = "_fast" if fast else ""
        fname = f"{monitor_id}{suffix}.json"
        (schedules_dir / fname).write_text(
            json.dumps(sched, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote schedules/{TODAY_YYYYMMDD}/{fname}: {len(sched['slots'])} slots ({desc})")

    # 通常版スケジュール（monitor_id=101）
    _write_schedule(101, False, build_schedule(fast=False), "60分間隔")
    _write_schedule(101, True,  build_schedule(fast=True),  "5/10/15分間隔")

    # 指示書09: monitor_id=102 L字+1画面デモ
    _write_schedule(102, False, build_schedule_0102(fast=False), "L字+1画面+4分割動画、60分間隔")
    _write_schedule(102, True,  build_schedule_0102(fast=True),  "L字+1画面+4分割動画、1分間隔")

    # H-04: monitor_id=103 複数場混在
    _write_schedule(103, False, build_schedule_0103(fast=False), "複数場混在、通常")
    _write_schedule(103, True,  build_schedule_0103(fast=True),  "複数場混在、短縮")

    # H-04: monitor_id=104 1レース固定
    _write_schedule(104, False, build_schedule_0104(fast=False), "1レース固定、通常")
    _write_schedule(104, True,  build_schedule_0104(fast=True),  "1レース固定、短縮")

    # H-04: monitor_id=105 slot遷移
    _write_schedule(105, False, build_schedule_0105(fast=False), "slot遷移、通常")
    _write_schedule(105, True,  build_schedule_0105(fast=True),  "slot遷移、短縮")

    # H-01: monitor_id=106 レース中止サンプル
    _write_schedule(106, False, build_schedule_0106(fast=False), "レース中止、通常")
    _write_schedule(106, True,  build_schedule_0106(fast=True),  "レース中止、短縮")

    # H-01: monitor_id=107 開催中止サンプル
    _write_schedule(107, False, build_schedule_0107(fast=False), "開催中止、通常")
    _write_schedule(107, True,  build_schedule_0107(fast=True),  "開催中止、短縮")

    # 3R-entries-results-phase2 (2026-04-21): monitor 108〜116（9 パターン × 3 レース）
    #   schedule JSON 生成
    for mid in sorted(MONITOR_TO_PATTERN.keys()):
        pattern = MONITOR_TO_PATTERN[mid]
        _write_schedule(mid, False, build_schedule_entries_results(mid, fast=False),
                        f"3R成績 {pattern}、通常")
        _write_schedule(mid, True,  build_schedule_entries_results(mid, fast=True),
                        f"3R成績 {pattern}、短縮")

    # 3R-entries-results-phase2 (2026-04-21): results/ ディレクトリ
    results_dir = Path(__file__).resolve().parent.parent / "results" / TODAY_YYYYMMDD
    results_dir.mkdir(parents=True, exist_ok=True)
    for p in results_dir.glob("*.json"):
        p.unlink()
    # 9 パターン × 3 レース = 27 results JSON 生成
    for pattern, races in PATTERN_TO_RACES.items():
        for (org, pp, rr) in races:
            race_spec = _race_spec_for_results(org, pp, rr)
            seed = (hash((org, pp, rr)) % 10000) + 1
            # NORMAL パターンの最初のレース（NAR_49_01）に特払いサンプルを仕込む
            special_bet, special_idx = (None, -1)
            if pattern == "NORMAL" and rr == 1:
                special_bet, special_idx = ("win", 0)   # 単勝 70円
            data = gen_results_json(race_spec, pattern, seed, special_bet, special_idx)
            fname = f"{org}_{pp}_{rr:02d}.json"
            (results_dir / fname).write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"wrote results/{TODAY_YYYYMMDD}/{fname}: pattern={pattern} "
                  f"entries={len(data['entries'])} "
                  f"payouts={sum(len(v) for k,v in data['payouts'].items() if isinstance(v,list))}")

    # ==============================================================
    # Phase 3 (2026-04-21): ばんえい競馬データ生成
    # --------------------------------------------------------------
    # - results/NAR_03_{01,02,03}.json: 帯広 1R/2R/3R（成績モード用）
    #   03 に同着パターン E（2 着 3 頭同着 + 返還）のテストケースを含める
    # - odds/NAR_03_{04,05,06}.json: 帯広 4R/5R/6R（出走表モード用）
    # - schedules/20260421/{119,120,121,122}.json: ばんえい用スケジュール
    # --------------------------------------------------------------
    print()
    # results JSON 生成（既存 3R の削除後なので追加のみ）
    banei_results = [
        (1, "NORMAL", 2.5, 5, False),
        (2, "NORMAL", 1.8, 5, False),
        # 3R は E パターン（2着 3 頭同着 + 返還）で同着/返還の動作検証
        (3, "E",      1.8, 4, True),
    ]
    for (rr, pat, water, hcount, refund) in banei_results:
        data = gen_banei_results_json(rr, pat, water, hcount, refund)
        fname = f"NAR_03_{rr:02d}.json"
        (results_dir / fname).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote results/{TODAY_YYYYMMDD}/{fname}: banei pattern={pat} "
              f"water={water}% refund={'yes' if refund else 'no'}")

    # odds JSON 生成（既存 odds の削除後なので追加のみ、出走表モード検証用）
    banei_odds = [
        (4, 1.8, 9),
        (5, 1.8, 9),
        (6, 2.1, 9),
    ]
    for (rr, water, hcount) in banei_odds:
        data = gen_banei_odds_json(rr, water, hcount)
        fname = f"NAR_03_{rr:02d}.json"
        (odds_dir / fname).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote odds/{TODAY_YYYYMMDD}/{fname}: banei water={water}% horses={hcount}")
    # ==============================================================
    # Phase 5 補助 (2026-04-22): 拡張 monitor 117-124 の schedule を 20260421 →
    #   TODAY に複製（日付文字列を置換）。これらは gen_data.py 本体の
    #   build_schedule_* 系関数で生成していない手動メンテの schedule で、
    #   TODAY ≠ 20260421 のときに 20260422 などへも同期コピーが必要なため、
    #   ここでスケジュール削除後に再配置する。
    # --------------------------------------------------------------
    # 2026-04-30 session3: 117 は monitor=117 比較ビュー (新潟 1R-12R) として
    # 別管理 (output/gen_niigata_117.py が生成)。ここの auto-copy は対象外にする。
    extra_monitors = [118, 119, 120, 121, 122, 123, 124]
    source_date = "20260421"
    if TODAY_YYYYMMDD != source_date:
        source_dir = SCHEDULES_OUT_BASE / source_date
        for mon in extra_monitors:
            for suffix in (f"{mon}.json", f"{mon}_fast.json"):
                src_path = source_dir / suffix
                if not src_path.exists():
                    continue
                data = json.loads(src_path.read_text(encoding="utf-8"))
                data["display_date"] = TODAY_YYYYMMDD
                for slot in data.get("slots", []):
                    slot["start_time"] = slot["start_time"].replace(
                        f"{source_date[:4]}-{source_date[4:6]}-{source_date[6:8]}",
                        f"{TODAY_YYYYMMDD[:4]}-{TODAY_YYYYMMDD[4:6]}-{TODAY_YYYYMMDD[6:8]}"
                    )
                    slot["end_time"] = slot["end_time"].replace(
                        f"{source_date[:4]}-{source_date[4:6]}-{source_date[6:8]}",
                        f"{TODAY_YYYYMMDD[:4]}-{TODAY_YYYYMMDD[4:6]}-{TODAY_YYYYMMDD[6:8]}"
                    )
                    for scr in slot.get("screens", []):
                        for race in scr.get("races", []):
                            if "post_time_iso" in race:
                                race["post_time_iso"] = race["post_time_iso"].replace(
                                    f"{source_date[:4]}-{source_date[4:6]}-{source_date[6:8]}",
                                    f"{TODAY_YYYYMMDD[:4]}-{TODAY_YYYYMMDD[4:6]}-{TODAY_YYYYMMDD[6:8]}"
                                )
                            if "data_source" in race:
                                race["data_source"] = race["data_source"].replace(
                                    source_date, TODAY_YYYYMMDD
                                )
                (schedules_dir / suffix).write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
        print(f"wrote schedules/{TODAY_YYYYMMDD}/: 117-124 copied from {source_date}")

    # 通常版を返り値保持（下の print 用）
    sched = build_schedule(fast=False)

    # H-08: 変更情報JSON（場単位、changes/{YYYYMMDD}/）を生成
    print()
    # 生成済 odds JSON を読み直して場単位に groupby（new パス）
    odds_by_file = {}
    for p in sorted(odds_dir.glob("*.json")):
        try:
            # _group_odds_by_place は "odds_" プレフィックス前提なしで動作するが、
            # 旧コードとの互換で "odds_" を付け直して渡す
            odds_by_file["odds_" + p.name] = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[warn] cannot read {p.name}: {e}")
    groups = _group_odds_by_place(odds_by_file)
    # field-rename-v0.5 (2026-04-20): v0.5 §4.3 命名で unpack
    for (organizer_type, place_cd, place_name), entries in sorted(groups.items()):
        if not organizer_type or not place_cd:
            continue
        cdata = make_changes_json_for_place(organizer_type, place_cd, place_name, entries)
        fname = f"{organizer_type}_{place_cd}.json"
        (changes_dir / fname).write_text(
            json.dumps(cdata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote changes/{TODAY_YYYYMMDD}/{fname}: "
              f"{len(cdata['changes'])}件 ({place_name})")

    print(f"\nNOW = {NOW_ISO}")
    print(f"slot1 start = {sched['slots'][0]['start_time']}")
    print(f"slot2 start = {sched['slots'][1]['start_time']}")
    print(f"slot3 start = {sched['slots'][2]['start_time']}")


if __name__ == "__main__":
    main()
