# CLAUDE.md — odds-demo（D.O.S プロトタイプ実装本体）

このリポジトリの `4screen-demo/` が **D.O.S プロトタイプの唯一の編集対象**（GitHub Pages 配信元）。
プロジェクト全体のパス・用語・最新版番号は中央 `C:\Users\oikawa.masafumi\Documents\claude\CLAUDE.md` を参照。
最新スナップショット・残課題は `4screen-demo/HANDOFF.md`、運用 URL は `4screen-demo/DEMO_GUIDE.md`（いずれも 2026-07-07 に本リポジトリへ移設済み。以降の追記はこちら側に行う）。

## ディレクトリ構造

```
4screen-demo/
├ index.html                  ← 親フレーム。スケジュール poll、iframe 4 つ管理、時刻補正
├ templates/                  ← 子テンプレ（芥川様 HTML 派生）
│   ├ single-screen.html      単勝・複勝・枠連
│   ├ single-umaren-wide.html 馬連・ワイド（自動ローテ）
│   ├ single-popular*.html    人気順 1-15 / 16-30
│   ├ single-umaren/umatan-*  馬連/馬単マトリクス
│   ├ cutin.html              SCR-CUT-001/002（芥川 screen6.html L803-835 由来）
│   ├ side-entries.html       L字左袖（出走表）
│   ├ wide-popular.html       L字右下（4 賭式 ×N 件）
│   ├ video-frame.html        L字右上（HLS 動画、TECH-VERIFICATION-ONLY）
│   └ entries-results-*.html  出走成績（3R/6R、screen8 6/6版準拠）
├ assets/css/
│   ├ style.css              ← 芥川様アセット。改変禁止（PreToolUse hook でブロックされる）
│   └ dos-overrides.css      ← デモ専用ヘルパー。独自追加はすべてここへ
├ assets/js/common.js        ← ポーリング・時刻補正・色判定・取消馬対応の共通基盤
├ schedules/ odds/ results/ changes/ ← 日付フォルダ配下の JSON
└ _tools/gen_data.py         ← データ再生成（NOW 基準で post_time を配置）
```

## 必須遵守事項

1. **`assets/css/style.css` は改変禁止**。独自追加は `dos-overrides.css` に書く（芥川様の正式対応で削除する前提）
2. **`px` 使用禁止**：`rem` 基準、`vw`/`vh`/`%` のみ（システム組み込み申し送り仕様書 §4 準拠）。iframe 内の vw/vh は iframe 自身基準（親ウィンドウ基準ではない）
3. **インライン style はカスタムプロパティ注入のみ**：`--horse-count` / `--row-count` / `grid-row` 等。色はクラス付与で、hex/rgb 直接注入禁止。例外：`single-screen.html` の `style="display:none;"`（frame ローテ機構の初期状態、意図的）
4. **フォント**：日本語 Yu Gothic UI、英数 Segoe UI（クラス側で指定済、上書きしない）
5. **`TECH-VERIFICATION-ONLY` マーカー**：権利処理未完コード（HLS 等）はマーカーで囲み `TECH_VERIFICATION_NOTES.md` に登録
6. **`TEMPORARY-MIGRATION-COMPAT` マーカー**：旧 4 桁 monitor URL 正規化等、本番移行時削除コード（`grep "TEMPORARY-MIGRATION-COMPAT"` で抽出）
7. **`common.js` を編集したら必ず `?v=` を bump**：子テンプレ 13 件の `common.js?v=` と `index.html` の buildChildQuery の v。怠ると iframe が旧版キャッシュを使う（`_saleContext` undefined 症状）
8. **`gen_data.py` を改修したら必ず lint**：`python -X utf8 <中央>/output/tools/payout_lint.py`（9 賭式 rank-aware 検証）が 0 NG になるまで完了としない
9. **賭式の表記ゆれ**：三連系は「3連複/3連単」数字表記。grep は表記ゆれ併記で検索

## データ再生成・ローカル確認

```bash
cd "C:/Users/oikawa.masafumi/Documents/GitHub/odds-demo/4screen-demo"
python -X utf8 _tools/gen_data.py        # デモ実演前推奨（NOW 基準で post_time 再配置）

# プレビュー: 中央司令所の launch.json 登録済み
mcp__Claude_Preview__preview_start name=odds-demo-github   # localhost:9876（これが唯一の正）
```

主要確認 URL（3 桁 monitor 形式）:

| URL | 内容 |
|---|---|
| `?monitor=101&fast=1&page_rotation=3` | 4 分割 3 スロット（column-major: P1=左上, P2=左下, P3=右上, P4=右下） |
| `?monitor=102&fast=1` | L字 → 1 画面 → 4 分割右下動画 の 3 スロット |
| `?monitor=105&fast=1` | PAT-4SPLIT-UMATAN（row-grouped） |
| `?monitor=106` / `107` | レース中止 / 開催中止 |
| `?monitor=117&fast=1` | 新潟 1R-12R 比較ビュー |
| `?monitor=118&fast=1` | 4 分割全パターン一覧 |
| `?monitor=128&fast=1` | 4K 出走成績 4 分割（2 場×1-12R、screen8 準拠） |

## スクリーンショット・4K 検証

- **HLS 動画フレーム活性時は preview_screenshot がハングしやすい**。回避：サーバ stop/start、または DOM eval で済ませる。確実に PNG が要るときは headless Chrome 直接実行：
  ```bash
  "C:/Program Files/Google/Chrome/Application/chrome.exe" --headless --disable-gpu \
    --window-size=1920,1080 --hide-scrollbars --virtual-time-budget=8000 \
    --screenshot="<中央>/output/scratch/<name>.png" "http://localhost:9876/index.html?monitor=NNN"
  ```
- **4K (3840×2160)**：`preview_resize width=3840 height=2160`。screenshot は timeout しがちなので DOM eval ベースで検証（root fontSize の比例拡縮 + `scrollWidth/Height ≤ clientWidth/Height`）
- 定型手順は中央司令所の `/demo-capture` skill を参照

## GitHub Pages 公開フロー

1. ローカルで `gen_data.py` 実行
2. https://github.com/deruca-systems/odds-demo の `4screen-demo/` に「Upload files」でアップロード
3. 数分で `https://deruca-systems.github.io/odds-demo/4screen-demo/` に反映

コミット規約は英語 Conventional Commits（`feat(schedule):` / `fix(payouts):` / `chore(deploy):` 等、本文に仕様章節を引用）。
