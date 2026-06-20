/* App mode: EMA psychology map and EMA-based weekly simulation replay. */
var AppMode = (() => {
  const STORAGE_KEY = "priceac.app.mode";
  const MODES = ["ema", "simulation"];
  let mode = "ema";
  const listeners = new Set();

  const load = () => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "basic" || saved === "pro") {
        mode = "ema";
        return;
      }

      if (MODES.includes(saved)) {
        mode = saved;
      }
    } catch (error) {
      console.warn("Không đọc được chế độ app", error);
    }
  };

  const getMode = () => mode;
  const isEma = () => mode === "ema";
  const isSimulation = () => mode === "simulation";
  const getPsychologyModel = () => "ema";

  const setMode = (nextMode) => {
    if (!MODES.includes(nextMode)) {
      return;
    }

    if (mode === nextMode) {
      return;
    }

    mode = nextMode;

    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch (error) {
      console.warn("Không lưu được chế độ app", error);
    }

    listeners.forEach((listener) => listener(mode));
  };

  const toggle = () => {
    const index = MODES.indexOf(mode);
    setMode(MODES[(index + 1) % MODES.length]);
  };

  const onChange = (listener) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };

  load();

  return {
    getMode,
    isEma,
    isSimulation,
    getPsychologyModel,
    setMode,
    toggle,
    onChange,
    load
  };
})();
