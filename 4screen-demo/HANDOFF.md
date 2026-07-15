# 引継ぎ資料 — 4画面JSONポーリングサンプル（odds-demo）

> **⚠ 2026-07-07 移設ノート**: 本ファイルは旧パス（00.仕事\…\git\keiba-odds\src\odds-demo、更新停止済み）から移設した 2026-04-19 時点のスナップショット。以降の変更（screen5/6 組込、column-major 確定、payout fix、3split 改名等）は各 CC完了報告と本リポジトリの git log を正とする。追記はこのファイルに時系列で行う。

最終更新日: 2026-04-17
作業セッション区切り時点の実装状況と、次セッションで扱うべき残課題をまとめる。

2026-04-17 更新概要:
- 指示書08 取消馬対応（is_scratched）実装・ユーザーフィードバック反映（opacity → ダークグレー背景+赤太字方式に改訂）
- 指示書09 L字レイアウト+動画組込 実装（monitor_id=0102）
- 親 index.html のスロット切替ロジック変更: location.reload() 撤廃 → inline 切替（動画継続再生のため）
- 仕様書§4 準拠で px 完全廃止、vw/vh ベースに統一（L字レイアウトも FHD/4K 比例拡縮）
- **C-01〜C-05 改修（2026-04-17）**:
  - C-01 ポーリング本番デフォルト30秒化（`?fast=1` 連動で10秒、案2採用）
  - C-02 カットイン表示時間10秒確定（★要確認、次回MTG正式議事録化予定）
  - C-03 L字レイアウト使用テンプレ（side-entries / wide-popular）のカットイン呼出削除
  - C-04 ダブルバッファ方式（DocumentFragment + replaceChildren）で画面更新時のちらつき低減
  - C-05 video-frame.html の px 撲滅（`min(0.7vw, 1.2vh)`）
- **動画URL修正（2026-04-17）**: `VIDEO_URL_BASE` のパスを `/hls-live/keiba/_definst_/liveevent/` → `/keiba/nar/live/` に変更。
  旧パスはサブプレイリスト用でマスター（EXT-X-STREAM-INF）は新パスに存在（manifestLoadError解消）
- **H-06 対応（2026-04-17）**: gen_data.py の人気順配列（umaren/umatan/trio/trifecta_popular）で取消馬除外・rank振り直し（Option A採用）
- **H-04 対応（2026-04-17）**: スケジュールJSON新構造 `slot.screens[].races[]` 導入、画面別進行+次レース自動遷移（post+60秒, fast=1時+5秒, `?next_race_sec=N` で上書き）
  - display_pattern_id マッピング表（M-01 成果物）を `display_pattern_mapping_v1.md` に策定
  - 新サンプル schedule: `schedule_0103`（複数場混在）, `schedule_0104`（1レース固定）, `schedule_0105`（slot遷移）
  - `slot.race_rotation_seconds` は廃止、発走時刻ベースの次レース遷移へ
- **H-03 対応（2026-04-19）**: 枠単（frame_umatan）ページング実装
  - オッズJSONの `race.frame_umatan` に枠単オッズ追加（`is_popular`=odds<10.0）
  - **同枠組合せルール**（2026-04-19 及川仕様）: 同枠 `frame_a == frame_b` は同枠頭数が2頭以上のときのみ出力
    - 例: 8頭立て → 同枠なし（全56件）
    - 例: 10頭立て → 7-7, 8-8 のみ（全58件）
    - 例: 16頭以上 → 全8枠同枠あり（全64件）
  - **枠単発売なしレース**: `has_frame_umatan=False` 指定で `frame_umatan: []` 空配列出力（サンプル: 名古屋9R）
  - `templates/single-screen.html` に `#frame-utan` ブロック追加（初期 display:none）
  - 親 `index.html` の 1秒tick で 15秒ごとに枠連↔枠単を postMessage で自動切替
  - **発売なし時のページング停止**: 子 iframe が `frameUmatanAvailability` postMessage で親に通知、親の `checkFrameOddsPaging` は `state.hasFrameUmatan=false` のとき tick を進めず枠連固定
  - レース切替時は枠連に強制リセット + hasFrameUmatan を true に初期化（新レースで再判定）
  - 他テンプレには影響なし。scope: single-screen.html のみ
- **H-01/H-02/H-08 対応（2026-04-17）**: オッズJSON スキーマ拡張 + 変更情報JSON新規追加（SCR-INF-001/003 向けの先行スキーマ拡張、表示側は H-07 で対応）
  - `race.odds_status`（0:発売中 / 1:確定 / 2:レース中止 / 3:開催中止）+ `race.place_code` 追加
  - `horses[]` に 12項目追加: `sex`/`age`/`fwt`/`cnm`/`wt2`/`scratch_reason`/`jockey_changed`/`org_jockey_nm`/`chg_jockey_nm`/`chg_reason_cd`/`org_genryokigo`/`new_genryokigo`
  - `fwt` は小数形式 kg（例: 55.0、DB設計書 ×10格納は本番JSON生成側で変換想定）
  - 新規ディレクトリ `changes/{YYYYMMDD}/{org}_{place}.json` で cchg 変更情報を配信（場単位）
  - 騎手変更サンプル: `odds_JRA_09_11.json` 馬番3（川田→池添、chg_reason_cd=05 騎手負傷）
  - 減量記号サンプル: `odds_NAR_45_02.json` 馬番4 ★ / `odds_NAR_49_07.json` 馬番7 ▲
  - 中止サンプル: `schedule_0106`（レース中止 中山8R, odds_status=2）/ `schedule_0107`（開催中止 船橋5R, odds_status=3）
  - 現行テンプレ（single-screen 等）は新項目未参照・表示影響なし（H-07 で SCR-INF 系テンプレ追加時に使用開始）

---

## 1. プロジェクト概要

### 1.1 目的

地方競馬オッズ表示システム（2026年7月サテライト石狩での試験運用予定）向けの、静的JSONポーリングのみで4画面分割表示を実現するサンプル実装。

### 1.2 参画メンバー

- フォーマイルズ　内山様：表示画面・DB担当
- AIR PROSPECT　堀井様：管理画面担当
- リンクスティップ　**芥川様：デザイン担当**
- デルカ　及川様：プロジェクトリーダー（= 本 Claude セッションのユーザー）

### 1.3 本サンプルの位置づけ

- 4/14 MTG で決定したアーキテクチャ（親iframeがスケジュール管理、子iframeが芥川様テンプレートを描画）を静的ファイルだけで検証するデモ
- **GitHub Pages ホスト済み**: `https://deruca-systems.github.io/odds-demo/4screen-demo/`
- 芥川様 HTML + CSS（screen2.html / header.html 由来）を基盤に、JS でデータ流し込み

---

## 2. ディレクトリ構成

```
C:\Users\oikawa.masafumi\Documents\00.仕事\地方競馬オッズ表示システム(仮)\git\keiba-odds\
├── design/
│   ├── システム組み込み申し送り仕様書.md          （最重要・色/クラス/CSS変数ルール）
│   └── htdocs/
│       ├── assets/css/style.css                  （旧版、参照のみ、改変しない）
│       ├── screen1.html, screen2.html            （4画面一体HTML 芥川様）
│       ├── screen3.html                          （4画面一体、枠単、最近追加）
│       ├── single-screen.html                    （単勝・複勝・枠連 単画面）
│       ├── single-umaren-wide.html               （馬連・ワイド 単画面、旧版）
│       ├── single-popular.html                   （人気順1-15 単画面）
│       └── single-popular-second.html            （人気順16-30 単画面）
│
└── src/odds-demo/   ★本サンプルの実装位置
    ├── HANDOFF.md                                 （本ファイル）
    ├── README.md                                  （運用・仕様ドキュメント、芥川様確認事項A〜I）
    ├── DEMO_GUIDE.md                              （実演ガイド、URL・タイムライン・公開手順）
    ├── index.html                                 （親フレーム、スケジュール制御 + common.js 読込）
    ├── templates/
    │   ├── single-screen.html                     （単勝・複勝・枠連）
    │   ├── single-umaren-wide.html                （馬連・ワイド、ページ自動ローテ）
    │   ├── single-popular.html                    （人気順1-15）
    │   ├── single-popular-second.html             （人気順16-30）
    │   ├── single-umaren-first.html               馬連（馬番順）軸1-9
    │   ├── single-umaren-second.html              馬連（馬番順）軸10-17
    │   ├── single-umatan-first.html               馬単（馬番順）軸1-9
    │   ├── single-umatan-second.html              馬単（馬番順）軸10-18
    │   ├── cutin.html                             CUT-001/002 オーバーレイ（fetch挿入）
    │   ├── side-entries.html                      ★指示書09 L字左袖 出走表
    │   ├── wide-popular.html                      ★指示書09 L字右下 4賭式×5件
    │   └── video-frame.html                       ★指示書09 HLS動画 (TECH-VERIFICATION-ONLY)
    ├── assets/
    │   ├── css/
    │   │   ├── style.css                          （screen2_files 版スーパーセット、改変禁止）
    │   │   └── demo-helpers.css                   （デモ専用ヘルパー、取消馬スタイル含む）
    │   ├── js/common.js                           （共通ユーティリティ + エラーハンドリング基盤 + 取消馬ヘルパー）
    │   └── images/weather/*.svg                   （天候アイコン）
    ├── data/
    │   ├── schedule_0101.json                     （通常版 3slot 60分間隔）
    │   ├── schedule_0101_fast.json                （fast版 5/10/15分）
    │   ├── schedule_0102.json                     ★指示書09 L字+1画面+4分割動画 60分×3
    │   ├── schedule_0102_fast.json                ★指示書09 同上 1分×3
    │   └── odds_{ORG}_{PLACE}_{RACE}.json × 12    （船橋4R取消1・阪神11R取消2除外1・門別7R 18頭を追加）
    ├── _tools/
    │   └── gen_data.py                            （NOW基準データ生成、L字/1画面/4split slot ビルダー追加）
    ├── TECH_VERIFICATION_NOTES.md                 ★指示書09 TECH-VERIFICATION-ONLY マーカー管理
    ├── README.md                                  （§J 取消馬対応、§K L字+動画組込 追加）
    ├── DEMO_GUIDE.md
    └── HANDOFF.md                                 （本ファイル）

C:\Users\oikawa.masafumi\Documents\00.仕事\地方競馬オッズ表示システム(仮)\docs\仕様書_specs\claude code実装指示\
├── 4画面サンプル実装指示書.txt                     （初回指示）
├── 03_馬連ワイドP2P3ページローテーション.txt         （破棄済み）
├── 03_2_CC指示_馬連ワイドP2P3_データ表示修正.md      （旧仕様）
├── 03_3_CC指示_馬連ワイド分割表示_完全修正版.md     （pairSum対称分割・確定）
├── 04_OrganizerType対応.txt                       ★実装済 JRA/NARプレフィクス
├── 05_カットイン CUT-001CUT-002 実装.txt           ★実装済
└── 07_CC指示_エラーハンドリング.md                  ★実装済 指数バックオフ

C:\Users\oikawa.masafumi\Documents\00.仕事\地方競馬オッズ表示システム(仮)\docs\画面サンプル(202604015_screen34サンプル)\
├── screen2.html / screen2_files/                  （馬連/馬単マトリックス原デザイン、4ブロック切抜き済）
└── header.html / header_files/                    （ヘッダー色バリエーション11種、.race-time.start 等）
```

---

## 3. 実装済み機能（累計）

### 3.1 基本アーキテクチャ

- [x] 親index.html（4分割iframe管理、スケジュールpoll 10秒、時間帯スロット切替でリロード）
- [x] 子テンプレート 9種（single-screen / umaren-wide / popular / popular-second / umaren-first / umaren-second / umatan-first / umatan-second / cutin）
- [x] common.js（フォーマッタ、色判定、マトリックス描画、ページ分割、カットイン、エラーハンドリング）
- [x] gen_data.py（NOW基準 post_time、標準枠割り、JRA/NAR prefix、umatan_matrix生成）

### 3.2 1日シミュレーション（fast モード slot 5/10/15分）

| スロット | レース | 頭数 | post_time | テンプレ構成 |
|---|---|---|---|---|
| slot1 | 船橋1R | 8 | NOW+3分 | 既存4枚（カットイン実演用、NOW+30秒で締切） |
| | 船橋2R | 11 | NOW+10分 | 既存4枚 |
| | 船橋3R | 12 | NOW+15分 | **新マトリクス4枚**（馬連1/2・馬単1/2） |
| slot2 | 名古屋2R | 13 | NOW+60分 | 既存4枚 |
| | 名古屋7R | 14 | NOW+63分 | 既存4枚 |
| | **名古屋8R** | 16 | NOW+66分 | **新マトリクス4枚** |
| | 名古屋9R | 10 | NOW+69分 | 既存4枚 |
| slot3 | **東京11R** | 18 | NOW+123分（前日発売）| **新マトリクス4枚**（フル表示） |
| | 中山11R | 16 | NOW+126分 | 既存4枚 |

`gen_data.py` の `MATRIX_VARIANT_FILES` で 3 レース designate → `frames_of()` で新テンプレ4枚に振り分け。

### 3.3 UI制御

- [x] URLクエリ: `?monitor=0101` `?fast=1` `?page_rotation=N` `?schedule_poll=N` `?odds_poll=N` `?cutin_sec=N` `?safety_margin_sec=N`
- [x] 情報バー + H キー表示切替
- [x] 端末時刻補正（親で初回固定、子に baseOffset 伝搬）
- [x] レースローテーション（45秒ごと、race_rotation_seconds 秒）、スロット境界で reload

### 3.4 子テンプレートの動的機能

- [x] ヘッダー時間ベース切替（pre=発走HH:MM、countdown=締切N分前、closed=発売締切）
  - `.race-time[data-mode]` で変化、`.start` クラスは pre モード時のみ（芥川 header.html 準拠）
  - P1〜P4 共通で赤グラデ警告色（`demo-helpers.css` I-1 暫定）
- [x] 締切の2段階定義: 実投票締切（発走2分前） / 表示上の締切（実締切 - 30秒、安全マージン）
- [x] is_closing（1分前点滅） / is_closed（発売締切表示）の自動切替
- [x] 前日発売モード（race-info 非表示、前日発売ラベルのみ）
- [x] オッズ色自動判定（win-popular / win-secondary / place-popular / value-popular / odds-popular / odds-unpopular）
- [x] 騎手名4文字切り（truncateJockey）
- [x] 馬連ワイド: pairSum対称分割（`calcUmarenLayout`）、15秒ごとページローテ
- [x] 馬連・馬単マトリクス（馬番順）: 9軸×行数、odds-popular/unpopular/cross（同馬）自動判定
- [x] P1-P2-P3-P4 の行高さ完全同期（`demo-helpers.css` で flex column + minmax(0,1fr) + flex:1 1 0）

### 3.5 カットイン CUT-001/CUT-002

- [x] `templates/cutin.html` を子iframe起動時に fetch → body に DOM 挿入
- [x] 表示締切5分前で CUT-001 発火（「締切 5 分前」固定表示、10秒）
- [x] 表示締切到達で CUT-002 発火（「発売を締め切りました」、10秒）
- [x] `CUTIN_DISPLAY_SEC=10` 秒（仕様書原典は30秒、デモ短縮のため）
- [x] ヘッダーと同じ時刻基準（`serverOffsetMs` 初回固定）で同期

### 3.6 エラーハンドリング（指示書07 準拠）

- [x] `fetchWithOffset()` に AbortController / 10秒タイムアウト
- [x] `startResilientPolling()` 指数バックオフ（×1→×1→×2→×4→×8→×12上限）
- [x] `registerPoller` / `getAllPollerStatus` / `dumpPollerStatus` で状態公開
- [x] 失敗時は render() を呼ばず既存 lastData 画面維持
- [x] 成功で failCount=0 即時リセット
- [x] 親の情報バー status に「スケジュール取得失敗（連続N回）」表示
- [x] 9つの poller 全てがこの仕組みで動作（親 schedule + 8子テンプレート）

### 3.7 データ構造（指示書04 OrganizerType 対応）

- [x] オッズJSON ファイル名: `odds_{JRA|NAR}_{placeCode}_{raceNo}.json`
- [x] オッズJSON 内 `race.org` フィールドあり
- [x] schedule JSON の `data_source` は新命名規則
- [x] `umatan_matrix`（18頭で306件）を gen_data.py で生成
- [x] 本番S3パス想定: `odds/{YYYYMMDD}/{org}_{place}_{race}.json`

### 3.8 取消馬対応（指示書08、2026-04-16 実装＋ユーザーフィードバック反映）

- [x] `horses[].is_scratched`（0/1/2）フィールドをサポート
- [x] `common.js`: `scratchedLabel` / `scratchedLabelShort` / `buildScratchedSet` / `filterScratchedFromPopular`
- [x] `computeWinClasses` / `computePlaceClasses` は取消馬を自動除外
- [x] `renderMatrixTable` は取消馬軸/相手を暗背景+空白化
- [x] 表示方式: **opacity 廃止、`.race-table__scratched` ラベルセル（#3a3a3a + 赤太字 #FF5252）** で「出走取消」/「競走除外」
- [x] 人気順画面は短縮表記「取消」/「除外」（`scratchedLabelShort`）
- [x] 馬連ワイド・マトリクス系: `.body-scratched` / `.odds-scratched` / `.row-scratched` による暗背景化（opacity なし）
- [x] サンプルデータ: 船橋4R（8頭・5番取消） / 阪神11R（18頭・5/10取消・15除外）

### 3.9 L字レイアウト+動画組込（指示書09、2026-04-17 実装）

- [x] 親 index.html: `applyLayout()` で `.grid` に `layout-4split` / `layout-1screen` / `layout-lshape` 切替
- [x] `configureVideoFrame()` で type='video' の frame を処理（setVideoConfig postMessage）
- [x] **スロット切替時の location.reload() 撤廃** → inline 切替で動画継続再生
- [x] `clearUnusedFrames()` で不要 iframe を about:blank クリア
- [x] L字 CSS: `grid-template-columns: 20% 1fr`、`.cell-2 { aspect-ratio: 16 / 9 }`
- [x] px 完全廃止（親・子とも vw/vh/rem/% のみ）、仕様書§4 準拠
- [x] 新テンプレート:
  - `side-entries.html` — 出走表（`font-size: min(3.448vw, 1.852vh)`、馬名 1fr 伸縮）
  - `wide-popular.html` — 4賭式×5件、馬番正方形、「-」基準寄せ（first:end / last:start / middle:center）
  - `video-frame.html` — hls.js 再生、quality_cap/muted/volume 反映、source 同一なら再ロードしない
- [x] schedule_0102 3スロット構成:
  - slot1 L字: side-entries + 大井ライブ動画 + wide-popular
  - slot2 1画面: 大井ライブ動画のみ
  - slot3 4分割右下動画: 単勝/馬連ワイド/人気順/動画
- [x] VENUE_CODE_MAP（NAR 15場）+ buildVideoUrl() で本番URL組立
- [x] `video_source_override` で開発時の疎通確認用差替可能
- [x] TECH-VERIFICATION-ONLY マーカー + `TECH_VERIFICATION_NOTES.md` で本番切替チェックリスト
- [x] ビューポート 1280 : FHD : 4K = 1 : 1.5 : 3 の比例拡縮を検証済み

---

## 4. 芥川様未確認事項（README.md 参照・I-3/I-5 が特に重要）

| # | 項目 | 優先 | 概要 |
|---|---|---|---|
| A | 天候ラベル2文字対応（小雨/小雪） | 中 | demo-helpers.css で min-width 対応 |
| B | 前日発売ラベル適用スコープ | 中 | `.popular` 以外で定義コピー |
| C | 騎手名5文字以上切り詰めルール | 低 | 先頭4文字で切り詰め実装 |
| D | 馬連ワイドページ分割 | **確定** | pairSum対称分割 |
| E | 枠番色クラスのテンプレート別差分 | 低 | 未確認 |
| F | 締切直前/発走済みのビジュアル | **高** | 現状 opacity 点滅暫定 |
| G | **カットイン CUT-001/002 正式HTML納品** | **高** | 暫定実装済、正式版受領で差替 |
| H | 暗黙の文字数前提（course/レース名） | 中 | 未確認 |
| **I-1** | `.race-time[data-mode]` 赤グラデ背景 | 中 | demo-helpers 暫定 |
| **I-2** | `.race-header` 既定背景（header-{color}必須化） | 中 | 既存4テンプレに暫定付与 |
| **I-3** | **`.umaren-wide .race-table__row/__name` の calc 固定高さ削除** | **高** | 単勝側行高さと不一致になる根本原因 |
| **I-4** | `.screen-umatan` の number-{color} 対応 | 中 | demo-helpers で暫定追加 |
| **I-5** | **単体HTML（馬連1/2・馬単1/2）の正式納品** | **高** | 暫定切り抜き済、header色も要確認 |
| **I-6** | `.race-time.start` クラス対応 | 確定 | header.html 受領で実装済 |
| **I-7** | 文言「発売終了」→「発売締切」 | 確定 | 変更完了 |

---

## 5. 環境・ツール情報

### 5.1 開発マシン

- Windows 11（日本語UI）
- Python 3.14.4（`python -X utf8` で UTF-8 モード必須）
- Node.js 未インストール
- GitHub リポジトリ: **`deruca-systems/odds-demo`**（public）
  - GitHub Pages 公開中: `https://deruca-systems.github.io/odds-demo/`
  - 4画面デモは `4screen-demo/` サブフォルダに配置
  - 前回 fetch ポーリングサンプルがルート直下に共存

### 5.2 プレビュー（ローカル確認）

- Claude Preview tool: `preview_start odds-demo` で `python -m http.server 8765`
- URL: `http://localhost:8765/?monitor=0101&fast=1&page_rotation=3`
- `preview_screenshot` はしばしばタイムアウト → stop/start で回復

### 5.3 データ再生成

```bash
cd "C:/Users/oikawa.masafumi/Documents/00.仕事/地方競馬オッズ表示システム(仮)/git/keiba-odds"
python -X utf8 src/odds-demo/_tools/gen_data.py
```

全 `odds_{ORG}_{PLACE}_{RACE}.json` と schedule JSON が NOW 基準で上書き。**デモ実演前に推奨**（情報バー時刻表示の見栄え向上）。

### 5.4 GitHub Pages 公開フロー

1. ローカルで `gen_data.py` 実行
2. https://github.com/deruca-systems/odds-demo を開く
3. `4screen-demo/` サブフォルダに「Upload files」で変更分をアップロード
4. 数分で自動再公開

詳細手順は [DEMO_GUIDE.md](DEMO_GUIDE.md) §9 参照。

---

## 6. 残課題・未着手タスク

### 6.1 優先度: 高

- [ ] 芥川様への確認事項（G / I-3 / I-5 特に優先）を MTG で合意
- [ ] I-3 合意後 → style.css 修正取込 → demo-helpers.css の flex column 暫定ルール削除
- [ ] I-5 正式HTML受領後 → 4テンプレ（新マトリクス）を丸ごと差替
- [ ] G 正式HTML受領後 → `templates/cutin.html` を差替、`demo-helpers.css` のカットイン暫定ブロック削除

### 6.2 優先度: 中（本番実装時）

- [ ] 本番 S3 パス設計の確定（堀井様との調整）
  - `schedules/{monitor_id}.json`
  - `odds/{YYYYMMDD}/{org}_{place}_{race}.json`
- [ ] CloudFront 304 Not Modified 対応（ポーリング負荷軽減）
- [ ] 端末×複数モニターでの多端末配信パターン
- [ ] サーバー側の障害検知・通知（heartbeat or S3 ログ活用）

### 6.3 優先度: 低（将来拡張）

- [ ] screen3.html / screen4.html の枠単（`frame-umatan`）取込
- [ ] 3連複/3連単の独立画面テンプレ
- [ ] カットイン CUT-003+（レース確定・中断等のトリガー）
- [ ] 管理画面 heartbeat 送信機能（`getAllPollerStatus()` を土台）
- [ ] 馬連ワイド手動ページ切替UI（自動ローテと共存）

### 6.4 既知の小問題

- `preview_screenshot` がタイムアウト → サーバ stop/start で回復
- 静的JSON のため `server_time` が gen_data.py 実行時刻で固定 → 親で offsetFixed 管理、子は baseOffset を親から受信
- race_rotation_seconds は 45秒固定（URLクエリなし）、早回ししたい場合は gen_data.py の `build_slot` で変更

---

## 7. 次セッションの始め方

### 7.1 新チャット開始時の指示テンプレ

```
地方競馬オッズ表示システム(仮) の odds-demo サンプル実装の続き。
まず前セッションの引継ぎ資料を読んで状況を把握してください:
@C:\Users\oikawa.masafumi\Documents\00.仕事\地方競馬オッズ表示システム(仮)\git\keiba-odds\src\odds-demo\HANDOFF.md

把握できたら、以下のタスクを進めて:
[具体的な作業を記載]
```

### 7.2 最初に確認すべきこと

1. **HANDOFF.md を読む**（本ファイル）
2. **README.md** で芥川様確認事項A〜I の最新ステータスを確認
3. **DEMO_GUIDE.md** で公開URL・タイムライン確認
4. `git status` で未コミット変更の有無を確認（デモ前後で data/* の更新あり得る）
5. 必要なら `python -X utf8 src/odds-demo/_tools/gen_data.py` でデータ再生成
6. `preview_start odds-demo` でローカル起動、`http://localhost:8765/?monitor=0101&fast=1&page_rotation=3` 確認

### 7.3 設定値の変更場所

| 何を変える | どこを触る |
|---|---|
| スケジュール構造（slot数、レース） | `_tools/gen_data.py` の `RACE_DEFINITIONS` / `build_slot` |
| 馬名/騎手名プール | `_tools/gen_data.py` の `*_NAMES` / `JOCKEYS_*` |
| 新テンプレ配置レース | `_tools/gen_data.py` の `MATRIX_VARIANT_FILES` |
| ポーリング秒数（C-01, 2026-04-17 本番30秒確定） | `index.html` の `SCHEDULE_POLL_SEC` / `ODDS_POLL_SEC`（本番デフォ30秒、`?fast=1` で10秒）、または `?schedule_poll=N` / `?odds_poll=N` |
| 次レース遷移秒数（H-04, 2026-04-17 本番60秒確定） | `index.html` の `NEXT_RACE_DELAY_SEC`（本番デフォ60秒、`?fast=1` で5秒）、または `?next_race_sec=N` |
| 枠連↔枠単 切替秒数（H-03, 2026-04-19） | `index.html` の `FRAME_UMATAN_PAGE_SEC`（デフォ15秒）。`single-screen.html` のみ対象 |
| display_pattern マッピング | `_tools/gen_data.py` の `DISPLAY_PATTERN_MAP` 辞書。詳細は `10_改修指示/display_pattern_mapping_v1.md` |
| schedule 構造・screens 構成 | `_tools/gen_data.py` の `build_slot` / `build_schedule_01XX` 各関数 |
| ページローテ秒数 | `templates/single-umaren-wide.html` の `UMAREN_PAGE_ROTATION_SEC` |
| カットイン表示秒数（C-02, 2026-04-17 10秒確定 ★要確認） | `common.js` の `CUTIN_DISPLAY_SEC`（10秒）、またはURLクエリ `?cutin_sec=N` |
| 安全マージン秒数 | `common.js` の `DEADLINE_SAFETY_MARGIN_SEC`、またはURLクエリ `?safety_margin_sec=N` |
| バックオフ倍率・間隔 | `common.js` の `startResilientPolling` / `multiplierFor` |
| ページ分割ロジック | `common.js` の `calcUmarenLayout` |
| オッズ色判定 | `common.js` の `computeWinClasses` / `computePlaceClasses` / `computeFramePopular` 等 |

### 7.4 指示書ベースの作業を行う場合

指示書ファイルがある場合（`docs/仕様書_specs/claude code実装指示/`）は、ファイル名を指定するだけで、Claude 側で読込 → 不明点確認 → 実装 → 検証 の流れで進められる。

既存指示書:
- `04_OrganizerType対応.txt` ✅実装済
- `05_カットイン CUT-001CUT-002 実装.txt` ✅実装済
- `07_CC指示_エラーハンドリング.md` ✅実装済

今後追加される可能性のある指示書（推測）:
- 06（欠番？ 要確認）
- 08以降（運用投入・本番接続・管理画面連携 etc.）

---

## 8. 重要な設計原則（遵守事項）

1. **芥川様CSSは改変しない** — `assets/css/style.css` は `screen2_files/style.css` のコピー。独自スタイル追加は `demo-helpers.css` のみ
2. **申し送り仕様書のルール遵守**
   - px禁止、rem基準
   - インラインstyleは CSS 変数注入（`--horse-count` / `--name-length` / `--row-count` / `grid-row`）に限定
   - 色指定はクラス付与のみ、hex/rgb 直接注入禁止
   - フォント: 日本語=Yu Gothic UI、英数=Segoe UI
3. **demo-helpers.css に追加したルールは「暫定」扱い** — 芥川様正式対応で削除／style.css 移植する前提
4. **スケジュールJSONは CRM側で生成される前提** — サンプルは gen_data.py で代替。本番実装時は JSON 構造（`slots[]` 形式、`data_source` 含む）を堀井様と合意
5. **エラーハンドリング（指示書07）**
   - 全 fetch は `startResilientPolling` で指数バックオフ管理
   - 失敗時は画面維持（既存 lastData）、render() を呼ばない
   - `AbortController` で 10秒タイムアウト
   - 通知バッジは不要（顧客向け非対象、運用スタッフは将来の管理画面経由）

---

## 9. 関連ドキュメント

- **申し送り仕様書**: `design/システム組み込み申し送り仕様書.md`
- **README.md**（本デモ内）: 全仕様・芥川様確認事項A〜I
- **DEMO_GUIDE.md**（本デモ内）: 実演ガイド・URL・タイムライン・GitHub Pages公開手順
- **実装指示書**: `docs/仕様書_specs/claude code実装指示/`
  - 03_3_CC指示_馬連ワイド分割表示_完全修正版.md
  - 04_OrganizerType対応.txt
  - 05_カットイン CUT-001CUT-002 実装.txt
  - 07_CC指示_エラーハンドリング.md
  - **08_CC指示_取消馬対応.md** ✅実装済（2026-04-16）
  - **09_CC指示_04_L字レイアウト動画組込.md** ✅実装済（2026-04-17）
- **リファレンス画像**: `docs/新しいフォルダー/screen3.png`・`screen4.png`
- **芥川様原デザイン**: `docs/画面サンプル(202604015_screen34サンプル)/`
  - screen2.html / screen2_files/（馬連/馬単マトリックス）
  - header.html / header_files/（ヘッダー色バリエーション）
- **プロジェクト要件定義**: `docs/仕様書_specs/要件定義書_v3.0.docx`
- **画面仕様書**: `docs/仕様書_specs/画面仕様書_競馬オッズ表示システム_v1.0.docx`

---

## 10. 公開URL・動作確認URL

### 本番デモ（GitHub Pages）

```
https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=0101&fast=1&page_rotation=3
https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=0102&fast=1        ← ★指示書09 L字+動画デモ
```

### ローカル動作確認

```
http://localhost:8765/?monitor=0101&fast=1&page_rotation=3       4分割3スロット + 取消馬
http://localhost:8765/?monitor=0102&fast=1                       ★L字 → 1画面 → 4分割右下動画（各1分）
```

URL クエリ一覧は DEMO_GUIDE.md §2 参照。

---

以上。本資料の更新は新しい作業区切り時点で行うこと。

---

## 追記 2026-07-14: video_config をネスト形式に整合（v0.6.5 §3.7）

- schedule JSON の video screen 設定を、旧フラット形式（screen 直下に `venue_code` 等）から **`screen.video_config` オブジェクト（JSON構造仕様書 v0.6.5 §3.7 準拠）** に変更。
  - `_tools/gen_data.py` build_slot(): `screen_entry["video_config"] = {...}` で出力
  - `index.html` buildScreenStates(): `screen.video_config || screen` の dual-read（旧フラット形式の既存 schedule への後方互換。生成側実値出力の定着後に削除可）
- 20260714 以降の schedules/・schedules/manual/ はネスト形式。20260713 以前の日付フォルダはフラットのまま（dual-read で動作、リント対象は 20260629 以降 0 NG 維持）
- 背景: 内山様バッチの video_config 実値出力開始依頼（`output/reports/内山様依頼_video_config実値化_venue_code出力_20260714.md`）に合わせ、プロト出力と正本仕様のズレを解消
- 備考: gen_data.py 2227-2358 の build_lshape_slot / build_1screen_slot / build_4split_with_video_slot は旧構造（frames）の未使用残骸（2110 行のコメントでは削除済みとされているが実体が残存）。呼び出し元なし・今回未修正

## 追記 2026-07-14 (2): 音声デフォルト出力方針 ＋ place_cd 正本体系の確定

- **音声方針**: audio_muted のデフォルト・生成値を **false（音声はデフォルトで出力、ミュートにしない）** に変更（及川決定）。
  - `_tools/gen_data.py` `_video_config()`: audio_muted=False
  - `templates/video-frame.html`: 未指定時デフォルト false ＋ `tryPlay()` 新設（音声ON play() がポリシーでブロックされたらミュートに切替えて再生継続）
  - `index.html`: audio_muted フォールバック 2 箇所 true→false
  - 表示端末は起動フラグ `--autoplay-policy=no-user-gesture-required` で音声ON自動再生を許可する運用
- **place_cd 正本**: DB設計書 v1.11 §12.places により place_cd は「NAR: マスコミ様コード表(105) / JRA: コード表2001」体系と確定。
  - ⚠️ 本プロトの NAR ダミー値（30=門別/45=船橋/49=名古屋/41=佐賀）は (105) と不一致（正: 36/19/24/32。(105)の30は福山）。JSON構造仕様書 v0.6.5 付録A.2 も同ダミー値を記載。**本番データ接続前に race_id・odds/results ファイル名・schedules を含む一括是正が必要**（是正時は payout_lint / display_pattern_lint / prevday_venue_lint で検証）

## 追記 2026-07-14 (3): NAR 場コード (105)体系への一括是正 完了

- gen_data.py の NAR 場コードを正本（コード表(105)）へ一括是正: **30門別→36 / 45船橋→19 / 49名古屋→24 / 41佐賀→32**（帯広03は元々一致）。race_id・odds/results/changes ファイル名・schedules を含む。
- 凍結スナップショット（118-124、schedules/20260421 由来）はコピー時に NAR_30/45/49/41 → NAR_36/19/24/32 へ書き換えるロジックを copy ループに追加（源泉は凍結のまま）。
- 検証: payout_lint PASS／display_pattern_lint・prevday_venue_lint 20260714+manual 0 NG／grep 残存 0／プレビューで monitor=101（NAR_19_01=船橋）・118 正常表示。
- 仕様書側は **JSON構造仕様書 v0.6.6**（2026-07-14、output/reports/ と docs/仕様書_specs/ に配置）で §3.5.1 video 判定・§3.7 video_config（dp80 実値／dp90-94 null／audio_muted=false）・付録A.2 (105)正本化・付録C #4 クローズを反映。
- 20260713 以前の日付フォルダは旧ダミーコードのまま（凍結スナップショット扱い、dual-read と同様に触らない）。

## 追記 2026-07-14 (4): 情報バーのデバッグ限定化・ジェスチャー音声復帰

- 画面上部の情報バーは **`?debug=1` 指定時のみ表示**（お披露目 7/24・実稼働対応）。非指定時は右上の復帰ハンドルも出さない。H キーのトグルは常時有効（キーボード接続時の保守用）。
- video-frame.html: ミュートフォールバック発動後、**動画フレーム内のクリック/キー入力で音声ON復帰**（`gestureUnmute`）。親ページのクリックでは user activation が iframe に伝播しないため、動画自体をクリックする必要がある。表示端末は起動フラグ運用のためこの経路は不要（一般ブラウザでの確認用）。

## 追記 2026-07-15: 池澤様 GCH 実装のマージ・馬体重特殊値表示・STG 同期

- **池澤様 STG 実装（7/15 11:30）を main へマージ**（本人承認 13:36）: 新規 4 ファイル（templates/gch-video-frame.html、assets/js/video-display.js・gch-video-frame.js、assets/css/gch-video-frame.css）＋ index.html の GCH 分岐（dp90-94→gch テンプレ、applyGreenChannelScreen、setGreenChannelConfig 契約）。
- **DosVideoDisplay.narConfig**: video_config.venue_code 未供給時に cell の place_cd（コード表(105)）から venue_code をフロント自己解決（内山バッチ対応前の暫定経路）。JSON に venue_code があればそちら優先。
- 音声デフォルトは 2026-07-14 方針（audio_muted=false）に統一（池澤版デフォルト muted から変更、明示指定は従来どおり優先）。
- **馬体重特殊値表示（馬体重特殊値仕様書 v1.0 §4.5）**: common.js に fmtWeight/fmtWeightDiff(diff, wt2, weight) を実装。null（計量前・地全協流儀）/0（取消）→ 空欄、9999→計不、wt2=0→(初)、wt2=9999→(前計不)。旧実装の null→'(0)'／'(計不)' 誤表示を修正（single-screen / entries-results-3r / 6r）。
- common.js キャッシュバスターは **v=20260716a**。仕様面の残: 馬体重特殊値仕様書 v1.1（null=計量前の追認）と JSON 構造仕様書への weight/wt2 nullable 追記は PL 判断待ち。
- 運用合意: **フロント改修のベースは GitHub main を正**とする（池澤様同意 7/15）。STG は 45 ファイル同期済み（invalidation I9FBE65CZ8ANCOHKN1LZ36UREU）。

## 追記 2026-07-15 (2): CRM 背景色を芥川ヘッダークラスで適用（back_color 10 色化と対）

- CRM 背景色が反映されない事象の原因は **Phase 5（4/22）の CSS 変数注入に対する受け側 CSS が一度も実装されていなかった**こと（git 全履歴で確認）。単色ベタ塗りではなく **back_color_code → style.css の .race-header.header-\*（芥川グラデーション）へのクラス付け替え**方式で実装し直した（index.html: BACK_COLOR_TO_HEADER_CLASS / applyHeaderColor）。
- マッピングは新パレット 10 値（芥川グラデ開始色）＋旧シード 8 実値（STG DB SELECT 確認、G ピンク→水色再定義）の両対応。マスタ更新（堀井様依頼_back_color芥川パレット10色化_20260715）の前後どちらでも動く。
- slot 切替で同一テンプレのまま色だけ変わる経路（data-source-only 更新）にも適用を追加。
- .race-header を持たないテンプレ（出走成績・side-entries・wide-popular・changes-info）は従来どおり対象外。対応する場合は芥川様デザイン相談。
- 検証: ローカルで新旧混在 4 色（blue/orange/green/light_blue）、STG 実データ（monitor 8: B青/D緑）で適用確認済み。CRM の色名は A〜J場の 10 スロット化を堀井様へ依頼中（正本対照表は依頼書参照）。

## 追記 2026-07-15 (3): STG 実データ検証で発覚した 2 件の修正（成績切替・枠連なし）

- **出走成績の成績モード切替不全**: entries-results-3r/6r は親から results/ パスが来る前提だったが、内山バッチの data_source は常に odds/（設計書 v1.5）→ results 試行が実際は odds を読み永遠に出走表モード。**どちらの形式でも results/odds 両 URL を導出**するよう修正（プロトの results/ 渡しとも両立）。STG 浦和1R・名古屋1R で成績モード表示を確認。
- **枠連発売なし時の枠番表示**: frame_odds 空（8頭未満）でも枠番 1〜8 のラベルだけ描画されていた → single-screen でブロックごと非表示に。枠連↔枠単ローテの 'uren' 復帰メッセージで空ブロックが再表示されないよう dataset.frameOddsAvailable でガード。
- 既知の表示課題（未対応・判断待ち）: ヘッダーの race_class「普通」表示。値は JSON 仕様 §4.4 どおり（cscnm.race_type_cd=競走種類）でバッチ正常。地全協 HP はクラス条件（例「Ｃ３六 七」）を表示しており、対応案は (a) フロントで「普通」のみ非表示 (b) クラス条件フィールドの JSON 追加（内山改修＋仕様改訂）。
- 子テンプレのキャッシュバスター v=20260716b。

## 追記 2026-07-15 (4): dp50 自動ページング実装・固定範囲フィルタ・「普通」非表示

- **dp50（出走成績 自動ページング）を実装**: 実バッチは races[] に当日同場の全レースを出力（設計書 v1.5 §6.5）するが、親は先頭 3 件を送るだけで常に 1〜3R 固定だった（STG monitor 8 で顕在化）。1-3R→4-6R→7-9R→10-12R を既定 15 秒（?page_rotation= で上書き）でループする親側ページングを追加（checkEntriesResultsPaging、1秒tick 内）。
- **dp51-54/61/62（固定範囲）に rr フィルタ**: races[].rr（無ければ race_id から復元）で範囲絞り込み。プロトの「schedule 側で絞って渡す」形式とも両立。
- **dp60 は意図的に無変更**（全件送信・6r テンプレが 6件×最大4ブロック配置＝monitor 128 の screen8 4分割互換）。整理一覧 §1 の「1-6R→7-12R ループ」定義との整合は芥川様/PL と要相談（現状 12 件なら 2 ブロック同時表示になる）。
- **race_class「普通」をヘッダー非表示に**（common.js renderRaceHeader）: 地全協 keiba.go.jp の当日メニューと同じく特別・準重賞・重賞のみ表示（及川決定 7/15）。クラス条件（「Ｃ３六 七」等）の表示は JSON にフィールドが無いため別途判断（内山改修＋仕様改訂が必要な場合）。
- common.js キャッシュバスター v=20260716c。STG 実データで ①成績モード切替 ②普通非表示 ④15秒ページングループを確認済み。back_color 10色化は堀井様が STG/PROD 適用済（7/15 15:54）。

## 追記 2026-07-15 (5): 確定前の空 results への防御

- 実バッチは**レース確定前から** results/{date}/{race}.json を entries=[]・odds_status=null の骨組みで生成する（STG 名古屋5R で確認）。旧判定（entries が配列なら成績モード）だと「競走成績」ヘッダーのみの空表示になるため、**entries.length > 0 を成績モード条件に追加**（3r/6r）。確定までは出走表（オッズ）を表示し続け、entries が入った次のポーリングで成績へ切替わる。
- 空生成がバッチの意図（骨組み先行 PUT）か否かは resultJSON 出力プログラム設計書 v1.0 の生成タイミング規定と突合のうえ、必要なら内山様へ確認（フロント防御済みのため実害はない）。
- 既知の設計判断待ち: **出走成績（3r/6r）のヘッダー（race-screen__header / six-race__header）は芥川テンプレの固定配色**で、CRM 背景色の適用対象外（適用対象は .race-header を持つ単勝系・人気順系・マトリクス系のみ）。成績画面にも CRM 色を適用するかは芥川様デザイン確認事項。
- 子テンプレキャッシュバスター v=20260716d。

## 追記 2026-07-15 (6): 出走成績ヘッダーにも CRM 背景色を適用（即適用・及川決定）

- 3r/6r の成績ヘッダー（race-screen__header / six-race__header）は描画ごとに再生成されるため、親 applyHeaderColor が iframe <html> に **has-custom-hdr ＋ CSS 変数 --custom-header-grad（芥川グラデ 2 値）** を注入し、dos-overrides.css の受けルールで適用する方式（.race-header 系のクラス付け替えと併存）。
- HEADER_GRADS（index.html）は style.css の header-* 定義の写し。**芥川様がパレットを更新したら追従が必要**。
- STG 実データで 4 面（単勝系×2・出走成績×2）とも CRM 設定色の芥川グラデ表示を確認。schedule JSON の back_color_code はプレビュー再生成までは旧 HEX のまま流れてくるが、旧 HEX 互換マッピングで同じ芥川色に解決される。
- dos-overrides.css v=20260716a／子テンプレ v=20260716e。

## 追記 2026-07-15 (7): 訂正 — 「確定前の空 results 生成」は過渡事象（追記 (5) の一般化を撤回）

- 追記 (5) の「実バッチはレース確定前から entries=[] の results を生成する」は**単一観測（7/15 名古屋5R、16時ごろ）からの過度な一般化で誤り**。STG 定常状態の走査（7/15 19:39、名古屋全12R）では未確定レース（odds_status=0）の results は**未生成（403）**であり、resultJSON 出力プログラム設計書 v1.0 §4/§5.1 の規定（odds_status=1 検知後に生成）どおり。反証の詳細は `output/reports/仕様書宿題4件_論点整理_20260715.md` §4。
- 7/15 の空 results は過渡事象。有力仮説＝「odds_status=1 セットと crs（着順）投入の時間差の隙間で生成ループが回った」。ただし観測ファイルは odds_status=null だったため仮説で未説明の細部が残る → 内山様照会は「生成タイミング規定の追加」ではなく **順序保証の確認**（＋空生成瞬間のファイル内 odds_status が null になり得るか）に差し替え。
- フロントの entries.length>0 ガード（追記 (5) の修正）は順序保証の有無に関わらず安全側のため**維持**。
