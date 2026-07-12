const RSI_HEIGHT_KEY = 'rsi-analyzer-rsi-height';
const DEFAULT_RSI_HEIGHT = 240;
const MIN_RSI_HEIGHT = 120;

export function initChartSplit({ chartBody, rsiPanel, splitterEl, onResize }) {
  if (!chartBody || !rsiPanel || !splitterEl) return;

  const maxHeight = () =>
    Math.max(MIN_RSI_HEIGHT, Math.floor(chartBody.clientHeight * 0.55));

  const applyHeight = (height) => {
    const clamped = Math.max(MIN_RSI_HEIGHT, Math.min(maxHeight(), height));
    chartBody.style.setProperty('--rsi-panel-height', `${clamped}px`);
    rsiPanel.style.height = `${clamped}px`;
    localStorage.setItem(RSI_HEIGHT_KEY, String(clamped));
    onResize?.();
    return clamped;
  };

  const saved = Number(localStorage.getItem(RSI_HEIGHT_KEY));
  applyHeight(saved >= MIN_RSI_HEIGHT ? saved : DEFAULT_RSI_HEIGHT);

  let dragging = false;

  const heightFromPointer = (clientY) => {
    const rect = chartBody.getBoundingClientRect();
    return rect.bottom - clientY;
  };

  const onPointerMove = (event) => {
    if (!dragging) return;
    applyHeight(heightFromPointer(event.clientY));
  };

  const stopDrag = () => {
    if (!dragging) return;
    dragging = false;
    document.body.classList.remove('resizing-chart-split');
    splitterEl.classList.remove('active');
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', stopDrag);
    window.removeEventListener('pointercancel', stopDrag);
  };

  const startDrag = (event) => {
    if (event.button !== 0) return;
    dragging = true;
    document.body.classList.add('resizing-chart-split');
    splitterEl.classList.add('active');
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', stopDrag);
    window.addEventListener('pointercancel', stopDrag);
    event.preventDefault();
  };

  splitterEl.addEventListener('pointerdown', startDrag);
}
