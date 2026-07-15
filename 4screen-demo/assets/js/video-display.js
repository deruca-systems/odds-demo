(function (window) {
  "use strict";

  // place_cd (NAR コード表105) → venue_code。DB設計書 v1.11 §12.places 準拠。
  var NAR_TRACKS = {
    3: "obihiro",
    10: "morioka",
    11: "mizusawa",
    18: "urawa",
    19: "funabashi",
    20: "ooi",
    21: "kawasaki",
    22: "kanazawa",
    23: "kasamatsu",
    24: "nagoya",
    27: "sonoda",
    28: "himeji",
    31: "kouchi",
    32: "saga",
    36: "monbetsu",
  };

  function numericValue(value) {
    if (
      typeof value !== "number" &&
      (typeof value !== "string" || value.trim() === "")
    ) {
      return null;
    }

    var numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }

  function integerValue(value) {
    var numeric = numericValue(value);
    return numeric !== null && numeric % 1 === 0 ? numeric : null;
  }

  function isTargetPattern(patternId) {
    var id = integerValue(patternId);
    return id === 80 || (id >= 90 && id <= 94);
  }

  function isGreenPattern(patternId) {
    var id = integerValue(patternId);
    return id >= 90 && id <= 94;
  }

  function greenChannel(patternId) {
    var id = integerValue(patternId);
    return isGreenPattern(id) ? id - 89 : null;
  }

  function narConfig(screen) {
    var placeCode = screen && screen.place_cd;
    var code = numericValue(placeCode);
    var track = NAR_TRACKS[code];
    if (!track) {
      return null;
    }

    var config = screen && screen.video_config;
    var volume = config ? numericValue(config.volume) : null;
    if (volume === null) {
      volume = 0.7;
    } else {
      volume = Math.max(0, Math.min(1, volume));
    }

    return {
      venue_code: track,
      quality_mode: config && config.quality_mode
        ? config.quality_mode
        : "auto",
      quality_cap: config ? config.quality_cap : undefined,
      quality_fixed: config ? config.quality_fixed : undefined,
      audio_muted:
        config && typeof config.audio_muted === "boolean"
          ? config.audio_muted
          : true,
      volume: volume,
    };
  }

  function greenConfig(screen) {
    var config = screen && screen.video_config;
    var volume = config ? numericValue(config.volume) : null;

    if (volume === null) {
      volume = 0.7;
    } else {
      volume = Math.max(0, Math.min(1, volume));
    }

    return {
      channel: greenChannel(screen && screen.display_pattern_id),
      audio_muted:
        config && typeof config.audio_muted === "boolean"
          ? config.audio_muted
          : true,
      volume: volume,
    };
  }

  function manifestStreamKey(manifestUrl) {
    if (typeof manifestUrl !== "string") {
      return "";
    }

    var match = manifestUrl.match(
      /\/gch\/([0-9a-f]{32})\/([0-9a-f]{32})\/(?:[^?#]*\/)?([^/?#]+\.m3u8)(?:[?#]|$)/i
    );
    return match
      ? match[1] + "/" + match[2] + "/" + match[3]
      : manifestUrl.split(/[?#]/, 1)[0];
  }

  window.DosVideoDisplay = {
    isTargetPattern: isTargetPattern,
    isGreenPattern: isGreenPattern,
    greenChannel: greenChannel,
    narConfig: narConfig,
    greenConfig: greenConfig,
    manifestStreamKey: manifestStreamKey,
  };
})(window);
