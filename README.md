# odds-demo (Public Mirror)

**DERUCA Odds System（D.O.S）** — 地方競馬オッズ表示システムのポーリングサンプル実装（公開ミラー）。

本リポジトリは GitHub Pages で動作デモを公開するためのミラーです。  
開発本体は private リポジトリで管理されています。

## デモURL

| URL | 内容 |
|---|---|
| [4分割標準](https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=0101&fast=1) | 単勝・複勝・枠連 / 馬連ワイド / 人気順 ×2 の4分割 |
| [L字+動画](https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=0102&fast=1) | L字レイアウトで出走表＋ライブ映像＋人気順 |
| [複数場混在](https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=0103&fast=1&next_race_sec=5) | 画面ごとに異なる場のレースを表示 |
| [1レース固定](https://deruca-systems.github.io/odds-demo/4screen-demo/?monitor=0104&fast=1) | 全画面同一レース（締切後も継続表示）|

## 主な機能

- 4分割 / L字 / 1画面 の複数レイアウト
- 静的 JSON ポーリング方式（WebSocket 不使用）
- 画面ごとに独立した発走時刻ベースの次レース自動遷移
- 単勝・複勝 / 枠連 / 枠単（交互表示）/ 馬連・ワイド / 馬連・馬単マトリクス / 人気順 など複数テンプレート
- 取消馬・発売中止レースのサンプルデータ含む

## ディレクトリ

`4screen-demo/` 配下にすべての動作ファイルを配置。

## ライセンス

All rights reserved. Proprietary project.
