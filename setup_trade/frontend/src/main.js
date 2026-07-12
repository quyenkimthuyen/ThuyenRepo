import {
  loadPeriods,
  loadCandles,
  validateSetup,
  saveSetup,
  analyzePeriod,
  runBacktestExplore,
  runBacktestFinal,
  runOptimize,
  foldStep,
  backtestReportUrl,
  runValidation,
  validationReportUrl,
} from "./api.js";
import { createPriceChart, createRsiChart, syncCharts } from "./chart/candles.js";

const FOLD_PERIODS = {
  fold_a: { label: "train_2022", optimize: "bt_2023", final: "bt_2024" },
  fold_b: { label: "train_2024", optimize: "bt_2025", final: "bt_2026" },
};

const state = {
  period: "train_2022",
  foldId: "fold_a",
  entryTime: null,
  gate: null,
  tab: "chart",
};

const periodSelect = document.getElementById("period-select");
const foldSelect = document.getElementById("fold-select");
const directionSelect = document.getElementById("direction-select");
const gateStatus = document.getElementById("gate-status");
const entryTimeEl = document.getElementById("entry-time");
const detectedSetupEl = document.getElementById("detected-setup");
const gateReasonEl = document.getElementById("gate-reason");
const saveBtn = document.getElementById("save-setup");
const analyzeResult = document.getElementById("analyze-result");
const backtestResult = document.getElementById("backtest-result");
const foldResult = document.getElementById("fold-result");
const reportLink = document.getElementById("report-link");
const validationReportLink = document.getElementById("validation-report-link");

const price = createPriceChart(document.getElementById("price-chart"));
const rsiPane = createRsiChart(document.getElementById("rsi-chart"));
syncCharts(price.chart, rsiPane.chart);

function currentFold() {
  return FOLD_PERIODS[state.foldId] || FOLD_PERIODS.fold_a;
}

async function initPeriods() {
  const cfg = await loadPeriods();
  const names = Object.keys(cfg.periods || {});
  periodSelect.innerHTML = names.map((p) => `<option value="${p}">${p}</option>`).join("");
  periodSelect.value = "train_2022";
  state.period = periodSelect.value;
}

async function loadChart() {
  const data = await loadCandles(state.period, 2500);
  const candles = data.candles.map((c) => ({
    time: c.time,
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  }));
  price.candles.setData(candles);
  price.ema50.setData(data.candles.filter((c) => c.ema50).map((c) => ({ time: c.time, value: c.ema50 })));
  price.ema200.setData(data.candles.filter((c) => c.ema200).map((c) => ({ time: c.time, value: c.ema200 })));
  rsiPane.rsi.setData(data.candles.filter((c) => c.rsi14_h4).map((c) => ({ time: c.time, value: c.rsi14_h4 })));
  price.chart.timeScale().fitContent();
}

function setGate(valid, reason, detected) {
  gateStatus.textContent = valid ? "Gate PASS" : `Gate FAIL: ${reason}`;
  gateStatus.className = `gate ${valid ? "ok" : "bad"}`;
  gateReasonEl.textContent = reason;
  detectedSetupEl.textContent = detected?.setup_id || "—";
  saveBtn.disabled = !valid;
}

async function onCrosshair(time) {
  if (!time) return;
  const iso = new Date(time * 1000).toISOString();
  state.entryTime = iso;
  entryTimeEl.textContent = iso;
  const payload = {
    direction: directionSelect.value,
    entry_time: iso,
    label_period: state.period,
  };
  try {
    const gate = await validateSetup(payload);
    state.gate = gate;
    setGate(gate.valid, gate.reason, gate.detected);
  } catch (e) {
    setGate(false, e.message, null);
  }
}

price.chart.subscribeClick((param) => {
  if (param.time) onCrosshair(param.time);
});

periodSelect.addEventListener("change", () => {
  state.period = periodSelect.value;
  loadChart();
});

foldSelect.addEventListener("change", () => {
  state.foldId = foldSelect.value;
  const f = currentFold();
  periodSelect.value = f.label;
  state.period = f.label;
  loadChart();
});

directionSelect.addEventListener("change", () => {
  if (state.entryTime) onCrosshair(Math.floor(new Date(state.entryTime).getTime() / 1000));
});

saveBtn.addEventListener("click", async () => {
  if (!state.entryTime || !state.gate?.valid) return;
  await saveSetup({
    direction: directionSelect.value,
    entry_time: state.entryTime,
    label_period: state.period,
    setup_id: state.gate.detected?.setup_id,
  });
  alert("Đã lưu setup");
});

document.getElementById("run-analyze").addEventListener("click", async () => {
  analyzeResult.textContent = "Đang chạy…";
  const applyDisable = document.getElementById("apply-disable").checked;
  try {
    const r = await analyzePeriod(state.period, true, applyDisable);
    analyzeResult.textContent = JSON.stringify(r, null, 2);
  } catch (e) {
    analyzeResult.textContent = e.message;
  }
});

document.getElementById("run-explore").addEventListener("click", async () => {
  backtestResult.textContent = "Đang explore…";
  reportLink.classList.add("hidden");
  const period = currentFold().optimize;
  try {
    const r = await runBacktestExplore(period);
    backtestResult.textContent = JSON.stringify(r.metrics, null, 2);
  } catch (e) {
    backtestResult.textContent = e.message;
  }
});

document.getElementById("run-optimize").addEventListener("click", async () => {
  backtestResult.textContent = "Đang optimize (có thể mất vài phút)…";
  try {
    const r = await runOptimize(currentFold().optimize);
    backtestResult.textContent = JSON.stringify(r, null, 2);
  } catch (e) {
    backtestResult.textContent = e.message;
  }
});

document.getElementById("run-backtest").addEventListener("click", async () => {
  backtestResult.textContent = "Đang chạy final test…";
  const period = currentFold().final;
  try {
    const r = await runBacktestFinal(period);
    backtestResult.textContent = JSON.stringify({ metrics: r.metrics, pass: r.pass, monte_carlo: r.monte_carlo }, null, 2);
    reportLink.href = backtestReportUrl(period);
    reportLink.classList.remove("hidden");
  } catch (e) {
    backtestResult.textContent = e.message;
    reportLink.classList.add("hidden");
  }
});

async function runFold(step) {
  foldResult.textContent = `Đang chạy ${step}…`;
  try {
    const r = await foldStep(state.foldId, step, step === "auto_label" ? { max_add: 50 } : {});
    foldResult.textContent = JSON.stringify(r, null, 2);
    if (step === "auto_label" || step === "full_pipeline") loadChart();
  } catch (e) {
    foldResult.textContent = e.message;
  }
}

document.getElementById("fold-label-status").addEventListener("click", () => runFold("label_status"));
document.getElementById("fold-auto-label").addEventListener("click", () => runFold("auto_label"));
document.getElementById("fold-analyze").addEventListener("click", () => runFold("analyze"));
document.getElementById("fold-optimize").addEventListener("click", () => runFold("optimize"));
document.getElementById("fold-final").addEventListener("click", () => runFold("final_backtest"));
document.getElementById("fold-full").addEventListener("click", () => runFold("full_pipeline"));
document.getElementById("fold-validate").addEventListener("click", async () => {
  foldResult.textContent = "Đang chạy validation (optimize + OOS)…";
  validationReportLink.classList.add("hidden");
  try {
    const r = await runValidation(state.foldId, false);
    foldResult.textContent = [
      `VERDICT: ${r.verdict}`,
      "",
      `In-sample (${r.in_sample.period}): ${r.in_sample.trades} trades, PF ${r.in_sample.profit_factor}, PASS=${r.in_sample.pass}`,
      `OOS (${r.out_of_sample.period}): ${r.out_of_sample.trades} trades, PF ${r.out_of_sample.profit_factor}, PASS=${r.out_of_sample.pass}`,
      "",
      ...(r.warnings || []).map((w) => `⚠ ${w}`),
      "",
      JSON.stringify(r, null, 2),
    ].join("\n");
    validationReportLink.href = validationReportUrl(state.foldId);
    validationReportLink.classList.remove("hidden");
  } catch (e) {
    foldResult.textContent = e.message;
  }
});

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.tab = btn.dataset.tab;
    document.querySelectorAll(".panel-section").forEach((p) => p.classList.add("hidden"));
    document.getElementById(`panel-${state.tab}`).classList.remove("hidden");
    if (state.tab === "analyze") {
      document.getElementById("run-analyze").click();
    }
  });
});

initPeriods().then(loadChart);
