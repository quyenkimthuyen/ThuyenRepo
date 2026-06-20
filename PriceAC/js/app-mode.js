/* App mode: basic (legacy) vs pro (validated analysis + risk framework). */
var AppMode = (() => {
  const STORAGE_KEY = "priceac.app.mode";
  let mode = "basic";
  const listeners = new Set();

  const load = () => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "basic" || saved === "pro") {
        mode = saved;
      }
    } catch (error) {
      console.warn("Không đọc được chế độ app", error);
    }
  };

  const getMode = () => mode;
  const isPro = () => mode === "pro";
  const isBasic = () => mode === "basic";

  const setMode = (nextMode) => {
    if (nextMode !== "basic" && nextMode !== "pro") {
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
    setMode(mode === "pro" ? "basic" : "pro");
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
    setMode,
    toggle,
    onChange,
    load
  };
})();
