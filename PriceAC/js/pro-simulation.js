/* EMA psychology replay: walk-forward weekly checkpoints, same zones as EMA mode. */
var ProSimulation = (() => {
  const SPEEDS = [
    { id: "0.5x", label: "0.5×", ms: 900 },
    { id: "1x", label: "1×", ms: 450 },
    { id: "2x", label: "2×", ms: 220 },
    { id: "4x", label: "4×", ms: 110 },
    { id: "8x", label: "8×", ms: 55 }
  ];

  const STEP_OPTIONS = [
    { id: 1, label: "1 nến" },
    { id: 3, label: "3 nến" },
    { id: 7, label: "7 nến" }
  ];

  let state = {
    armed: false,
    playing: false,
    startDate: null,
    endDate: null,
    cursorDate: null,
    timeline: [],
    cursorIndex: 0,
    speedIndex: 1,
    stepBars: 1,
    timerId: null,
    psychologyCache: null,
    lastPsychologyWeek: null,
    psychologyCacheByWeek: new Map(),
    prewarming: false,
    prewarmReady: false,
    prewarmProgress: 0,
    prewarmTotal: 0,
    baselineCache: null,
    accuracyLog: [],
    hysteresis: null
  };

  let getContext = () => ({ fullData: [], interval: "1D", hasCache: false });
  let onFrame = () => {};
  let refreshPsychology = () => null;
  let getBaselineCache = () => null;
  let prewarmToken = 0;
  let dockResizeObserver = null;

  const syncDockHeight = () => {
    if (typeof document === "undefined" || !document.documentElement?.style) {
      return;
    }

    const dock = document.querySelector("#pro-simulation");
    if (!dock || dock.hidden || !AppMode.isSimulation()) {
      document.documentElement.style.setProperty("--sim-dock-height", "0px");
      return;
    }

    document.documentElement.style.setProperty("--sim-dock-height", `${dock.offsetHeight}px`);
  };

  const bindDockResize = () => {
    if (typeof document === "undefined" || typeof ResizeObserver === "undefined") {
      return;
    }

    const dock = document.querySelector("#pro-simulation");
    if (!dock) {
      return;
    }

    dockResizeObserver?.disconnect();
    dockResizeObserver = new ResizeObserver(() => {
      syncDockHeight();
    });
    dockResizeObserver.observe(dock);
  };

  const clampDate = (date, min, max) => {
    if (date < min) {
      return min;
    }
    if (date > max) {
      return max;
    }
    return date;
  };

  const getDataBounds = (fullData) => {
    if (!fullData?.length) {
      return { min: null, max: null };
    }

    return {
      min: fullData[0].date,
      max: fullData[fullData.length - 1].date
    };
  };

  const buildTimeline = (fullData, startDate, endDate, interval) => {
    const series = PsychologyEngine.aggregateSeries(fullData, interval);
    return series
      .filter((point) => point.date >= startDate && point.date <= endDate)
      .map((point) => point.date);
  };

  const defaultRange = (fullData) => {
    const { min, max } = getDataBounds(fullData);
    if (!min || !max) {
      return { startDate: null, endDate: null };
    }

    const end = max;
    const daily = PsychologyEngine.aggregateSeries(fullData, "1D");
    const endIndex = daily.findIndex((point) => point.date === end);
    const startIndex = Math.max(0, endIndex - 180);
    return {
      startDate: daily[startIndex]?.date || min,
      endDate: end
    };
  };

  const clearTimer = () => {
    if (state.timerId) {
      clearTimeout(state.timerId);
      state.timerId = null;
    }
  };

  let pendingFrame = false;

  const scheduleFrame = (callback) => {
    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(callback);
      return;
    }

    if (typeof setTimeout === "function") {
      setTimeout(callback, 0);
      return;
    }

    callback();
  };

  const flushFrame = () => {
    pendingFrame = false;
    onFrame();
    syncUi();
  };

  const emitFrame = () => {
    if (pendingFrame) {
      return;
    }

    pendingFrame = true;
    scheduleFrame(() => {
      pendingFrame = false;
      onFrame();
      syncUi();
    });
  };

  const clearSimPsychology = () => {
    prewarmToken += 1;
    state.psychologyCache = null;
    state.lastPsychologyWeek = null;
    state.psychologyCacheByWeek = new Map();
    state.prewarming = false;
    state.prewarmReady = false;
    state.prewarmProgress = 0;
    state.prewarmTotal = 0;
    state.baselineCache = null;
    state.accuracyLog = [];
    state.hysteresis = PsychologyEngine.createSimulationHysteresisState();
  };

  const buildAccuracyEntry = (weekKey, asOfDate, walkForwardCache) => {
    const comparison = PsychologyEngine.comparePsychologyAtDate(
      walkForwardCache,
      state.baselineCache,
      asOfDate
    );
    const distance = comparison.comparable
      ? PsychologyEngine.zoneCycleDistance(comparison.walkForwardZone, comparison.baselineZone)
      : null;

    return {
      weekKey,
      asOfDate,
      simZone: comparison.walkForwardZone,
      baselineZone: comparison.baselineZone,
      match: comparison.match,
      comparable: comparison.comparable,
      cycleDistance: distance,
      relaxedMatch: comparison.comparable && distance !== null && distance <= 2
    };
  };

  const getAccuracySummary = (cursorDate = state.cursorDate) => {
    if (!cursorDate || !state.accuracyLog.length) {
      return {
        hasAccuracy: false,
        percent: null,
        relaxedPercent: null,
        matched: 0,
        relaxedMatched: 0,
        comparable: 0,
        total: 0,
        current: null
      };
    }

    const entries = state.accuracyLog.filter((entry) => entry.asOfDate <= cursorDate);
    const comparableEntries = entries.filter((entry) => entry.comparable);
    const matched = comparableEntries.filter((entry) => entry.match).length;
    const relaxedMatched = comparableEntries.filter((entry) => entry.relaxedMatch).length;
    const currentWeek = PsychologyEngine.getWeekStart(cursorDate);
    const current = entries.find((entry) => entry.weekKey === currentWeek) || null;

    return {
      hasAccuracy: comparableEntries.length > 0,
      percent: comparableEntries.length
        ? Math.round((matched / comparableEntries.length) * 100)
        : null,
      relaxedPercent: comparableEntries.length
        ? Math.round((relaxedMatched / comparableEntries.length) * 100)
        : null,
      matched,
      relaxedMatched,
      comparable: comparableEntries.length,
      total: entries.length,
      current
    };
  };

  const buildWeeklyAsOfDates = (timeline) => {
    const byWeek = new Map();

    timeline.forEach((date) => {
      const weekKey = PsychologyEngine.getWeekStart(date);
      byWeek.set(weekKey, date);
    });

    return [...byWeek.entries()].map(([weekKey, asOfDate]) => ({ weekKey, asOfDate }));
  };

  const resolveWalkForwardCacheAtDate = (asOfDate) => {
    if (!asOfDate) {
      return null;
    }

    const weekKey = PsychologyEngine.getWeekStart(asOfDate);
    const stored = state.psychologyCacheByWeek.get(weekKey);
    if (stored && stored.rangeEnd <= asOfDate) {
      return stored;
    }

    return refreshPsychology(asOfDate);
  };

  const applyPsychologyForCursor = (cursorDate) => {
    if (!cursorDate) {
      state.psychologyCache = null;
      state.lastPsychologyWeek = null;
      return;
    }

    const weekKey = PsychologyEngine.getWeekStart(cursorDate);
    state.lastPsychologyWeek = weekKey;

    const relevant = state.accuracyLog
      .filter((entry) => entry.asOfDate <= cursorDate)
      .sort((left, right) => left.asOfDate.localeCompare(right.asOfDate));

    const hysteresis = PsychologyEngine.createSimulationHysteresisState();
    let cache = null;

    relevant.forEach((entry) => {
      const raw = resolveWalkForwardCacheAtDate(entry.asOfDate);
      if (raw) {
        cache = PsychologyEngine.applySimulationHysteresis(raw, entry.asOfDate, hysteresis);
      }
    });

    state.hysteresis = hysteresis;

    if (cache && cache.rangeEnd <= cursorDate) {
      state.psychologyCache = cache;
      return;
    }

    const raw = resolveWalkForwardCacheAtDate(cursorDate);
    state.psychologyCache = raw
      ? PsychologyEngine.applySimulationHysteresis(raw, cursorDate, hysteresis)
      : null;
    state.hysteresis = hysteresis;
  };

  const prewarmPsychologyCaches = () => {
    const token = ++prewarmToken;
    state.baselineCache = typeof getBaselineCache === "function" ? getBaselineCache() : null;
    state.accuracyLog = [];
    const checkpoints = buildWeeklyAsOfDates(state.timeline);

    state.psychologyCacheByWeek = new Map();
    state.prewarming = checkpoints.length > 0;
    state.prewarmReady = checkpoints.length === 0;
    state.prewarmProgress = 0;
    state.prewarmTotal = checkpoints.length;

    if (!checkpoints.length) {
      applyPsychologyForCursor(state.cursorDate);
      syncUi();
      return;
    }

    syncUi();

    let index = 0;
    const step = () => {
      if (token !== prewarmToken) {
        return;
      }

      if (index >= checkpoints.length) {
        state.prewarming = false;
        state.prewarmReady = true;
        applyPsychologyForCursor(state.cursorDate);
        emitFrame();
        syncUi();
        return;
      }

      const { weekKey, asOfDate } = checkpoints[index];
      const cache = refreshPsychology(asOfDate);
      if (cache) {
        state.psychologyCacheByWeek.set(weekKey, cache);
      }
      state.accuracyLog.push(buildAccuracyEntry(weekKey, asOfDate, cache));

      index += 1;
      state.prewarmProgress = index;
      syncUi();
      scheduleFrame(step);
    };

    scheduleFrame(step);
  };

  const maybeRefreshPsychology = () => {
    applyPsychologyForCursor(state.cursorDate);
  };

  const setCursorByIndex = (index, notify = true) => {
    if (!state.timeline.length) {
      return;
    }

    state.cursorIndex = Math.max(0, Math.min(index, state.timeline.length - 1));
    state.cursorDate = state.timeline[state.cursorIndex];
    state.armed = true;
    maybeRefreshPsychology();

    if (notify) {
      emitFrame();
    }
  };

  const rebuildTimeline = (notify = true) => {
    const { fullData, interval } = getContext();
    if (!state.startDate || !state.endDate || !fullData.length) {
      state.timeline = [];
      state.cursorIndex = 0;
      state.cursorDate = null;
      return;
    }

    state.timeline = buildTimeline(fullData, state.startDate, state.endDate, interval);
    if (!state.timeline.length) {
      state.cursorDate = null;
      state.cursorIndex = 0;
      return;
    }

    if (!state.cursorDate || state.cursorDate < state.startDate || state.cursorDate > state.endDate) {
      setCursorByIndex(0, false);
    } else {
      const found = state.timeline.indexOf(state.cursorDate);
      setCursorByIndex(found >= 0 ? found : state.timeline.length - 1, false);
    }

    if (notify) {
      emitFrame();
    }
  };

  const arm = (startDate, endDate) => {
    const { fullData } = getContext();
    const bounds = getDataBounds(fullData);
    if (!bounds.min || !bounds.max) {
      return false;
    }

    const start = clampDate(startDate, bounds.min, bounds.max);
    const end = clampDate(endDate, bounds.min, bounds.max);
    if (start > end) {
      return false;
    }

    state.startDate = start;
    state.endDate = end;
    state.armed = true;
    state.playing = false;
    clearTimer();
    clearSimPsychology();
    rebuildTimeline(false);
    prewarmPsychologyCaches();
    return true;
  };

  const play = () => {
    if (state.prewarming || !state.prewarmReady) {
      return;
    }
    if (!state.timeline.length) {
      applyRangeFromInputs();
    }

    if (!state.timeline.length) {
      rebuildTimeline(false);
    }

    if (!state.timeline.length) {
      return;
    }

    if (state.cursorIndex >= state.timeline.length - 1) {
      setCursorByIndex(0, true);
    }

    state.playing = true;
    state.armed = true;
    scheduleTick();
    syncUi();
  };

  const pause = () => {
    state.playing = false;
    clearTimer();
    flushFrame();
  };

  const stop = () => {
    state.playing = false;
    state.armed = false;
    clearTimer();
    state.cursorDate = null;
    state.cursorIndex = 0;
    state.timeline = [];
    clearSimPsychology();
    flushFrame();
  };

  const scheduleTick = () => {
    clearTimer();
    if (!state.playing) {
      return;
    }

    const speed = SPEEDS[state.speedIndex] || SPEEDS[1];
    state.timerId = setTimeout(() => {
      const nextIndex = state.cursorIndex + state.stepBars;
      if (nextIndex >= state.timeline.length) {
        setCursorByIndex(state.timeline.length - 1, true);
        pause();
        return;
      }

      setCursorByIndex(nextIndex, true);
      scheduleTick();
    }, speed.ms);
  };

  const seekPercent = (percent) => {
    if (!state.timeline.length) {
      return;
    }

    const index = Math.round((percent / 100) * (state.timeline.length - 1));
    pause();
    setCursorByIndex(index, true);
  };

  const isActive = () => state.armed && Boolean(state.cursorDate);

  const isPlaying = () => state.playing;

  const getCutoffDate = () => (isActive() ? state.cursorDate : null);

  const getStatus = () => {
    if (!isActive()) {
      return {
        active: false,
        playing: false,
        label: "Chế độ xem trực tiếp",
        progress: 0
      };
    }

    const progress = state.timeline.length > 1
      ? Math.round((state.cursorIndex / (state.timeline.length - 1)) * 100)
      : 100;

    return {
      active: true,
      playing: state.playing,
      prewarming: state.prewarming,
      prewarmReady: state.prewarmReady,
      prewarmProgress: state.prewarmProgress,
      prewarmTotal: state.prewarmTotal,
      label: `${state.cursorDate} · ${state.cursorIndex + 1}/${state.timeline.length}`,
      progress,
      cursorDate: state.cursorDate,
      startDate: state.startDate,
      endDate: state.endDate,
      accuracy: getAccuracySummary()
    };
  };

  const syncAccuracyUi = () => {
    const block = document.querySelector("#sim-accuracy");
    const pctEl = document.querySelector("#sim-accuracy-pct");
    const detailEl = document.querySelector("#sim-accuracy-detail");

    if (!block || !pctEl || !detailEl) {
      return;
    }

    const summary = getAccuracySummary();
    const show = state.prewarmReady && isActive() && summary.hasAccuracy;
    block.hidden = !show;

    if (!show) {
      return;
    }

    pctEl.textContent = `${summary.percent}%`;
    pctEl.classList.toggle("is-strong", summary.percent >= 50);
    pctEl.classList.toggle("is-weak", summary.percent < 35);

    const current = summary.current;
    const currentLine = current
      ? `Tuần này: ${current.match ? "Khớp" : "Lệch"}${current.relaxedMatch && !current.match ? " (gần đúng)" : ""} · ${PsychologyEngine.zoneLabelsVi[current.simZone] || "—"} vs 10Y ${PsychologyEngine.zoneLabelsVi[current.baselineZone] || "—"}`
      : "";

    detailEl.textContent = `Chính xác ${summary.matched}/${summary.comparable} tuần · gần đúng ${summary.relaxedMatched}/${summary.comparable} (${summary.relaxedPercent}%). ${currentLine} So với bản đồ 10 năm.`;
  };

  const syncVisibility = () => {
    if (typeof document === "undefined") {
      return;
    }

    const panel = document.querySelector("#pro-simulation");
    if (!panel) {
      return;
    }

    const show = AppMode.isSimulation();
    panel.hidden = !show;
    document.body.classList.toggle("pro-simulation-ready", show);
    syncDockHeight();
  };

  const syncDateInputConstraints = () => {
    if (typeof document === "undefined") {
      return;
    }

    const { fullData } = getContext();
    const bounds = getDataBounds(fullData);
    const startInput = document.querySelector("#sim-start");
    const endInput = document.querySelector("#sim-end");

    if (!startInput || !endInput || !bounds.min || !bounds.max) {
      return;
    }

    const startValue = startInput.value || state.startDate || bounds.min;
    const endValue = endInput.value || state.endDate || bounds.max;

    startInput.min = bounds.min;
    startInput.max = endValue;
    endInput.min = startValue;
    endInput.max = bounds.max;
    startInput.disabled = state.playing;
    endInput.disabled = state.playing;
  };

  const writeDateInputs = (startDate, endDate) => {
    if (typeof document === "undefined") {
      return;
    }

    const startInput = document.querySelector("#sim-start");
    const endInput = document.querySelector("#sim-end");

    if (startInput && startDate) {
      startInput.value = startDate;
    }
    if (endInput && endDate) {
      endInput.value = endDate;
    }

    syncDateInputConstraints();
  };

  const readDatesFromInputs = () => {
    if (typeof document === "undefined") {
      return { startDate: state.startDate, endDate: state.endDate };
    }

    const startInput = document.querySelector("#sim-start");
    const endInput = document.querySelector("#sim-end");
    const startDate = startInput?.value || state.startDate;
    const endDate = endInput?.value || state.endDate;

    if (startDate) {
      state.startDate = startDate;
    }
    if (endDate) {
      state.endDate = endDate;
    }

    syncDateInputConstraints();
    return { startDate: state.startDate, endDate: state.endDate };
  };

  const syncUi = () => {
    if (typeof document === "undefined") {
      return;
    }

    syncVisibility();

    const status = getStatus();
    const scrubber = document.querySelector("#sim-scrubber");
    const cursorLabel = document.querySelector("#sim-cursor-label");
    const statusEl = document.querySelector("#sim-status");
    const runBtn = document.querySelector("#sim-run");
    const pauseBtn = document.querySelector("#sim-pause");
    const stopBtn = document.querySelector("#sim-stop");

    syncDateInputConstraints();

    if (scrubber) {
      scrubber.value = String(status.progress);
      scrubber.disabled = !status.active || !state.timeline.length || state.prewarming;
    }

    if (cursorLabel) {
      cursorLabel.textContent = status.active ? status.label : "Chưa chạy giả lập EMA";
    }

    if (statusEl) {
      const speed = SPEEDS[state.speedIndex]?.label || "1×";
      const step = STEP_OPTIONS.find((item) => item.id === state.stepBars)?.label || "1 nến";

      if (state.prewarming) {
        statusEl.textContent = `Đang chuẩn bị giả lập EMA · phân tích tuần ${state.prewarmProgress}/${state.prewarmTotal} (checkpoint 1 tuần, không nhìn trước)...`;
      } else if (status.active) {
        statusEl.textContent = `Giả lập EMA · ${status.playing ? "đang chạy" : "tạm dừng"} · ${speed} · ${step}${state.psychologyCache ? ` · vùng ${state.psychologyCache.rangeEnd}` : ""}`;
      } else {
        statusEl.textContent = "Chọn khoảng thời gian, bấm Áp dụng — pre-run vùng tâm lý EMA theo tuần rồi replay.";
      }
    }

    if (runBtn) {
      runBtn.disabled = !AppMode.isSimulation() || state.prewarming || !state.prewarmReady;
      runBtn.classList.toggle("active", status.playing);
    }
    if (pauseBtn) {
      pauseBtn.disabled = !status.active;
    }
    if (stopBtn) {
      stopBtn.disabled = !status.active;
    }

    document.body.classList.toggle("is-simulating", status.active);
    document.body.classList.toggle("is-sim-playing", status.playing);
    syncAccuracyUi();
    scheduleFrame(syncDockHeight);
  };

  const applyRangeFromInputs = () => {
    const { startDate, endDate } = readDatesFromInputs();
    if (!startDate || !endDate) {
      return false;
    }

    return arm(startDate, endDate);
  };

  const seedDefaults = () => {
    const { fullData } = getContext();
    const range = defaultRange(fullData);
    state.startDate = range.startDate;
    state.endDate = range.endDate;
    writeDateInputs(range.startDate, range.endDate);
  };

  const bindUi = () => {
    if (typeof document === "undefined") {
      return;
    }

    document.querySelector("#sim-apply")?.addEventListener("click", () => {
      pause();
      applyRangeFromInputs();
    });

    document.querySelector("#sim-run")?.addEventListener("click", () => {
      if (!state.armed || !state.timeline.length) {
        applyRangeFromInputs();
      }
      play();
    });

    document.querySelector("#sim-pause")?.addEventListener("click", () => {
      pause();
    });

    document.querySelector("#sim-stop")?.addEventListener("click", () => {
      stop();
    });

    document.querySelector("#sim-scrubber")?.addEventListener("input", (event) => {
      seekPercent(Number(event.target.value));
    });

    document.querySelector("#sim-speed")?.addEventListener("change", (event) => {
      state.speedIndex = SPEEDS.findIndex((item) => item.id === event.target.value);
      if (state.speedIndex < 0) {
        state.speedIndex = 1;
      }
      syncUi();
      if (state.playing) {
        scheduleTick();
      }
    });

    document.querySelector("#sim-step")?.addEventListener("change", (event) => {
      state.stepBars = Number(event.target.value) || 1;
      syncUi();
    });

    ["#sim-start", "#sim-end"].forEach((selector) => {
      const input = document.querySelector(selector);
      input?.addEventListener("change", () => {
        pause();
        readDatesFromInputs();
      });
      input?.addEventListener("input", () => {
        if (state.playing) {
          pause();
        }
        syncDateInputConstraints();
      });
    });
  };

  const init = (options = {}) => {
    getContext = options.getContext || getContext;
    onFrame = options.onFrame || onFrame;
    refreshPsychology = options.refreshPsychology || refreshPsychology;
    getBaselineCache = options.getBaselineCache || getBaselineCache;
    bindUi();
    bindDockResize();

    if (typeof document === "undefined") {
      return;
    }

    const speedSelect = document.querySelector("#sim-speed");
    if (speedSelect && !speedSelect.options.length) {
      speedSelect.innerHTML = SPEEDS.map(
        (item) => `<option value="${item.id}">${item.label}</option>`
      ).join("");
      speedSelect.value = SPEEDS[state.speedIndex].id;
    }

    const stepSelect = document.querySelector("#sim-step");
    if (stepSelect && !stepSelect.options.length) {
      stepSelect.innerHTML = STEP_OPTIONS.map(
        (item) => `<option value="${item.id}">${item.label}</option>`
      ).join("");
      stepSelect.value = String(state.stepBars);
    }

    seedDefaults();
    syncUi();
  };

  const onModeChange = () => {
    if (!AppMode.isSimulation()) {
      stop();
    } else {
      clearSimPsychology();
      seedDefaults();
    }
    syncVisibility();
    syncUi();
  };

  const onContextChange = () => {
    pause();
    clearSimPsychology();
    seedDefaults();
    if (state.armed && state.startDate && state.endDate) {
      rebuildTimeline(false);
      prewarmPsychologyCaches();
    } else {
      emitFrame();
    }
  };

  const getPsychologyCache = () => state.psychologyCache;

  const isPrewarming = () => state.prewarming;

  const getAccuracySummaryForCursor = (cursorDate) => getAccuracySummary(cursorDate);

  return {
    SPEEDS,
    init,
    arm,
    play,
    pause,
    stop,
    seekPercent,
    isActive,
    isPlaying,
    getCutoffDate,
    getStatus,
    getPsychologyCache,
    isPrewarming,
    getAccuracySummaryForCursor,
    syncVisibility,
    syncUi,
    onModeChange,
    onContextChange,
    rebuildTimeline
  };
})();
