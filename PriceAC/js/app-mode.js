/* App mode: basic, pro (validated analysis), simulation (Pro replay). */
var AppMode = (() => {
  const STORAGE_KEY = "priceac.app.mode";
  const MODES = ["basic", "pro", "simulation"];
  let mode = "basic";
  const listeners = new Set();

  const load = () => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (MODES.includes(saved)) {
        mode = saved;
      }
    } catch (error) {
      console.warn("Không đọc được chế độ app", error);
    }
  };

  const getMode = () => mode;
  const isPro = () => mode === "pro";
  const isBasic = () => mode === "basic";
  const isSimulation = () => mode === "simulation";
  const usesProAnalysis = () => mode === "pro" || mode === "simulation";

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
    isPro,
    isBasic,
    isSimulation,
    usesProAnalysis,
    setMode,
    toggle,
    onChange,
    load
  };
})();
