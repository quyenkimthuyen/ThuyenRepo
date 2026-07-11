const STORAGE_KEY = 'aitrade-sidebar-width';
const DEFAULT_WIDTH = 380;
const MIN_WIDTH = 300;
const MAX_RATIO = 0.55;

export function initSidebarResize({ layoutEl, sidebarEl, resizerEl, onResize }) {
  if (!layoutEl || !sidebarEl || !resizerEl) return;

  const saved = Number(localStorage.getItem(STORAGE_KEY));
  if (saved >= MIN_WIDTH) {
    layoutEl.style.setProperty('--sidebar-width', `${saved}px`);
  }

  let dragging = false;
  let startX = 0;
  let startWidth = 0;

  const maxWidth = () => Math.floor(window.innerWidth * MAX_RATIO);

  const applyWidth = (width) => {
    const clamped = Math.max(MIN_WIDTH, Math.min(maxWidth(), width));
    layoutEl.style.setProperty('--sidebar-width', `${clamped}px`);
    localStorage.setItem(STORAGE_KEY, String(clamped));
    onResize?.();
    return clamped;
  };

  const onPointerMove = (event) => {
    if (!dragging) return;
    const delta = event.clientX - startX;
    applyWidth(startWidth + delta);
  };

  const stopDrag = () => {
    if (!dragging) return;
    dragging = false;
    document.body.classList.remove('resizing-sidebar');
    resizerEl.classList.remove('active');
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', stopDrag);
    window.removeEventListener('pointercancel', stopDrag);
  };

  const startDrag = (event) => {
    if (event.button !== 0) return;
    dragging = true;
    startX = event.clientX;
    startWidth = sidebarEl.getBoundingClientRect().width;
    document.body.classList.add('resizing-sidebar');
    resizerEl.classList.add('active');
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', stopDrag);
    window.addEventListener('pointercancel', stopDrag);
    event.preventDefault();
  };

  resizerEl.addEventListener('pointerdown', startDrag);

  resizerEl.addEventListener('keydown', (event) => {
    const step = event.shiftKey ? 40 : 16;
    const current = sidebarEl.getBoundingClientRect().width;
    if (event.key === 'ArrowLeft') applyWidth(current - step);
    if (event.key === 'ArrowRight') applyWidth(current + step);
    if (event.key === 'Home') applyWidth(MIN_WIDTH);
    if (event.key === 'End') applyWidth(maxWidth());
  });

  window.addEventListener('resize', () => {
    const current = sidebarEl.getBoundingClientRect().width;
    if (current > maxWidth()) applyWidth(maxWidth());
    onResize?.();
  });
}

const CHART_RSI_HEIGHT_KEY = 'aitrade-chart-rsi-height';
const DEFAULT_RSI_PANEL_HEIGHT = 246;
const MIN_RSI_PANEL_HEIGHT = 120;
const MAX_RSI_PANEL_RATIO = 0.58;

export function initChartSplit({ chartBody, rsiPanel, splitterEl, onResize }) {
  if (!chartBody || !rsiPanel || !splitterEl) return;

  const maxPanelHeight = () =>
    Math.max(MIN_RSI_PANEL_HEIGHT, Math.floor(chartBody.clientHeight * MAX_RSI_PANEL_RATIO));

  const applyRsiHeight = (height) => {
    const clamped = Math.max(MIN_RSI_PANEL_HEIGHT, Math.min(maxPanelHeight(), height));
    chartBody.style.setProperty('--rsi-panel-height', `${clamped}px`);
    rsiPanel.style.height = `${clamped}px`;
    localStorage.setItem(CHART_RSI_HEIGHT_KEY, String(clamped));
    onResize?.();
    return clamped;
  };

  const saved = Number(localStorage.getItem(CHART_RSI_HEIGHT_KEY));
  applyRsiHeight(saved >= MIN_RSI_PANEL_HEIGHT ? saved : DEFAULT_RSI_PANEL_HEIGHT);

  let dragging = false;

  const heightFromPointer = (clientY) => {
    const bodyRect = chartBody.getBoundingClientRect();
    return bodyRect.bottom - clientY;
  };

  const onPointerMove = (event) => {
    if (!dragging) return;
    applyRsiHeight(heightFromPointer(event.clientY));
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
    applyRsiHeight(heightFromPointer(event.clientY));
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', stopDrag);
    window.addEventListener('pointercancel', stopDrag);
    event.preventDefault();
  };

  splitterEl.addEventListener('pointerdown', startDrag);

  splitterEl.addEventListener('keydown', (event) => {
    const step = event.shiftKey ? 24 : 8;
    const current = rsiPanel.getBoundingClientRect().height;
    if (event.key === 'ArrowUp') applyRsiHeight(current + step);
    if (event.key === 'ArrowDown') applyRsiHeight(current - step);
    if (event.key === 'Home') applyRsiHeight(MIN_RSI_PANEL_HEIGHT);
    if (event.key === 'End') applyRsiHeight(maxPanelHeight());
  });

  window.addEventListener('resize', () => {
    const current = rsiPanel.getBoundingClientRect().height;
    if (current > maxPanelHeight()) applyRsiHeight(maxPanelHeight());
    else onResize?.();
  });

  return { applyRsiHeight };
}
