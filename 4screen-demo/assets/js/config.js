/**
 * DERUCA Odds System - Runtime Configuration
 *
 * url-config-separation (2026-04-20):
 *   環境ごとに書き換える値（URL・パス・場コード対応）を本ファイルに集約。
 *   プロト起動では全てデフォルト値で動作する。本番環境へ切り替える際は、
 *   本ファイルのみを修正すれば足りる設計。
 *
 * 本番切替時の代表的な変更点:
 *   - baseUrl: 配信元 CloudFront ドメイン（例: 'https://odds.deruca.jp'）
 *              同一オリジン運用（HTML と JSON が同じオリジン）の場合は空文字列のまま。
 *   - video.urlBase: 実際の HLS 配信 URL（2026-04-20 時点で本番値が入っている）。
 *   - video.venueCodeMap: 検証済み場コードで書き換え。
 *
 * 読み込み順序: index.html で common.js よりも**前**に <script> 読み込みすること。
 */
(function(w) {
  'use strict';

  w.DERUCA_CONFIG = {
    // ------------------------------------------------------------
    // JSON 配信の Base URL
    // ------------------------------------------------------------
    // 空文字列 = ページ相対 / オリジン相対（プロトタイプのデフォルト）。
    // 本番で別ドメイン配信する場合は末尾スラッシュなしで設定:
    //   baseUrl: 'https://odds.deruca.jp'
    // 末尾スラッシュの調整は buildUrl が吸収する。
    baseUrl: '',

    // ------------------------------------------------------------
    // JSON パステンプレート（v0.5 §1.5 準拠）
    // ------------------------------------------------------------
    // プレースホルダ:
    //   {YYYYMMDD}   display_date
    //   {monitor_id} INT（ゼロ埋めなし）
    //   {ORG}        'JRA' / 'NAR'
    //   {PP}         2桁ゼロ埋め
    //   {RR}         2桁ゼロ埋め
    //   {fastSuffix} '_fast' or ''（スケジュールのみ）
    //
    // フロントが直接組み立てるのは schedule のみ。
    // odds / changes は schedule JSON の data_source 経由で取得するため、
    // ここでは参考値として保持する（将来的なテスト用途等）。
    paths: {
      schedule: 'schedules/{YYYYMMDD}/{monitor_id}{fastSuffix}.json',
      odds:     'odds/{YYYYMMDD}/{ORG}_{PP}_{RR}.json',
      changes:  'changes/{YYYYMMDD}/{ORG}_{PP}.json'
    },

    // ------------------------------------------------------------
    // display_pattern_id 参照マップ（v0.5 §1.3.1 INT → パターン情報）
    // ------------------------------------------------------------
    // display-pattern-id-numeric (2026-04-20): v0.5 §1.3.1 で display_pattern_id は INT。
    //   index.html の描画は slot.screens[].template を直接使うため本マップを参照しないが、
    //   新メンバーのデバッグ・カスタムロジック実装時の参照用として保持。
    //   DB 側 display_pattern_id 確定時（v0.5 付録B）は本マップを更新。
    //   gen_data.py の DISPLAY_PATTERN_NUMERIC_IDS と同期。
    patterns: {
      1: { name: '4分割標準',          layout: '4split'  },
      2: { name: '4分割馬連馬単',      layout: '4split'  },
      3: { name: 'L字+動画',           layout: 'lshape'  },
      4: { name: '1画面動画',          layout: '1screen' },
      5: { name: '4分割右下動画',      layout: '4split'  },
      // 3R-entries-results-phase2 (2026-04-21): 出走成績 3R 表示
      10: { name: '3R出走成績',        layout: '1screen' }
    },

    // ------------------------------------------------------------
    // 動画 (HLS) 配信設定
    // ------------------------------------------------------------
    // 旧 index.html の `// === BEGIN: TECH-VERIFICATION-ONLY ===` ブロックを
    // 集約したもの。権利処理未完了のため、商用利用契約後に正式 URL を設定する運用。
    video: {
      // HLS マスタープレイリストの URL ベース（末尾スラッシュ込み）
      // 例: 'https://movie61auhrn2-3.keiba-racing.jp/keiba/nar/live/' → NAR 本番
      //
      // 2026-04-17 修正: パスを `/hls-live/keiba/_definst_/liveevent/` → `/keiba/nar/live/` に変更。
      //   旧パスはサブプレイリスト（各品質）用で、マスタープレイリスト
      //   （EXT-X-STREAM-INF）は新パス `/keiba/nar/live/` に存在する。
      //   参考: simple.keiba-lv-st.jp が使用している URL =
      //     https://movie61auhrn2-3.keiba-racing.jp/keiba/nar/live/ooi_https.m3u8
      urlBase: 'https://movie61auhrn2-3.keiba-racing.jp/keiba/nar/live/',

      // schedule JSON の video_config.venue_code → HLS URL 用場コードの対応表
      // key: v0.5 §3.7 video_config.venue_code（スキーマ側の識別子）
      // value: HLS URL 内に含まれる場コード
      // 未知の venue_code は buildVideoUrl で null を返し、console.error を出す。
      venueCodeMap: {
        'monbetsu':  'monbetsu',   // 門別（確認済）
        'ooi':       'ooi',        // 大井（確認済）
        'sonoda':    'sonoda',     // 園田（VOD URL 推測）
        // 以下は推測。本番稼働前に実際の URL で検証必要。
        'obihiro':   'obihiro',
        'morioka':   'morioka',
        'mizusawa':  'mizusawa',
        'urawa':     'urawa',
        'funabashi': 'funabashi',
        'kawasaki':  'kawasaki',
        'kanazawa':  'kanazawa',
        'kasamatsu': 'kasamatsu',
        'nagoya':    'nagoya',
        'himeji':    'himeji',
        'kouchi':    'kouchi',
        'saga':      'saga'
      }
    }
  };

  // ------------------------------------------------------------
  // ヘルパ関数
  // ------------------------------------------------------------

  /**
   * 相対パスを baseUrl と結合して URL を作る。
   *   baseUrl 空文字 → 相対パスそのまま返す（プロトタイプ挙動、ページ相対解決）
   *   baseUrl 有り  → 末尾/先頭スラッシュを調整して連結
   */
  w.DERUCA_CONFIG.buildUrl = function(relPath) {
    var base = w.DERUCA_CONFIG.baseUrl || '';
    if (!base) return relPath;
    if (base.charAt(base.length - 1) === '/') base = base.slice(0, -1);
    var rel = relPath.charAt(0) === '/' ? relPath.slice(1) : relPath;
    return base + '/' + rel;
  };

  /**
   * スケジュール JSON の相対パスを組み立てる。
   *   displayDate: 'YYYYMMDD' 文字列（8桁）
   *   monitorId:   integer or string（ゼロ埋めなし）
   *   fast:        boolean（true なら '_fast' サフィックス付与）
   */
  w.DERUCA_CONFIG.buildSchedulePath = function(displayDate, monitorId, fast) {
    return w.DERUCA_CONFIG.paths.schedule
      .replace('{YYYYMMDD}', String(displayDate))
      .replace('{monitor_id}', String(monitorId))
      .replace('{fastSuffix}', fast ? '_fast' : '');
  };

  /**
   * スケジュール JSON のフル URL を返す（buildSchedulePath + buildUrl）
   */
  w.DERUCA_CONFIG.buildScheduleUrl = function(displayDate, monitorId, fast) {
    return w.DERUCA_CONFIG.buildUrl(
      w.DERUCA_CONFIG.buildSchedulePath(displayDate, monitorId, fast)
    );
  };

  /**
   * data_source（schedule JSON 内の相対パス）を解決して子 iframe に渡す URL を作る。
   *   baseUrl 空   → '../{data_source}' （templates/ からルートへ遡る、プロト挙動）
   *   baseUrl 有り → buildUrl で絶対 URL 化
   */
  w.DERUCA_CONFIG.resolveDataSource = function(dataSource) {
    if (!dataSource) return null;
    if (w.DERUCA_CONFIG.baseUrl) {
      return w.DERUCA_CONFIG.buildUrl(dataSource);
    }
    // プロト: 同一オリジン、templates/*.html から ../ でルートへ遡る
    return '../' + dataSource;
  };

  /**
   * 動画 HLS URL を組み立てる（旧 buildVideoUrl の置換）。
   *   frame: schedule JSON の video_config 相当
   *          （venue_code, quality_mode, quality_fixed, video_source_override を含む）
   */
  w.DERUCA_CONFIG.buildVideoUrl = function(frame) {
    if (frame.video_source_override) return frame.video_source_override;
    var venueCode = w.DERUCA_CONFIG.video.venueCodeMap[frame.venue_code];
    if (!venueCode) {
      console.error('Unknown venue_code:', frame.venue_code);
      return null;
    }
    if (frame.quality_mode === 'fixed' && frame.quality_fixed) {
      return w.DERUCA_CONFIG.video.urlBase + venueCode + frame.quality_fixed + '.m3u8';
    }
    // auto モード: マスタープレイリスト
    return w.DERUCA_CONFIG.video.urlBase + venueCode + '_https.m3u8';
  };

})(window);
