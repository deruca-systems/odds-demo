# CSS ガイド（DERUCA Odds System プロトタイプ）

| 項目 | 内容 |
|---|---|
| 対象 | `assets/css/style.css`（2659 行）/ `assets/css/dos-overrides.css`（375 行）|
| 作成日 | 2026-04-20（css-restructure-option-c 案C）|
| 読者 | フロントエンド新メンバー（2026-05-01 着任予定）|
| 目的 | CSS を変更する際の「どのファイル・どのセクションを触るか」を特定しやすくする |

---

## 0. このドキュメントの使い方

CSS を修正するとき、以下の順序で該当箇所を特定する:

1. 「どのテンプレートの表示を変えるか」を決める（例: 単勝複勝のオッズ値色）
2. 本書の **§5 テンプレート × CSS セクション対応表** を引く
3. 該当セクション（例: `SCREEN2 / 単勝複勝ブロック`）を `style.css` から検索
4. 必要に応じて `dos-overrides.css` の同等セクションも確認

---

## 1. CSS RESET（共通基盤）

| 項目 | 内容 |
|---|---|
| 行 | `style.css` L1-92 |
| 役割 | CSS リセット（全テンプレート必須）|
| 対応テンプレ | 全テンプレート |
| 主要セレクタ | `*`、`html`、`body`、`:where(...)` 系 |
| 根拠 | The new CSS reset v1.7.3 |

**変更時の注意**: 全テンプレートに波及するため、変更は極力避ける。新しいリセットルールが必要な場合も、該当セクション内でのみ修正。

---

## 2. SCREEN 系（単勝複勝・枠連・枠単）

`single-screen.html` の中で 3 つのブロックを使い分ける構造。親 index.html が `frameOddsPage` postMessage で 15 秒周期に `uren`（枠連）/ `utan`（枠単）を切替える。単勝複勝は常時表示。

### §2.1 SCREEN1 / 枠連オッズブロック

| 項目 | 内容 |
|---|---|
| 行 | `style.css` L92-907 付近（`/* SCREEN1 / 枠連オッズブロック */` ヘッダから `/* SCREEN2 */` 前まで）|
| 役割 | `single-screen.html` の `<div id="frame-uren">` 配下の枠連オッズを描画 |
| 対応テンプレ | `single-screen.html`（初期表示、15秒周期で SCREEN3 と切替）|
| 主要セレクタ | `.screen`、`.screen .frame-odds__*`、`html.single-screen`、`block-*` / `row-*` / `frame-*` |
| 画面パターン | display_pattern_id **1**（4分割標準）、**5**（4分割右下動画）|

### §2.2 SCREEN2 / 単勝複勝ブロック

| 項目 | 内容 |
|---|---|
| 行 | `style.css` L908-1099 付近 |
| 役割 | `single-screen.html` の `<div id="screen-main">` 配下の単勝複勝オッズを描画 |
| 対応テンプレ | `single-screen.html`（常時表示）|
| 主要セレクタ | `.screen .screen-main`、`.screen .screen-main .screen-table__*`、`body-*` |
| 画面パターン | display_pattern_id **1**、**5** |

### §2.3 SCREEN3 / 枠単オッズブロック

| 項目 | 内容 |
|---|---|
| 行 | `style.css` L1100-1937 付近 |
| 役割 | `single-screen.html` の `<div id="frame-utan">` 配下の枠単オッズを描画 |
| 対応テンプレ | `single-screen.html`（H-03 2026-04-19 追加、15秒周期で SCREEN1 と切替）|
| 主要セレクタ | `.screen`、`.screen .frame-utan__*`、`block-*` / `row-*` / `frame-*` |
| 画面パターン | display_pattern_id **1**、**5** |
| 特記 | 発売なしレースは親 index.html が `frameUtanAvailability` postMessage でページング停止。CSS 側は `display:none` が親 JS から制御されるため対応不要。|

**SCREEN1/2/3 共通セレクタ（144 個）**: `.screen` 基盤クラス（画面枠・ヘッダ基盤）、`.wrapper`。この共通部は 3 ブロックから参照されるため、変更時は SCREEN1/2/3 すべてへの影響を意識する。

---

## 3. HEADER（レースヘッダ共通）

| 項目 | 内容 |
|---|---|
| 行 | `style.css` L1938-2184 付近 |
| 役割 | 全テンプレ共通のレース情報ヘッダ（場名・R番・発走時刻・天候・馬場・距離）|
| 対応テンプレ | 全テンプレート（common.js `renderRaceHeader` から描画）|
| 主要セレクタ | `.race-container`、`#hdr-venue` / `#hdr-race` / `#hdr-raceName` / `#hdr-weatherIcon` / `#hdr-weatherLabel` / `#hdr-condition` / `#hdr-surface` / `#hdr-distance` / `#hdr-direction` / `.race-time` / `#hdr-postTime` / `#hdr-deadline`、`.race-info`、`.previous-day` |

**表示モード切替**: `.race-time[data-mode]` で 3 モード切替:
- `pre`: 「発走 HH:MM」（締切 10 分以上前）
- `countdown`: 「締切 N 分前」（締切 10 分以内）
- `closed`: 「発売締切」（締切到達後）

切替は common.js `renderRaceHeader` が `data-mode` を書き換えることで行う。CSS 側は `.race-time[data-mode="..."]` セレクタで装飾する。

**変更時の注意**: 全テンプレのヘッダに波及するため慎重に変更。テンプレ固有の微調整は各テンプレ側の `<style>` で override する運用。

---

## 4. RACE（出走表）

| 項目 | 内容 |
|---|---|
| 行 | `style.css` L2185-2659 |
| 役割 | 出走表テンプレ `side-entries.html` の馬情報表示 |
| 対応テンプレ | `side-entries.html`（L字レイアウトの左側で使用）|
| 主要セレクタ | `.race-container`、`html.single-screen`（縮尺調整）|
| 画面パターン | display_pattern_id **3**（L字+動画）|

**変更時の注意**: 出走表の表示に限定。他テンプレには影響しない。

---

## 5. テンプレート × CSS セクション対応表

| テンプレート | 使用 CSS セクション |
|---|---|
| `single-screen.html` | SCREEN1（枠連）+ SCREEN2（単勝複勝）+ SCREEN3（枠単）+ HEADER |
| `single-umaren-first.html` | SCREEN1/2/3 の `.screen` 共通部 + HEADER + `dos-overrides.css` |
| `single-umaren-second.html` | 同上 |
| `single-umaren-wide.html` | SCREEN1/2/3 の `.screen` 共通部 + HEADER + `dos-overrides.css`（L12以降）|
| `single-umatan-first.html` | 同上（馬単マトリクス） |
| `single-umatan-second.html` | 同上 |
| `single-popular.html` | SCREEN1/2/3 の `.popular` ルール + HEADER + `dos-overrides.css` |
| `single-popular-second.html` | 同上 |
| `wide-popular.html` | SCREEN1/2/3 の `.popular` + HEADER + `dos-overrides.css` |
| `side-entries.html` | RACE + HEADER |
| `video-frame.html` | `dos-overrides.css` のみ（video iframe 用）|
| `cutin.html` | `dos-overrides.css` のみ（カットイン overlay）|
| **`entries-results-3r.html`** | **RACE（`.race-container .race-screen .race-record/__payout/__table`）+ 新規 SCREEN3R セクション（style.css 末尾）**|

### §5.1 3R 出走成績テンプレの CSS 依存

`entries-results-3r.html`（display_pattern_id=10）は以下を使用:

1. **RACE セクション L2270-2723**（芥川様 style.css 由来の基本構造）
   - `.race-container .race-screen__col` / `.race-record` / `.race-payout` / `.race-table`
2. **新規 SCREEN3R セクション**（style.css 末尾、Phase 2 で追加）
   - `.race-record[data-pattern]` / `.race-payout[data-pattern]` / `.race-payout__refund` / `.race-payout--cancelled`
   - `.race-payout__row.is-special-pay` / `.race-record__time .time-int/.time-frac` / `.race-table__row.row-scratched`

### §5.2 `.race-info` 命名衝突の注意

**重要**: `.race-info` は文脈により 2 種類の意味を持つ:

1. **HEADER セクション内**（既存、L2105-2172）: `.screen .race-header .race-info` → レースヘッダの天気・距離・回り情報ブロック
2. **3R 表示内**（新規、L2703-2723）: `.race-container .race-info` → 右端の減量記号凡例

**親スコープが異なる**（`.screen .race-header` vs `.race-container`）ため CSS カスケード上は独立動作するが、同名クラスで意味が違う点に注意。新メンバーが `.race-info` を修正する際は**どちらのスコープかを確認**すること。

---

## 6. dos-overrides.css の役割

| 項目 | 内容 |
|---|---|
| 行 | `dos-overrides.css` 375 行 |
| 役割 | 本家 `style.css` に一切手を入れずに追加するヘルパ CSS |
| 主な内容 | `html.single-screen` font-size の vw/vh `min()` 対応（L12〜）、`.umaren-wide` の flex chain 改修、馬単テーブル用枠色、馬連ワイド組合せ表の軽微な調整 |

**設計原則**: `style.css` の構造を保ったまま、テンプレ固有の微調整はここに追加する。新メンバーが変更する際は `dos-overrides.css` を優先（リスク低）。

---

## 7. 枠番カラー命名規則（BEM modifier）

全 SCREEN 系で共通の 8 色クラス（枠番 1〜8 対応）:

| 枠番 | クラス名（接頭辞別）|
|---|---|
| 1 | `row-white` / `block-white` / `body-white` / `frame-white` / `number-white` |
| 2 | `row-black` / `block-black` / ... |
| 3 | `row-red` / `block-red` / ... |
| 4 | `row-blue` / ... |
| 5 | `row-yellow` / ... |
| 6 | `row-green` / ... |
| 7 | `row-orange` / ... |
| 8 | `row-pink` / ... |

common.js の `FRAME_ROW_CLASS` / `FRAME_BLOCK_CLASS` / `FRAME_BODY_CLASS` / `FRAME_NUMBER_CLASS` と連動。変更時は common.js 側のマッピングも同期更新。

---

## 8. 変更時のチェックリスト

修正対象テンプレを決めたら:

1. [ ] 本書 §5 でどのセクションを触るか特定
2. [ ] 該当セクションの「変更影響」注記を確認
3. [ ] SCREEN1/2/3 の共通部（`.screen` 基盤）に触る場合、3 ブロックすべてに影響することを認識
4. [ ] HEADER を触る場合、全テンプレに影響することを認識
5. [ ] 変更後、`?monitor=101` / `?monitor=102` / ... で non-regression 確認
6. [ ] 枠番カラーを触った場合、common.js の `FRAME_*_CLASS` も同期更新

---

## 9. 将来の本格分割（案B）への移行指針

本プロジェクトは暫定的に**案 C（ドキュメント強化）**でクリアしているが、以下が発生した場合は案 B（テンプレ別フル分割）への移行を検討:

- 新メンバーから「style.css が大きすぎて編集時どこを触るか迷う」の意見
- パターン追加時の CSS 衝突が 3 回以上発生
- HTTP 配信で CSS サイズがボトルネック化（現状 2659 行は問題なし）

移行時の推奨分割案:

```
assets/css/
├── base/
│   ├── reset.css              (現 L1-92)
│   └── variables.css          (色・サイズ変数抽出)
├── components/
│   ├── race-header.css        (現 HEADER セクション、~246 行)
│   └── cutin.css              (dos-overrides.css から分離)
└── patterns/
    ├── screen-main.css        (SCREEN2、~400 行)
    ├── screen-frame-odds.css  (SCREEN1、~400 行)
    ├── screen-frame-utan.css (SCREEN3、~400 行)
    ├── screen-matrix.css      (screen-umaren/umatan)
    ├── umaren-wide.css        (~119 行)
    ├── popular.css            (~300 行)
    ├── side-entries.css       (RACE セクション、~488 行)
    └── video-frame.css        (~50 行)
```

移行工数は 1〜1.5 日（CSS ルール追跡・重複除去・テスト）。

---

以上、DERUCA Odds System プロトタイプ CSS ガイド。
