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
      // 2026-06-29 Phase 3: 手動切替・プレビュー経路（§3.12 / 2026-06-16 堀井さん確定契約）。
      //   通常=monitor_id / プレビュー=monitor_id+preview=1 / 手動切替=monitor_uuid。
      schedulePreview:      'schedules/preview/{YYYYMMDD}/{monitor_id}{fastSuffix}.json',
      scheduleManual:       'schedules/manual/{YYYYMMDD}/{monitor_uuid}.json',  // v0.6.2（日付フォルダあり）
      scheduleManualNoDate: 'schedules/manual/{monitor_uuid}.json',            // 内山設計書 v1.2（日付フォルダなし）
      odds:     'odds/{YYYYMMDD}/{ORG}_{PP}_{RR}.json',
      changes:  'changes/{YYYYMMDD}/{ORG}_{PP}.json'
    },

    // 手動切替パスの日付フォルダ有無 = **なし**（内山様 スケジュールJSON出力プログラム設計書 v1.2
    //   §3.1/§6.8.3 で確定。根拠: manual は monitor_uuid=VARCHAR(36) の CRM 発番 UUID 単位で大域一意
    //   のため日付フォルダ不要。「manual/ 配下に日付フォルダは挟まない」と明記）。
    //   プレビューは monitor_id 単位のため日付フォルダあり（v1.2 §6.8.2）。
    //   将来仕様が変わった場合のみ true（日付フォルダあり）に切替。
    manualScheduleHasDateFolder: false,

    // ------------------------------------------------------------
    // display_pattern_id 参照マップ（display_patternマスタ整理一覧_20260623.md §1）
    // ------------------------------------------------------------
    // 2026-06-29: display_pattern は **screen(セル)単位** の新ID へ全面移行。
    //   layout は slot.layout_pattern が持つため、本マップは display_pattern の
    //   表示名参照（デバッグ用）に用途を限定する。index.html の描画は
    //   screen.template（一次）/ DISPLAY_PATTERN_ID_TO_TEMPLATE（二次）で解決。
    //   gen_data.py の DISPLAY_PATTERN_NAMES と同期。
    patterns: {
      1:   { name: '単勝・複勝・枠連・枠単' },
      10:  { name: '馬連・ワイド（自動ページング）' },
      11:  { name: '馬連・ワイド①（P1）' },
      12:  { name: '馬連・ワイド②（P2）' },
      13:  { name: '馬連・ワイド③（P3）' },
      20:  { name: '馬連（自動ページング）' },
      21:  { name: '馬連①' },
      22:  { name: '馬連②' },
      30:  { name: '馬単（自動ページング）' },
      31:  { name: '馬単①' },
      32:  { name: '馬単②' },
      40:  { name: '人気順（自動ページング）' },
      41:  { name: '人気順①（1〜15位）' },
      42:  { name: '人気順②（16〜30位）' },
      50:  { name: '出走成績（自動ページング）' },
      51:  { name: '出走成績 1-3R' },
      52:  { name: '出走成績 4-6R' },
      53:  { name: '出走成績 7-9R' },
      54:  { name: '出走成績 10-12R' },
      60:  { name: '出走成績(4K用)（自動ページング）' },
      61:  { name: '出走成績(4K用) 1-6R' },
      62:  { name: '出走成績(4K用) 7-12R' },
      70:  { name: '変更情報' },
      80:  { name: 'レース動画（地方競馬LIVE）' },
      90:  { name: 'JRA動画（ch1 全場中継）' },
      91:  { name: 'JRA動画（ch2 パドック中継）' },
      92:  { name: 'JRA動画（ch3 関東主場中継）' },
      93:  { name: 'JRA動画（ch4 関西主場中継）' },
      94:  { name: 'JRA動画（ch5 第3場中継）' },
      100: { name: 'L字 左袖（出走表）' },
      101: { name: 'L字 右下（人気・ワイド人気 4賭式）' }
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
   * プレビュー用スケジュール URL（§3.12 / 2026-06-16 確定契約）。
   *   ?monitor_id=…&preview=1 → schedules/preview/{date}/{monitor_id}.json
   */
  w.DERUCA_CONFIG.buildPreviewScheduleUrl = function(displayDate, monitorId, fast) {
    var rel = w.DERUCA_CONFIG.paths.schedulePreview
      .replace('{YYYYMMDD}', String(displayDate))
      .replace('{monitor_id}', String(monitorId))
      .replace('{fastSuffix}', fast ? '_fast' : '');
    return w.DERUCA_CONFIG.buildUrl(rel);
  };

  /**
   * 手動切替用スケジュール URL（§3.12 / 2026-06-16 確定契約）。
   *   ?monitor_uuid=… → schedules/manual/.../{monitor_uuid}.json
   *   日付フォルダ有無は manualScheduleHasDateFolder フラグで切替（版ズレ未確定）。
   */
  w.DERUCA_CONFIG.buildManualScheduleUrl = function(displayDate, monitorUuid) {
    var tmpl = w.DERUCA_CONFIG.manualScheduleHasDateFolder
      ? w.DERUCA_CONFIG.paths.scheduleManual
      : w.DERUCA_CONFIG.paths.scheduleManualNoDate;
    var rel = tmpl
      .replace('{YYYYMMDD}', String(displayDate))
      .replace('{monitor_uuid}', String(monitorUuid));
    return w.DERUCA_CONFIG.buildUrl(rel);
  };

  /**
   * data_source（schedule JSON 内の相対パス）を解決して子 iframe に渡す URL を作る。
   *   baseUrl 空   → '../{data_source}' （templates/ からルートへ遡る、プロト挙動）
   *   baseUrl 有り → buildUrl で絶対 URL 化
   */
  w.DERUCA_CONFIG.resolveDataSource = function(dataSource) {
    if (!dataSource) return null;
    // 2026-08-01: 先頭スラッシュ付き（オリジン絶対パス）はそのまま返す。
    //   schedules JSON の signage_url は "/dos-signage/000003/....jpg" の形で来る
    //   （スケジュールJSON出力プログラム設計書 v1.7 §6.4.6）。従来は odds/... のような
    //   相対パスしか想定しておらず '../' を付けていたため、"..//dos-signage/..." という
    //   壊れた URL になり画像が 404 になっていた（STG 実データで確認）。
    //   絶対パスは baseUrl の有無にかかわらず解決不要。
    if (dataSource.charAt(0) === '/') return dataSource;
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
