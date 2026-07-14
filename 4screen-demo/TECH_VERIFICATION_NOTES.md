# TECH_VERIFICATION_NOTES.md

> **⚠ 2026-07-07 移設ノート**: 旧パスからの 2026-04-17 スナップショット移設。現状のマーカー箇所は `grep -rn "TECH-VERIFICATION-ONLY"` で再確認すること。

技術検証目的で組み込んだコードの管理ドキュメント。
マーカー `TECH-VERIFICATION-ONLY` が付いたブロックは本番実装前に除去または差し替えが必要。

最終更新: 2026-04-16
対象: 指示書09 CC指示_04_L字レイアウト動画組込

---

## マーカー一覧

| ファイル | 箇所 | 削除・差替理由 |
|--------|------|--------|
| `index.html` | `VIDEO_URL_BASE` 定数 | NAR との商用利用契約完了後、正式配信URLに差し替え |
| `index.html` | `VENUE_CODE_MAP` 定数 | 本番URLで各場コードを再検証・確定（現状 monbetsu/ooi/sonoda 以外は推測値） |
| `index.html` | `buildVideoUrl()` 関数 | 本番配信URLの確定後に実装を見直す |
| `index.html` | `configureVideoFrame()` 関数（applyFrames 内の video 分岐） | 同上 |
| `templates/video-frame.html` | hls.js CDN `<script src="https://cdn.jsdelivr.net/...">` タグ | 権利処理完了後、自社バンドルまたは契約CDNに変更 |
| `templates/video-frame.html` | `applyConfig()` 関数（BEGIN/END マーカー内） | 正式URL・hls.js 配信方法が確定したら実装見直し |
| `_tools/gen_data.py` | `DEV_VIDEO_SOURCE` 定数（Mux 公開テストストリーム） | 開発時の疎通確認用。NAR 正式URL稼働後は `build_schedule_0102()` の `video_source_override` 引数を削除し、VENUE_CODE_MAP 経由の本番URL組立に戻す |
| `data/schedule_0102.json`, `data/schedule_0102_fast.json` | video frame の `video_source_override` フィールド | 上記の実出力。gen_data.py から再生成するか、直接手動削除で OK |

---

## マーカー検索コマンド（将来の切替時に使用）

```bash
# Windows PowerShell
Select-String -Path src/odds-demo/**/*.html, src/odds-demo/**/*.js -Pattern "TECH-VERIFICATION-ONLY"

# macOS / Linux
grep -rn "TECH-VERIFICATION-ONLY" src/odds-demo/
```

---

## 本番切替時のチェックリスト

1. [ ] NAR との商用利用契約完了（玉澤社長確認）
2. [ ] 各開催場の HLS URL を実際に疎通確認（15場）
3. [ ] `VENUE_CODE_MAP` の全場コードを本番URLで確定
4. [ ] `VIDEO_URL_BASE` を正式ドメインに差し替え
5. [ ] hls.js を自社バンドル or 契約CDN へ切り替え（バージョン固定）
6. [ ] 全マーカー箇所を検索・除去または差し替え
7. [ ] 動作確認（4分割 / L字 / 1画面 の3レイアウトで1場ずつ疎通）
8. [ ] TECH_VERIFICATION_NOTES.md 自体を削除（または履歴に残す）
9. [ ] `templates/video-frame.html` の status 表示要素（`<div class="status" id="status">`）は
       デバッグ用途のため、本番では削除または CSS で非表示化する
       （`.status { display: none; }` 等）。`setStatus()` 呼出も併せて削除可。

---

## 関連ドキュメント

- 指示書: `docs/仕様書_specs/claude code実装指示/09_CC指示_04_L字レイアウト動画組込.md`
- HANDOFF: `src/odds-demo/HANDOFF.md`
- README: `src/odds-demo/README.md`
