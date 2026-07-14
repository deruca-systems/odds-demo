# 4画面JSONポーリングサンプル（odds-demo）

> **⚠ 2026-07-07 移設ノート**: 旧パス（00.仕事\…\git\keiba-odds\src\odds-demo）からの 2026-04-17 スナップショット移設。以降の変更は git log と CC完了報告を正とする。

4/14 MTGで決定したアーキテクチャに基づき作成した、4画面分割＋スケジュール制御＋端末時刻補正のサンプル実装。
GitHub Pagesでホスト可能な静的ファイル構成。

## ディレクトリ構成

```
odds-demo/
├── index.html                             親フレーム（4分割/1画面/L字 iframe管理＋スケジュールpoll＋時刻補正）
├── templates/
│   ├── single-screen.html                 単勝・複勝・枠連（芥川様 single-screen.html 準拠）
│   ├── single-umaren-wide.html            馬連・ワイド（ページ分割対応）
│   ├── single-popular.html                人気順1-15
│   ├── single-popular-second.html         人気順16-30
│   ├── single-umaren-first.html           馬連オッズ（馬番順）軸馬1-9
│   ├── single-umaren-second.html          馬連オッズ（馬番順）軸馬10-17
│   ├── single-umatan-first.html           馬単オッズ（馬番順）軸馬1-9
│   ├── single-umatan-second.html          馬単オッズ（馬番順）軸馬10-18
│   ├── cutin.html                         カットイン CUT-001/CUT-002（子iframe起動時に fetch → 挿入）
│   ├── side-entries.html                 ★L字左袖 出走表（指示書09）
│   ├── wide-popular.html                 ★L字右下 4賭式×5件 人気順（指示書09）
│   └── video-frame.html                  ★動画フレーム HLS再生（指示書09、TECH-VERIFICATION-ONLY）
├── assets/
│   ├── css/
│   │   ├── style.css                      芥川様 style.css をそのまま使用
│   │   └── demo-helpers.css               デモ専用の最小ヘルパー（.is-hidden、取消馬スタイル等）
│   ├── js/common.js                       子テンプレート共通ユーティリティ
│   └── images/weather/                    天候アイコン（芥川様アセット）
├── data/
│   ├── schedule_0101.json                 端末0101用スケジュール（3スロット・60分間隔版）
│   ├── schedule_0101_fast.json            同上の短縮版（5分/10分/15分間隔）— 動作確認用
│   ├── schedule_0102.json                ★端末0102用 L字+1画面+4分割動画デモ（60分×3）
│   ├── schedule_0102_fast.json           ★同上の短縮版（1分×3）
│   ├── odds_NAR_45_01.json                船橋1R   8頭 晴/ダ1200m（pageCount=1 / 4列×上下2段で全組合せ）
│   ├── odds_NAR_45_02.json                船橋2R  11頭 晴/ダ1400m（pageCount=2）
│   ├── odds_NAR_45_03.json                船橋3R  12頭 曇/ダ1600m（pageCount=2）
│   ├── odds_NAR_45_04.json               ★船橋4R   8頭 曇/ダ1200m 取消馬1頭（指示書08）
│   ├── odds_NAR_49_02.json                名古屋2R 13頭 曇/ダ1200m（pageCount=2）
│   ├── odds_NAR_49_07.json                名古屋7R 14頭 小雨/ダ1400m（pageCount=2）
│   ├── odds_NAR_49_08.json                名古屋8R 16頭  雨/ダ1800m（pageCount=2）
│   ├── odds_NAR_49_09.json                名古屋9R 10頭  雨/ダ1200m（pageCount=2）
│   ├── odds_NAR_30_07.json               ★門別7R  18頭 晴/ダ1200m（monitor=0102 デモ用）
│   ├── odds_JRA_05_11.json                東京11R  18頭 晴/芝2400m・前日発売（pageCount=3）
│   ├── odds_JRA_06_11.json                中山11R  16頭 晴/芝1600m（pageCount=2）
│   └── odds_JRA_09_11.json               ★阪神11R 18頭 曇/芝2000m 取消2・除外1（指示書08）
├── _tools/
│   └── gen_data.py                        JSONデータ再生成スクリプト（NOW基準post_time配置）
├── TECH_VERIFICATION_NOTES.md            ★TECH-VERIFICATION-ONLY マーカー管理（指示書09）
└── README.md
```

★ = 指示書08（取消馬対応）/ 指示書09（L字レイアウト+動画組込）で追加。

## 起動方法

### GitHub Pages
`src/odds-demo/` をドキュメントルートとして公開する。

### ローカル確認
```
cd src/odds-demo
python -m http.server 8765
```
ブラウザで次のURLを開く:
- `http://localhost:8765/?monitor=0101` — 4分割3スロット（船橋/名古屋/東京中山）+ 取消馬
- `http://localhost:8765/?monitor=0102&fast=1` — **L字 → 1画面 → 4分割右下動画 の3スロット**（指示書09）

### URLクエリ
親ページ `index.html` で指定可能:

| クエリ | デフォルト | 説明 |
|---|---|---|
| `monitor` | `0101` | 端末番号。`data/schedule_{monitor}.json` が読み込まれる。`0101`=4split基本 / `0102`=L字+動画 / `0103`=複数場混在 / `0104`=1レース固定 / `0105`=slot遷移 / `0106`=レース中止(H-01) / `0107`=開催中止(H-01) |
| `fast` | なし | `1` でデモ用モード: 短縮版スケジュール（`data/schedule_{monitor}_fast.json`）+ ポーリング10秒化 + **次レース遷移5秒化** |
| `schedule_poll` | `30`（`fast=1` 時 `10`）| スケジュールJSONポーリング秒数。**本番デフォルト30秒**（C-01, 2026-04-17）。個別指定は最優先 |
| `odds_poll` | `30`（`fast=1` 時 `10`）| オッズJSONポーリング秒数（子フレームへ伝搬）。**本番デフォルト30秒**（C-01, 2026-04-17）。個別指定は最優先 |
| `next_race_sec` | `60`（`fast=1` 時 `5`）| 発走時刻 + N秒で次レース自動遷移。**本番デフォルト60秒**（= 締切+180秒、J-WEB準拠、H-04 2026-04-17 確定）。個別指定は最優先 |
| `page_rotation` | `15` | 馬連ワイド画面のページ自動ローテーション秒数（子フレームへ伝搬） |
| `page` | なし | 馬連ワイド画面のページ固定（`1`/`2`/`3`）。指定時は自動ローテーション停止 |

例: 
- 通常: `?monitor=0101`
- 動作確認（短縮）: `?monitor=0101&fast=1`
- 高頻度poll: `?monitor=0101&schedule_poll=3&odds_poll=3`
- ページ切替を速く: `?monitor=0101&fast=1&page_rotation=5`
- 馬連ワイド Page 2 固定: `?monitor=0101&page=2`

子テンプレート `templates/*.html` 単体デバッグ時:

| クエリ | デフォルト | 説明 |
|---|---|---|
| `poll` | `30`（`fast=1` 時 `10`）| このテンプレ自身のオッズJSONポーリング秒数（C-01, 2026-04-17）|
| `page` | `1` | （`single-umaren-wide.html` のみ）表示ページ番号 |

## アーキテクチャ

### 親フレーム（`index.html`）
- URLクエリ `?monitor=XXXX` で端末番号を受け取り `data/schedule_XXXX.json` をポーリング（**本番デフォルト30秒**、`?fast=1` で10秒）
- スケジュール定義の `slot.screens[].races[]` から **画面別に独立したレース進行を管理**（H-04, 2026-04-17 で刷新）
  - 各画面は `post_time_iso + NEXT_RACE_DELAY_SEC`（既定60秒）の 1秒tick判定で次レースへ自動遷移
  - slot.race_rotation_seconds は廃止。遷移トリガーは発走時刻基準
  - display_pattern_id で screens[] の標準構成をパターン化（M-01、`display_pattern_mapping_v1.md` 参照）
- `slot.end_time` に**補正時刻**が到達したら screenStates を再構築（layout/template が変わる場合は iframe 再ロード、同じ場合は data_source のみ更新）
- スケジュール取得時に端末時刻との差分 `serverOffset` を算出し、**最初の1回だけ固定**
  - 本番では毎回更新（サーバが常時最新 `server_time` を返す前提）
  - デモでは静的JSONのため最初の1回で固定しないと「サーバ時刻」の表示が凍結してしまう
- 上部に情報バーを表示
  - キーボード `H` キーで表示/非表示トグル
  - 右上の `i` ハンドル（非表示時のみ表示）クリックでも復帰可能
  - `非表示` ボタンでも非表示化可能

### 子フレーム（`templates/*.html` × 4）
- 親から `postMessage({ type: 'setDataUrl', url, baseOffset })` を受信
- 受信した data_url を **本番デフォルト30秒**（`?fast=1` 時 10秒）間隔でポーリング
- fetchで取得したJSONデータで既存DOM要素を書き換え
- 申し送り仕様書のCSS変数・クラス体系のみを使用
- インラインstyleは **CSSカスタムプロパティ（`--horse-count` / `--name-length`）注入のみ**
- 色指定は全てクラス付与（hex/rgb直接注入なし）
- `race.is_previous_day === true` のとき race-info の代わりに 「前日発売」 ラベル表示

### 端末時刻補正（fetch往復の中間点で算出）
```javascript
var t0 = Date.now();
var res = await fetch(url + '?t=' + t0);
var data = await res.json();
var t1 = Date.now();
var clientTime = t0 + (t1 - t0) / 2;
var serverOffset = new Date(data.server_time).getTime() - clientTime;
// 以後: correctedNow = Date.now() + serverOffset
```
- 親: スケジュール取得時に **初回のみ** 算出（デモ用の凍結回避、本番では毎回更新可）
- 子: 各オッズJSON取得時に同様に算出し、親へ `childServerTime` で報告（診断用途）
- カットイン表示・レース切替・時間帯切替の判定すべてにこの補正時刻を使用

## スケジュールJSON仕様

### 構造（`slots[]` 配列方式）

```json
{
  "server_time": "2026-04-14T11:00:00+09:00",
  "monitor_id": "0101",
  "slots": [
    {
      "slot_id": 1,
      "start_time": "2026-04-14T11:00:00+09:00",
      "end_time":   "2026-04-14T12:00:00+09:00",
      "layout": "4split",
      "race_rotation_seconds": 45,
      "races": [
        {
          "race_key": "船橋1R",
          "frames": [
            { "position": 1, "template": "templates/single-screen.html",          "data_source": "data/odds_NAR_45_01.json" },
            { "position": 2, "template": "templates/single-umaren-wide.html",     "data_source": "data/odds_NAR_45_01.json" },
            { "position": 3, "template": "templates/single-popular.html",         "data_source": "data/odds_NAR_45_01.json" },
            { "position": 4, "template": "templates/single-popular-second.html",  "data_source": "data/odds_NAR_45_01.json" }
          ]
        },
        { "race_key": "船橋2R", "frames": [ ... ] },
        { "race_key": "船橋3R", "frames": [ ... ] }
      ]
    },
    { "slot_id": 2, "start_time": "...12:00:00...", "end_time": "...13:00:00...", "races": [ ... ] },
    { "slot_id": 3, "start_time": "...13:00:00...", "end_time": "...14:00:00...", "races": [ ... ] }
  ]
}
```

- 親ページは `slots[]` から **補正時刻(`correctedNow`) が `start_time` ≤ now < `end_time` のスロット**を現在スロットとして選ぶ
- `start_time` は ISO 8601（`2026-04-14T11:00:00+09:00`）推奨。`HH:MM:SS` 形式も受け付ける（当日扱い）
- スロット境界を跨ぐと親ページが `location.reload()` して新スロットの構成に差し替える（メモリ解放）
- `races[]` は `race_rotation_seconds` 秒ごとに自動ローテーション
- 旧形式（`current_slot` / `next_slot`）も互換実装あり

### 本サンプルの構成

**通常版 `schedule_0101.json`** — 60分ごとにスロット切替

| slot | 時間帯 | レース | ローテ間隔 |
|---|---|---|---|
| 1 | 起動〜+60分 | 船橋1R（8頭）→2R（10頭）→3R（12頭） | 45秒 |
| 2 | +60〜+120分 | 名古屋7R（14頭）→8R（16頭）→9R（10頭） | 45秒 |
| 3 | +120〜+180分 | 東京11R（18頭・前日発売）→中山11R（16頭） | 45秒 |

**短縮版 `schedule_0101_fast.json`**（`?fast=1` で選択） — 動作確認用

| slot | 時間帯 | 同上のレース | ローテ間隔 |
|---|---|---|---|
| 1 | 起動〜+5分 | 船橋3レース | 45秒 |
| 2 | +5〜+15分 | 名古屋3レース | 45秒 |
| 3 | +15〜+30分 | 東京11R/中山11R | 45秒 |

### `post_time` 基準のdeadline動的算出

`gen_data.py` 実行時に、各レースの `race.post_time` は「実行時刻 + N分」の **実時刻** (`HH:MM` 文字列) + `race.post_time_iso`（ISO 8601）として埋まる。子フレームJSは:

```js
computeDeadline(race.post_time_iso || race.post_time, correctedNow());
// → { deadline_min, remaining_sec, is_approaching, is_closing, is_closed }
```

- 発走まで > 7分: 通常表示
- 発走2〜7分前: `is_approaching` true
- 発走2分前以内: `is_closing` true、`.race-time.is-closing` クラス付与で点滅
- 発走済み: `is_closed` true、`.race-time.is-closed` クラス付与でグレーアウト

子フレームは 1秒 tick (`startHeaderTicker`) でヘッダーの `deadline` 表示を毎秒再計算し、**ブラウザを開きっぱなしにしておくと締切までのカウントダウンが自然に進む**。

## オッズJSON仕様

申し送り仕様書セクション10の受け渡しインターフェースに準拠。

### オッズJSONファイル命名規則

ファイル名: `odds_{org}_{placeCode}_{raceNo}.json`

| 要素 | 値 | 説明 |
|------|---|------|
| `{org}` | `JRA` or `NAR` | OrganizerType。DB上は数値(1=JRA, 2=NAR)だがファイル名は可読性優先で文字列 |
| `{placeCode}` | `01`〜`55` | 場コード。JRA: 01〜10、NAR: 01〜55。JRA/NARで01〜10が重複するため `{org}` が必須 |
| `{raceNo}` | `01`〜`12` | レース番号 |

例: `odds_NAR_45_01.json`（船橋1R）、`odds_JRA_05_11.json`（東京11R）

本番S3パス: `odds/{YYYYMMDD}/{org}_{placeCode}_{raceNo}.json`
- 日付フォルダで日別管理。S3ライフサイクルルールで古い日付フォルダを自動削除
- orgは文字列「JRA」「NAR」を使用（DB数値ではない）

オッズJSONの `race` オブジェクト内にも `org` フィールドを持つ（フロントエンドでJRA/NAR識別が必要なケースに備える）。

### JSON構造

```json
{
  "server_time": "2026-04-14T11:00:30+09:00",
  "race": {
    "org": "JRA",
    "venue": "東京", "race_no": 11, "race_name": "フェブラリーステークス",
    "deadline_min": 0, "post_time": "15:45",
    "weather": "sunny", "weather_label": "晴",
    "surface": "ダ", "condition": "良", "distance": 1600, "direction": "左",
    "is_previous_day": true
  },
  "horses":            [ { "frame_no":1, "horse_no":1, "horse_name":"...", ... } ],
  "frame_odds":        [ { "frame_a":1, "frame_b":2, "odds":12.1 } ],
  "umaren_matrix":     [ { "a":1, "b":2, "odds":22.4 } ],
  "wide_matrix":       [ { "a":1, "b":2, "min":5.2, "max":8.1 } ],
  "umaren_popular":    [ { "rank":1, "a":1, "b":8, "odds":7.1 } ],
  "umatan_popular":    [ { "rank":1, "a":1, "b":8, "odds":12.4 } ],
  "trio_popular":      [ { "rank":1, "a":1, "b":4, "c":8, "odds":28.6 } ],
  "trifecta_popular":  [ { "rank":1, "a":1, "b":8, "c":4, "odds":124.6 } ]
}
```

- `is_popular` / `is_secondary` フラグは不要。**オッズ値から自動判定**する。
- `umaren_popular` 等の上位リストは最大30件を推奨（P4の「16-30」枠が全て埋まるため）。

### 枠割ルール（標準）
`_tools/gen_data.py` で採用している日本競馬標準:

| N頭 | 枠割 |
|---|---|
| 1〜8 | 1頭/枠（馬番=枠番） |
| 9〜16 | 高い枠から順に 2頭/枠 化 |
| 17〜18 | 最高枠から順に 3頭/枠 化（N=18 は 7枠と8枠が3頭） |

例:
- 12頭 → 枠1(1), 枠2(2), 枠3(3), 枠4(4), 枠5(5,6), 枠6(7,8), 枠7(9,10), 枠8(11,12)
- 16頭 → 全枠 2頭/枠
- 18頭 → 枠1〜6(2頭), 枠7(13,14,15), 枠8(16,17,18)

### 馬連/ワイド画面のページ分割（4列×上下2段レイアウト）

【画面仕様】馬連・ワイド画面の分割基準.xlsx 準拠・確定仕様。

**ページ数:**
| 頭数 | ページ数 |
|------|---------|
| 5〜8頭 | 1ページ |
| 9〜14頭 | 2ページ |
| 15〜18頭 | 3ページ |

**軸の配置ルール（4列 × 上下2段）:**

```
nAxes   = N - 1                 （軸の総数。馬番Nは相手不在のため軸にならない）
nPages  = ページ数
nTop    = nPages * 4            （上段軸の総数）
pairSum = nTop * 2 + 1          （上段軸+下段軸の合計値 = 対称ペアリング定数）

1ページ = 4列。ページp（0..nPages-1）の列c（0..3）:
  topAxis      = p * 4 + c + 1                     （上段は若番から順）
  botCandidate = pairSum - topAxis                 （下段は pairSum 対称）
  botAxis      = botCandidate   ただし以下両条件を満たす場合のみ配置
                 (botCandidate <= nAxes) AND (botCandidate > nTop)
                 → 満たさなければ下段なし（上段のみの列）
```

**ペアリング合計値 pairSum:**
- 1ページ構成: 9  （上段1-4 と 下段5-8 が対称ペア）
- 2ページ構成: 17 （上段1-8 と 下段9-16 が対称ペア）
- 3ページ構成: 25 （上段1-12 と 下段13-24 が対称ペア）

**全頭数の配置一覧**（列は「上/下」記法、`-` は下段なし＝上段のみの列）:

| 頭数 | P | 列1 | 列2 | 列3 | 列4 |
|------|---|-----|-----|-----|-----|
| 5 | 1 | 1/- | 2/- | 3/- | 4/- |
| 6 | 1 | 1/- | 2/- | 3/- | 4/5 |
| 7 | 1 | 1/- | 2/- | 3/6 | 4/5 |
| 8 | 1 | 1/- | 2/7 | 3/6 | 4/5 |
| 9 | 1 | 1/- | 2/- | 3/- | 4/- |
| 9 | 2 | 5/- | 6/- | 7/- | 8/- |
| 10 | 1 | 1/- | 2/- | 3/- | 4/- |
| 10 | 2 | 5/- | 6/- | 7/- | 8/9 |
| 11 | 2 | 5/- | 6/- | 7/10 | 8/9 |
| 12 | 2 | 5/- | 6/11 | 7/10 | 8/9 |
| 13 | 2 | 5/12 | 6/11 | 7/10 | 8/9 |
| 14 | 1 | 1/- | 2/- | 3/- | 4/13 |
| 14 | 2 | 5/12 | 6/11 | 7/10 | 8/9 |
| 15 | 3 | 9/- | 10/- | 11/14 | 12/13 |
| 16 | 3 | 9/- | 10/15 | 11/14 | 12/13 |
| 17 | 3 | 9/16 | 10/15 | 11/14 | 12/13 |
| 18 | 2 | 5/- | 6/- | 7/- | 8/17 |
| 18 | 3 | 9/16 | 10/15 | 11/14 | 12/13 |

（表中のP=ページ。P1,P2,P3全ての組合せが正しく網羅される。）

- 各軸の相手馬は「軸+1 〜 N」（上三角行列）
  - 18頭 P1 列1: 上段=軸1（相手2-18, 17行）
  - 18頭 P2 列4: 上段=軸8（相手9-18, 10行）/ 下段=軸17（相手18, 1行）
  - 18頭 P3 列1: 上段=軸9（相手10-18, 9行）/ 下段=軸16（相手17-18, 2行）

**DOM構造（1ページ分）:**
```
div.race-table  (grid-template-columns: repeat(4, 1fr))
  div.race-table__col × 4
    div.race-table__body.body-{色}  上段ブロック（name → rows）
    div.race-table__body.body-{色}  下段ブロック（rows → name）※ botAxis=null の列では生成しない
```

**列ラッパー `.race-table__col` のレイアウト（芥川様 screen3.html 準拠）:**
```css
.umaren-wide .race-main .race-table__col {
  display: grid;
  grid-template-rows: repeat(var(--row-count), 1fr);  /* 親 .umaren-wide の --row-count = max(10, --horse-count) */
  height: 100%;
}
```
- **列 grid の 1行高さ = 単勝側（`.screen .race-table__body`）の 1行高さと一致**（どちらも同じ `--row-count` 基準の `1fr`）
- 上段 body: `style="--row-count: {itemCount}; grid-row: 1 / span {itemCount};"`
- 下段 body: `style="--row-count: {itemCount}; grid-row: span {itemCount} / -1;"`（末端揃え）
- body 内部も `--row-count=itemCount` により 行数ぴったりの grid → **body 内 1行高さ も 列 grid の 1行高さと一致**
- 上下段の間の余白（空行）は列 grid 内で自動的に中央に配置され、視覚的な分離になる
- 下段なしの列は上段のみで、下段領域は空行のまま

**ページローテーション:**
- ページ数 ≥ 2 の場合、子フレーム自身が `UMAREN_PAGE_ROTATION_SEC` 秒（デフォルト15秒）ごとに自動でページを切替
- ポーリング（10秒間隔）ではタイマーに一切触らない（`currentPageCount` 比較で判定）
- URLクエリ `?page_rotation=N` でローテーション秒数を上書き
- URLクエリ `?page=N` を指定した場合は固定表示（ローテーション停止、デバッグ用）
- ページ分割ロジックは `assets/js/common.js` の `calcUmarenLayout(N)` に集約
  - 返り値: `Array<Array<{topAxis, topPartners, botAxis, botPartners}>>` = pages → cols

### オッズ文字色の自動判定ルール
JSON側にフラグを持たず、取得した値から算出:

| クラス | 適用条件 |
|---|---|
| `win-popular` | 単勝オッズ 昇順 上位3頭 |
| `win-secondary` | 単勝オッズ 昇順 4〜5位 |
| `place-popular` | 複勝オッズ min/max の各下位50% |
| `value-popular` | 枠連オッズ 昇順 上位5組 |
| `odds-popular` | 馬連/馬単/3連複/3連単 人気リストのランク1〜3 |
| `unpopular` | 馬連マトリクス オッズ 1000倍以上 |

実装は `assets/js/common.js` の `computeWinClasses` / `computePlaceClasses` / `computeFramePopular` / `isTopPopular` / `isUmarenUnpopular`。

## サンプルデータ（今回の構成）

### 4分割レイアウト

| 位置 | テンプレート | 内容 |
|---|---|---|
| P1 | single-screen | 単勝/複勝/枠連 |
| P2 | single-umaren-wide | 馬連/ワイド（ページ分割対応） |
| P3 | single-popular | 人気順 1-15 |
| P4 | single-popular-second | 人気順 16-30 |

4画面は同じレースを表示し、45秒ごとに同一スロット内の次レースへローテーション。スロットが切り替わると画面全体がリロードされ、新スロットの構成が読み込まれる。

### 1日開催シミュレーション

8レース（標準枠割り適用）:

| Org | 場コード | レース | 頭数 | 天候 | コース | 前日発売 | ファイル |
|---|---|---|---|---|---|---|---|
| NAR | 45 (船橋) | 1R | 8  | 晴 | ダ1200m 左 | | `odds_NAR_45_01.json` |
| NAR | 45 (船橋) | 2R | **11** | 晴 | ダ1400m 左 | | `odds_NAR_45_02.json` |
| NAR | 45 (船橋) | 3R | 12 | 曇 | ダ1600m 左 | | `odds_NAR_45_03.json` |
| NAR | 49 (名古屋) | 2R | **13** | 曇 | ダ1200m 右 | | `odds_NAR_49_02.json` |
| NAR | 49 (名古屋) | 7R | 14 | **小雨** | ダ1400m 右 | | `odds_NAR_49_07.json` |
| NAR | 49 (名古屋) | 8R | 16 | 雨 | ダ1800m 右 | | `odds_NAR_49_08.json` |
| NAR | 49 (名古屋) | 9R | 10 | 雨 | ダ1200m 右 | | `odds_NAR_49_09.json` |
| JRA | 05 (東京) | 11R | 18 | 晴 | 芝2400m 左 | ✓ | `odds_JRA_05_11.json` |
| JRA | 06 (中山) | 11R | 16 | 晴 | 芝1600m 右 | | `odds_JRA_06_11.json` |

### 再生成

```
python src/odds-demo/_tools/gen_data.py
```

実行時に以下を自動更新:
- 各レースの `server_time` が **現在JST時刻**
- 各レースの `post_time` が **現在時刻 + N分**（N はレース毎に +3, +6, +9, +63, +66, +69, +123, +126）
- スケジュール `slots[].start_time` / `end_time` が **NOW基準の絶対時刻**

**→ 再生成直後にブラウザを開けば、slot 1（午前）の船橋1Rから開始し、リアルタイムにカウントダウン・自動切替が進行する**。

## 設定値の場所

### ポーリング秒数の変更（C-01, 2026-04-17: 本番デフォルト30秒確定）
- **即時変更**: URLクエリ `?schedule_poll=5&odds_poll=5`（個別指定は最優先）
- **恒久変更**: `index.html` 冒頭の `SCHEDULE_POLL_SEC` / `ODDS_POLL_SEC` 定数（**本番デフォルト=30秒**）
- **子単体**: `assets/js/common.js` 冒頭の `POLL_INTERVAL_MS`（**本番デフォルト=30000ms**）
- **デモ用モード**: `?fast=1` 指定時は自動で10秒に短縮（スロット短縮版と連動）

### レースローテーション秒数
`data/schedule_0101.json` の `slots[].race_rotation_seconds`（初期値=45）

### スロット切替時刻
`data/schedule_0101.json` の `slots[].start_time` / `end_time`。`gen_data.py` 実行時に自動で現在時刻+N分の絶対時刻が埋まるため、手動編集は原則不要。

### 時間帯切替検査間隔
`index.html` の `SLOT_TICK_SEC`（初期値=5秒）。**純クライアントtickなのでサーバ負荷に関与しない。**

### 情報バー表示更新
`index.html` の `DISPLAY_TICK_SEC`（初期値=1秒）。**同じく純クライアントtick。**

## よくある質問

### Q. サーバ時刻が大きくずれるのを直せる？
A. 本番では直る。デモ環境では静的JSONの `server_time` が更新されないため以下の方針:

1. **デモ側**: 親で `offsetFixed` フラグを立て、最初に取得した `server_time` に対して offset を1回だけ計算・固定。以降 `correctedNow() = Date.now() + serverOffset` は実時間と同じペースで進行する。JSONを繰り返し読んでも offset は再計算されない。
2. **本番**: サーバが常に最新の `server_time` を返すため、毎回 offset を再計算しても値はほぼ一定（ネットワーク遅延差分のみ）。`offsetFixed` を外す or 一定間隔で再計算でもOK。

### Q. 時間帯切替判定の1秒tickはサーバ負荷にならない？
A. ならない。1秒tickは `setInterval` で動く**純クライアント側の時刻比較のみ**。HTTP通信は発生しない。
- サーバへの通信は `pollSchedule`（**本番デフォルト30秒**）と、子フレームの `poll`（**本番デフォルト30秒**×4iframe）だけ（C-01, 2026-04-17）。
- 端末1台あたり30秒間隔×5通信 = 1分間10リクエスト。100端末で約17 rps。S3+CloudFront前提で十分余裕。
- `?fast=1` 指定時のみデモ実演向けに10秒へ短縮（GitHub Pages のデモURL参照）。本番運用時は `fast` を付けない。
- 本番でさらに軽くする場合、`SLOT_TICK_SEC` を増やす（初期値=5秒）・`DISPLAY_TICK_SEC` を増やす（初期値=1秒、UX優先）等で調整可能。

### Q. 情報バーを非表示にした後、再表示する方法は？
A. いずれでも可:
- キーボード `H` キー（ホームロウですぐ押せる）
- 画面右上に現れる小さな `i` ハンドル（19×19 rem 相当）クリック
- `document.body.classList.remove('hide-bar')` を DevTools で実行

## 制約事項（実装準拠）
- GitHub Pagesでホスト可能な静的ファイル構成（サーバーサイド処理なし）
- FHD（1920x1080）前提
- `px` 使用禁止（`rem` 基準）
- フォント: 日本語=`Yu Gothic UI`、英数=`Segoe UI`
- 芥川様HTMLテンプレートのCSS/クラス体系を尊重し、独自スタイル追加は `demo-helpers.css` にまとめた以下のみ:
  - `.is-hidden { display:none !important; }` — 表示切替用
  - `html.single-screen { font-size: min(1.0416666667vw, 1.8518518518vh); }` — FHDで縦に見切れないよう高さ基準も併用
  - `.weather { min-width: 8.6rem; }` / `.weather span { white-space: nowrap; }` — 2文字天候ラベル（小雨/小雪）の折り返し抑止（**要・芥川様確認**、後述）
  - `.screen/.umaren-wide` 配下の `.previous-day` スタイル — 芥川様CSSは `.popular` スコープのみ定義のため、単勝複勝・馬連ワイド画面で前日発売表示が崩れる回避（**要・芥川様確認**、後述）
  - `.race-time.is-closing` / `.race-time.is-closed` — 発走直前/発走済みの視覚フィードバック（デモ表現、本番デザイン未確定）
- インラインstyleは **CSS変数（`--horse-count` / `--name-length`）注入に限定**
- 色指定は必ずクラス付与で行う（hex/rgb直接注入は禁止）

## 本番実装との対応

| サンプル | 本番 |
|---|---|
| `data/schedule_0101.json` | CRMが生成してS3に配置（端末ごと、`schedules/{monitor_id}.json`） |
| `data/odds_NAR_45_01.json` | `odds/{YYYYMMDD}/NAR_{placeCode}_{raceNo}.json`（EC2がDB→JSON変換して配置） |
| `data/odds_JRA_05_11.json` | `odds/{YYYYMMDD}/JRA_{placeCode}_{raceNo}.json`（同上） |
| `templates/single-*.html` | 芥川様テンプレートをそのまま使用 |
| `assets/css/style.css` | 芥川様 `style.css` |
| `?monitor=XXXX` 経由のスケジュールJSON選択 | 端末配信URL構成と同等 |
| `offsetFixed` による offset 1回固定 | サーバが常に最新 `server_time` を返すため毎回再計算でOK |
| `race_rotation_seconds` 45秒 | 実際の発走スケジュールに合わせて可変（場・レース毎に異なる） |
| `slots[].start_time` が NOW+N分 の絶対時刻 | CRMが管理画面UIで設定した時間帯を絶対時刻で出力 |
| `race.post_time` / `post_time_iso` が実時刻 | DB側の実際の発走時刻を書き出し |
| deadline_min をクライアント側で `post_time` から算出 | 同じ。サーバ側は `post_time` のみ返せばよく、`deadline_min` は参考値 |
| `schedule_0101_fast.json` （短縮版） | 存在しない（本番は実スケジュール通り） |

## 芥川様への確認事項

本サンプル作成中に検出した、デザインCSS（`design/htdocs/assets/css/style.css`）側の設計見直しが必要と思われる項目。現在は `assets/css/demo-helpers.css` で暫定回避しているが、**組み込み本実装の開始前に芥川様と以下を合意**する必要がある。

### A. 天候ラベル 2文字表記（小雨・小雪）の折り返し

**現象**
- `assets/images/weather/` には `light-rain.svg`（小雨）・`light-snow.svg`（小雪）が含まれており、2文字ラベルは仕様上のケース
- 一方 `style.css` の `.weather` は `width: 6.4rem` 固定で 1文字ラベル前提の寸法
- 2文字ラベルを流し込むと span が 2行に折り返す（`width=34px, height=52px`）

**必要な計算幅**
- 1文字ラベル（晴/曇/雨/雪）: icon 26 + gap 4 + text 26 = **56px** ≤ 64px ✓
- 2文字ラベル（小雨/小雪）: icon 26 + gap 4 + text **52** = **82px** > 64px ✗

**確認事項**
- `.weather` の幅を `min-width` 指定に変更し 2文字を収容する（推奨: `min-width: 8.6rem` 程度）
- または `.weather.weather-long` のような修飾子クラスを用意しシステム側で付け替える
- どちらの方針をとるか？

**現在のデモ側暫定対応**
```css
.screen .race-header .race-info .weather,
.umaren-wide .race-header .race-info .weather,
.popular .race-header .race-info .weather {
  width: auto;
  min-width: 8.6rem;
}
.weather span { white-space: nowrap; }
```

### B. 前日発売ラベルの適用スコープ

**現象**
- `style.css` の `.previous-day` スタイルは **`.popular` スコープ専用**（line 850 付近）で定義されている
- しかし実運用では**レース単位の属性**（例: 東京11R を前日発売として表示）で、全テンプレートに跨って「前日発売」表示を出すケースがある
- `.screen` / `.umaren-wide` 内で `.previous-day` を置いても未スタイルのため表示が崩れる（寸法・色・背景が効かない）

**確認事項**
- 単勝複勝画面（`screen1.html`, `single-screen.html` 等）および馬連ワイド画面（`single-umaren-wide.html`）でも「前日発売」ラベル表示が必要か？
- 必要なら `.previous-day` を `.race-header` 配下で共通化（スコープ緩和）していただけるか？
- それとも**前日発売専用テンプレート**（例: `single-screen-previous-day.html`）をテンプレート単位で用意する運用か？

**現在のデモ側暫定対応**: `.popular` 内の `.previous-day` スタイルを `.screen` / `.umaren-wide` にもコピー展開（同一値）

### C. 騎手名 5文字以上の切り詰めルール

**現象**
- 現行サンプルHTML（`design/htdocs/screen1.html` 等）では騎手名が `L．ヒュ` / `M．デム` / `C．ルメ` のように **4文字で切られた状態**でハードコードされている
- 実運用ではDB上のフル氏名（例: `C.ルメール`, `M.デムーロ`, `D.レーン`）から**何らかのルールで4文字に切り詰めて**表示する必要がある

**確認事項**
- 切り詰めルールは「単純に先頭4文字」でよいか？
- 表示文字幅（CJK + 半角混在）を考慮した幅ベース切り詰めが必要か？
- 切り詰め後に末尾 `…` や省略記号を付けるか？（現行サンプルは付いていない）
- そもそも `.race-table__jockey` のセル幅（`9.5rem`）を広げて切り詰め自体を不要にする選択肢はあるか？

**現在のデモ側暫定対応**: `common.js` の `truncateJockey(name)` で `length >= 5` なら先頭4文字に切る

### D. 馬連ワイド画面のページ分割ロジック

**対応状況**: **正式仕様確定・実装済み**（Excel「馬連・ワイド画面の分割基準.xlsx」準拠の pairSum 対称分割アルゴリズム）。

- ページ数: 5-8頭=1P / 9-14頭=2P / 15-18頭=3P
- `pairSum = nTop * 2 + 1` による上段/下段対称ペアリング
- 全頭数5〜18の配置は上記「馬連/ワイド画面のページ分割」セクションの表参照
- 検証: 全14パターン（5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18頭）で `calcUmarenLayout` の出力が Excel仕様と完全一致確認済み

**残課題**（運用決定が必要）
- ページローテーション秒数の推奨値（現在15秒デフォルト）
- 自動ローテーションと手動切替UI（将来）との共存方針
- 下段ブロック（name 末尾）のアライメント
  - 下段 body は内部 `grid-template-rows: repeat(--row-count, 1fr)` で行が均等分配されるため、name は自然に末尾行に配置される
  - 芥川様 screen3/screen4 の `.race-table__col { justify-content: space-between }` スタイルに準拠

### E. 枠番色クラス適用のテンプレート別差分

**現象**
- `.popular` テンプレートの人気順テーブルには `.popular-table__combination` 内で `.number-white` 〜 `.number-pink` の色クラスを馬番スパンに付けるが、**3連複/3連単の ハイフン区切り 3要素** 構成（`<span>-</span><span>-</span>`）で空エントリ時に中央ハイフンが消えるケースがある
- 現行サンプルHTML L.498-520 あたりでも同様のパターン（空の数字spanのみ）

**確認事項**
- 空エントリ時の表示（ランク16-30で該当がないとき）は `-` ダッシュ繋ぎでよいか？空白でよいか？
- 横に並べる3連単/3連複で `0.0` 固定値を出す現仕様は残す？データなしなら非表示にする運用に変える？

### F. 締切直前/発走済みのビジュアルフィードバック

**現象**
- 本サンプルでは `computeDeadline()` で発走までの残り時間を算出し、残り2分以内で `.race-time.is-closing`（点滅）、発走済みで `.race-time.is-closed`（グレーアウト）を付与して可視化
- 芥川様CSSにはこれら状態クラスは未定義

**確認事項**
- 本番運用では締切直前にどのようなビジュアルで注意喚起するか（点滅・色変更・アイコン表示等）
- 発走後〜確定までの間の表示仕様（「発走」「レース中」等のテキスト表示、オッズ表示の停止有無）
- **カットイン表示**（レース確定・中断表示）との干渉設計

### G. カットイン CUT-001/CUT-002 の暫定HTML

**現状**
- CUT-001（締切5分前）・CUT-002（発売終了）はスクリーンショット（Bパターン）から及川が再現した暫定HTMLで実装している
- HTML構造は `templates/cutin.html` に単体ファイルとして集約（差し替えを1ファイル置換で完結させるため）
- CSSは `demo-helpers.css` に暫定スタイルとして記載（`.cutin-overlay` 〜 `.cutin__footer--thankyou`）
- JS側（`common.js` の `checkCutin` / `showCutin` / `ensureCutinTemplate`）は、子テンプレート起動時に `cutin.html` を1回 fetch → `document.body` に挿入、発走時刻から逆算して表示、`CUTIN_DISPLAY_SEC` 秒後に自動解除
- 各子テンプレート（single-screen, single-umaren-wide, single-popular, single-popular-second）は IIFE 冒頭で `D.ensureCutinTemplate()` を呼び、poll 毎に `D.checkCutin(race, correctedNow)` を呼ぶ

**正式版到着時の差し替え手順**
1. 芥川様から正式なカットインHTML＋CSSを受領
2. `templates/cutin.html` を正式HTMLで丸ごと上書き（**この1ファイル置換で完了**）
3. `demo-helpers.css` のカットイン関連スタイル（`.cutin-overlay` 〜 `.cutin__footer--thankyou`）を削除
4. 芥川様の `style.css` にカットイン用スタイルが含まれていることを確認
5. JS側は以下のid属性が正式版HTMLでも維持されていれば変更不要:
   - `cutinOverlay` — オーバーレイ最外殻（`is-hidden` トグル対象）
   - `cutin-venue` — 場名テキスト
   - `cutin-race` — レース番号テキスト
   - `cutin-body` — 中央コンテンツ（`innerHTML` を動的に書き換える）
   - `cutin-footer` — フッターテキスト＋クラス切替

**芥川様へのお願い**
- 正式版のカットインHTMLを作成する際、上記のid属性を組み込んでいただけるとJS側の改修なしで差し替えが完了します
- id属性の変更が必要な場合は事前にご連絡ください

**締切の定義（2段階）**

本システムでは「締切」を2段階で扱う:

1. **実業務締切（投票締切）** = `post_time - DEADLINE_BEFORE_POST_MIN分`（= 発走2分前、既定）
2. **表示上の締切** = `実業務締切 - DEADLINE_SAFETY_MARGIN_SEC秒`（= 実締切より30秒早い、既定）

**表示は全て「表示上の締切」を基準にカウントダウン**する。これにより客が「画面上まだ締切表示が出ていないのに券売機で購入できなかった」体験を防ぐ。

タイムライン（post_time = 15:00、既定値の場合）:

| 時刻 | 状態 | ヘッダー `.race-time` | カットイン |
|---|---|---|---|
| 〜 14:47:30 | pre | 「発走 15:00」 | - |
| 14:47:30 〜 | countdown 開始 | 「締切 10 分前」 | - |
| 14:52:30 〜 | `is_approaching` (5分前) | 「締切 5 分前」 | **CUT-001 発火**（10秒表示 ★要確認） |
| 14:56:30 〜 14:57:30 | `is_closing` (1分前) | 「締切 1 分前」**点滅** | - |
| 14:57:30 | 表示締切到達 `is_closed` | 「発売締切」 | **CUT-002 発火**（10秒表示 ★要確認） |
| 14:58:00 | 実業務締切（券売機側の実際の締切） | 「発売締切」 | - |
| 15:00:00 | 発走 | 「発売締切」継続（次レースローテまで） | - |

ヘッダーの切替は JS（`renderRaceHeader`）が `.race-time` の innerHTML を `data-mode` に応じて書き換える。テンプレートHTML側の初期構造（「発走 HH:MM」or「締切 N 分前」）は起動時の1秒tick内で上書きされる。

**設定値**

| 設定 | 場所 | デフォルト | 上書き方法 |
|------|------|----------|-----------|
| カットイン表示秒数 | `common.js` `CUTIN_DISPLAY_SEC` | **10秒（★要確認、次回MTGで正式確定予定。C-02, 2026-04-17 及川判断）** | URLクエリ `?cutin_sec=N` |
| 実業務締切（発走何分前） | `common.js` `DEADLINE_BEFORE_POST_MIN` | 2分前 | 定数書き換え |
| 安全マージン（実締切より何秒早く表示するか） | `common.js` `DEADLINE_SAFETY_MARGIN_SEC` | 30秒 | URLクエリ `?safety_margin_sec=N` |
| カットイン CUT-001 発火タイミング | `common.js` `COUNTDOWN_START_MIN` | 5分前 | 定数書き換え |
| ヘッダー「締切N分前」切替開始 | `common.js` `COUNTDOWN_HEADER_START_MIN` | 10分前 | 定数書き換え |

### H. その他、暗黙の文字数前提



**現象** — 今回の確認で見つかった **固定寸法 × 文字数** のミスマッチ候補:

| 箇所 | 現在の幅 | 文字数前提（推定） | 問題が出そうなケース |
|---|---|---|---|
| `.weather` | 6.4rem | 1文字 | 小雨・小雪（2文字）で折り返し（A で対応済） |
| `.race-table__jockey` | 9.5rem | 4文字以内 | 5文字以上をそのまま流すと切れる（C で対応済） |
| `.course` | 17.6rem | 馬場1文字+種別1文字+距離4桁+向き3文字 | 海外距離等で桁数超過時に破綻？ |
| `.race-title span`（レース名） | 伸縮 | 日本語10〜12文字程度 | 非常に長いレース名での改行動作 |
| `.race-table__name` | 16.7rem | `--name-length` で可変 | 16文字以上の馬名での計算式挙動 |

**確認事項**
- 上記「問題が出そうなケース」を実データで当てた際のテスト済み範囲と、未テスト範囲を明示してもらえるか？
- 文字数超過時の**フォールバック仕様**（省略・縮小・表示不可セーフ）を整理いただきたい

### I. screen2.html / style.css 差し替えに伴う追加確認事項（2026-04-15）

馬単1/馬単2/馬連1/馬連2 のテンプレ切り抜き実装時に、芥川様 `screen2_files/style.css`（screen1 用を含むスーパーセット）を `assets/css/style.css` に差し替えた。その過程で以下の差分を検出し、`demo-helpers.css` で暫定対応している。いずれも芥川様 style.css 側の正式対応が望ましい項目。

#### I-1. ヘッダー `.race-time` の背景色を時間ベースで切替

**現状**
- 芥川様 `style.css` では `.race-time` の背景色が画面種別ごとに別定義:
  - `.screen`（単勝画面） → 赤グラデ `linear-gradient(#BF0808 → #5A0F02)`（締切警告色想定）
  - `.umaren-wide` / `.popular` / `.screen-second` → 黒 `#0D1117`（発走時刻表示想定）
- この設計は「画面種別で表示内容が固定（単勝=締切、他=発走時刻）」前提

**今回の変更**
- 4画面すべてで**時間ベース切替**（pre=発走HH:MM、countdown=締切N分前、closed=発売締切）を行うようにした
- `countdown`/`closed` モード時は全画面で赤グラデ警告色に統一するため、`demo-helpers.css` に暫定ルール追加:
  ```css
  .race-header .race-info .race-time[data-mode="countdown"],
  .race-header .race-info .race-time[data-mode="closed"] {
    background: linear-gradient(98.03deg, #BF0808 24.91%, #5A0F02 75.09%);
    border-left: 0.2rem solid #000000;
  }
  ```

**芥川様への確認事項**
- 4画面共通で countdown/closed モード時は警告色背景にする方針で良いか
- 警告色の具体的な色・グラデーション仕様（`.screen` 定義の流用で良いか、画面種別ごとに変えるか）
- 正式対応としては `style.css` 側に `.race-time[data-mode="..."]` 属性ベースのルールを追加してほしい

#### I-2. `.race-header` 既定背景色の消失（`header-{color}` クラス必須化）

**現状**
- 旧 `style.css`（design/htdocs 版）では `.screen .race-header` / `.umaren-wide .race-header` / `.popular .race-header` / `.popular.popular-second .race-header` にそれぞれ既定のグラデ背景が設定されていた
- 新 `style.css`（screen2_files 版）は `.race-header.header-{color}` サブクラスのみに背景を定義し、`header-{color}` が無い場合は**透明**
- 既存4テンプレート（single-screen/single-umaren-wide/single-popular/single-popular-second）は `header-{color}` 指定が無かったため、入替直後はヘッダー背景が消失

**暫定対応**（既存テンプレート側で対応済み）
- single-screen.html → `header-green` 付与（旧 `.screen` の緑グラデ）
- single-umaren-wide.html → `header-teal` 付与（旧 `.umaren-wide` の teal グラデ）
- single-popular.html → `header-blue` 付与（旧 `.popular` の青グラデ）
- single-popular-second.html → `header-red` 付与（旧 `.popular.popular-second` の赤グラデ）

**芥川様への確認事項**
- 新デザインでは「画面種別で固定背景」ではなく「`header-{color}` で明示」する方向で良いか
- 単勝/馬連ワイド/人気順1-15/人気順16-30 それぞれの本番での既定 header 色
- レースカテゴリー（メイン/新馬/OP 等）に応じて header 色を動的に切替える仕様なのか

#### I-3. 馬連ワイド `.race-table__row` / `.race-table__name` の高さが calc で固定される問題

**現状**
- 新 `style.css` line 1599-1603 付近で以下が追加されている:
  ```css
  .umaren-wide .race-main .race-table__row {
    height: calc(46rem / var(--row-count));
  }
  .umaren-wide .race-main .race-table__name {
    height: calc(46rem / var(--row-count));
  }
  ```
- ここで参照される `--row-count` は body 側にインラインで注入される「その body の項目数 N」なので、各行が `46rem/N` の固定高さになる
- 結果、P1（単勝側）の行高さ（col grid の `46rem/10`）と一致しなくなる

**暫定対応**（`demo-helpers.css`）
- `.umaren-wide` の flex chain 全段に `min-height: 0` を付与し、grid 子要素による膨張を防止
- body を flex column に切替え、row/name に `flex: 1 1 0` で body 高さを等分配
  → 各行 = col 1行高さ = P1 の単勝行と揃う

**芥川様への確認事項**
- `.race-table__row` / `.race-table__name` の `height: calc(46rem / var(--row-count))` は**削除してほしい**（body 側の `--row-count` を見てしまうため整合しない）
- もしくは body 側 `--row-count` 注入を止め、col 側 `--row-count`（= `max(10, --horse-count)`）を参照する実装に変更したい

#### I-4. `.screen-umatan` に number-{color} クラス対応が無い

**現状**
- 新 `style.css` では `.screen.screen-umaren` のみ `.screen-table__number.number-{white|black|red|...}` の色定義がある
- `.screen.screen-umatan` 側は `nth-child(2..19)` ベースで 18頭固定の色分けになっている（<18頭レースで枠色が正しくマッピングされない）

**暫定対応**（`demo-helpers.css`）
- `.screen.screen-umatan` に umaren と同等の `number-{color}` 色定義を展開（nth-child より高い特異度で上書き）

**芥川様への確認事項**
- `.screen-umatan` でも `.screen-umaren` と同じ `number-{color}` クラスベースで枠色を当てる方針で良いか
- 18頭未満レースでの nth-child ベースの色分けは誤動作するため、クラスベースに統一したい

#### I-5. 単体HTML（single-umaren-first / second, single-umatan-first / second）の暫定切り抜き

**現状**
- `screen2.html` から `.screen.screen-umaren.screen-first` / `.screen.screen-umaren.screen-second` / `.screen.screen-umatan.screen-first` / `.screen.screen-umatan.screen-second` の4ブロックを切り抜き、それぞれ `templates/single-umaren-first.html` / `templates/single-umaren-second.html` / `templates/single-umatan-first.html` / `templates/single-umatan-second.html` として暫定実装
- 芥川様から single-* 単体HTMLの正式納品は未受領（本対応は及川が実装許可を得て暫定で対応）

**芥川様への確認事項**
- 4テンプレの正式 single-* HTML の納品時期
- header 色の正式指定（現在は暫定で header-yellow / light_blue / orange / purple を割り当て済）
- 正式納品時は該当4ファイルを丸ごと差し替える方針

#### I-6. 発走時刻表示の `.race-time.start` クラス対応（header.html 整合）

**現状**
- 芥川様 `header.html`（2026-04-15 受領）で、発走時刻表示時は `.race-time` に `.start` クラスを付ける設計が確認された:
  ```html
  <!-- 締切5分前 -->   <div class="race-time">       <span>締切</span>...<span>分前</span></div>
  <!-- 発走時刻表示 --> <div class="race-time start"><span>発走</span>...</div>
  ```
- 対応する style.css 定義: `.race-time.start { background: #0D1117; }`（黒背景）

**対応状況（実装済み）**
- `common.js` の `renderRaceHeader` で `rtMode === 'pre'`（発走HH:MM表示）時に `.start` クラスを付与、他モード時は外す処理を追加
- デモ向け警告色（data-mode=countdown/closed の赤グラデ、I-1）と両立する形で動作確認済み

#### I-7. 締切到達時のヘッダー文言「発売終了」→「発売締切」

**決定事項**
- ヘッダー `.race-time` の `is_closed` 時のテキストは **「発売締切」** とする（当初の「発売終了」から変更、2026-04-15）
- CUT-002 カットインの本文は **「発売を締め切りました」**（変更なし）、CUT-002 カットイン自体の名称は仕様書05 由来の「発売終了カットイン」という呼称のまま維持（`CUT-002（発売終了）` 表記はコード内コメント・ドキュメントで残存）

**意図**
- 「発売終了」だと「全レースの発売が終わった」印象で、「このレースの投票締切」のニュアンスを出すため「発売締切」に統一

---

以上を MTG または書面で合意後、デモ側の暫定CSSは順次削除するか、本実装テンプレートに取り込む方針とする。

## 未実装・スコープ外
- `screen3.html` / `screen4.html`（枠単）：芥川様の実装待ち
- pageCount=2 時の軸9以降の馬（対応組合せ）の表示方針（確認事項D参照）
- カットイン表示（レース確定・中断表示など）：時刻補正の仕組みに相乗せる形で後日追加
- 端末×複数モニターでの多端末配信パターン（`monitor_id` 命名規則の詰め）

---

## J. 取消馬対応（指示書08）— 2026-04-16 実装

DB設計書v1.5 の `crc.is_scratched`（0=正常 / 1=出走取消 / 2=競走除外）をフロント側で表示するための実装。

### データ仕様
- `horses[].is_scratched` フィールドを追加（0 省略可）
- `gen_data.py` の `make_race(scratched_horse_nos={horse_no: 1|2})` で注入

### 表示仕様（ユーザー要望 2026-04-16 改訂後）
- 行全体: opacity は使わず、**単勝+複勝セルを結合したラベルセル** `.race-table__scratched` にダークグレー背景（#3a3a3a）+ 赤太字（#FF5252）
- 単勝・複勝・枠連画面（`single-screen.html`）: 結合ラベル「出走取消」「競走除外」を `grid-column: span 2`
- 人気順画面（`single-popular*.html`, `side-entries.html`）: 単勝セル幅 6.3rem に収まる **短縮表記「取消」「除外」**（`scratchedLabelShort`）
- 馬連ワイド画面: 軸馬取消 → `.body-scratched` で軸ブロック配下の全オッズセル背景 #1a1a1a、軸名は元の枠色を維持。相手馬取消 → `.row-scratched` で該当行の umaren/wide セル背景 #1a1a1a
- マトリクス画面（馬連/馬単 馬番順）: 軸取消 → body-scratched 配下の `.screen-table__odds` を #1a1a1a + 空白。相手取消 → `.odds-scratched` で空白+暗背景
- 人気・次点（`computeWinClasses`/`computePlaceClasses`）: 取消馬を自動除外（内部で `horses.filter(h => !h.is_scratched)`）
- 人気順リスト: `filterScratchedFromPopular(list, horses, combSize)` で取消馬を含むエントリをスキップ、件数維持のため繰り上げ
- 枠連: JSON生成側の責務（全頭取消時にエントリ除外）、表示側は触らない

### サンプルデータ
- `odds_NAR_45_04.json` — 船橋4R 8頭、5番出走取消 → 既存4テンプレで検証
- `odds_JRA_09_11.json` — 阪神11R 18頭、5/10 取消・15 除外 → マトリクス4枚テンプレで検証

### 共通関数（`common.js`）
- `scratchedLabel(isScratched)` → "出走取消"|"競走除外"|""
- `scratchedLabelShort(isScratched)` → "取消"|"除外"|""（人気順画面用）
- `buildScratchedSet(horses)` → { horse_no: true } セット
- `filterScratchedFromPopular(list, horses, combSize)`

### CSS（`demo-helpers.css`）
```css
.race-table__scratched { grid-column: span 2; background: #3a3a3a; color: #FF5252; font-weight: 700; ... }
.popular .race-table__row .race-table__scratched { grid-column: auto; font-size: 1.8rem; }
.odds-scratched { background-color: #1a1a1a; }
.body-scratched ... .screen-table__odds { background-color: #1a1a1a; }
```

---

## K. L字レイアウト + 動画組込（指示書09）— 2026-04-17 実装

monitor_id=0102 で 3パターンのレイアウトをローテーション実演するデモ。

### 3スロット構成（`schedule_0102_fast.json` で各1分、`schedule_0102.json` で各60分）

| slot | layout | 内容 |
|---|---|---|
| 1 | **lshape** (L字) | P1: side-entries（出走表）/ P2: video（大井ライブ）/ P3: wide-popular（4賭式×5件人気順） |
| 2 | **1screen** (1画面) | P1: video（大井ライブ 全画面） |
| 3 | **4split** (4分割 右下動画) | P1: single-screen / P2: single-umaren-wide / P3: single-popular / **P4: video** |

### 親 `index.html` 側の実装
- `applyLayout(layoutValue)` でレイアウト切替（`.grid` に `layout-4split` / `layout-1screen` / `layout-lshape` クラス付与）
- `configureVideoFrame(iframe, frame)` で type='video' の frame を処理（`setVideoConfig` postMessage 送信）
- スロット切替時の **location.reload() は撤廃**（2026-04-16 ユーザー要望）。`applyLayout` + `applyFrames` の inline 切替で同一ページ上でシームレス遷移 → **動画 iframe が継続再生**される
- `clearUnusedFrames()` で使われない position の iframe を about:blank にクリア

### L字レイアウト CSS（`index.html`、仕様書§4 準拠・px廃止）
```css
.grid.layout-lshape {
  grid-template-columns: 20% 1fr;              /* cell1 : cell2+cell3 = 20 : 80 */
  grid-template-rows: auto 1fr;
}
.grid.layout-lshape .cell-2 {
  aspect-ratio: 16 / 9;                         /* 動画枠は幅から 16:9 自動算出 */
  max-height: 100%;
}
```
**ビューポート比例拡縮**（仕様書§4 FHD→4K対応）:

| | 1280×720 | FHD 1920×1080 | 4K 3840×2160 |
|---|---|---|---|
| cell1 | 256×720 | 384×1080 | 768×2160 |
| cell2 (16:9) | 1024×576 | 1536×864 | 3072×1728 |
| cell3 | 1024×144 | 1536×216 | 3072×432 |

### 新テンプレート
**`templates/side-entries.html`** — L字左袖
- `html.single-screen { font-size: min(3.448vw, 1.852vh) !important }` で rem 動的算出
- `.popular` の padding 解除、`race-main` を 1fr、`race-table__row` の馬名列を `1fr` で cell1 全幅を使う
- `race-header` の天候・馬場・発走時刻ブロックは非表示、場名+R+レース名のみ
- `--horse-count` のみ注入（--row-count は style.css 側の `max(10, var(--horse-count))` 自動算出）

**`templates/wide-popular.html`** — L字右下
- `html.single-screen { font-size: min(1.25vw, 10vh) !important }` で横長 cell 向け rem 決定
- 4賭式（馬連・馬単・3連複・3連単）× 上位5件、`grid-template-columns: 1fr 1fr 1fr 1fr`
- 馬番セル `span:nth-child(odd)` を 1.5rem 正方形（FHD ≒ 30×30px）
- 組合せの寄せ方: `span:first-child { justify-self: end }`（左馬番は右寄せ）、`span:last-child { justify-self: start }`（右馬番は左寄せ）、3賭式の真ん中 `span:nth-child(3)` は `justify-self: center`
- `.race-header` は非表示（cell3 高さを最大限使う）

**`templates/video-frame.html`** — 動画再生共通（4分割/1画面/L字）
- `setVideoConfig` postMessage 受信 → **hls.js** で HLS ライブ再生
- パラメータ: `video_source` / `quality_mode` (auto/fixed) / `quality_cap` / `audio_muted` / `volume`
- 同じ source の再送信では iframe を再ロードしない（slot 切替でも継続再生）
- **TECH-VERIFICATION-ONLY マーカー内**で実装（権利処理前提、本番切替時に除去/差替）

### 動画URL組立（`index.html`、TECH-VERIFICATION-ONLY）
```javascript
VIDEO_URL_BASE = 'https://movie61auhrn2-3.keiba-racing.jp/keiba/nar/live/';  // マスタープレイリスト (2026-04-17 修正)
VENUE_CODE_MAP = { monbetsu, ooi, sonoda, obihiro, morioka, ... };   // NAR 15場

function buildVideoUrl(frame) {
  if (frame.video_source_override) return frame.video_source_override;   // 開発時テスト用
  return VIDEO_URL_BASE + VENUE_CODE_MAP[frame.venue_code] + '_https.m3u8';
}
```
- 本サンプルは `venue_code: "ooi"` で大井の実URLを使用（門別は配信終了時刻あり、翌日開催場で随時切替）
- 本番切替時は [TECH_VERIFICATION_NOTES.md](TECH_VERIFICATION_NOTES.md) のチェックリストに従う

### gen_data.py 新機能
- `build_lshape_slot()` / `build_1screen_slot()` / `build_4split_with_video_slot()` — 各レイアウト用 slot ビルダー
- `build_schedule_0102(fast)` — L字/1画面/4分割動画の3スロット schedule 生成
- `MONBETSU_NAMES`（18頭分）を新規追加

### 仕様書§4 準拠状況
- [x] px 使用なし（親・子 iframe とも、`rem` + `vw` + `vh` + `%` のみ）
- [x] ビューポート変動で全要素が比例拡縮（1280 : FHD : 4K = 1 : 1.5 : 3）
- [x] `--horse-count` 方式は継続、`--row-count: max(10, var(--horse-count))` は style.css 側算出
- [x] 色指定はクラス付与のみ（hex/rgb 直接注入なし）

### TECH-VERIFICATION-ONLY マーカー
以下のブロックは本番切替前に除去/差替が必要（詳細は `TECH_VERIFICATION_NOTES.md`）:
- `index.html`: `VIDEO_URL_BASE` / `VENUE_CODE_MAP` 定数、`buildVideoUrl()` / `configureVideoFrame()` 関数
- `templates/video-frame.html`: hls.js CDN タグ、`applyConfig()` 関数
- `gen_data.py`: `DEV_VIDEO_SOURCE`（現状 None）、schedule 内の `video_source_override` フィールド

検索コマンド:
```powershell
Select-String -Path src/odds-demo/**/*.html, src/odds-demo/**/*.js, src/odds-demo/**/*.py -Pattern "TECH-VERIFICATION-ONLY"
```
