/**
 * 4画面JSONポーリングサンプル - 子テンプレート共通ユーティリティ
 *
 * 申し送り仕様書のクラス命名・CSS変数注入ルールに準拠。
 *  - row-* / number-* / block-* / body-* / odds-d1 / odds-d3（O-3 桁数ベース配色）/
 *    odds-cross / odds-scratched / body-scratched / weight-long / weight-diff / minute
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
// 2026-06-04: CUT-003 (サイネージカットイン) 表示秒数。要件定義書 v3.3 §3.2「締切後30秒程度」。
//   CUT-002 (10秒) 終了直後に CUT-003 が発火し、本秒数だけ表示される。
//   ?signage_cutin_sec=N で上書き可（開発検証用）。
var SIGNAGE_CUTIN_DISPLAY_SEC = 30;
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
    // 2026-06-04: CUT-003 (サイネージカットイン) 秒数の URL クエリ上書き
    var sq = new URL(location.href).searchParams.get('signage_cutin_sec');
    if (sq) {
      var sn = Number(sq);
      if (isFinite(sn) && sn >= 1) SIGNAGE_CUTIN_DISPLAY_SEC = sn;
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

// ---- 親 iframe からの serverOffset broadcast 受信 ----
// server_time-fix-v3 (2026-04-20): 中央集権型の時刻同期。
//   親が HTTP Date+Age から算出した serverOffset を postMessage で受信し保持する。
//   fetchWithOffset は優先的にこの値を使い、未受信時のみ自前で Date+Age から算出する。
//   未受信時は null（初期値）。親が broadcast を送ってきた時点で数値化される。
var _broadcastedServerOffset = null;

// 2026-06-29: 前日発売/対象レース固定 context（§3.5.4）。親 index.html が
//   setSaleContext で送る。target_date_offset>=1 のとき renderRaceHeader を
//   「前日発売」モードに切替える（旧 odds JSON の is_previous_day は v0.6.4 で撤去）。
var _saleContext = { target_race_no: null, target_date_offset: 0 };

window.addEventListener('message', function(e) {
  if (e.data && e.data.type === 'setServerOffset') {
    _broadcastedServerOffset = e.data.offset;
  }
  if (e.data && e.data.type === 'setSaleContext') {
    _saleContext.target_race_no = (e.data.target_race_no != null) ? e.data.target_race_no : null;
    _saleContext.target_date_offset = e.data.target_date_offset || 0;
  }
  // 2026-06-04: 親からのサイネージ URL 受信 (CUT-003 用)。
  //   各 SCR-ODD-* テンプレ共通で受信し cutinState.signage_url に保持。
  //   checkCutin が CUT-002 終了後に本 URL で CUT-003 を発火する。
  if (e.data && e.data.type === 'setSignageUrl') {
    cutinState.signage_url = e.data.url || null;
  }
  // 2026-08-05: カットイン発火済み状態の復元（引地様 №21）。
  //   dp20/30/40 の自動ページングは template を差し替える＝**iframe をリロードする**ため、
  //   子の cutinState.shownForRace が毎回リセットされ、同じレースのカットインが
  //   ページ送りのたびに何度も出ていた（15秒周期なら15秒ごとに「締切5分前」）。
  //   親がレース単位で発火済みキーを保持し、リロード後の子へ復元する。
  //   ⚠ 送信は親の iframe.onload 内・setDataUrl より前。初回 poll の checkCutin より必ず先に届く。
  if (e.data && e.data.type === 'restoreCutinState') {
    if (e.data.shownForRace) cutinState.shownForRace = e.data.shownForRace;
  }
});

// 2026-08-05: カットインの発火状況を親に通知する（引地様 №21）。
//   親は (a) 発火済みキーを保持してリロード後の子に復元し、
//       (b) 表示中はページ送りを保留する（10秒/30秒の表示を途中で切らないため）。
function notifyCutinState() {
  if (window.parent === window) return;
  try {
    window.parent.postMessage({
      type: 'cutinState',
      shownForRace: cutinState.shownForRace,
      active: !!cutinState.active
    }, '*');
  } catch (_) {}
}

// 【ハンドシェイク】リスナー登録直後に親へ offset を要求する。
//   iframe.onload 発火と <script> ロード完了のタイミング不一致を吸収するため、
//   子側のリスナー登録完了を起点に能動的に要求する方式（構造的タイミング保証）。
//   親側は index.html の message ハンドラで requestServerOffset を受けて即応答する。
if (window.parent !== window) {
  try {
    window.parent.postMessage({ type: 'requestServerOffset' }, '*');
  } catch (_) {}
}

/**
 * post_time からの「表示上の締切時刻（ミリ秒）」を算出。
 * 表示締切 = post_time - DEADLINE_BEFORE_POST_MIN分 - DEADLINE_SAFETY_MARGIN_SEC秒
 * computeDeadline と checkCutin の両方で同じ基準を使うための共通ヘルパ。
 */
function effectiveDeadlineMs(postMs) {
  return postMs - (DEADLINE_BEFORE_POST_MIN * 60 + DEADLINE_SAFETY_MARGIN_SEC) * 1000;
}

// ---- カットイン表示状態 ----
// 2026-06-04: CUT-003 (signage) 追加に伴い拡張。
//   - type: 'countdown' (CUT-001) / 'closed' (CUT-002) / 'signage' (CUT-003)
//   - shownForRace: 同一レースで CUT-001/002 を重複発火しないためのキー
//   - signage_url: 親から postMessage で受信した signage 画像 URL (CUT-003 用)
//   - chainTimer: CUT-002 終了後に CUT-003 を発火させる setTimeout ハンドル
var cutinState = {
  active: false,
  type: null,
  hideTimer: null,
  shownForRace: null,
  signage_url: null,
  chainTimer: null
};

// 枠番→クラス名マップ（1-8枠。9頭以上は 8枠 2頭入りルールで 1-8 に収まる）
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

// field-rename-v0.5 (2026-04-20): v0.5 §4.3 weather_cd (INT 1-6) → アイコンファイル名。
//   旧仕様は string キー ('sunny'/'cloudy'/...）だったが v0.5 で INT コードに統一された。
//   付録A.7 の統一値（1=晴, 2=曇, 3=小雨, 4=雨, 5=小雪, 6=雪）に準拠。
var WEATHER_ICON = {
  1: 'sunny.svg',
  2: 'cloudy.svg',
  3: 'light-rain.svg',
  4: 'rain.svg',
  5: 'light-snow.svg',
  6: 'snow.svg'
};

// field-rename-v0.5 (2026-04-20): v0.5 §4.3 track_cd / track_cond_cd / course_direction
//   INT コード → 表示文字列（renderRaceHeader で使用）
//   付録A.8-A.10 準拠。
var TRACK_LABEL = { 0: 'ダ', 1: '芝', 2: 'サ', 3: '障' };
var TRACK_COND_LABEL = { 1: '良', 2: '稍重', 3: '重', 4: '不良' };
// 2026-04-21 Phase 3: ばんえいは直線固定（course_direction=0 を"直線"として受ける）
var COURSE_DIRECTION_LABEL = { 0: '直線', 1: '右', 2: '左', 3: '直線' };

// 2026-04-21 Phase 3: ばんえい判定（organizer_type=NAR + place_cd=03、帯広固定）
function isBaneiRace(race) {
  return !!race && race.organizer_type === 'NAR' && race.place_cd === '03';
}

// ---- フォーマッタ ----
// 2026-04-22 Phase 5: 賭式 × 主催者別のオッズ上限 (cap) 値。
// DB 仕様:
//   999.9     : 単勝/複勝/枠連/枠単（NAR・JRA 共通）
//   9999.9    : 馬連(NAR) / 馬単(NAR) / ワイド（NAR・JRA）
//   99999.9   : 馬連(JRA) / 馬単(JRA) / 3連複（NAR・JRA）/ 3連単(NAR)
//   999999.9  : 3連単(JRA)
// cap 値超過時は cap 値をそのまま表示（ユーザー確定仕様、2026-04-22）
var ODDS_CAPS = {
  NAR: {
    win: 999.9, place: 999.9,
    frame_quinella: 999.9, frame_exacta: 999.9,
    quinella: 9999.9, exacta: 9999.9, wide: 9999.9,
    trio: 99999.9, trifecta: 99999.9
  },
  JRA: {
    win: 999.9, place: 999.9,
    frame_quinella: 999.9, frame_exacta: 999.9,
    quinella: 99999.9, exacta: 99999.9, wide: 9999.9,
    trio: 99999.9, trifecta: 999999.9
  }
};

function oddsCapFor(betType, organizer) {
  var m = ODDS_CAPS[organizer || 'NAR'] || ODDS_CAPS.NAR;
  return m[betType] || 999.9;
}

function fmtOdds(v, betType, organizer) {
  if (v === null || v === undefined) return '';
  // 引数 1 つだけの旧呼出もサポート（互換性）：従来は 999.9 cap
  var cap = betType ? oddsCapFor(betType, organizer) : 999.9;
  if (v >= cap) return cap.toFixed(1);
  return Number(v).toFixed(1);
}

// O-3b (2026-07-29 及川決定): オッズ未着時の共通表示。
//   票が入っていない組合せ・馬は配信 JSON に値が来ない（枠連は要素ごと欠落、
//   単勝/複勝は null）。従来は画面ごとに 空欄 / '-' / '0.0' / 行削除 の 4 通りに
//   分かれていたため、'-' に一本化する。'0.0' は「0倍」と誤読されるため廃止。
//
//   ※ 取消・除外セル（odds-scratched / body-scratched）と馬単の自己交差セル
//     （odds-cross）は「値なし」ではなく「無効」なので、本関数を使わず
//     従来どおり空白 + 専用クラスで表す。
var ODDS_EMPTY = '-';

function fmtOddsOr(v, betType, organizer) {
  var s = fmtOdds(v, betType, organizer);
  return s === '' ? ODDS_EMPTY : s;
}

// O-3 (2026-07-28 芥川様打合せ / 2026-07-29 及川決定): オッズ配色の共通判定。
//   従来は画面ごとに付与ルールが異なっていた（単勝=昇順上位3/4-5位、複勝=上位50%、
//   枠連枠単=is_popular、馬連ワイド=odds>=1000、人気順=rank<=3、マトリクス=上位5と>=1000）。
//   これを「オッズの桁数」に一本化する。順位ベースの配色は全廃。
//
//   1桁      (odds <  10.0) → odds-d1（#FF8000 オレンジ）
//   2桁      (10.0〜99.9)   → クラスなし（既定色＝白）
//   3桁以上  (odds >= 100.0)→ odds-d3（#00B2FF 水色）
//
//   判定はキャップ適用後の値で行う（表示している文字列と色を一致させるため）。
//   値が無い（票が入っていない＝'-' 表示）ときは色を付けない。
function oddsColorClass(v, betType, organizer) {
  if (v === null || v === undefined) return '';
  var cap = betType ? oddsCapFor(betType, organizer) : 999.9;
  var shown = (v >= cap) ? cap : v;
  if (shown < 10) return 'odds-d1';
  if (shown >= 100) return 'odds-d3';
  return '';
}

// クラス名を組み立てるヘルパ（base + 配色クラス）。
function oddsClass(base, v, betType, organizer) {
  var c = oddsColorClass(v, betType, organizer);
  return c ? (base + ' ' + c) : base;
}

// O-3b 追補 (2026-07-29 及川指摘): min - max 形式のセル（複勝・ワイド）を組み立てる。
//   セルは `1fr auto 1fr` の 3 span 構成で、真ん中が区切りのハイフン。
//   両方とも票が入っていないと `-` `-` `-` と 3 つ並び、区切りと値の区別がつかない。
//   → 両方欠損のときは中央の 1 個だけ残して左右を空にする（グリッドは崩さない）。
//   片方だけ欠損のときは従来どおり 3 span（値のある側と対比できるほうが分かりやすい）。
function fillMinMaxCell(cellEl, min, max, betType, organizer) {
  var noMin = (min === null || min === undefined);
  var noMax = (max === null || max === undefined);
  if (noMin && noMax) {
    cellEl.appendChild(el('span', null, ''));
    cellEl.appendChild(el('span', null, ODDS_EMPTY));
    cellEl.appendChild(el('span', null, ''));
    return cellEl;
  }
  cellEl.appendChild(el('span', oddsColorClass(min, betType, organizer) || null, fmtOddsOr(min, betType, organizer)));
  cellEl.appendChild(el('span', null, '-'));
  cellEl.appendChild(el('span', oddsColorClass(max, betType, organizer) || null, fmtOddsOr(max, betType, organizer)));
  return cellEl;
}

// O-2 (2026-07-28 芥川様打合せ AI#7 / 2026-07-29 及川決定): 性齢の性別表記。
//   JSON の sex は 牡/牝/セ（JSON構造仕様書 §4.4、DB crc.sex 由来）。
//   お披露目会で「セ」は表示に不適との指摘があり、表示側で置換する
//   （データ契約・内山様バッチには手を入れない）。
//
//   表記は **半角カナ「ｾﾝ」**。NAR 公式（Let's 地方競馬の出馬表）が「セン」表記のため
//   それに合わせつつ、全角「セン」は列幅 3rem に収まらないため半角を採る。
//   実測（列幅 3rem = 39px / 1.2rem = 16px / Yu Gothic UI）:
//     騙        … 1桁 27px / 2桁 34px  → 1行
//     ｾﾝ(半角)  … 1桁 27px / 2桁 35px  → 1行   ← 採用
//     セン(全角)… 1桁 37px / 2桁 39px  → **2桁で折り返す**
//   地方競馬は 10 歳以上の出走があるため、2桁で折り返さないことが採否の条件。
var SEX_LABEL = { 'セ': 'ｾﾝ' };

function fmtSex(sex) {
  return SEX_LABEL[sex] || sex || '';
}

// 減量記号（JSON 構造仕様書 v0.6.6 付録 A.12）。値は減量 kg。
//   NAR/JRA とも 5 記号で kg 値は一致（★4 / ▲3 / △2 / ◇2 / ☆1）。
var GENRYO_KG = { '★': 4, '▲': 3, '△': 2, '◇': 2, '☆': 1 };

// 2026-07-22: 減量記号の解決（山内様 実機検証 §3-2 の欠落修正）。
//   odds JSON の horses[] は `org_genryokigo` / `new_genryokigo`（仕様 §3 系）、
//   results JSON の entries[] は `genryokigo`（仕様 §4.5.4）と名前が異なる。
//   出走表テンプレートは horses[] を描画するのに `genryokigo` を読んでいたため
//   常に空になり、減量記号が表示されなかった。両系統を吸収する。
//   優先順は仕様 §4.5.4（`crc.new_genryokigo` または `crc.org_genryokigo`）に合わせ
//   騎手変更後（new）を優先する。
function genryokigoOf(h) {
  if (!h) return null;
  return h.genryokigo || h.new_genryokigo || h.org_genryokigo || null;
}

// 2026-07-22: 実負担重量（及川決定 2026-07-22）。
//   JSON の `fwt` は「基本斤量（減量前）」。同一レース・同一性齢で減量記号のある騎手と
//   無い騎手の fwt が同値であることを prod 実データで確認済（笠松 7/24 1R ほか）。
//   出馬表は減量後の実負担重量を表示するため、記号ぶんを差し引く。
//   ばんえいは負担重量（3-4桁）で減量記号の運用が無いため対象外。
function effectiveFwt(h, banei) {
  if (!h || h.fwt === null || h.fwt === undefined) return null;
  if (banei) return h.fwt;
  var kg = GENRYO_KG[genryokigoOf(h)];
  return kg ? h.fwt - kg : h.fwt;
}

// 馬体重の表示（馬体重特殊値仕様書 v1.0 §4.5 準拠、2026-07-15 表示文字列確定）
//   null/undefined = 計量前（電文未着。前日発売・当日計量前で正規に発生）→ 空欄
//                    （地全協 keiba.go.jp 出馬表と同じ「未計量は何も出さない」流儀。及川決定 2026-07-15）
//   0    = 出走取消（行の抑制は is_scratched 側で行う）→ 空欄
//   9999 = 計量不能（最終値）→ '計不'
//   それ以外 = 実体重をそのまま表示
function fmtWeight(weight) {
  if (weight === null || weight === undefined || weight === 0) return '';
  if (weight === 9999) return '計不';
  return String(weight);
}

// 馬体重増減の表示（同 §4.5）。第2・第3引数は省略可（旧呼び出し互換）。
//   weight が計量前/取消/計不 → 増減欄は空（誤って '(0)' や '(計不)' を出さない）
//   wt2=0 → '(初)'、wt2=9999 → '(前計不)'
//   diff が null（上記以外＝算出不能）→ 空
function fmtWeightDiff(diff, wt2, weight) {
  if (weight === null || weight === undefined || weight === 0 || weight === 9999) return '';
  if (wt2 === 0) return '(初)';
  if (wt2 === 9999) return '(前計不)';
  if (diff === null || diff === undefined) return '';
  if (typeof diff === 'string') return '(' + diff + ')';
  if (diff > 0) return '(+' + diff + ')';
  return '(' + diff + ')';
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
// O-3 (2026-07-29): 順位ベースの配色判定を全廃した。
//   撤去した関数: computeWinClasses（単勝 昇順上位3/4-5位）/ computePlaceClasses（複勝 上位50%）
//                 computeFramePopular（枠連 下位5件）/ isTopPopular（rank<=3）
//                 isUmarenUnpopular（odds>=1000）
//   配色は oddsColorClass()（桁数ベース）に一本化されている。
//   ※ computePlaceClasses は `null <= threshold` が true になるため、票が入っていない
//     複勝オッズにも強調色が付く不具合があった。桁数ベースでは null を無色にして解消。

// ---- H-03 (2026-04-19): 枠単マトリクス描画 ----
// 仕様: wrapper 内に 2つの body を生成（上段=軸枠1-4、下段=軸枠5-8）。
// 各 body は「frame 列（ヘッダー9セル）+ 4枠分の block（各9セル）」の5カラム grid。
// block 内: label（軸枠）+ frame 1〜8 のオッズ 8セル = 9行。
// utanData: race.frame_utan（8×8=64件の配列）
// wrapperEl:  '.frame-umatan__wrapper' 要素
// 2026-04-30 session3 修正: クラス名を芥川 design.zip 準拠の `frame-umatan` に統一
//   （旧 `frame-utan` は style.css に対応 CSS が無く崩れの原因だったため）。
function renderFrameUtan(utanData, wrapperEl, organizer) {
  if (!wrapperEl) return;
  var matrix = {};
  (utanData || []).forEach(function(d) {
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
          item.textContent = fmtOddsOr(entry.odds, 'frame_exacta', organizer);
          // O-3: is_popular（下位5件）ベースを廃し、桁数ベースに統一
          var uCls = oddsColorClass(entry.odds, 'frame_exacta', organizer);
          if (uCls) item.classList.add(uCls);
        } else {
          item.textContent = ODDS_EMPTY;   // O-3b: 未着の組合せ
        }
        block.appendChild(item);
      }
      body.appendChild(block);
    });

    frag.appendChild(body);
  });

  wrapperEl.replaceChildren(frag);
}

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
  // 2026-06-29: 前日発売は親からの sale context（target_date_offset>=1）で駆動（§3.5.4）。
  //   opts.previousDay 明示指定も尊重（呼び出し側で上書き可能）。
  if (opts.previousDay || (typeof _saleContext !== 'undefined' && _saleContext.target_date_offset >= 1)) {
    mode = 'previous-day';
  }

  // field-rename-v0.5 (2026-04-20): race.venue → race.place_name、race.race_no → race.rr
  setText(doc.querySelector('#hdr-venue'), race.place_name || '');
  setRaceNumber(doc.querySelector('#hdr-race'), race.rr);
  setText(doc.querySelector('#hdr-raceName'), race.race_name || '');
  // 2026-07-22: race_class（競走種類）の表示を廃止（及川決定）。
  //   NAR 公式は「当日メニュー（一覧）」では競走種類を独立カラムで出すが、
  //   「個別出馬表（DebaTable）」では種類ラベルを出さず競走名のみを表示する。
  //   本画面は単一レース表示＝個別出馬表に相当するため、種類は出さないのが NAR 準拠。
  //   これにより「涼月特別」＋「特別」＝「涼月特別特別」の重複表示も解消する
  //   （山内様 実機検証 §3-3'。7/24 の 3 場で 11 レースが該当）。
  //   ※ 7/15 の「普通は非表示・特別等は表示」判断は一覧ページの体裁に基づくものだった。
  //   ※ NAR は競走名にクラス条件（Ａ４ / Ｃ３一 等）を付すが、当該フィールドは
  //      現行 JSON に無い（別課題として内山様へ確認中）。
  setText(doc.querySelector('#hdr-raceClass'), '');

  var raceInfo = doc.querySelector('.race-info');
  var prevDay = doc.querySelector('.previous-day');

  if (mode === 'full') {
    if (raceInfo) raceInfo.classList.remove('is-hidden');
    if (prevDay)  prevDay.classList.add('is-hidden');
    var icon = doc.querySelector('#hdr-weatherIcon');
    if (icon) {
      // field-rename-v0.5 (2026-04-20): race.weather → race.weather_cd (INT)
      icon.src = '../assets/images/weather/' + (WEATHER_ICON[race.weather_cd] || 'sunny.svg');
      icon.alt = race.weather_label || '';
    }
    setText(doc.querySelector('#hdr-weatherLabel'), race.weather_label || '');
    // field-rename-v0.5 (2026-04-20): race.condition → race.track_cond_cd、race.surface → race.track_cd、
    //   race.direction → race.course_direction。INT コードを表示文字列に変換（ラベルマップ参照）。
    // 2026-04-21 Phase 3: ばんえい時は馬場水分 (track_water_pct) を良/稍重/重/不良の代わりに表示、
    //   かつ「ダ 200m (直線)」は固定値で冗長なため非表示（ユーザーフィードバック ラウンド 4）
    var condText = TRACK_COND_LABEL[race.track_cond_cd] || '';
    if (isBaneiRace(race) && race.track_water_pct != null) {
      // 2026-07-22: 数値をそのまま連結すると 0.0 が "0%" になり小数が落ちる。
      //   常に小数1桁で表示する（山内様 実機検証 §3-5「##0.0％」であるべき）。
      condText = Number(race.track_water_pct).toFixed(1) + '%';
    }
    setText(doc.querySelector('#hdr-condition'), condText);
    if (isBaneiRace(race)) {
      setText(doc.querySelector('#hdr-surface'),   '');
      setText(doc.querySelector('#hdr-distance'),  '');
      setText(doc.querySelector('#hdr-direction'), '');
    } else {
      setText(doc.querySelector('#hdr-surface'),   TRACK_LABEL[race.track_cd] || '');
      setText(doc.querySelector('#hdr-distance'),  (race.distance || '') + 'm');
      setText(doc.querySelector('#hdr-direction'), '(' + (COURSE_DIRECTION_LABEL[race.course_direction] || '') + ')');
    }

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
      // 時は外して既定背景（dos-overrides.css 側で data-mode=countdown/closed の赤グラデ）
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

// ---- fetch with server-time offset ----
// server_time-fix-v3 (2026-04-20): 時刻補正ソースを HTTP Date+Age ヘッダに刷新。
//   serverOffset 決定の優先順位:
//     1. 親 broadcast（_broadcastedServerOffset）があればそれを採用（全子 iframe で同一）
//     2. なければレスポンスの Date + Age ヘッダから自前計算（分散型フォールバック）
//     3. Date 欠落時は 0（端末時刻そのまま）
//   ブラウザキャッシュ回避は { cache: 'no-cache' } で保証（?t= クエリは撤去）。
//   timeoutMs（既定10秒）で AbortController によるタイムアウトを発動。
//   指示書07 のエラーハンドリング仕様で「タイムアウトも失敗」として扱う。
//   data.server_time は補正には使用しない（監査用途でフィールド自体は継続出力される）。
async function fetchWithOffset(url, timeoutMs) {
  timeoutMs = timeoutMs || 10000;
  var t0 = Date.now();
  var controller = new AbortController();
  var timer = setTimeout(function() { controller.abort(); }, timeoutMs);
  try {
    var res = await fetch(url, {
      signal: controller.signal,
      cache: 'no-cache'
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    var data = await res.json();
    var t1 = Date.now();
    var clientTime = t0 + (t1 - t0) / 2;

    var serverOffset;
    if (_broadcastedServerOffset !== null) {
      // 親 broadcast が届いていればそれを使う（中央集権、全子 iframe で同一）
      serverOffset = _broadcastedServerOffset;
    } else {
      // フォールバック: Date+Age ヘッダから自前計算
      serverOffset = 0;
      var dateHeader = res.headers.get('Date');
      if (dateHeader) {
        var dateMs = Date.parse(dateHeader);
        if (!isNaN(dateMs)) {
          var ageSec = Number(res.headers.get('Age')) || 0;
          serverOffset = (dateMs + ageSec * 1000) - clientTime;
        }
      }
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

// 2026-07-31: 返還レース（レース不成立）の判定。
//   実データでは odds_status=1（確定）のまま、全賭式の払戻が
//   combination="0"/"0-0"/"0-0-0"・amount=100・is_void=true で配信され、
//   entries（着順）は**永久に空**のままになる。
//   （2026-07-24 大井5R・6R、07-28 名古屋2R・3R、金沢4R・5R で実発生）
//   odds_status=2「レース中止」は実データに存在しないため、この形で判定するしかない。
//   1 件でも通常の払戻があれば返還レースではない（確定途中で payouts だけ入った状態と区別する）。
function isVoidRace(payouts) {
  if (!payouts) return false;
  var found = false;
  for (var k in payouts) {
    if (k === 'bet_order' || !payouts.hasOwnProperty(k)) continue;
    var arr = payouts[k];
    if (!arr || !arr.length) continue;
    for (var i = 0; i < arr.length; i++) {
      if (!arr[i].is_void) return false;
      found = true;
    }
  }
  return found;
}

// 2026-07-30: 前日発売の参照先が存在しないときの案内（山内様 実機検証 #2 / 及川決定）。
//   index.html が target_date_offset>=1 のとき data_source を翌日パスへ書き換えるが、
//   その場が翌日に開催しない場合は参照先 JSON が存在せず 404 になる。
//   誤って当日オッズを「前日発売」として出すよりは空にするのが正しいが、
//   理由が分からないため案内を重ねる。本筋は CRM 側で「翌日開催の無い場は
//   表示日=翌日で保存できない」バリデーションを入れること（堀井様領域）。
//   ※ 親 index.html は setSaleContext を受け取らず offset=0 のままなので発火しない。
var _prevDayNoticeEl = null;
function setPrevDaySaleUnavailable(on) {
  if (on) {
    if (_prevDayNoticeEl) return;
    var d = document.createElement('div');
    d.className = 'dos-prevday-unavailable';
    d.textContent = '本日の前日発売はありません';
    document.body.appendChild(d);
    _prevDayNoticeEl = d;
  } else if (_prevDayNoticeEl) {
    if (_prevDayNoticeEl.parentNode) _prevDayNoticeEl.parentNode.removeChild(_prevDayNoticeEl);
    _prevDayNoticeEl = null;
  }
}

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
      setPrevDaySaleUnavailable(false);
      try { opts.onSuccess(result); } catch (renderErr) {
        console.error('[' + name + '] onSuccess error:', renderErr);
      }
    } catch (err) {
      failCount++;
      lastErrorMessage = err && err.message ? err.message : String(err);
      lastErrorTime = Date.now();
      console.error('[' + name + '] poll error (count=' + failCount + '):', err);
      // 前日発売セルで参照先が無い（404）＝翌日にその場の開催が無いケース
      if (_saleContext.target_date_offset >= 1 && /HTTP 40[34]/.test(lastErrorMessage)) {
        setPrevDaySaleUnavailable(true);
      }
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
  // 方針（5/18 サテライト石狩 議事録 §1.3・README 確認事項C）:
  //   地方競馬には同名騎手識別のための公式3文字略称体系があるが、(a) 単純な頭3文字切りでは再現できず
  //   (b) JRA 側に略称データが存在しないため、**略称は採用せず JRA/地方とも騎手名の切り捨てで統一**する。
  //
  // 2026-07-16 修正（及川決定）: **スペースを完全に除去**してから 4 文字判定する。
  //   NAR データは姓名をスペースで詰めて桁揃えする（例「藤江　渉」「佐々木 世麗」）。スペースを
  //   1 つに正規化するだけでは、そのスペースが 4 文字枠を 1 つ食うため **姓 3 文字の騎手は名が丸ごと消え**、
  //   さらに **同姓騎手が区別できなくなる**（5/18 議事録「五十嵐で切っちゃうとかぶっちゃう」が実際に発生）。
  //
  //   実データ 219 名（2026-07-13〜16・全15場）での検証:
  //     - 208 名（95%）が **フルネーム表示**になる（山口 達弥 → 山口達弥／藤江　渉 → 藤江渉）
  //     - **同姓衝突が 2 件 → 0 件**（佐々木 世麗/志音 → 佐々木世/佐々木志、山本 聡哉/聡紀 → 山本聡哉/山本聡紀）
  //   4 文字枠をすべて実文字に使えるため、スペース温存より情報量が多く衝突も少ない。
  //     佐々木 世麗 → 佐々木世 ／ 菅原 吏久人 → 菅原吏久 ／ 木間塚 龍馬 → 木間塚龍
  var s = String(name).replace(/\s+/g, '');
  return s.length >= 5 ? s.slice(0, 4) : s;
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
  // 2026-05-01: cutin.html 構造を芥川 closing-timer-board に移植。
  //             テンプレ更新時の即時反映のため cache-bust を付与。
  cutinTemplateState.loading = fetch('./cutin.html?v=20260604e', { cache: 'no-store' })
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
  // field-rename-v0.5 (2026-04-20): race.org/venue/race_no → organizer_type/place_name/rr
  var raceKey    = (race.organizer_type || '') + '-' + (race.place_name || '') + (race.rr || '');

  // CUT-002: 締切到達
  if (remainMs <= 0 && cutinState.shownForRace !== raceKey + '_closed') {
    showCutin('closed', race);
    cutinState.shownForRace = raceKey + '_closed';
    notifyCutinState();   // 2026-08-05 №21: 発火済みを親へ（リロードを跨いで保持させる）
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
    notifyCutinState();   // 2026-08-05 №21: 発火済みを親へ（リロードを跨いで保持させる）
    return;
  }
}

/**
 * カットインDOM書き換え＋表示。CUTIN_DISPLAY_SEC 経過後に自動非表示。
 * 2026-06-04: type='signage' (CUT-003) 追加。表示時間は SIGNAGE_CUTIN_DISPLAY_SEC。
 *
 * 表示シーケンス (要件定義書 v3.3 §3.2 SCR-CUT-003 対応):
 *   CUT-001 (5分前)    -> 10秒で自動非表示
 *   CUT-002 (発売締切) -> 10秒で自動非表示 -> 即 CUT-003 へチェーン
 *   CUT-003 (サイネージ) -> 30秒で自動非表示 -> 通常画面に復帰
 */
function showCutin(type, race, minutesLeft) {
  var overlay = document.getElementById('cutinOverlay');
  if (!overlay) return;

  var board   = document.getElementById('cutin-board');
  var venueEl = document.getElementById('cutin-venue');
  var raceEl  = document.getElementById('cutin-race');
  var body    = document.getElementById('cutin-body');
  var footer  = document.getElementById('cutin-footer');
  var signageWrap = document.getElementById('cutin-signage');
  var signageImg  = document.getElementById('cutin-signage-image');
  if (!board || !venueEl || !raceEl || !body || !footer) return;

  // 既存タイマーをクリア (発火連鎖時の暴発防止)
  if (cutinState.hideTimer) { clearTimeout(cutinState.hideTimer); cutinState.hideTimer = null; }
  if (cutinState.chainTimer) { clearTimeout(cutinState.chainTimer); cutinState.chainTimer = null; }

  if (type === 'signage') {
    // CUT-003: サイネージカットイン (オッズエリア重畳、画像のみ)
    if (!signageWrap || !signageImg) return;
    // 画像 URL は親から受信した signage_url を使う
    if (!cutinState.signage_url) {
      // signage_url 未設定なら CUT-003 を出さず通常画面に復帰
      overlay.classList.add('is-hidden');
      cutinState.active = false;
      cutinState.type = null;
      notifyCutinState();
      return;
    }
    signageImg.src = cutinState.signage_url;
    board.classList.add('is-hidden');         // closing-timer-board を隠す
    signageWrap.classList.remove('is-hidden'); // signage を表示
    overlay.classList.remove('is-hidden');
    cutinState.active = true;
    cutinState.type = 'signage';
    notifyCutinState();   // 2026-08-05 №21: 表示中はページ送りを保留させる
    cutinState.hideTimer = setTimeout(function() {
      overlay.classList.add('is-hidden');
      signageWrap.classList.add('is-hidden');
      cutinState.active = false;
      cutinState.type = null;
      notifyCutinState();
    }, SIGNAGE_CUTIN_DISPLAY_SEC * 1000);
    return;
  }

  // CUT-001 / CUT-002: closing-timer-board (芥川 screen6 正式版)
  // field-rename-v0.5 (2026-04-20): race.venue → race.place_name、race.race_no → race.rr
  venueEl.textContent = race.place_name || '';
  raceEl.textContent  = (race.rr != null ? race.rr + 'R' : '');

  if (type === 'countdown') {
    body.className = 'closing-timer-board__body';
    body.innerHTML =
      '<span class="closing-timer-board__label">締切</span>' +
      '<span class="closing-timer-board__minutes">' + minutesLeft + '</span>' +
      '<span class="closing-timer-board__label">分前</span>';
    footer.className = 'closing-timer-board__foot';
    footer.textContent = 'お早めにご投票ください。';
  } else {
    body.className = 'closing-timer-board__body';
    body.innerHTML = '<span class="closing-timer-board__close">発売を締め切りました</span>';
    footer.className = 'closing-timer-board__foot betting-closed';
    footer.textContent = 'ご投票誠にありがとうございました';
  }

  // closing-timer-board を表示、signage を隠す
  if (signageWrap) signageWrap.classList.add('is-hidden');
  board.classList.remove('is-hidden');
  overlay.classList.remove('is-hidden');
  cutinState.active = true;
  cutinState.type = type;
  notifyCutinState();   // 2026-08-05 №21: 表示中はページ送りを保留させる

  cutinState.hideTimer = setTimeout(function() {
    // CUT-002 終了直後に CUT-003 (signage) を発火 (signage_url ありの場合)。
    //   要件定義書 v3.3 §3.2: SCR-CUT-003 (サイネージカットイン、締切後30秒程度)
    if (type === 'closed' && cutinState.signage_url) {
      // overlay は閉じずにそのまま board → signage に切替 (連続感を維持)
      showCutin('signage', race);
    } else {
      overlay.classList.add('is-hidden');
      board.classList.add('is-hidden');
      cutinState.active = false;
      cutinState.type = null;
      notifyCutinState();
    }
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
  // O-3b: オッズ未着時は '-'。取消・自己交差セルには使わない
  ODDS_EMPTY: ODDS_EMPTY,
  fmtOddsOr: fmtOddsOr,
  // O-3: オッズ配色（桁数ベース）。順位ベースの旧ルールは全廃した
  oddsColorClass: oddsColorClass,
  oddsClass: oddsClass,
  fillMinMaxCell: fillMinMaxCell,   // 複勝・ワイドの min - max セル
  fmtSex: fmtSex,          // O-2: 性齢の性別表記（セ → 騙）
  fmtWeight: fmtWeight,
  fmtWeightDiff: fmtWeightDiff,
  GENRYO_KG: GENRYO_KG,
  genryokigoOf: genryokigoOf,
  effectiveFwt: effectiveFwt,
  frameClassOf: frameClassOf,
  frameOfHorse: frameOfHorse,
  isVoidRace: isVoidRace,   // 返還レース判定（3R/6R 出走成績で使用）
  fetchWithOffset: fetchWithOffset,
  setText: setText,
  el: el,
  setRaceNumber: setRaceNumber,
  renderRaceHeader: renderRaceHeader,
  renderFrameUtan: renderFrameUtan,  // H-03
  // 指示書08: 取消馬対応
  scratchedLabel: scratchedLabel,
  scratchedLabelShort: scratchedLabelShort,
  buildScratchedSet: buildScratchedSet,
  filterScratchedFromPopular: filterScratchedFromPopular,
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
  // 2026-08-05 №22: オッズ画面のページ定義（描画パラメータ＋空判定＋親通知）
  // 2026-08-16 ISH-25: キーをテンプレ名 → ページ番号（1始まり）へ変更
  matrixPageOpts: matrixPageOpts,           // (type, page)
  matrixPageCount: matrixPageCount,         // (type)
  matrixPagePairs: matrixPagePairs,
  matrixPageHasContent: matrixPageHasContent,
  popularPageOpts: popularPageOpts,         // (page)
  popularPageCount: popularPageCount,
  popularPageHasContent: popularPageHasContent,
  notifyOddsPagesAvailability: notifyOddsPagesAvailability,  // (url, data, kind)
  MATRIX_PAGES: MATRIX_PAGES,
  POPULAR_PAGES: POPULAR_PAGES,
  // 指示書07 エラーハンドリング
  startResilientPolling: startResilientPolling,
  registerPoller: registerPoller,
  getAllPollerStatus: getAllPollerStatus,
  dumpPollerStatus: dumpPollerStatus,
  // server_time-fix-v3 (2026-04-20): テスト T22 観測用の exposure。
  //   親 window 側から document.getElementById('frameN').contentWindow.OddsDemo
  //     .getBroadcastedOffset() で各子の broadcast 受信状態（null 未受信 / 数値受信済）を確認可能。
  getBroadcastedOffset: function() { return _broadcastedServerOffset; }
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
 *
 * 構造:
 *   各 axis 馬 → <div class="screen-table__body body-{frameColor}">
 *                   <div class="screen-table__name">{axis}</div>
 *                   <div class="screen-table__row">
 *                     <div class="screen-table__number number-{frameColor}">{b}</div>
 *                     <div class="screen-table__odds [odds-cross|odds-scratched|odds-d1|odds-d3]">{oddsValue}</div>
 *                   </div>
 *                   ...
 *                 </div>
 *
 *   umaren: 各 axis に対し b = axis+1..N の行
 *   umatan: 各 axis に対し b = 1..N の行（b == axis なら odds-cross）
 */
/**
 * 馬番順マトリクスの「ページ定義」。単一の正とし、描画も空判定もここから導く。
 *
 * 2026-08-05 (引地様 №22): dp20/30 の自動ページングで 2 ページ目が真っ黒になっていた。
 *   馬連の**ページ2**は軸馬 10〜17 を出すので、少頭数のレースでは
 *   描くものが 1 つも無い（8頭・9頭の実データで実測: セル 0 個）。dp50 にある
 *   「ページが1つなら送らない」ガードが dp20/30/40 に無かった。
 *
 * ページに中身があるかは **テンプレ名から機械的に決まる**ので、親（index.html）に
 * 頭数のしきい値を書き写すと必ず腐る。ここに 1 か所だけ置き、
 *   ・テンプレは matrixPageOpts() で描画パラメータを受け取る
 *   ・notifyOddsPagesAvailability() が全ページの可否を計算して親へ通知する
 * とし、**描画と可否判定が同じ列挙関数 matrixPagePairs() を通る**ようにする。
 */
/*
 * 2026-08-16 (ISH-25): **キーをテンプレ名からページ番号へ移した。**
 *   旧: 1ページ＝1テンプレで、ページ送り＝親が iframe.src を差し替える方式だった。
 *       src が変わると iframe がまるごと再読込され、**4分割で3画面が同時に 0.33 秒暗転**する
 *       （2026-08-16 の録画をフレーム解析して実測。輝度 80.4 → 47.1 → 79.4 の10フレーム）。
 *   新: 1テンプレが全ページを描けるようにし、**親は postMessage でページ番号だけ送る**。
 *       iframe は再読込されないので暗転しない。出走成績（dp50/60）が既にこの方式で、
 *       同じ録画で暗転ゼロ・切替1〜3フレームであることを確認済み。
 *
 *   ページ番号は **1 始まり**（?page=N・setOddsPage の page と一致させる）。
 */
var MATRIX_PAGES = {
  umaren: [
    { axisFrom: 1,  axisTo: 9  },   // ページ1（dp21）
    { axisFrom: 10, axisTo: 17 }    // ページ2（dp22）
  ],
  umatan: [
    { axisFrom: 1,  axisTo: 9  },   // ページ1（dp31）
    { axisFrom: 10, axisTo: 18 }    // ページ2（dp32）
  ]
};

/** 種別とページ番号（1始まり）から描画パラメータの複製を返す。 */
function matrixPageOpts(type, page) {
  var list = MATRIX_PAGES[type];
  if (!list) {
    console.warn('[matrix-page] 未知の種別: ' + type);
    return null;
  }
  var s = list[(page || 1) - 1];
  if (!s) {
    console.warn('[matrix-page] 未定義のページ: ' + type + ' page=' + page);
    return null;
  }
  return { type: type, axisFrom: s.axisFrom, axisTo: s.axisTo };
}

/** 種別のページ数。親がローテの上限に使う。 */
function matrixPageCount(type) {
  return (MATRIX_PAGES[type] || []).length;
}

/**
 * このページに描かれる (軸, 相手[]) を列挙する。
 * renderMatrixTable の描画も、親へ返す「中身があるか」も必ずここを通す（二重管理をしない）。
 */
function matrixPagePairs(horses, opts) {
  var pairs = [];
  var n = (horses || []).length;
  if (!n || !opts) return pairs;
  var frameOf = {};
  horses.forEach(function(h) { frameOf[h.horse_no] = h.frame_no; });
  var axisTo = Math.min(opts.axisTo, n);
  for (var axis = opts.axisFrom; axis <= axisTo; axis++) {
    if (!frameOf[axis]) continue;                         // 該当馬なし
    var opp = [];
    // umatan は相手 1..n（自己交差セルを含む）／umaren は無順なので軸より大きい馬番のみ
    var from = (opts.type === 'umatan') ? 1 : (axis + 1);
    for (var b = from; b <= n; b++) {
      if (frameOf[b]) opp.push(b);
    }
    pairs.push({ axis: axis, frame: frameOf[axis], opp: opp });
  }
  return pairs;
}

/** このページに1セルでも描かれるか。0 なら親はこのページへページ送りしてはいけない。 */
function matrixPageHasContent(horses, opts) {
  return matrixPagePairs(horses, opts).some(function(p) { return p.opp.length > 0; });
}

/**
 * 人気順（SCR-ODD-004）のページ定義。MATRIX_PAGES と同じ考え方で単一の正とする。
 *   ①=上位1〜15位 / ②=上位16〜30位。テンプレはここから offset/limit を受け取る。
 * 2026-08-05: dp40（人気順の自動ページング）も親が template を差し替える＝iframe を
 *   リロードする作りなので、№21（カットイン再発火）も №22（中身の無いページへ送る）も
 *   同じ穴がある。dp20/30 と同じ仕組みに載せる（及川指示）。
 */
/* 2026-08-16 (ISH-25): MATRIX_PAGES と同じくページ番号キーへ移した（理由は上記）。 */
var POPULAR_PAGES = [
  { offset: 0,  limit: 15 },   // ページ1（dp41）上位 1〜15 位
  { offset: 15, limit: 15 }    // ページ2（dp42）上位 16〜30 位
];

/** ページ番号（1始まり）から人気順の描画パラメータの複製を返す。 */
function popularPageOpts(page) {
  var s = POPULAR_PAGES[(page || 1) - 1];
  if (!s) {
    console.warn('[popular-page] 未定義のページ: page=' + page);
    return null;
  }
  return { offset: s.offset, limit: s.limit };
}

/** 人気順のページ数。 */
function popularPageCount() {
  return POPULAR_PAGES.length;
}

/** 人気順の 4 賭式リスト（取消除外後）。描画側と同じ手順を通す。 */
function popularLists(data, horses) {
  return [
    filterScratchedFromPopular(data.umaren_popular,   horses, 2),
    filterScratchedFromPopular(data.umatan_popular,   horses, 2),
    filterScratchedFromPopular(data.trio_popular,     horses, 3),
    filterScratchedFromPopular(data.trifecta_popular, horses, 3)
  ];
}

/**
 * このページに 1 件でも実データが載るか。
 * 4 賭式すべてが offset に届かない（＝全欄 '-' だけ）なら中身なしとする。
 */
function popularPageHasContent(data, horses, spec) {
  if (!spec) return true;
  return popularLists(data || {}, horses || []).some(function(list) {
    return (list || []).length > spec.offset;
  });
}

/**
 * 2026-08-05 (引地様 №22): オッズ画面の各ページの「中身の有無」を親へ通知する。
 *   親（checkOddsAutoPaging）は false のページを飛ばす。
 *   **表示中の子が全ページ分を答える**ので、空のページは一度も画面に出ない
 *   （「出してから空だと分かる」方式だと一瞬黒くなる）。
 *   馬番順マトリクス（dp20/30）と人気順（dp40）の両方をここで面倒を見る。
 */
function notifyOddsPagesAvailability(dataUrl, data, kind) {
  if (window.parent === window) return;
  data = data || {};
  var horses = data.horses || [];
  // 2026-08-16 (ISH-25): キーをテンプレ名からページ番号へ。
  //   pages[i] が false のページへ親はローテしない（i は 0 始まり＝ページ i+1）。
  //   kind は 'umaren' | 'umatan' | 'popular'。**表示中の子が自分の種別の全ページを答える。**
  var pages = [];
  if (kind === 'popular') {
    POPULAR_PAGES.forEach(function(spec) {
      pages.push(popularPageHasContent(data, horses, spec));
    });
  } else if (MATRIX_PAGES[kind]) {
    MATRIX_PAGES[kind].forEach(function(spec) {
      pages.push(matrixPageHasContent(horses, {
        type: kind, axisFrom: spec.axisFrom, axisTo: spec.axisTo
      }));
    });
  } else {
    return;   // 種別不明なら通知しない（親は 1 ページ運用のまま）
  }
  try {
    window.parent.postMessage({
      type: 'oddsPagesAvailability',
      url: dataUrl,
      kind: kind,
      horses: horses.length,
      pages: pages
    }, '*');
  } catch (_) {}
}

function renderMatrixTable(container, horses, matrix, opts) {
  if (!container) return;
  var n = (horses || []).length;
  if (n === 0 || !opts) {
    container.replaceChildren();
    return;
  }

  var type = opts.type;

  // horse_no → frame_no マップ
  var frameOf = {};
  horses.forEach(function(h) { frameOf[h.horse_no] = h.frame_no; });

  // 指示書08: 取消馬の horse_no セット（軸・相手の両方で使用）
  var scratchedSet = buildScratchedSet(horses);

  // O-3 (2026-07-29): 「表示範囲の昇順上位N」による人気判定は廃止。
  //   配色は oddsColorClass()（桁数ベース）がセル単位で決めるため、事前集計は不要。

  // 2026-08-05 №22: 軸・相手の列挙は matrixPagePairs() に一本化した。
  //   親へ通知する「このページに中身があるか」と同じ関数を通すことで、
  //   描画結果と可否判定が食い違わないようにする。
  var pairs = matrixPagePairs(horses, opts);
  var fragment = document.createDocumentFragment();
  for (var pi = 0; pi < pairs.length; pi++) {
    var axis = pairs[pi].axis;
    var axisFrame = pairs[pi].frame;
    var axisScratched = !!scratchedSet[axis];
    var body = document.createElement('div');
    body.className = 'screen-table__body ' + (FRAME_BODY_CLASS[axisFrame] || '');
    if (axisScratched) body.classList.add('body-scratched');

    var name = document.createElement('div');
    name.className = 'screen-table__name';
    name.textContent = String(axis);
    body.appendChild(name);

    var opp = pairs[pi].opp;
    for (var oi = 0; oi < opp.length; oi++) {
      var bb = opp[oi];
      var bFrame = frameOf[bb];
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
        // 2026-04-22 Phase 5: type (umaren/umatan) + organizer_type で cap 適用
        var matrixBetType = (type === 'umaren' ? 'quinella' : (type === 'umatan' ? 'exacta' : type));
        if (e && typeof e.odds === 'number') {
          oddsDiv.textContent = fmtOdds(e.odds, matrixBetType, opts.organizer_type);
          // O-3: 順位ベース（昇順上位N / odds>=1000）を廃し、桁数ベースに統一
          var mCls = oddsColorClass(e.odds, matrixBetType, opts.organizer_type);
          if (mCls) oddsDiv.classList.add(mCls);
        } else {
          // O-3b: 票が入っていない／組合せが未配信 → 空欄ではなく '-'
          oddsDiv.textContent = ODDS_EMPTY;
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
