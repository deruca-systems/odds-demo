# odds-demo (Public Mirror)

**DERUCA Odds System（D.O.S）** — 競馬オッズ表示システムのフロントエンド プロトタイプ実装。

本リポジトリは GitHub Pages で動作デモを公開するためのリポジトリです。
仕様書類・設計資料は private リポジトリで管理しています。

## デモ URL

配布データは 2026-05-01 のため、URL に `&date=20260501` を付与してアクセスしてください。

| URL | 内容 |
|---|---|
| [4 分割標準](https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=101&date=20260501&fast=1) | 単複枠 / 人気順 / 馬連ワイド / 人気順第二 の 4 分割（PAT-4SPLIT-STD、column-major） |
| [3 分割切替](https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=102&date=20260501&fast=1) | 3 分割（出走表 + 動画 + 人気順）→ 1 画面 → 4 分割右下動画 のスロット遷移 |
| [4 分割馬連馬単](https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=105&date=20260501&fast=1) | 上段 = 馬連 1/2、下段 = 馬単 1/2 の row-grouped レイアウト |
| [出走表 + 成績払戻](https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=117&date=20260501&fast=1) | 新潟 1R-12R 比較ビュー（PAT-3R-ENTRIES-RESULTS、3R 出走成績） |
| [全パターン showcase](https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=118&date=20260501&fast=1) | 4 分割全パターン（NORMAL + 同着 A〜H + 出走表）の showcase |
| [レース中止](https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=106&date=20260501&fast=1) | レース中止時の表示 |
| [開催中止](https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=107&date=20260501&fast=1) | 開催中止時の表示 |

## 主な機能

- レイアウト: 4 分割 / 1 画面 / 3 分割
- 静的 JSON 配信 + Fetch ポーリング方式（30 秒、`?fast=1` で 10 秒短縮）
- 全 9 賭式対応: 単勝 / 複勝 / 枠連 / 枠単 / 馬連 / 馬単 / ワイド / 三連複 / 三連単
- 馬連・馬単マトリクス表示（前半 1〜9 軸 / 後半 10 番以降軸の自動ローテ）
- 人気順ランキング（馬連・馬単・三連複・三連単 を 1〜15 / 16〜30 で展開）
- 出走表 + 競走成績 + 払戻金（screen5 準拠）
- 変更情報画面（騎手変更 / 出走取消 / 競走除外 / 発走時刻変更）
- カットイン: 締切 5 分前 / 締切（締切後次レース自動遷移）
- 同着パターン: NORMAL + A〜H の 9 パターン対応
- 取消馬・除外馬対応、レース中止・開催中止オーバーレイ
- HTTP `Date` + `Age` ヘッダによる時刻補正（NTP 非同期端末でも発走時刻判定が正確）
- 4K (3840×2160) と FHD (1920×1080) 両対応（rem ベース）

## URL パラメータ

| パラメータ | 例 | 用途 |
|---|---|---|
| `monitor` | `101` | モニター ID（`schedules/{date}/{monitor}.json` を取得） |
| `date` | `20260501` | 開催日（未指定時は端末暦日） |
| `fast` | `1` | ポーリング 30 秒 → 10 秒、レース遷移 60 秒 → 5 秒に短縮 |
| `next_race_sec` | `5` | 次レース遷移秒の明示指定 |

## ディレクトリ

`4screen-demo/` 配下にすべての動作ファイルを配置しています。

```
4screen-demo/
├ index.html                親フレーム（スケジュール poll + iframe 管理 + 時刻補正）
├ templates/                子テンプレ（オッズ・情報系・カットイン）
├ assets/css/, assets/js/   スタイル・共通スクリプト
├ assets/images/            アイコン・天候 SVG
├ schedules/, odds/, results/, changes/   JSON 配信ファイル群
└ _tools/gen_data.py        デモデータ再生成スクリプト
```

## ライセンス

All rights reserved. Proprietary project.
