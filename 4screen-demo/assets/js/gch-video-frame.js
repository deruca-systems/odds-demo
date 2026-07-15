(function () {
  "use strict";

  var STREAMS_URL = "../gch_data/gch-streams.json";
  var POLL_INTERVAL_MS = 2000;
  var FETCH_TIMEOUT_MS = 10000;
  var TOKEN_REFRESH_LEAD_MS = 5 * 60 * 60 * 1000;
  var video = document.getElementById("gch-video");
  var statusEl = document.getElementById("gch-status");

  var state = {
    channel: null,
    audioMuted: true,
    volume: 0.7,
    pollTimer: null,
    tokenTimer: null,
    hls: null,
    mediaCleanup: null,
    generation: 0,
    loadedChannel: null,
    streamIdentity: "",
    playing: false,
    authFallbackUsed: false,
    requestSerial: 0,
    latestRequest: 0,
    forceReloadPending: false,
    fetchInFlight: null,
    fetchInFlightChannel: null,
    autoplayMutedFallback: false,
  };

  function applyAudio() {
    video.muted = state.audioMuted || state.autoplayMutedFallback;
    video.volume = state.volume;
  }

  function clearTokenTimer() {
    if (state.tokenTimer !== null) {
      window.clearTimeout(state.tokenTimer);
      state.tokenTimer = null;
    }
  }

  function cleanupMediaListeners() {
    if (state.mediaCleanup) {
      state.mediaCleanup();
      state.mediaCleanup = null;
    }
  }

  function destroyPlayer() {
    state.generation += 1;
    cleanupMediaListeners();
    if (state.hls) {
      state.hls.destroy();
      state.hls = null;
    }
    video.pause();
    video.removeAttribute("src");
    video.load();
    state.loadedChannel = null;
    state.streamIdentity = "";
    state.playing = false;
  }

  function showStatus(message) {
    destroyPlayer();
    document.body.classList.remove("is-playing");
    statusEl.textContent = message;
  }

  function markPlaying(generation) {
    if (
      generation !== state.generation ||
      video.videoWidth <= 0 ||
      video.videoHeight <= 0
    ) {
      return;
    }
    cleanupMediaListeners();
    state.playing = true;
    state.authFallbackUsed = false;
    document.body.classList.add("is-playing");
  }

  function waitForVisibleVideo(generation) {
    cleanupMediaListeners();

    function onMediaProgress() {
      markPlaying(generation);
    }

    var eventNames = ["loadeddata", "playing", "resize", "timeupdate"];
    eventNames.forEach(function (eventName) {
      video.addEventListener(eventName, onMediaProgress);
    });
    state.mediaCleanup = function () {
      eventNames.forEach(function (eventName) {
        video.removeEventListener(eventName, onMediaProgress);
      });
    };

    onMediaProgress();
    function showAutoplayError() {
      if (generation === state.generation) {
        showStatus(state.channel + "ch — 自動再生が拒否されました");
      }
    }
    function tryMutedAutoplay(error) {
      if (
        generation !== state.generation ||
        !error ||
        error.name !== "NotAllowedError" ||
        video.muted
      ) {
        showAutoplayError();
        return;
      }

      state.autoplayMutedFallback = true;
      video.muted = true;
      var retryResult;
      try {
        retryResult = video.play();
      } catch (_error) {
        showAutoplayError();
        return;
      }
      if (retryResult && typeof retryResult.catch === "function") {
        retryResult.catch(showAutoplayError);
      }
    }

    var playResult;
    try {
      playResult = video.play();
    } catch (error) {
      tryMutedAutoplay(error);
      return;
    }
    if (playResult && typeof playResult.catch === "function") {
      playResult.catch(tryMutedAutoplay);
    }
  }

  function hlsErrorMessage(data) {
    var message = state.channel + "ch — HLS再生エラー";
    if (data && data.response && data.response.code) {
      message += " (HTTP " + data.response.code + ")";
    }
    return message;
  }

  function refreshStreams(forceReload) {
    if (forceReload) {
      state.forceReloadPending = true;
    }
    var capturedChannel = state.channel;
    if (
      state.fetchInFlight &&
      state.fetchInFlightChannel === capturedChannel
    ) {
      return state.fetchInFlight;
    }

    var requestId = state.requestSerial + 1;
    state.requestSerial = requestId;
    state.latestRequest = requestId;

    var abortController = null;
    if (typeof AbortController !== "undefined") {
      try {
        abortController = new AbortController();
      } catch (_error) {
        abortController = null;
      }
    }
    var fetchTimeout = null;
    if (abortController) {
      fetchTimeout = window.setTimeout(function () {
        abortController.abort();
      }, FETCH_TIMEOUT_MS);
    }
    var fetchOptions = { cache: "no-store" };
    if (abortController) {
      fetchOptions.signal = abortController.signal;
    }
    var fetchResult;
    try {
      fetchResult = fetch(STREAMS_URL, fetchOptions);
    } catch (error) {
      fetchResult = Promise.reject(error);
    }

    var requestPromise = Promise.resolve(fetchResult)
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.json();
      })
      .then(function (snapshot) {
        if (!snapshot || !Array.isArray(snapshot.channels)) {
          throw new Error("channels配列がありません");
        }
        if (
          requestId !== state.latestRequest ||
          capturedChannel !== state.channel
        ) {
          return snapshot;
        }
        var shouldForceReload = state.forceReloadPending;
        state.forceReloadPending = false;
        applySnapshot(snapshot, shouldForceReload);
        return snapshot;
      })
      .catch(function (error) {
        if (
          requestId !== state.latestRequest ||
          capturedChannel !== state.channel
        ) {
          return null;
        }
        if (state.loadedChannel !== null && state.streamIdentity) {
          if (typeof console !== "undefined" && console.error) {
            console.error("配信情報の取得に失敗しました", error);
          }
        } else {
          showStatus("配信情報の取得に失敗しました: " + error.message);
        }
        throw error;
      });

    requestPromise = requestPromise.then(
      function (result) {
        if (fetchTimeout !== null) {
          window.clearTimeout(fetchTimeout);
          fetchTimeout = null;
        }
        if (state.fetchInFlight === requestPromise) {
          state.fetchInFlight = null;
          state.fetchInFlightChannel = null;
        }
        return result;
      },
      function (error) {
        if (fetchTimeout !== null) {
          window.clearTimeout(fetchTimeout);
          fetchTimeout = null;
        }
        if (state.fetchInFlight === requestPromise) {
          state.fetchInFlight = null;
          state.fetchInFlightChannel = null;
        }
        throw error;
      }
    );
    state.fetchInFlight = requestPromise;
    state.fetchInFlightChannel = capturedChannel;
    return requestPromise;
  }

  function handleFatalHlsError(data, generation) {
    if (generation !== state.generation || !data || !data.fatal) {
      return;
    }

    var isNetworkError =
      window.Hls && data.type === window.Hls.ErrorTypes.NETWORK_ERROR;
    var responseCode =
      data && data.response ? Number(data.response.code) || 0 : 0;
    var isAuthError = responseCode === 401 || responseCode === 403;

    if (isNetworkError && isAuthError && !state.authFallbackUsed) {
      state.authFallbackUsed = true;
      refreshStreams(true).catch(function () {});
      return;
    }

    if (isNetworkError && state.hls) {
      try {
        state.hls.startLoad();
        return;
      } catch (_error) {
        showStatus(hlsErrorMessage(data));
        return;
      }
    }

    showStatus(hlsErrorMessage(data));
  }

  function startPlayback(channel, manifestUrl, streamIdentity) {
    destroyPlayer();
    var generation = state.generation;
    state.autoplayMutedFallback = false;
    state.loadedChannel = channel.num;
    state.streamIdentity = streamIdentity;
    statusEl.textContent = channel.num + "ch — 読み込み中";
    document.body.classList.remove("is-playing");
    applyAudio();

    if (window.Hls && window.Hls.isSupported()) {
      try {
        state.hls = new window.Hls({
          enableWorker: true,
          lowLatencyMode: false,
          backBufferLength: 30,
          fragLoadingMaxRetry: 6,
          levelLoadingMaxRetry: 4,
        });
        state.hls.on(window.Hls.Events.ERROR, function (_event, data) {
          handleFatalHlsError(data, generation);
        });
        state.hls.on(window.Hls.Events.MANIFEST_PARSED, function () {
          if (generation === state.generation) {
            waitForVisibleVideo(generation);
          }
        });
        state.hls.loadSource(manifestUrl);
        state.hls.attachMedia(video);
      } catch (_error) {
        showStatus(channel.num + "ch — HLSプレイヤーの開始に失敗しました");
      }
      return;
    }

    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      try {
        video.src = manifestUrl;
        video.load();
        waitForVisibleVideo(generation);
      } catch (_error) {
        showStatus(channel.num + "ch — HLS再生の開始に失敗しました");
      }
      return;
    }

    showStatus(channel.num + "ch — このブラウザはHLS再生に対応していません");
  }

  function scheduleTokenRefresh(channel) {
    clearTokenTimer();
    var expiresAt =
      channel && channel.playback && channel.playback.tokenExpiresAt;
    if (!expiresAt) {
      return;
    }

    var expiresMs = Date.parse(expiresAt);
    if (!Number.isFinite(expiresMs)) {
      return;
    }

    var delay = expiresMs - TOKEN_REFRESH_LEAD_MS - Date.now();
    state.tokenTimer = window.setTimeout(function () {
      state.tokenTimer = null;
      refreshStreams(true).catch(function () {});
    }, Math.max(1000, delay));
  }

  function applySnapshot(snapshot, forceReload) {
    var channel = null;
    snapshot.channels.some(function (entry) {
      if (entry && Number(entry.num) === state.channel) {
        channel = entry;
        return true;
      }
      return false;
    });

    if (!channel) {
      clearTokenTimer();
      showStatus(state.channel + "ch — 配信情報が見つかりません");
      return;
    }

    var manifestUrl =
      channel.playback && typeof channel.playback.manifestUrl === "string"
        ? channel.playback.manifestUrl
        : "";
    if (channel.status !== "on_air" || !manifestUrl) {
      clearTokenTimer();
      var detail =
        (channel.error && channel.error.message) ||
        channel.statusLabel ||
        (channel.status === "off_air" ? "放送休止中" : "配信できません");
      showStatus(channel.num + "ch — " + detail);
      return;
    }

    scheduleTokenRefresh(channel);
    var identity = window.DosVideoDisplay.manifestStreamKey(manifestUrl);
    if (
      !forceReload &&
      state.loadedChannel === state.channel &&
      state.streamIdentity === identity
    ) {
      applyAudio();
      return;
    }

    startPlayback(channel, manifestUrl, identity);
  }

  function startPollingOnce() {
    if (state.pollTimer === null) {
      state.pollTimer = window.setInterval(function () {
        refreshStreams(false).catch(function () {});
      }, POLL_INTERVAL_MS);
    }
  }

  window.addEventListener("message", function (event) {
    if (event.source !== window.parent) {
      return;
    }
    var config = event.data;
    if (!config || config.type !== "setGreenChannelConfig") {
      return;
    }
    if (
      typeof config.channel !== "number" ||
      !Number.isInteger(config.channel) ||
      config.channel < 1 ||
      config.channel > 5
    ) {
      return;
    }

    var channelChanged = state.channel !== config.channel;
    state.channel = config.channel;
    state.autoplayMutedFallback = false;
    state.audioMuted =
      typeof config.audio_muted === "boolean" ? config.audio_muted : true;
    state.volume =
      typeof config.volume === "number" && Number.isFinite(config.volume)
        ? Math.max(0, Math.min(1, config.volume))
        : 0.7;
    if (channelChanged) {
      state.authFallbackUsed = false;
      clearTokenTimer();
      showStatus(state.channel + "ch — 配信情報を取得中");
    }
    applyAudio();
    refreshStreams(channelChanged).catch(function () {});
    startPollingOnce();
  });
})();
