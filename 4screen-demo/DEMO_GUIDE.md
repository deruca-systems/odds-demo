# 4画面オッズ表示デモ 実演ガイド

> **⚠ 2026-07-07 移設ノート**: 旧パスからの 2026-04-17 スナップショット移設。monitor 番号・URL は最新の schedules/ 実体と突合してから使うこと。

2026-04-15 作成。サテライト石狩（2026年7月試験運用）向け 4画面JSONポーリングサンプルのデモ実演用資料。

---

## 1. 公開URL（GitHub Pages ホスト）

**本番デモURL**:
```
https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=0101&fast=1&page_rotation=3
```

公開手順は [9. GitHub Pages 公開手順](#9-github-pages-公開手順) 参照。

### 1.1 デモ動作の仕組み（GitHub Pages 上）

- データ（schedule / odds JSON）は git コミット時点の時刻で静的に焼かれる
- **ブラウザでデモを開いたその瞬間**を slot1 開始として、デモタイムライン（5/10/15分＝計30分）が進行
- そのため GitHub Pages 上ではいつ開いても常に「slot1 → slot2 → slot3」の流れを体験できる（コミット時刻は内部補正されて無関係）

### 1.2 実演直前の推奨オペレーション

`src/odds-demo/_tools/gen_data.py` をローカルで実行 → `data/` 配下を再生成 → コミット・プッシュ、の流れを**実演前日〜当日朝に1回**走らせると、内部時刻のずれが最小化されます（デモ自体は古いコミットでも動作しますが、情報バーに古い時刻が見える見栄え上の問題があるため）。

```bash
cd "C:/Users/oikawa.masafumi/Documents/00.仕事/地方競馬オッズ表示システム(仮)/git/keiba-odds"
python -X utf8 src/odds-demo/_tools/gen_data.py
# → src/odds-demo/data/ の各 JSON が更新される
# → git add data/* → commit → push → GitHub Pages が自動再公開（数分）
```

### 1.3 ローカル動作確認（開発時のみ）

GitHub Pages に上げる前にローカルで確認する場合:

```bash
cd "C:/Users/oikawa.masafumi/Documents/00.仕事/地方競馬オッズ表示システム(仮)/git/keiba-odds/src/odds-demo"
python -m http.server 8765
```
→ ブラウザで `http://localhost:8765/?monitor=0101&fast=1&page_rotation=3`

### 1.4 H キーで情報バー非表示

初期表示では上部に情報バー（端末ID・現在スロット・サーバ時刻・補正値等）が出る。**H キー**で非表示→本番想定のフル画面に。右上の小さな復帰ハンドルで再表示可能。

---

## 2. デモURL（クエリ一覧）

| URLクエリ | デフォルト | 用途 |
|---|---|---|
| `monitor=XXXX` | 必須 | 端末ID。`0101` 固定でデモ運用 |
| `fast=1` | なし | **デモ用モード**: slot 期間を 5/10/15分に短縮 + ポーリング 10秒化（C-01, 2026-04-17） |
| `page_rotation=N` | 15 | 馬連ワイド画面のページ内ローテ秒数（デモは 3 で高速化） |
| `schedule_poll=N` | 30（`fast=1` 時 10） | スケジュール JSON の poll 間隔（秒）。本番デフォルト30秒（C-01, 2026-04-17）、個別指定は最優先 |
| `odds_poll=N` | 30（`fast=1` 時 10） | オッズ JSON の poll 間隔（秒、子 iframe に伝搬）。本番デフォルト30秒（C-01, 2026-04-17）、個別指定は最優先 |
| `cutin_sec=N` | 10 | カットイン表示秒数（★要確認、次回MTG正式確定予定。C-02, 2026-04-17 及川判断） |
| `safety_margin_sec=N` | 30 | 表示上の締切を実投票締切より何秒早めるか |

### 実演時のURL例

`BASE = https://deruca-systems.github.io/odds-demo/4screen-demo` とする。

- **標準デモ**（推奨）:
  `${BASE}/?monitor=0101&fast=1&page_rotation=3`
- **カットイン時間を旧仕様（30秒）で比較**:
  `${BASE}/?monitor=0101&fast=1&page_rotation=3&cutin_sec=30`
- **ポーリング状況を見せる（poll 頻度上げ）**:
  `${BASE}/?monitor=0101&fast=1&schedule_poll=3&odds_poll=3`
- **本番相当（30秒ポーリング）で見せる**:
  `${BASE}/?monitor=0101` （`fast` を外す）

---

## 3. デモタイムライン（fast モード）

gen_data.py 実行時刻を `NOW`（= slot1 開始）として以下の流れ。各スロット終了時に画面リロードして次スロット構成に差し替わる。

### 3.1 スロット / レース配置

| スロット | 期間 | レース | 頭数 | post_time | テンプレ構成 |
|---|---|---|---|---|---|
| **slot1** | NOW〜+5分 | 船橋1R | 8頭 | NOW+3分 | **既存4枚**（カットイン実演） |
| | | 船橋2R | 11頭 | NOW+10分 | **既存4枚** |
| | | 船橋3R | 12頭 | NOW+15分 | **新テンプレ4枚**（馬連/馬単マトリックス） |
| **slot2** | NOW+5〜+15分 | 名古屋2R | 13頭 | NOW+60分 | 既存4枚 |
| | | 名古屋7R | 14頭 | NOW+63分 | 既存4枚 |
| | | **名古屋8R** | 16頭 | NOW+66分 | **新テンプレ4枚** |
| | | 名古屋9R | 10頭 | NOW+69分 | 既存4枚 |
| **slot3** | NOW+15〜+30分 | **東京11R** | 18頭 | NOW+123分 | **新テンプレ4枚**（前日発売）|
| | | 中山11R | 16頭 | NOW+126分 | 既存4枚 |

※ 各スロット内の race rotation は 45秒固定。ローテ順は表示順と同じ。

### 3.2 slot1 タイムライン（カットイン実演）

船橋1R は NOW+3分発走で、**表示上の締切 = NOW+0:30**。slot1 開始直後にカットイン CUT-001 / CUT-002 を一気に見せられる構成。

| 経過時刻 | レース | 出来事 | ヘッダー表示 | カットイン |
|---|---|---|---|---|
| 0:00 | 1R | slot1 開始、1R 表示 | 「締切 1 分前」点滅 | **CUT-001 発火**（10秒）|
| 0:10 | 1R | CUT-001 非表示 | 「締切 1 分前」点滅 | - |
| 0:30 | 1R | 表示締切到達 | 「発売締切」 | **CUT-002 発火**（10秒）|
| 0:40 | 1R | CUT-002 非表示 | 「発売締切」 | - |
| 0:45 | → 2R | race rotation | 「締切 7 分前」（countdown）| - |
| 1:30 | → 3R | race rotation、**新テンプレ切替** | ※新テンプレは独自ヘッダー | - |
| 2:15 | → 1R | race rotation | 「発売締切」（維持）| - |
| 3:00 | → 2R | race rotation | 「締切 5 分前」| **CUT-001 発火** |
| 3:45 | → 3R | race rotation、新テンプレ | - | - |
| 4:30 | → 1R | race rotation | 「発売締切」 | - |
| 5:00 | - | slot1 終了、リロード → slot2 | - | - |

### 3.3 slot2 タイムライン

| 経過時刻 | レース | ヘッダー状態 | テンプレ |
|---|---|---|---|
| 5:00 | 2R | 「発走 HH:MM」（pre）| 既存 |
| 5:45 | 7R | 「発走 HH:MM」（pre）| 既存 |
| 6:30 | **8R** | 「発走 HH:MM」（pre）| **新テンプレ（16頭マトリックス）** |
| 7:15 | 9R | 「発走 HH:MM」（pre）| 既存 |
| ... | rotation 継続 | - | - |
| 15:00 | - | slot2 終了、リロード → slot3 | - |

### 3.4 slot3 タイムライン

| 経過時刻 | レース | ヘッダー状態 | テンプレ |
|---|---|---|---|
| 15:00 | **東京11R** | **前日発売ラベル**のみ（race-info 非表示）| **新テンプレ（18頭フル）** |
| 15:45 | 中山11R | 「発走 HH:MM」（pre）| 既存 |
| ... | rotation 継続 | - | - |
| 30:00 | - | slot3 終了 | - |

---

## 4. デモの見どころ

### 4.1 【slot1 0:00〜0:40】カットイン CUT-001 / CUT-002

- **CUT-001（締切5分前）**: 黄色 `5` + 赤フッター「お早めにご投票ください。」
- **CUT-002（発売終了）**: 黄色「発売を締め切りました」+ グレーフッター「ご投票誠にありがとうございました」
- **客体験保護の安全マージン**: 実投票締切（発走2分前）より 30秒早く CUT-002 発火 → 「画面に締切表示が出ていないのに券売機で締切」を回避

### 4.2 【slot1 1:30〜】船橋3R 新テンプレマトリックス（12頭）

- P1: 馬連オッズ（馬番順）軸馬1-9
- P2: 馬連オッズ（馬番順）軸馬10-11（12頭なので一部空）
- P3: 馬単オッズ（馬番順）軸馬1-9
- P4: 馬単オッズ（馬番順）軸馬10-12
- ヘッダー色が4画面で異なる（オレンジ / 紫 / 黄 / 水色）
- **同馬同士の ×（odds-cross）** が馬単で見える

### 4.3 【slot1 全般】P1 と P2 の行高さ同期

- P1（単勝・複勝・枠連）と P2（馬連・ワイド）の1行高さが**完全一致**
- `--row-count = max(10, --horse-count)` で両画面のグリッドを揃えた設計

### 4.4 【slot2 名古屋8R】16頭マトリックス

- 船橋3R よりも行数が埋まった状態（名古屋8R は 16頭）
- umaren-second でも行数が多く、マトリックスのボリューム感が出る

### 4.5 【slot3 東京11R】18頭フルマトリックス ＋ 前日発売

- screen2.html サンプルの原設計通り 18頭で全マスが埋まる
- 前日発売レースのためヘッダーには **「前日発売」ラベルのみ**（天候・馬場・発走時刻は非表示）
- race_rotation で中山11R（既存テンプレ、16頭）と交互切り替え

### 4.6 【全般】時間ベースのヘッダー表示切替

NOW 基準の post_time に応じて `.race-time` の表示が:

| 残り時間 | モード | 表示 | 背景 |
|---|---|---|---|
| >10分 | pre | 「発走 HH:MM」 | `.start` クラス = 黒 `#0D1117` |
| 10〜1分 | countdown | 「締切 N 分前」 | 赤グラデ（警告色） |
| 1分以内 | countdown + closing | 「締切 1 分前」（点滅）| 赤グラデ |
| 0以降 | closed | **「発売締切」** | 赤グラデ（彩度/輝度下げ） |

---

## 5. よくある質問

### Q1. サーバ時刻（情報バーの補正値）がマイナスで大きいですが？

A. 静的 JSON の `server_time` が gen_data.py 実行時刻で固定されているため、時間経過で補正値がどんどんマイナスに蓄積します。デモでは初回 offset を固定しているので表示上は正常進行します。本番では CRM が常に最新の `server_time` を返すため発生しません。

### Q2. カットインが 10秒で消えるのは早くないですか？

A. **C-02（2026-04-17 及川判断）で仕様値を 10秒 に確定**しました（★要確認、次回MTGで正式議事録化予定）。旧仕様（仕様書05 原典の30秒）で比較したい場合は URLクエリ `?cutin_sec=30` で切替可能です。

### Q3. 船橋3R で 馬連 P2 の一部が空なのは？

A. 12頭レースなので、軸馬12 の組合せ相手（b>12）が存在せず空になります。18頭レース（slot3 東京11R）で全マス埋まった状態を確認できます。

### Q4. 船橋2R の「締切 7 分前」はどこから？

A. 船橋2R は post_time = NOW+10分、表示締切 = NOW+7分30秒。slot1 開始時 NOW+0:45（2R ローテ）時点で残り 6:45、2分後に rotate 再登場 → 残り 4:45、CUT-001 発火などのパターンが発生します。

### Q5. カットイン表示中もオッズは更新されますか？

A. はい、バックグラウンドの poll は継続しています。カットイン終了後に最新オッズが表示されます。

### Q6. 新テンプレと既存テンプレの切替はどこで決まっている？

A. `_tools/gen_data.py` の `MATRIX_VARIANT_FILES` 集合（3レース: 船橋3R / 名古屋8R / 東京11R）。本番実装では CRM 側が schedule JSON で配信テンプレを指定する想定。

---

## 6. 未決定事項（芥川様／堀井様との確認事項）

本サンプルで暫定対応している設計判断のうち、本番実装までに合意が必要な項目。詳細は [README.md](README.md) の「芥川様への確認事項」A〜I セクション参照。

### 6.1 芥川様（リンクスティップ・デザイン担当）への確認事項（A〜I）

| 項目 | 内容 | 影響度 |
|---|---|---|
| A | 天候ラベル 2文字表記（小雨/小雪）の折り返し対応 | 中 |
| B | 前日発売ラベルの適用スコープ（`.popular` 以外の画面での定義） | 中 |
| C | 騎手名 5文字以上の切り詰めルール（先頭4文字 vs 幅ベース） | 低 |
| D | 馬連ワイド画面のページ分割ロジック（pairSum対称分割で確定）| 確定済 |
| E | 枠番色クラス適用のテンプレート別差分 | 低 |
| F | 締切直前/発走済みのビジュアル（現状は opacity 1↔0.5 の点滅暫定） | **高** |
| G | カットイン CUT-001/CUT-002 の正式HTML納品 | **高** |
| H | 暗黙の文字数前提（course/raceName/馬名の長さフォールバック） | 中 |
| **I** | **screen2.html / style.css 差し替えに伴う追加事項（下記 I-1〜I-7）** | - |
| I-1 | `.race-time[data-mode=countdown/closed]` の赤グラデ背景仕様 | 中 |
| I-2 | `.race-header` 既定背景色（`header-{color}` クラス必須化、既存4テンプレに付与済） | 中 |
| I-3 | `.umaren-wide .race-table__row/__name` の `calc(46rem/--row-count)` 固定高さ削除依頼 | **高** |
| I-4 | `.screen-umatan` の number-{color} クラス対応 | 中 |
| I-5 | 単体HTML（馬連1/2・馬単1/2）の正式納品、header 色の正式指定 | **高** |
| I-6 | `.race-time.start` クラス対応（header.html 受領で確認、実装済） | 確定済 |
| I-7 | ヘッダー文言「発売終了」→「発売締切」の変更 | 確定済 |

### 6.2 堀井様（AIR PROSPECT・管理画面担当）との調整事項

| 項目 | 内容 |
|---|---|
| スケジュールJSON配信パス | 本番S3: `schedules/{monitor_id}.json`（デモは `data/schedule_XXXX.json`） |
| オッズJSON配信パス | 本番S3: `odds/{YYYYMMDD}/{org}_{placeCode}_{raceNo}.json` |
| `monitor_id` の命名規則・端末×モニター対応 | 複数端末／複数モニター配信パターン |
| `race_rotation_seconds` の動的更新タイミング | スロット切替時のみか、レース途中でも変更可か |

### 6.3 本体側（フォーマイルズ内山様）との調整事項

| 項目 | 内容 |
|---|---|
| オッズ JSON 更新頻度 | **30秒間隔**（全画面リスト v1.0【3/10確定事項】、C-01 2026-04-17 確定）、本番時の実頻度 |
| `server_time` の精度 | NTP 同期前提、端末側時刻補正の許容ドリフト範囲 |
| 発走後〜確定までの JSON 内容 | `post_time_iso` 過去値の扱い、確定後のオッズ消去など |

---

## 7. トラブルシューティング

### 7.1 カットインが発火しない

- データ再生成（`gen_data.py`）から時間が経っている可能性。再生成して最新の NOW 基準に更新。
- ブラウザ iframe キャッシュの可能性。ページ全体をハードリロード（Ctrl+Shift+R / Cmd+Shift+R）。

### 7.2 行高さが P1/P2 で揃わない

- `demo-helpers.css` が正しく読み込まれているか確認。`style.css` だけではなく、後続の `demo-helpers.css` が必須。
- ブラウザキャッシュの可能性。`demo-helpers.css?t=現在時刻` でハードリロード。

### 7.3 ヘッダーの背景色が消えている

- `.race-header` に `header-{color}` クラスが付いているか確認。
  - single-screen → `header-green`
  - single-umaren-wide → `header-teal`
  - single-popular → `header-blue`
  - single-popular-second → `header-red`
  - 新テンプレ → yellow / light_blue / orange / purple

### 7.4 画面が右上に寄って、縦が見切れる

- `html.single-screen` の font-size が min(1.04vw, 1.85vh) で vh 側に追従するので、ブラウザの上下バー（URLバー等）で高さが縮むと文字サイズも縮小します。F11 でフルスクリーン化か、ブラウザの UI を最小化。

### 7.5 情報バーが出てこない

- 情報バーは初期表示、H キーで非表示切替。再表示は右上の小さな復帰ハンドルをクリック。
- URLクエリで永続非表示にするオプションは現状なし。

---

## 8. デモ実演チェックリスト

実演前に以下を確認:

- [ ] `gen_data.py` を実行済み（30分以内）
- [ ] `http://localhost:8765/?monitor=0101&fast=1&page_rotation=3` で開ける
- [ ] slot1 開始後すぐ CUT-001 が出ることを確認
- [ ] 船橋3R ローテ時（~1:30後）に新テンプレ4枚が表示されることを確認
- [ ] H キーで情報バー切替が動作
- [ ] ブラウザウィンドウが FHD 相当の広さ（見切れ防止）
- [ ] デモ用画面の音量オフ（現状音は出ないが念のため）

---

## 9. GitHub Pages 公開手順

本サンプルを GitHub Pages で公開する手順（初心者向け）。既に `deruca-systems/odds-demo` public リポジトリで GitHub Pages が有効化されている前提。

### 9.0 リポジトリ構成方針（サブフォルダ共存方式）

既存の「前回 fetch ポーリングサンプル」をリポジトリルートに残したまま、今回の 4画面デモを **`4screen-demo/` サブフォルダ**に追加します。前回サンプルとの URL 併存ができるメリットがあります。

```
【ローカル】                          【GitHub (odds-demo リポジトリ)】
                                      odds-demo/
                                      ├── (既存) 前回 fetch ポーリングサンプル
src/odds-demo/                        │
├── index.html             ───→      ├── 4screen-demo/
├── templates/             ───→      │   ├── index.html
├── assets/                ───→      │   ├── templates/
├── data/                  ───→      │   ├── assets/
├── _tools/                ───→      │   ├── data/
├── README.md              ───→      │   ├── _tools/
└── DEMO_GUIDE.md          ───→      │   ├── README.md
                                      │   └── DEMO_GUIDE.md
                                      └── (他、既存ファイル群)
```

公開後の URL:
- 前回サンプル: `https://deruca-systems.github.io/odds-demo/` （従来通り）
- 今回の4画面デモ: `https://deruca-systems.github.io/odds-demo/4screen-demo/`

### 9.1 ブラウザからアップロードする（サブフォルダ作成）

GitHub のブラウザUI ではファイルアップロード時にパスを手入力することでサブフォルダを作成できます。

1. https://github.com/deruca-systems/odds-demo を開く
2. 「Add file」ドロップダウン → **「Upload files」** をクリック
3. 画面上部のパス欄（デフォルトは空）で以下の操作を行う:
   - まず `4screen-demo` と入力してスラッシュキーを押す（またはそのまま次の操作へ）
   - すると `4screen-demo/` が仮想的にパスプレフィクスとして付加される
4. エクスプローラで `C:\...\keiba-odds\src\odds-demo\` を開く
5. **フォルダの中身全て**（`index.html`, `templates/`, `assets/`, `data/`, `_tools/`, `README.md`, `DEMO_GUIDE.md` など）をドラッグ&ドロップ
   - ⚠ `src/odds-demo/` フォルダごとではなく、**中身だけ**を選択
6. 下の「Commit changes」欄にメッセージ（例: `add 4screen demo`）を入力
7. 「Commit changes」ボタンをクリック

**💡 もしパス手入力がうまくいかない場合**（ブラウザUIのバージョンによる）:

代替手段1: ローカルで `4screen-demo` というフォルダを作り、中身をそこにコピーしてから、その `4screen-demo` フォルダごとドラッグ&ドロップ。

代替手段2: GitHub の Web 画面で「Add file」→「Create new file」を選び、ファイル名欄に `4screen-demo/dummy.txt` と入力（これで `4screen-demo/` フォルダが git 上に作られる）→ コミット後、そのフォルダを開いて「Upload files」で中身をアップロード → 最後に `dummy.txt` を削除。

**注意**: GitHub のブラウザアップロードは 1回あたり 最大 100 ファイルまで。本サンプルは約 20 ファイルなので問題なし。

### 9.2 GitHub Pages を確認する

既に `odds-demo` リポジトリで GitHub Pages 有効なら、サブフォルダは**自動で追加公開**されるため設定変更は不要。

念のため確認する場合:

1. リポジトリの **Settings** タブ → 左サイドバー **Pages**
2. 「Build and deployment」セクションで Source: `Deploy from a branch`, Branch: `main` / `(root)` になっていることを確認

### 9.3 デモURL で動作確認

アップロード後、2〜3分してから以下にアクセス:

```
https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=0101&fast=1&page_rotation=3
```

4分割画面が表示され、slot1 開始直後に船橋1R で CUT-001（締切5分前カットイン）が発火すれば成功。

### 9.4 更新時の手順（実演前の再生成含む）

コードやデータを更新して再公開する場合:

1. ローカルで `gen_data.py` 実行（データ再生成）
2. https://github.com/deruca-systems/odds-demo/tree/main/4screen-demo を開く（サブフォルダ直接）
3. 更新したいファイルごとに:
   - フォルダ内で「Add file」→「Upload files」で同名ファイルを再アップロード（= 上書き）
   - または該当ファイルを開き、✏️（鉛筆）アイコンで編集
4. Commit changes
5. GitHub Pages は自動的に数分で再ビルド＆公開

**💡 Tip**: 頻繁に更新するなら GitHub Desktop アプリをインストールするとブラウザ操作より圧倒的に楽です（差分自動検出、ワンクリックでコミット＆プッシュ）。
https://desktop.github.com/

### 9.5 トラブル時のチェックポイント

| 症状 | チェック |
|---|---|
| ページが 404 | GitHub Pages が有効化されているか、ビルドが完了しているか（Settings → Pages の上部メッセージ）。`4screen-demo/` 配下に `index.html` があるか |
| CSS が当たらない | `index.html` の `<link>` 相対パスが `assets/css/...` になっているか |
| iframe 内が 404 | `templates/` / `data/` フォルダが `4screen-demo/` サブフォルダにちゃんとアップロード済みか |
| データが古い日付 | `gen_data.py` を実行して `data/` を再生成・再アップロード |
| 日本語ファイル名のエラー | 本サンプルにはないはずだが、もし日本語ファイル名が紛れていないか確認 |
| 前回サンプルが表示されなくなった | `4screen-demo/` サブフォルダ作成時にルート直下のファイルを誤って削除していないか確認 |

### 9.6 参考リンク

- GitHub Pages 公式ドキュメント: https://docs.github.com/ja/pages
- GitHub ブラウザからのファイル編集: https://docs.github.com/ja/repositories/working-with-files/managing-files

---

## 10. 参考: 関連ドキュメント

- [README.md](README.md) — 本サンプルの完全仕様（構成・芥川様確認事項・芥川様CSS 差分等）
- [HANDOFF.md](HANDOFF.md) — セッション間引継ぎ資料
- [_tools/gen_data.py](_tools/gen_data.py) — テストデータ生成スクリプト
- `../../design/htdocs/` — 芥川様原デザイン一式
- `../../docs/仕様書_specs/claude code実装指示/` — 実装指示書（04/05）
- `../../docs/画面サンプル(202604015_screen34サンプル)/` — screen2 / header サンプル
