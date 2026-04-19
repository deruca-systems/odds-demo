/**
 * 4画面JSONポーリングサンプル - 子テンプレート共通ユーティリティ
 *
 * 申し送り仕様書のクラス命名・CSS変数注入ルールに準拠。
 *  - row-* / number-* / block-* / body-* / win-popular / win-secondary / place-popular /
 *    value-popular / odds-popular / odds-unpopular / unpopular / weight-long / weight-diff / minute
 *  - インラインstyleは --horse-count / --name-length のCSS変数注入のみ
 *  - 色やサイズは必ずクラス付与で制御
 */

// ---- 共通定数 ----
// C-01 (2026-04-17): 本番デフォルト30秒（全画面リスト v1.0【3/10確定事項】「オッズ画面更新頻度：30秒」）。
// URLクエリ ?fast=1 が付いているときだけ 10秒 に短縮（デモ実演用モード。スロット短縮版と同時連動）。
// 個別上書き ?poll=秒 は下記 applyPollQuery() で最優先に扱う。
var POLL_INTERVAL_MS = 30000; // 子テンプレのポーリング間隔（?fast=1 で10秒、?poll=秒 で任意上書き）

// ---- 締切／カットイン制御用定数 ----
// 表示上の締切時刻 = post_time - DEADLINE_BEFORE_POST_MIN分 - DEADLINE_SAFETY_MARGIN_SEC秒
// （客体験保護のため、実際の投票締切より DEADLINE_SAFETY_MARGIN_SEC 秒早く締切表示を出す）
// C-02 (2026-04-17): カットイン表示秒数の仕様値を 30秒 → 10秒 に変更。
//   及川の実機確認で「30秒は長すぎ、オッズ画面の視認時間が相対的に短くなる」と判断。
//   10秒は告知効果とオッズ視認時間のバランスとして最適と判断した。
//   ★要確認: 次回MTGで正式議事録化予定（2026-04-17 時点では及川の決定権で確定済）。
//   URLクエリ ?cutin_sec=N で個別上書き可（開発検証・仕様再評価用）。
//   C-01 のポーリング切替とは独立制御（案1: 定数+URLクエリのみ、シンプル採用）。
var CUTIN_DISPLAY_SEC = 10;             // カットイン表示秒数（正式仕様10秒、?cutin_sec=N で上書き可）
var DEADLINE_BEFORE_POST_MIN = 2;       // 発走何分前を「投票締切」とするか（実業務）
var DEADLINE_SAFETY_MARGIN_SEC = 30;    // 表示を実締切より何秒早めるか（URLクエリ ?safety_margin_sec=N で上書き可）
var COUNTDOWN_START_MIN = 5;            // 表示締切何分前からカットイン CUT-001 を出すか
var COUNTDOWN_HEADER_START_MIN = 10;    // 表示締切何分前からヘッダーを「発走 HH:MM」→「締切N分前」に切替えるか

// C-01 (2026-04-17): fast=1 連動（デモ用モード：ポーリングも10秒に短縮）。
// 個別上書き ?poll=秒 が後段で最優先になる。
(function applyFastAndPollQuery() {
  try {
    var sp = new URL(location.href).searchParams;
    if (sp.get('fast') === '1' || sp.get('fast') === 'true') {
      POLL_INTERVAL_MS = 10000;
    }
    var q = sp.get('poll');
    if (q) {
      var n = Number(q);
      if (isFinite(n) && n >= 1) POLL_INTERVAL_MS = n * 1000;
    }
  } catch (_) {}
})();

(function applyCutinQuery() {
  try {
    var q = new URL(location.href).searchParams.get('cutin_sec');
    if (q) {
      var n = Number(q);
      if (isFinite(n) && n >= 1) CUTIN_DISPLAY_SEC = n;
    }
  } catch (_) {}
})();

(function applySafetyMarginQuery() {
  try {
    var q = new URL(location.href).searchParams.get('safety_margin_sec');
    if (q != null && q !== '') {
      var n = Number(q);
      if (isFinite(n) && n >= 0) DEADLINE_SAFETY_MARGIN_SEC = n;
    }
  } catch (_) {}
})();

/**
 * post_time からの「表示上の締切時刻（ミリ秒）」を算出。
 * 表示締切 = post_time - DEADLINE_BEFORE_POST_MIN分 - DEADLINE_SAFETY_MARGIN_SEC秒
 * computeDeadline と checkCutin の両方で同じ基準を使うための共通ヘルパ。
 */
function effectiveDeadlineMs(postMs) {
  return postMs - (DEADLINE_BEFORE_POST_MIN * 60 + DEADLINE_SAFETY_MARGIN_SEC) * 1000;
}

// ---- カットイン表示状態 ----
var cutinState = {
  active: false,
  type: null,         // 'countdown' or 'closed'
  hideTimer: null,
  shownForRace: null  // 同一レースで重複表示しないためのキー（"{venue}{race_no}_{type}"）
};

// 枠番→クラス名マップ
var FRAME_ROW_CLASS = {
  1: 'row-white',  2: 'row-black', 3: 'row-red',   4: 'row-blue',
  5: 'row-yellow', 6: 'row-green', 7: 'row-orange', 8: 'row-pink'
};
var FRAME_BLOCK_CLASS = {
  1: 'block-white',  2: 'block-black', 3: 'block-red',   4: 'block-blue',
  5: 'block-yellow', 6: 'block-green', 7: 'block-orange', 8: 'block-pink'
};
var FRAME_BODY_CLASS = {
  1: 'body-white',  2: 'body-black', 3: 'body-red',   4: 'body-blue',
  5: 'body-yellow', 6: 'body-green', 7: 'body-orange', 8: 'body-pink'
};
var FRAME_NUMBER_CLASS = {
  1: 'number-white',  2: 'number-black', 3: 'number-red',   4: 'number-blue',
  5: 'number-yellow', 6: 'number-green', 7: 'number-orange', 8: 'number-pink'
};

// 天候ラベル→アイコンファイル名
var WEATHER_ICON = {
  'sunny': 'sunny.svg',
  'cloudy': 'cloudy.svg',
  'rain': 'rain.svg',
  'light-rain': 'light-rain.svg',
  'snow': 'snow.svg',
  'light-snow': 'light-snow.svg'
};

// ---- フォーマッタ ----
function fmtOdds(v) {
  if (v === null || v === undefined) return '';
  if (v >= 999.9) return '999.9';
  return Number(v).toFixed(1);
}

function fmtWeightDiff(diff) {
  if (diff === null || diff === undefined) return '(0)';
  if (typeof diff === 'string') return '(' + diff + ')';
  if (diff > 0) return '(+' + diff + ')';
  if (diff < 0) return '(' + diff + ')';
  return '(0)';
}

function frameClassOf(frameNo, kind) {
  var map = kind === 'block' ? FRAME_BLOCK_CLASS :
            kind === 'body'  ? FRAME_BODY_CLASS  :
            kind === 'num'   ? FRAME_NUMBER_CLASS : FRAME_ROW_CLASS;
  return map[frameNo] || '';
}

function frameOfHorse(horses, horseNo) {
  for (var i = 0; i < horses.length; i++) {
    if (horses[i].horse_no === horseNo) return horses[i].frame_no;
  }
  return 1;
}

// ---- 取消馬対応（指示書08） ----
// is_scratched: 0=正常 / 1=出走取消 / 2=競走除外
/**
 * 取消馬のラベル文字列を返す。
 * 指示書08 v2 改訂: 単勝+複勝を結合した1セルに表示する方針に伴い、
 * 「取消」「除外」→「出走取消」「競走除外」に変更（ユーザー要望 2026-04-16）。
 * @param {number} isScratched - 0/1/2
 * @returns {string} '' | '出走取消' | '競走除外'
 */
function scratchedLabel(isScratched) {
  if (isScratched === 1) return '出走取消';
  if (isScratched === 2) return '競走除外';
  return '';
}

/**
 * 取消馬の短縮ラベル文字列。
 * 人気順画面（.popular）は単勝セル幅 6.3rem に収まらないため、2文字表記を使う。
 * @param {number} isScratched - 0/1/2
 * @returns {string} '' | '取消' | '除外'
 */
function scratchedLabelShort(isScratched) {
  if (isScratched === 1) return '取消';
  if (isScratched === 2) return '除外';
  return '';
}

/**
 * horses 配列から取消馬の horse_no セットを構築
 * @param {Array} horses
 * @returns {Object} { horse_no: true, ... }
 */
function buildScratchedSet(horses) {
  var set = {};
  (horses || []).forEach(function(h) {
    if (h.is_scratched) set[h.horse_no] = true;
  });
  return set;
}

/**
 * 人気順リスト（umaren_popular/umatan_popular/trio_popular/trifecta_popular）から
 * 取消馬を含むエントリを除外する。表示側の防御的フィルタで、JSON生成側が既に
 * 除外していれば何も削らない。
 *
 * @param {Array} list - [{rank, a, b, [c], odds, is_popular}, ...]
 * @param {Array} horses
 * @param {number} combSize - 2 or 3
 */
function filterScratchedFromPopular(list, horses, combSize) {
  var scratchedSet = buildScratchedSet(horses);
  var keys = combSize === 2 ? ['a', 'b'] : ['a', 'b', 'c'];
  return (list || []).filter(function(entry) {
    for (var i = 0; i < keys.length; i++) {
      if (scratchedSet[entry[keys[i]]]) return false;
    }
    return true;
  });
}

// ---- 自動オッズ色付けルール ----
// 単勝オッズから「人気」「次点」判定を算出（JSONのis_popular/is_secondaryは使わない）
// ルール:
//   win-popular: 単勝オッズ昇順 上位3頭
//   win-secondary: 4〜5位
// 取消馬（is_scratched != 0）は対象から除外する（指示書08）。
function computeWinClasses(horses) {
  var active = (horses || []).filter(function(h) { return !h.is_scratched; });
  var sorted = active.slice().sort(function(a, b) { return a.win_odds - b.win_odds; });
  var cls = {};
  sorted.forEach(function(h, idx) {
    if (idx < 3) cls[h.horse_no] = 'win-popular';
    else if (idx < 5) cls[h.horse_no] = 'win-secondary';
  });
  return cls; // { horse_no: class }
}

// 複勝オッズmin/maxそれぞれの上位50%に place-popular を付ける
// 取消馬（is_scratched != 0）は対象から除外する（指示書08）。
function computePlaceClasses(horses) {
  var active = (horses || []).filter(function(h) { return !h.is_scratched; });
  var mins = active.map(function(h) { return h.place_odds_min; }).sort(function(a, b) { return a - b; });
  var maxs = active.map(function(h) { return h.place_odds_max; }).sort(function(a, b) { return a - b; });
  var minThreshold = mins.length > 0 ? mins[Math.ceil(mins.length / 2) - 1] : Infinity;
  var maxThreshold = maxs.length > 0 ? maxs[Math.ceil(maxs.length / 2) - 1] : Infinity;
  var res = {};
  (horses || []).forEach(function(h) {
    if (h.is_scratched) {
      res[h.horse_no] = { minPopular: false, maxPopular: false };
    } else {
      res[h.horse_no] = {
        minPopular: h.place_odds_min <= minThreshold,
        maxPopular: h.place_odds_max <= maxThreshold
      };
    }
  });
  return res;
}

// 枠連: 下位5件に value-popular
function computeFramePopular(frameOdds) {
  var sorted = frameOdds.slice().sort(function(a, b) { return a.odds - b.odds; });
  var pop = {};
  sorted.slice(0, 5).forEach(function(e) { pop[e.frame_a + '-' + e.frame_b] = true; });
  return pop;
}

// ---- H-03 (2026-04-19): 枠単マトリクス描画 ----
// 仕様: wrapper 内に 2つの body を生成（上段=軸枠1-4、下段=軸枠5-8）。
// 各 body は「frame 列（ヘッダー9セル）+ 4枠分の block（各9セル）」の5カラム grid。
// block 内: label（軸枠）+ frame 1〜8 のオッズ 8セル = 9行。
// umatanData: race.frame_umatan（8×8=64件の配列）
// wrapperEl:  '.frame-umatan__wrapper' 要素
function renderFrameUmatan(umatanData, wrapperEl) {
  if (!wrapperEl) return;
  var matrix = {};
  (umatanData || []).forEach(function(d) {
    matrix[d.frame_a + '-' + d.frame_b] = d;
  });

  var frag = document.createDocumentFragment();

  // 上段（1-4枠）・下段（5-8枠）の2 body
  [[1, 2, 3, 4], [5, 6, 7, 8]].forEach(function(frameGroup) {
    var body = el('div', 'frame-umatan__body');

    // 列ヘッダー（frame 列）: 空セル + 1〜8
    var frameRow = el('div', 'frame-umatan__frame');
    frameRow.appendChild(el('div', 'frame-umatan__number'));
    for (var fb = 1; fb <= 8; fb++) {
      frameRow.appendChild(el('div', 'frame-umatan__number', fb));
    }
    body.appendChild(frameRow);

    // 軸枠ごとの block
    frameGroup.forEach(function(fa) {
      var blockCls = FRAME_BLOCK_CLASS[fa] || '';
      var block = el('div', 'frame-umatan__block ' + blockCls);
      block.appendChild(el('div', 'frame-umatan__label', fa));
      for (var fb2 = 1; fb2 <= 8; fb2++) {
        var entry = matrix[fa + '-' + fb2];
        var item = el('div', 'frame-umatan__item');
        if (entry) {
          item.textContent = fmtOdds(entry.odds);
          if (entry.is_popular) item.classList.add('value-popular');
        } else {
          item.textContent = '-';
        }
        block.appendChild(item);
      }
      body.appendChild(block);
    });

    frag.appendChild(body);
  });

  wrapperEl.replaceChildren(frag);
}

// 人気順テーブル: 上位3件に odds-popular
function isTopPopular(rank) { return rank <= 3; }

// 馬連ワイド: umaren オッズが 1000倍以上 → unpopular（非人気強調）
function isUmarenUnpopular(odds) { return odds >= 1000; }

// ---- 共通ヘッダーレンダラー（race-title と race-info を更新） ----
// opts = { mode, correctedNowMs }
//   mode: 'full' | 'previous-day' | 'popular-fixed'
//     'full'          … 天候・馬場・発走/締切 をrace-infoとして表示
//     'previous-day'  … 「前日発売」ラベルを表示（race-infoは非表示）
//     'popular-fixed' … 常に前日発売ラベル
//   correctedNowMs: 補正済み現在時刻(ms)。post_time からの deadline 動的算出に使用
function renderRaceHeader(doc, race, opts) {
  opts = opts || {};
  var mode = opts.mode || 'full';
  if (race && race.is_previous_day) mode = 'previous-day';

  setText(doc.querySelector('#hdr-venue'), race.venue || '');
  setRaceNumber(doc.querySelector('#hdr-race'), race.race_no);
  setText(doc.querySelector('#hdr-raceName'), race.race_name || '');
  setText(doc.querySelector('#hdr-raceClass'), race.race_class || '');

  var raceInfo = doc.querySelector('.race-info');
  var prevDay = doc.querySelector('.previous-day');

  if (mode === 'full') {
    if (raceInfo) raceInfo.classList.remove('is-hidden');
    if (prevDay)  prevDay.classList.add('is-hidden');
    var icon = doc.querySelector('#hdr-weatherIcon');
    if (icon) {
      icon.src = '../assets/images/weather/' + (WEATHER_ICON[race.weather] || 'sunny.svg');
      icon.alt = race.weather_label || '';
    }
    setText(doc.querySelector('#hdr-weatherLabel'), race.weather_label || '');
    setText(doc.querySelector('#hdr-condition'),   race.condition || '');
    setText(doc.querySelector('#hdr-surface'),     race.surface || '');
    setText(doc.querySelector('#hdr-distance'),    (race.distance || '') + 'm');
    setText(doc.querySelector('#hdr-direction'),   '(' + (race.direction || '') + ')');

    // ヘッダー右側（.race-time）の表示を時刻依存で動的に切替:
    //   pre       — 表示締切 COUNTDOWN_HEADER_START_MIN 分より前: 「発走 HH:MM」
    //   countdown — 表示締切 COUNTDOWN_HEADER_START_MIN 分以内:   「締切 N 分前」
    //   closed    — 表示締切到達以降:                             「発売締切」
    // .race-time 内の子要素は JS が innerHTML で書き換える（テンプレート側の初期HTMLは起動時上書きされる）
    var dl = null;
    if (opts.correctedNowMs != null) {
      dl = computeDeadline(race.post_time_iso || race.post_time, opts.correctedNowMs);
    }
    var raceTime = doc.querySelector('.race-time');
    if (raceTime) {
      var rtMode;
      if (dl && dl.is_closed) {
        rtMode = 'closed';
      } else if (dl && dl.remaining_sec != null && dl.remaining_sec <= COUNTDOWN_HEADER_START_MIN * 60) {
        rtMode = 'countdown';
      } else {
        rtMode = 'pre';
      }
      // innerHTML 書き換えは mode 変化時のみ（描画コスト節約＆無用なレイアウト揺れ防止）
      if (raceTime.dataset.mode !== rtMode) {
        if (rtMode === 'closed') {
          raceTime.innerHTML = '<span class="minute" id="hdr-deadline">発売締切</span>';
        } else if (rtMode === 'countdown') {
          raceTime.innerHTML = '<span>締切</span><span class="minute" id="hdr-deadline"></span><span>分前</span>';
        } else {
          raceTime.innerHTML = '<span>発走</span><span class="minute" id="hdr-postTime"></span>';
        }
        raceTime.dataset.mode = rtMode;
      }
      // 値の更新（mode ごとに参照先が異なる）
      if (rtMode === 'countdown') {
        var dlEl = doc.querySelector('#hdr-deadline');
        if (dlEl && dl && dl.deadline_min != null) setText(dlEl, String(dl.deadline_min));
      } else if (rtMode === 'pre') {
        var ptEl = doc.querySelector('#hdr-postTime');
        if (ptEl) setText(ptEl, race.post_time || '');
      }
      // 状態クラス（is-closed = CSS で両側ラベル非表示、is-closing = 1分前点滅）
      raceTime.classList.toggle('is-closed', rtMode === 'closed');
      raceTime.classList.toggle('is-closing', !!(dl && dl.is_closing));
      // 芥川様 CSS (.race-time.start { background: #0D1117 }) に合わせて、発走時刻表示
      // （rtMode=pre = 「発走 HH:MM」）の時だけ .start クラスを付与。countdown/closed
      // 時は外して既定背景（demo-helpers.css 側で data-mode=countdown/closed の赤グラデ）
      // に戻す。
      raceTime.classList.toggle('start', rtMode === 'pre');
    }
  } else if (mode === 'previous-day' || mode === 'popular-fixed') {
    if (raceInfo) raceInfo.classList.add('is-hidden');
    if (prevDay)  prevDay.classList.remove('is-hidden');
  }
}

// レース番号をテキストノード直下に流し込む（元HTMLの <span class="race">12<span>R</span></span> を維持）
function setRaceNumber(raceEl, num) {
  if (!raceEl) return;
  var s = String(num == null ? '' : num);
  // 先頭テキストノードを確保
  if (!raceEl.firstChild || raceEl.firstChild.nodeType !== Node.TEXT_NODE) {
    raceEl.insertBefore(document.createTextNode(''), raceEl.firstChild || null);
  }
  if (raceEl.firstChild.nodeValue !== s) raceEl.firstChild.nodeValue = s;
}

// ---- 発走時刻から締切情報を動的算出 ----
// postTime: "HH:MM" 文字列 または ISO 8601 文字列
// correctedNowMs: 補正済み現在時刻(ms)
// 「締切」は「表示上の締切時刻」を指す（post_time - DEADLINE_BEFORE_POST_MIN分 - DEADLINE_SAFETY_MARGIN_SEC秒）。
// 実際の投票締切より DEADLINE_SAFETY_MARGIN_SEC 秒早く is_closed に入るため、客が
// 「画面上まだ締切と出ていないのに券売機で締切」という体験を防ぐ。
// 戻り値: {
//   deadline_min: number  // 表示締切までの残り分（切り上げ。0以上）
//   remaining_sec: number // 表示締切までの残り秒（マイナス含む、= 締切到達後は負）
//   is_approaching: bool  // 表示締切 COUNTDOWN_START_MIN(=5)分前以内
//   is_closing: bool      // 表示締切 1分前以内（点滅演出用）
//   is_closed: bool       // 表示締切到達（= 実締切より DEADLINE_SAFETY_MARGIN_SEC 秒早い）
// }
function computeDeadline(postTime, correctedNowMs) {
  if (!postTime) {
    return { deadline_min: null, remaining_sec: null, is_approaching: false, is_closing: false, is_closed: false };
  }
  var postMs;
  if (/\d{4}-\d{2}-\d{2}T/.test(postTime)) {
    postMs = Date.parse(postTime);
  } else {
    // "HH:MM" 形式: 今日（補正時刻ベース）の HH:MM として解釈
    var m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(postTime);
    if (!m) return { deadline_min: null, remaining_sec: null, is_approaching: false, is_closing: false, is_closed: false };
    var ref = new Date(correctedNowMs);
    var d = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate(),
                     Number(m[1]), Number(m[2]), Number(m[3] || 0));
    postMs = d.getTime();
    // 深夜跨ぎ補正: postMs が correctedNow より10時間以上過去なら翌日扱い
    if (postMs < correctedNowMs - 10 * 3600 * 1000) {
      postMs += 24 * 3600 * 1000;
    }
  }
  if (isNaN(postMs)) {
    return { deadline_min: null, remaining_sec: null, is_approaching: false, is_closing: false, is_closed: false };
  }
  var deadlineMs = effectiveDeadlineMs(postMs);
  var remainingSec = Math.floor((deadlineMs - correctedNowMs) / 1000);
  var isClosed = remainingSec <= 0;
  var deadlineMin = isClosed ? 0 : Math.ceil(remainingSec / 60);
  return {
    deadline_min: deadlineMin,
    remaining_sec: remainingSec,
    is_approaching: !isClosed && remainingSec <= COUNTDOWN_START_MIN * 60,
    is_closing: !isClosed && remainingSec <= 60,
    is_closed: isClosed
  };
}

// ---- fetch with server-time offset（ただしデモでは「初回だけ」offset確定が推奨） ----
// timeoutMs（既定10秒）で AbortController によるタイムアウトを発動。
// 指示書07 のエラーハンドリング仕様で「タイムアウトも失敗」として扱う。
async function fetchWithOffset(url, timeoutMs) {
  timeoutMs = timeoutMs || 10000;
  var t0 = Date.now();
  var controller = new AbortController();
  var timer = setTimeout(function() { controller.abort(); }, timeoutMs);
  try {
    var res = await fetch(url + '?t=' + t0, { signal: controller.signal });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    var data = await res.json();
    var t1 = Date.now();
    var clientTime = t0 + (t1 - t0) / 2;
    var serverOffset = 0;
    if (data && data.server_time) {
      var srv = Date.parse(data.server_time);
      if (!isNaN(srv)) serverOffset = srv - clientTime;
    }
    return { data: data, serverOffset: serverOffset };
  } finally {
    clearTimeout(timer);
  }
}

// ---- ポーリング共通: 指数バックオフ付きリトライ（指示書07 準拠） ----
//
// 指数バックオフ倍率:
//   failCount=0/1 → ×1, =2 → ×2, =3 → ×4, =4 → ×8, ≥5 → ×12（上限）
// 成功したらカウンタ即リセット。
// fetch 失敗時は render() を呼ばず、既存 lastData のままにして画面維持。
//
// opts:
//   fetch:        () => Promise<any>         fetch 実行関数（成功時 resolve、失敗時 reject）
//   onSuccess:    (result) => void           成功コールバック（render 等）
//   onFailure:    (err, failCount) => void   失敗コールバック（status 更新等、任意）
//   baseIntervalMs: number                   基本間隔（ミリ秒）
//   maxMultiplier:  number                   最大倍率（既定12）
//   name:          string                    ログ識別用
// 戻り値: { stop(), getStatus() }

function startResilientPolling(opts) {
  var baseMs = opts.baseIntervalMs;
  var maxMult = opts.maxMultiplier || 12;
  var name = opts.name || 'poller';
  var failCount = 0;
  var lastSuccessTime = null;
  var lastErrorMessage = null;
  var lastErrorTime = null;
  var stopped = false;
  var timer = null;

  function multiplierFor(fc) {
    if (fc <= 0) return 1;
    if (fc === 1) return 1;
    if (fc === 2) return 2;
    if (fc === 3) return 4;
    if (fc === 4) return 8;
    return maxMult;
  }

  async function tick() {
    if (stopped) return;
    try {
      var result = await opts.fetch();
      failCount = 0;
      lastSuccessTime = Date.now();
      try { opts.onSuccess(result); } catch (renderErr) {
        console.error('[' + name + '] onSuccess error:', renderErr);
      }
    } catch (err) {
      failCount++;
      lastErrorMessage = err && err.message ? err.message : String(err);
      lastErrorTime = Date.now();
      console.error('[' + name + '] poll error (count=' + failCount + '):', err);
      if (opts.onFailure) {
        try { opts.onFailure(err, failCount); } catch (_) {}
      }
    }
    if (stopped) return;
    var wait = baseMs * multiplierFor(failCount);
    timer = setTimeout(tick, wait);
  }

  // 初回即時実行
  tick();

  return {
    stop: function() {
      stopped = true;
      if (timer) { clearTimeout(timer); timer = null; }
    },
    getStatus: function() {
      return {
        name: name,
        failCount: failCount,
        lastSuccessTime: lastSuccessTime,
        lastErrorMessage: lastErrorMessage,
        lastErrorTime: lastErrorTime,
        nextWaitMs: baseMs * multiplierFor(failCount),
        stopped: stopped
      };
    }
  };
}

// 全 poller の状態を集約取得するためのレジストリ。
// 将来の管理画面連携（heartbeat/ビーコン送信）用の基盤。
var _pollerRegistry = [];
function registerPoller(poller) {
  _pollerRegistry.push(poller);
}
function getAllPollerStatus() {
  return _pollerRegistry.map(function(p) { return p.getStatus(); });
}
// DevTools の Console から `OddsDemo.dumpPollerStatus()` で全 poller 状態を表形式で確認。
function dumpPollerStatus() {
  var statuses = getAllPollerStatus();
  if (typeof console.table === 'function') {
    console.table(statuses);
  } else {
    console.log(statuses);
  }
  return statuses;
}

// ---- DOM ヘルパ ----
function setText(el, v) {
  if (!el) return;
  var s = String(v == null ? '' : v);
  if (el.textContent !== s) el.textContent = s;
}

function el(tag, className, text) {
  var e = document.createElement(tag);
  if (className) e.className = className;
  if (text != null) e.textContent = String(text);
  return e;
}

// 馬連ワイドの分割アルゴリズム（Excel「馬連・ワイド画面の分割基準.xlsx」準拠・完全確定仕様）:
//
//   ページ数:
//     5〜 8頭 → 1 ページ
//     9〜14頭 → 2 ページ
//    15〜18頭 → 3 ページ
//
//   軸の配置ルール（4列 × 上下2段）:
//     nAxes   = N - 1                 （軸の総数。馬番Nは相手がいないので軸にならない）
//     nPages  = ページ数              （上表）
//     nTop    = nPages * 4            （上段軸の総数）
//     pairSum = nTop * 2 + 1          （上段軸番号 + 下段軸番号 の合計値）
//
//     1 ページ = 4 列。列 c（0..3）:
//       topAxis      = p * 4 + c + 1                 （上段は若番から順）
//       botCandidate = pairSum - topAxis             （下段は pairSum - 上段 で対称）
//       botAxis      = botCandidate              ただし、以下条件を両方満たす場合のみ配置
//                      (botCandidate <= nAxes) AND (botCandidate > nTop)
//                      → 下段は必ず「上段範囲外の軸番号」かつ「軸総数以内」
//     （上記条件を満たさない場合 botAxis = null = 下段ブロックなし）
//
//     相手馬 = topAxis+1 〜 N（上三角行列）
//
//   返り値 calcUmarenLayout(N) → pages > columns
//     pages:   Array<columns>
//     columns: Array<{ topAxis, topPartners, botAxis, botPartners }>  長さ 4 固定
//       topAxis:      number （必ず存在）
//       topPartners:  number[] （topAxis+1 〜 N）
//       botAxis:      number | null
//       botPartners:  number[] （botAxis+1 〜 N。botAxis=null のとき []）
//
//   従来 API 互換: calcUmarenPages / umarenPageConfig は calcUmarenLayout の結果を加工
function calcUmarenLayout(nHorses) {
  var nAxes = nHorses - 1;
  var nPages = nHorses <= 8 ? 1 : nHorses <= 14 ? 2 : 3;
  var nTop = nPages * 4;
  var pairSum = nTop * 2 + 1;

  var pages = [];
  for (var p = 0; p < nPages; p++) {
    var columns = [];
    for (var c = 0; c < 4; c++) {
      var topAxis = p * 4 + c + 1;
      var botCandidate = pairSum - topAxis;
      var botAxis = (botCandidate <= nAxes && botCandidate > nTop) ? botCandidate : null;

      var topPartners = [];
      for (var i = topAxis + 1; i <= nHorses; i++) topPartners.push(i);

      var botPartners = [];
      if (botAxis !== null) {
        for (var j = botAxis + 1; j <= nHorses; j++) botPartners.push(j);
      }
      columns.push({ topAxis: topAxis, topPartners: topPartners, botAxis: botAxis, botPartners: botPartners });
    }
    pages.push(columns);
  }
  return pages;
}

// 従来 API: 旧形式（top/bottom だけの配列）で返す（他箇所との互換用）
function calcUmarenPages(totalHorses) {
  return calcUmarenLayout(totalHorses).map(function(cols) {
    return cols.map(function(col) {
      return { topAxis: col.topAxis, bottomAxis: col.botAxis };
    });
  });
}

// 従来 API 互換: pageCount と getAxes を返す
function umarenPageConfig(totalHorses) {
  var pages = calcUmarenLayout(totalHorses);
  return {
    pageCount: pages.length,
    getAxes: function(pageNo) {
      var p = Math.max(1, Math.min(pages.length, pageNo));
      var axes = [];
      (pages[p - 1] || []).forEach(function(col) {
        if (col.topAxis != null) axes.push(col.topAxis);
        if (col.botAxis != null) axes.push(col.botAxis);
      });
      return axes;
    }
  };
}

// 軸の相手馬番リスト（上三角: axis+1 〜 N）
function getPartners(axis, totalHorses) {
  var partners = [];
  for (var i = axis + 1; i <= totalHorses; i++) partners.push(i);
  return partners;
}

// 騎手名 5文字以上のとき 先頭4文字に切り詰める（日本競馬オッズ表示の慣例）
// 元HTMLでも「L．ヒュ」「M．デム」など4文字に切られている
function truncateJockey(name) {
  if (!name) return '';
  // 簡易的に length で判定（日本語文字は length 1 相当で扱う）
  return name.length >= 5 ? name.slice(0, 4) : name;
}

// ---- カットイン制御 ----

/**
 * カットインテンプレート（templates/cutin.html）を初回のみ fetch し、
 * document.body に挿入する。子テンプレート（single-*.html）から
 * setDataUrl 受信時 or 初回 poll 前に await で呼ぶこと。
 *
 * 正式版到着時は cutin.html を丸ごと差し替えればよい。id 属性
 * （cutinOverlay / cutin-venue / cutin-race / cutin-body / cutin-footer）が
 * 維持されていれば JS 側は変更不要。
 */
var cutinTemplateState = { loaded: false, loading: null };
function ensureCutinTemplate() {
  if (cutinTemplateState.loaded) return Promise.resolve();
  if (cutinTemplateState.loading) return cutinTemplateState.loading;
  cutinTemplateState.loading = fetch('./cutin.html')
    .then(function(res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.text();
    })
    .then(function(html) {
      // 既に #cutinOverlay が存在する場合は重複挿入を防ぐ（開発時のHMR対策）
      if (document.getElementById('cutinOverlay')) {
        cutinTemplateState.loaded = true;
        return;
      }
      var wrap = document.createElement('div');
      wrap.innerHTML = html.trim();
      while (wrap.firstElementChild) {
        document.body.appendChild(wrap.firstElementChild);
      }
      cutinTemplateState.loaded = true;
    })
    .catch(function(err) {
      console.error('[cutin] template load failed:', err);
      cutinTemplateState.loading = null; // 次回リトライ可
      throw err;
    });
  return cutinTemplateState.loading;
}

/**
 * post_time 文字列（"HH:MM" / "HH:MM:SS" / ISO 8601）を
 * correctedNowMs を基準としたミリ秒に解決する。
 * 深夜跨ぎは computeDeadline と同様の補正を行う。
 */
function resolvePostTime(postTimeStr, correctedNowMs) {
  if (!postTimeStr) return NaN;
  // ISO 8601 優先（タイムゾーン付きならそのまま）
  if (/[T]/.test(postTimeStr)) {
    var t = Date.parse(postTimeStr);
    if (!isNaN(t)) return t;
  }
  // "HH:MM" or "HH:MM:SS"
  var m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(postTimeStr);
  if (m) {
    var d = new Date(correctedNowMs);
    var postMs = new Date(
      d.getFullYear(), d.getMonth(), d.getDate(),
      Number(m[1]), Number(m[2]), Number(m[3] || 0)
    ).getTime();
    // 深夜跨ぎ補正
    if (postMs < correctedNowMs - 10 * 3600 * 1000) {
      postMs += 24 * 3600 * 1000;
    }
    return postMs;
  }
  return NaN;
}

/**
 * カットイン表示判定。各子テンプレートの poll 内、render 後に毎回呼ぶ。
 * CUT-001（締切5分前）/ CUT-002（発売終了）を重複なしで1回ずつ表示。
 */
function checkCutin(race, correctedNowMs) {
  if (!race || !race.post_time || race.is_previous_day) return;

  var postMs = resolvePostTime(race.post_time_iso || race.post_time, correctedNowMs);
  if (isNaN(postMs)) return;

  // 表示上の締切（post_time - 2分 - safety margin）を基準にカットインを発火
  // → ヘッダーの「締切N分前」と CUT-001 の数字が常に一致する
  var deadlineMs = effectiveDeadlineMs(postMs);
  var remainMs   = deadlineMs - correctedNowMs;
  var raceKey    = (race.org || '') + '-' + (race.venue || '') + (race.race_no || '');

  // CUT-002: 締切到達
  if (remainMs <= 0 && cutinState.shownForRace !== raceKey + '_closed') {
    showCutin('closed', race);
    cutinState.shownForRace = raceKey + '_closed';
    return;
  }

  // CUT-001: 締切 COUNTDOWN_START_MIN 分前以内
  // poll 間隔や初回ロード遅延で発火時点の remainMs が 4分台にずれ込むことがあるため、
  // 表示する「N 分前」は動的計算ではなく COUNTDOWN_START_MIN（= 5）で固定する。
  // 仕様上「締切5分前カットイン」なので、発火したら必ず「5 分前」と表示するのが正。
  if (remainMs > 0 && remainMs <= COUNTDOWN_START_MIN * 60 * 1000
      && cutinState.shownForRace !== raceKey + '_countdown'
      && cutinState.shownForRace !== raceKey + '_closed') {
    showCutin('countdown', race, COUNTDOWN_START_MIN);
    cutinState.shownForRace = raceKey + '_countdown';
    return;
  }
}

/**
 * カットインDOM書き換え＋表示。CUTIN_DISPLAY_SEC 経過後に自動非表示。
 * 正式版HTMLとの差し替えを想定し、id属性ベースでDOM操作する。
 */
function showCutin(type, race, minutesLeft) {
  var overlay = document.getElementById('cutinOverlay');
  if (!overlay) return;

  var venueEl = document.getElementById('cutin-venue');
  var raceEl  = document.getElementById('cutin-race');
  var body    = document.getElementById('cutin-body');
  var footer  = document.getElementById('cutin-footer');
  if (!venueEl || !raceEl || !body || !footer) return;

  venueEl.textContent = race.venue || '';
  raceEl.textContent  = (race.race_no != null ? race.race_no + 'R' : '');

  if (type === 'countdown') {
    body.className = 'cutin__body cutin__body--countdown';
    body.innerHTML =
      '<span class="cutin__label">締切</span>' +
      '<span class="cutin__number">' + minutesLeft + '</span>' +
      '<span class="cutin__label">分前</span>';
    footer.className = 'cutin__footer cutin__footer--warning';
    footer.textContent = 'お早めにご投票ください。';
  } else {
    body.className = 'cutin__body cutin__body--closed';
    body.innerHTML = '<span class="cutin__message">発売を締め切りました</span>';
    footer.className = 'cutin__footer cutin__footer--thankyou';
    footer.textContent = 'ご投票誠にありがとうございました';
  }

  overlay.classList.remove('is-hidden');
  cutinState.active = true;
  cutinState.type = type;

  if (cutinState.hideTimer) clearTimeout(cutinState.hideTimer);
  cutinState.hideTimer = setTimeout(function() {
    overlay.classList.add('is-hidden');
    cutinState.active = false;
  }, CUTIN_DISPLAY_SEC * 1000);
}

// ---- グローバル公開 ----
window.OddsDemo = {
  POLL_INTERVAL_MS: POLL_INTERVAL_MS,
  get pollInterval() { return POLL_INTERVAL_MS; },
  FRAME_ROW_CLASS: FRAME_ROW_CLASS,
  FRAME_BLOCK_CLASS: FRAME_BLOCK_CLASS,
  FRAME_BODY_CLASS: FRAME_BODY_CLASS,
  FRAME_NUMBER_CLASS: FRAME_NUMBER_CLASS,
  WEATHER_ICON: WEATHER_ICON,
  fmtOdds: fmtOdds,
  fmtWeightDiff: fmtWeightDiff,
  frameClassOf: frameClassOf,
  frameOfHorse: frameOfHorse,
  fetchWithOffset: fetchWithOffset,
  setText: setText,
  el: el,
  setRaceNumber: setRaceNumber,
  renderRaceHeader: renderRaceHeader,
  computeWinClasses: computeWinClasses,
  computePlaceClasses: computePlaceClasses,
  computeFramePopular: computeFramePopular,
  renderFrameUmatan: renderFrameUmatan,  // H-03
  // 指示書08: 取消馬対応
  scratchedLabel: scratchedLabel,
  scratchedLabelShort: scratchedLabelShort,
  buildScratchedSet: buildScratchedSet,
  filterScratchedFromPopular: filterScratchedFromPopular,
  isTopPopular: isTopPopular,
  isUmarenUnpopular: isUmarenUnpopular,
  umarenPageConfig: umarenPageConfig,
  calcUmarenPages: calcUmarenPages,
  calcUmarenLayout: calcUmarenLayout,
  getPartners: getPartners,
  truncateJockey: truncateJockey,
  computeDeadline: computeDeadline,
  startHeaderTicker: startHeaderTicker,
  checkCutin: checkCutin,
  showCutin: showCutin,
  resolvePostTime: resolvePostTime,
  ensureCutinTemplate: ensureCutinTemplate,
  renderMatrixTable: renderMatrixTable,
  // 指示書07 エラーハンドリング
  startResilientPolling: startResilientPolling,
  registerPoller: registerPoller,
  getAllPollerStatus: getAllPollerStatus,
  dumpPollerStatus: dumpPollerStatus
};

/**
 * 馬連・馬単の「馬番順」マトリックス画面（screen-umaren / screen-umatan）を描画する共通ヘルパ。
 *
 * @param {HTMLElement} container - .screen-table 要素（bodies をここに追加）
 * @param {Array} horses - race.horses
 * @param {Array} matrix - race.umaren_matrix or race.umatan_matrix
 * @param {Object} opts
 *   opts.type         'umaren' | 'umatan'
 *   opts.axisFrom     軸馬の開始番号（例: 1）
 *   opts.axisTo       軸馬の終了番号（例: 9）
 *   opts.unpopularThreshold  odds >= これ で odds-unpopular 付与（既定: 1000）
 *   opts.popularTopN         odds 昇順上位N個を odds-popular に（既定: 5）
 *
 * 構造:
 *   各 axis 馬 → <div class="screen-table__body body-{frameColor}">
 *                   <div class="screen-table__name">{axis}</div>
 *                   <div class="screen-table__row">
 *                     <div class="screen-table__number number-{frameColor}">{b}</div>
 *                     <div class="screen-table__odds [odds-cross|odds-popular|odds-unpopular]">{oddsValue}</div>
 *                   </div>
 *                   ...
 *                 </div>
 *
 *   umaren: 各 axis に対し b = axis+1..N の行
 *   umatan: 各 axis に対し b = 1..N の行（b == axis なら odds-cross）
 */
function renderMatrixTable(container, horses, matrix, opts) {
  if (!container) return;
  var n = (horses || []).length;
  if (n === 0) {
    container.replaceChildren();
    return;
  }

  var type = opts.type;
  var axisFrom = opts.axisFrom;
  var axisTo = Math.min(opts.axisTo, n);
  var unpopularThreshold = opts.unpopularThreshold != null ? opts.unpopularThreshold : 1000;
  var popularTopN = opts.popularTopN != null ? opts.popularTopN : 5;

  // horse_no → frame_no マップ
  var frameOf = {};
  horses.forEach(function(h) { frameOf[h.horse_no] = h.frame_no; });

  // 指示書08: 取消馬の horse_no セット（軸・相手の両方で使用）
  var scratchedSet = buildScratchedSet(horses);

  // odds-popular 判定用: 表示範囲に入るセルの odds 昇順上位 N を集める
  // 取消馬を含むセル（軸 or 相手が取消）は人気判定対象から除外する。
  var visibleOdds = [];
  for (var ax = axisFrom; ax <= axisTo; ax++) {
    if (scratchedSet[ax]) continue;
    var opposingFrom = (type === 'umatan') ? 1 : (ax + 1);
    var opposingTo = n;
    for (var b = opposingFrom; b <= opposingTo; b++) {
      if (type === 'umatan' && b === ax) continue;
      if (scratchedSet[b]) continue;
      var entry = findMatrixEntry(matrix, ax, b, type);
      if (entry && typeof entry.odds === 'number') {
        visibleOdds.push(entry.odds);
      }
    }
  }
  visibleOdds.sort(function(a, b) { return a - b; });
  var popularThreshold = visibleOdds.length >= popularTopN ? visibleOdds[popularTopN - 1] : Infinity;

  var fragment = document.createDocumentFragment();
  for (var axis = axisFrom; axis <= axisTo; axis++) {
    if (!frameOf[axis]) continue; // 該当馬なし
    var axisFrame = frameOf[axis];
    var axisScratched = !!scratchedSet[axis];
    var body = document.createElement('div');
    body.className = 'screen-table__body ' + (FRAME_BODY_CLASS[axisFrame] || '');
    if (axisScratched) body.classList.add('body-scratched');

    var name = document.createElement('div');
    name.className = 'screen-table__name';
    name.textContent = String(axis);
    body.appendChild(name);

    var oppFrom = (type === 'umatan') ? 1 : (axis + 1);
    var oppTo = n;
    for (var bb = oppFrom; bb <= oppTo; bb++) {
      var bFrame = frameOf[bb];
      if (!bFrame) continue;
      var row = document.createElement('div');
      row.className = 'screen-table__row';

      var numDiv = document.createElement('div');
      numDiv.className = 'screen-table__number ' + (FRAME_NUMBER_CLASS[bFrame] || '');
      numDiv.textContent = String(bb);
      row.appendChild(numDiv);

      var oddsDiv = document.createElement('div');
      oddsDiv.className = 'screen-table__odds';
      var oppScratched = !!scratchedSet[bb];
      if (type === 'umatan' && bb === axis) {
        oddsDiv.classList.add('odds-cross');
        oddsDiv.textContent = '';
      } else if (axisScratched || oppScratched) {
        // 軸 or 相手が取消 → オッズセルを空白化して odds-scratched を付与。
        // 軸取消時は body 全体に body-scratched が付くため重複薄化は避ける目的で、
        // 相手取消（軸は通常）のときのみ odds-scratched を追加する。
        if (!axisScratched) oddsDiv.classList.add('odds-scratched');
        oddsDiv.textContent = '';
      } else {
        var e = findMatrixEntry(matrix, axis, bb, type);
        if (e && typeof e.odds === 'number') {
          oddsDiv.textContent = fmtOdds(e.odds);
          if (e.odds <= popularThreshold) {
            oddsDiv.classList.add('odds-popular');
          } else if (e.odds >= unpopularThreshold) {
            oddsDiv.classList.add('odds-unpopular');
          }
        }
      }
      row.appendChild(oddsDiv);
      body.appendChild(row);
    }
    fragment.appendChild(body);
  }
  container.replaceChildren(fragment);
}

function findMatrixEntry(matrix, a, b, type) {
  if (!matrix) return null;
  if (type === 'umaren') {
    // 無順: matrix 内は a < b で保存されている想定
    var lo = Math.min(a, b), hi = Math.max(a, b);
    for (var i = 0; i < matrix.length; i++) {
      if (matrix[i].a === lo && matrix[i].b === hi) return matrix[i];
    }
  } else {
    // 順序あり
    for (var j = 0; j < matrix.length; j++) {
      if (matrix[j].a === a && matrix[j].b === b) return matrix[j];
    }
  }
  return null;
}

/**
 * 子テンプレートが呼び出す 1秒tick。
 * getState() から現在の state を取り出し、ヘッダーの deadline 表示を更新する。
 *   getState: function() → { doc, data, mode, serverOffsetMs }
 *   data が null の間（初回poll前）は何もしない。
 */
function startHeaderTicker(getState) {
  setInterval(function() {
    try {
      var s = getState();
      if (!s || !s.data || !s.data.race) return;
      renderRaceHeader(s.doc, s.data.race, {
        mode: s.mode || 'full',
        correctedNowMs: Date.now() + (s.serverOffsetMs || 0)
      });
    } catch (_) {}
  }, 1000);
}
