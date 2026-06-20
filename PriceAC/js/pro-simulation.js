/* Pro replay simulation: walk historical dates and refresh charts/indicators. */
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
    timerId: null
  };

  let getContext = () => ({ fullData: [], interval: "1D", hasCache: false });
  let onFrame = () => {};

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

  const setCursorByIndex = (index, notify = true) => {
    if (!state.timeline.length) {
      return;
    }

    state.cursorIndex = Math.max(0, Math.min(index, state.timeline.length - 1));
    state.cursorDate = state.timeline[state.cursorIndex];
    state.armed = true;

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
      state.cursorIndex = found >= 0 ? found : state.timeline.length - 1;
      state.cursorDate = state.timeline[state.cursorIndex];
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
    rebuildTimeline(true);
    return true;
  };

  const play = () => {
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
      label: `${state.cursorDate} · ${state.cursorIndex + 1}/${state.timeline.length}`,
      progress,
      cursorDate: state.cursorDate,
      startDate: state.startDate,
      endDate: state.endDate
    };
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
      scrubber.disabled = !status.active || !state.timeline.length;
    }

    if (cursorLabel) {
      cursorLabel.textContent = status.active ? status.label : "Chưa chạy giả lập";
    }

    if (statusEl) {
      const speed = SPEEDS[state.speedIndex]?.label || "1×";
      const step = STEP_OPTIONS.find((item) => item.id === state.stepBars)?.label || "1 nến";
      statusEl.textContent = status.active
        ? `Giả lập · ${status.playing ? "đang chạy" : "tạm dừng"} · ${speed} · ${step}`
        : "Chọn khoảng thời gian quá khứ, bấm Áp dụng rồi Run để xem chỉ số tiến hóa từng bước (không nhìn trước tương lai).";
    }

    if (runBtn) {
      runBtn.disabled = !AppMode.isSimulation();
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
    bindUi();

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
      seedDefaults();
    }
    syncVisibility();
    syncUi();
  };

  const onContextChange = () => {
    pause();
    seedDefaults();
    if (state.armed && state.startDate && state.endDate) {
      rebuildTimeline(true);
    } else {
      emitFrame();
    }
  };

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
    syncVisibility,
    syncUi,
    onModeChange,
    onContextChange,
    rebuildTimeline
  };
})();
