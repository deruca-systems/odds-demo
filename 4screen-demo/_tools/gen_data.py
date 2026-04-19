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

OUT = Path(__file__).resolve().parent.parent / "data"
# H-08 (2026-04-17): 変更情報JSON（場単位）は changes/{YYYYMMDD}/ 配下に配置
CHANGES_OUT_BASE = Path(__file__).resolve().parent.parent / "changes"

# --- 時刻基準 ---
JST = timezone(timedelta(hours=9))
NOW = datetime.now(JST)
NOW_ISO = NOW.strftime("%Y-%m-%dT%H:%M:%S+09:00")
TODAY_YYYYMMDD = NOW.strftime("%Y%m%d")  # H-08 用の日付フォルダ名


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
      org_jockey_nm / chg_jockey_nm / chg_reason_cd / org_genryokigo / new_genryokigo

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
            "chg_jockey_nm": chg_jockey_nm,
            "chg_reason_cd": chg_reason_cd,
            "org_genryokigo": org_genryokigo,
            "new_genryokigo": new_genryokigo,
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


# H-03 (2026-04-19): 枠単（frame_umatan）オッズ生成
# 仕様（2026-04-19 及川指示で改訂）:
#   - `enabled=False` のレースは空配列（枠単発売なし）。親 index.html はページング停止
#   - 同枠組合せ（frame_a == frame_b）は、その枠が2頭以上のときのみ出力
#     例: 8頭立て = 1〜8枠に1頭ずつ → 同枠組合せは全て存在しない
#     例: 10頭立て = 7-8枠が2頭ずつ → 7-7, 8-8 は存在、1-1〜6-6 は存在しない
#   - 相手枠が出走頭数ゼロの枠は組合せ自体が存在しない（通常、8頭以上立てなら全枠使われる）
def gen_frame_umatan(horses: list, seed: int, enabled: bool = True, num_frames: int = 8):
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
    org: str,
    venue: str,
    place_code: str,          # H-01: 場コード（例: "09"=阪神, "45"=船橋）
    race_no: int,
    race_name: str,
    weather: str,
    weather_label: str,
    surface: str,
    condition: str,
    distance: int,
    direction: str,
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
    has_frame_umatan: bool = True,      # H-03 (2026-04-19): False で枠単発売なしサンプル
):
    assert org in ("JRA", "NAR"), f"org must be 'JRA' or 'NAR', got {org!r}"
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
    return {
        "server_time": NOW_ISO,
        "race": {
            "org": org,
            "place_code": place_code,   # H-01 追加
            "venue": venue, "race_no": race_no, "race_name": race_name,
            "race_class": "", "deadline_min": reference_deadline, "post_time": post_time_hhmm,
            "post_time_iso": post_time_iso,
            "weather": weather, "weather_label": weather_label,
            "surface": surface, "condition": condition,
            "distance": distance, "direction": direction,
            "is_previous_day": is_previous_day,
            "odds_status": odds_status,  # H-01 追加
            # H-03 (2026-04-19): 枠単オッズ。race オブジェクト内に配置（指示書準拠）。
            # 仕様改訂 (2026-04-19): 同枠組合せは2頭以上の枠のみ、発売なしは空配列。
            "frame_umatan": gen_frame_umatan(horses, seed, enabled=has_frame_umatan),
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
        org="NAR", place_code="45",
        venue="船橋", race_no=1, race_name="サラ系3歳未勝利",
        weather="sunny", weather_label="晴",
        surface="ダ", condition="良", distance=1200, direction="左",
        post_time_offset_min=3, horses_n=8,
        name_pool=FUNABASHI_NAMES, jockey_pool=JOCKEYS_NAR, seed=101,
    )),
    ("odds_NAR_45_02.json", dict(
        org="NAR", place_code="45",
        venue="船橋", race_no=2, race_name="サラ系3歳新馬",
        weather="sunny", weather_label="晴",
        surface="ダ", condition="良", distance=1400, direction="左",
        post_time_offset_min=10, horses_n=11,
        name_pool=FUNABASHI_NAMES, jockey_pool=JOCKEYS_NAR, seed=102,
        # H-02 (2026-04-17): 見習騎手サンプル（馬番4に減量記号 ★）
        apprentice_horse_nos={4: "★"},
    )),
    ("odds_NAR_45_03.json", dict(
        org="NAR", place_code="45",
        venue="船橋", race_no=3, race_name="サラ系3歳1勝クラス",
        weather="cloudy", weather_label="曇",
        surface="ダ", condition="稍重", distance=1600, direction="左",
        post_time_offset_min=15, horses_n=12,
        name_pool=FUNABASHI_NAMES, jockey_pool=JOCKEYS_NAR, seed=103,
    )),
    # 指示書08: 取消馬デモ用 8頭レース（5番を出走取消）
    #   slot1 内で「既存4テンプレ（単勝複勝枠連 / 馬連ワイド / 人気1-15 / 人気16-30）」を
    #   取消馬入りで見せる。post_time は 1R(3分)と 2R(10分)の間に配置。
    ("odds_NAR_45_04.json", dict(
        org="NAR", place_code="45",
        venue="船橋", race_no=4, race_name="サラ系3歳500万下",
        weather="cloudy", weather_label="曇",
        surface="ダ", condition="良", distance=1200, direction="左",
        post_time_offset_min=8, horses_n=8,
        name_pool=FUNABASHI_NAMES, jockey_pool=JOCKEYS_NAR, seed=104,
        scratched_horse_nos={5: 1},  # 5番: 出走取消
    )),
    # ---- slot 2: 午後の部 ----
    ("odds_NAR_49_02.json", dict(
        org="NAR", place_code="49",
        venue="名古屋", race_no=2, race_name="サラ系2歳新馬",
        weather="cloudy", weather_label="曇",
        surface="ダ", condition="稍重", distance=1200, direction="右",
        post_time_offset_min=60, horses_n=13,
        name_pool=NAGOYA_NAMES, jockey_pool=JOCKEYS_NAR, seed=202,
    )),
    ("odds_NAR_49_07.json", dict(
        org="NAR", place_code="49",
        venue="名古屋", race_no=7, race_name="サラ系2歳未勝利",
        weather="light-rain", weather_label="小雨",
        surface="ダ", condition="重", distance=1400, direction="右",
        post_time_offset_min=63, horses_n=14,
        name_pool=NAGOYA_NAMES, jockey_pool=JOCKEYS_NAR, seed=207,
        # H-02: 見習騎手サンプル（馬番7に減量記号 ▲）
        apprentice_horse_nos={7: "▲"},
    )),
    ("odds_NAR_49_08.json", dict(
        org="NAR", place_code="49",
        venue="名古屋", race_no=8, race_name="サラ系3歳オープン",
        weather="rain", weather_label="雨",
        surface="ダ", condition="不良", distance=1800, direction="右",
        post_time_offset_min=66, horses_n=16,
        name_pool=NAGOYA_NAMES, jockey_pool=JOCKEYS_NAR, seed=208,
    )),
    ("odds_NAR_49_09.json", dict(
        org="NAR", place_code="49",
        venue="名古屋", race_no=9, race_name="サラ系3歳2勝クラス",
        weather="rain", weather_label="雨",
        surface="ダ", condition="不良", distance=1200, direction="右",
        post_time_offset_min=69, horses_n=10,
        name_pool=NAGOYA_NAMES, jockey_pool=JOCKEYS_NAR, seed=209,
        # H-03 (2026-04-19): 枠単発売なしサンプル。single-screen.html のページング停止確認用
        has_frame_umatan=False,
    )),
    # ---- slot 3: メインレースの部 ----
    ("odds_JRA_05_11.json", dict(
        org="JRA", place_code="05",
        venue="東京", race_no=11, race_name="フェブラリーステークス",
        weather="sunny", weather_label="晴",
        surface="芝", condition="良", distance=2400, direction="左",
        post_time_offset_min=123, horses_n=18,
        name_pool=TOKYO_NAMES, jockey_pool=JOCKEYS_JRA, seed=311,
        is_previous_day=True,
    )),
    ("odds_JRA_06_11.json", dict(
        org="JRA", place_code="06",
        venue="中山", race_no=11, race_name="スプリングステークス",
        weather="sunny", weather_label="晴",
        surface="芝", condition="良", distance=1600, direction="右",
        post_time_offset_min=126, horses_n=16,
        name_pool=NAKAYAMA_NAMES, jockey_pool=JOCKEYS_JRA, seed=312,
    )),
    # 指示書08: 取消馬デモ用 18頭レース（5/10番 出走取消・15番 競走除外）
    #   slot3 に追加、MATRIX_VARIANT_FILES に含めてマトリクス4枚テンプレで表示。
    #   マトリクス first/second の両方で取消・除外のブロック/セルが空白＋薄くなる挙動を検証。
    ("odds_JRA_09_11.json", dict(
        org="JRA", place_code="09",
        venue="阪神", race_no=11, race_name="大阪杯",
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
        org="NAR", place_code="30",
        venue="門別", race_no=7, race_name="サラ系3歳B2",
        weather="sunny", weather_label="晴",
        surface="ダ", condition="良", distance=1200, direction="右",
        post_time_offset_min=10, horses_n=18,
        name_pool=MONBETSU_NAMES, jockey_pool=JOCKEYS_NAR, seed=307,
    )),
    # ---- H-01 中止サンプル（schedule_0106/0107 用、2026-04-17）----
    # schedule_0106: レース中止（odds_status=2）— 中山8R
    ("odds_JRA_06_08.json", dict(
        org="JRA", place_code="06",
        venue="中山", race_no=8, race_name="中山8R（中止想定）",
        weather="rain", weather_label="雨",
        surface="芝", condition="不良", distance=1800, direction="右",
        post_time_offset_min=30, horses_n=10,
        name_pool=NAKAYAMA_NAMES, jockey_pool=JOCKEYS_JRA, seed=608,
        odds_status=2,  # レース中止
    )),
    # schedule_0107: 開催中止（odds_status=3）— 船橋5R（場全体中止想定）
    ("odds_NAR_45_05.json", dict(
        org="NAR", place_code="45",
        venue="船橋", race_no=5, race_name="船橋5R（開催中止想定）",
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
}


def _race_id_from_file(fname: str) -> str:
    """'odds_NAR_45_01.json' → 'NAR_45_01'."""
    return fname.replace("odds_", "").replace(".json", "")


def _race_key_from_odds(fname: str) -> str:
    """生成済みオッズJSONから venue+race_no を読み取って race_key を返す（失敗時は race_id 相当）。"""
    default = _race_id_from_file(fname)
    path = OUT / fname
    if not path.exists():
        return default
    try:
        j = json.loads(path.read_text(encoding="utf-8"))
        venue = j.get("race", {}).get("venue", "")
        rno = j.get("race", {}).get("race_no", "")
        if venue and rno:
            return f"{venue}{rno}R"
    except Exception:
        pass
    return default


def _race_spec(odds_file: str, post_offset_min: int) -> dict:
    """new 構造 (H-04) の race エントリを作る。
    odds_file: 'odds_NAR_45_01.json'
    post_offset_min: NOW からの発走時刻オフセット（分）
    """
    return {
        "race_id": _race_id_from_file(odds_file),
        "race_key": _race_key_from_odds(odds_file),
        "post_time_iso": now_plus_min(post_offset_min),
        "data_source": "data/" + odds_file,
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
    screens_out = []
    for s in pattern["screens"]:
        pos = s["position"]
        screen_entry = {
            "position": pos,
            "template": s["template"],
        }
        if s.get("type") == "video":
            screen_entry["type"] = "video"
            if video_config_by_pos and pos in video_config_by_pos:
                screen_entry.update(video_config_by_pos[pos])
            screen_entry["races"] = []  # video は races[] を空配列固定（Phase 1 §9.3 案V1）
        else:
            screen_entry["races"] = screen_races.get(pos, [])
        screens_out.append(screen_entry)
    return {
        "slot_id": slot_id,
        "start_time": now_plus_min(start_offset_min),
        "end_time": now_plus_min(end_offset_min),
        "layout": pattern["layout"],
        "display_pattern_id": display_pattern_id,
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
        "monitor_id": "0101",
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
        "monitor_id": "0102",
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
        "monitor_id": "0103",
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
        "monitor_id": "0104",
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
        "monitor_id": "0105",
        "slots": slots,
    }


# ========================================================================
# H-08 (2026-04-17): cchg 変更情報JSON生成（場単位）
# ========================================================================
def make_changes_json_for_place(org: str, place_code: str, place_name: str,
                                 odds_entries: list) -> dict:
    """指定場に属する全オッズJSONから changes エントリを逆引き生成する。

    Args:
        org: "JRA" | "NAR"
        place_code: 場コード文字列（例: "09"）
        place_name: 表示用場名（例: "阪神"）
        odds_entries: [(race_no, race_data_dict), ...]（post_time_iso 昇順）

    Returns:
        changes JSON dict（§4.3 スキーマに準拠）
    """
    changes = []
    seq = 0
    # post_time 昇順でイテレート（chg_time も発走前の妥当な時刻に割り当て）
    for (race_no, data) in sorted(odds_entries, key=lambda x: x[1]["race"]["post_time_iso"]):
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
                    "race_no": race_no,
                    "chg_type": 1,
                    "chg_type_name": CHG_TYPE_MAP[1],
                    "horse_no": h["horse_no"],
                    "horse_name": h["horse_name"],
                    "detail": {
                        "org_jockey_nm": h.get("org_jockey_nm"),
                        "chg_jockey_nm": h.get("chg_jockey_nm"),
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
                    "race_no": race_no,
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
        "org": org,
        "place_code": place_code,
        "place_name": place_name,
        "display_date": TODAY_YYYYMMDD,
        "changes": changes,
    }


def _group_odds_by_place(odds_by_file: dict) -> dict:
    """odds_by_file: {filename: data_dict} → {(org, place_code, place_name): [(race_no, data), ...]}"""
    out = {}
    for fn, data in odds_by_file.items():
        r = data.get("race", {})
        key = (r.get("org"), r.get("place_code"), r.get("venue"))
        out.setdefault(key, []).append((r.get("race_no"), data))
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
        "monitor_id": "0106",
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
        "monitor_id": "0107",
        "slots": slots,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # 古いオッズJSON削除
    for p in OUT.glob("odds_*.json"):
        p.unlink()

    # 各レースを書き出し
    for fname, params in RACE_DEFINITIONS:
        data = make_race(**params)
        (OUT / fname).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"wrote {fname}: {len(data['horses'])}頭 "
              f"post={data['race']['post_time']} "
              f"um={len(data['umaren_matrix'])} "
              f"um_pop={len(data['umaren_popular'])}")

    # 通常版スケジュール
    sched = build_schedule(fast=False)
    (OUT / "schedule_0101.json").write_text(
        json.dumps(sched, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote schedule_0101.json: {len(sched['slots'])} slots (60分間隔)")

    # 短縮版スケジュール
    sched_fast = build_schedule(fast=True)
    (OUT / "schedule_0101_fast.json").write_text(
        json.dumps(sched_fast, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote schedule_0101_fast.json: {len(sched_fast['slots'])} slots (5/10/15分間隔)")

    # 指示書09: monitor_id=0102 L字+1画面デモ スケジュール
    sched_0102 = build_schedule_0102(fast=False)
    (OUT / "schedule_0102.json").write_text(
        json.dumps(sched_0102, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote schedule_0102.json: {len(sched_0102['slots'])} slots (L字+1画面+4分割動画、60分間隔)")

    sched_0102_fast = build_schedule_0102(fast=True)
    (OUT / "schedule_0102_fast.json").write_text(
        json.dumps(sched_0102_fast, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote schedule_0102_fast.json: {len(sched_0102_fast['slots'])} slots (L字+1画面+4分割動画、1分間隔)")

    # H-04: monitor_id=0103 複数場混在
    for fast_flag, suffix, desc in [(False, "", "通常"), (True, "_fast", "短縮")]:
        s = build_schedule_0103(fast=fast_flag)
        (OUT / f"schedule_0103{suffix}.json").write_text(
            json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote schedule_0103{suffix}.json: {len(s['slots'])} slots (複数場混在、{desc})")

    # H-04: monitor_id=0104 1レース固定
    for fast_flag, suffix, desc in [(False, "", "通常"), (True, "_fast", "短縮")]:
        s = build_schedule_0104(fast=fast_flag)
        (OUT / f"schedule_0104{suffix}.json").write_text(
            json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote schedule_0104{suffix}.json: {len(s['slots'])} slots (1レース固定、{desc})")

    # H-04: monitor_id=0105 slot遷移
    for fast_flag, suffix, desc in [(False, "", "通常"), (True, "_fast", "短縮")]:
        s = build_schedule_0105(fast=fast_flag)
        (OUT / f"schedule_0105{suffix}.json").write_text(
            json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote schedule_0105{suffix}.json: {len(s['slots'])} slots (slot遷移、{desc})")

    # H-01: monitor_id=0106 レース中止サンプル
    for fast_flag, suffix, desc in [(False, "", "通常"), (True, "_fast", "短縮")]:
        s = build_schedule_0106(fast=fast_flag)
        (OUT / f"schedule_0106{suffix}.json").write_text(
            json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote schedule_0106{suffix}.json: {len(s['slots'])} slots (レース中止、{desc})")

    # H-01: monitor_id=0107 開催中止サンプル
    for fast_flag, suffix, desc in [(False, "", "通常"), (True, "_fast", "短縮")]:
        s = build_schedule_0107(fast=fast_flag)
        (OUT / f"schedule_0107{suffix}.json").write_text(
            json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote schedule_0107{suffix}.json: {len(s['slots'])} slots (開催中止、{desc})")

    # H-08: 変更情報JSON（場単位、changes/{YYYYMMDD}/）を生成
    print()
    changes_dir = CHANGES_OUT_BASE / TODAY_YYYYMMDD
    changes_dir.mkdir(parents=True, exist_ok=True)
    # 古いchanges JSON削除（同日分のみ）
    for p in changes_dir.glob("*.json"):
        p.unlink()
    # 生成済 odds_*.json を読み直して場単位に groupby
    odds_by_file = {}
    for p in sorted(OUT.glob("odds_*.json")):
        try:
            odds_by_file[p.name] = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[warn] cannot read {p.name}: {e}")
    groups = _group_odds_by_place(odds_by_file)
    for (org, place_code, venue), entries in sorted(groups.items()):
        if not org or not place_code:
            continue
        cdata = make_changes_json_for_place(org, place_code, venue, entries)
        fname = f"{org}_{place_code}.json"
        (changes_dir / fname).write_text(
            json.dumps(cdata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote changes/{TODAY_YYYYMMDD}/{fname}: "
              f"{len(cdata['changes'])}件 ({venue})")

    print(f"\nNOW = {NOW_ISO}")
    print(f"slot1 start = {sched['slots'][0]['start_time']}")
    print(f"slot2 start = {sched['slots'][1]['start_time']}")
    print(f"slot3 start = {sched['slots'][2]['start_time']}")


if __name__ == "__main__":
    main()
