/* App controller: market chart and insight strip only. */
const App = (() => {
  const activateChip = (button) => {
    button.parentElement.querySelectorAll(".chip").forEach((chip) => chip.classList.remove("active"));
    button.classList.add("active");
  };

  const activateAsset = (button) => {
    document.querySelectorAll(".asset-tab").forEach((tab) => {
      const isActive = tab === button;
      tab.classList.toggle("active", isActive);
      tab.setAttribute("aria-selected", String(isActive));
    });
  };

  const updateInsightStrip = (evaluation) => {
    const zoneEl = document.querySelector("#insight-zone");
    const zoneNoteEl = document.querySelector("#insight-zone-note");
    const confidenceEl = document.querySelector("#insight-confidence");
    const confidenceBar = document.querySelector("#insight-confidence-bar");
    const trendEl = document.querySelector("#insight-trend");
    const rsiEl = document.querySelector("#insight-rsi");

    if (!evaluation) {
      zoneEl.textContent = "Quan sát";
      zoneNoteEl.textContent = "Theo dữ liệu hiện tại";
      confidenceEl.textContent = "—";
      confidenceBar.style.width = "0%";
      trendEl.textContent = "—";
      trendEl.className = "";
      rsiEl.textContent = "—";
      return;
    }

    const zoneLabel = PsychologyEngine.zoneLabelsVi[evaluation.possibleZone] || evaluation.possibleZone;
    zoneEl.textContent = zoneLabel;
    zoneNoteEl.textContent = evaluation.signals?.[0] || "Xác suất, không phải lời khuyên";
    confidenceEl.textContent = `${evaluation.confidence}%`;
    confidenceBar.style.width = `${evaluation.confidence}%`;
    trendEl.textContent = `${evaluation.trend > 0 ? "+" : ""}${evaluation.trend}%`;
    trendEl.className = evaluation.trend >= 0 ? "is-up" : "is-down";
    rsiEl.textContent = String(evaluation.rsi);
  };

  const bindMarketControls = () => {
    document.querySelector(".asset-switch").addEventListener("click", (event) => {
      const button = event.target.closest(".asset-tab");
      if (!button) {
        return;
      }

      activateAsset(button);
      MarketChart.setAsset(button.dataset.asset);
    });

    document.querySelector(".interval-tabs").addEventListener("click", (event) => {
      const button = event.target.closest(".chip");
      if (!button) {
        return;
      }

      activateChip(button);
      MarketChart.setInterval(button.dataset.interval);
    });

    document.querySelector(".chart-mode-tabs").addEventListener("click", (event) => {
      const button = event.target.closest(".chip");
      if (!button) {
        return;
      }

      activateChip(button);
      MarketChart.setChartMode(button.dataset.mode);
    });

    document.querySelector(".range-tabs").addEventListener("click", (event) => {
      const button = event.target.closest(".chip");
      if (!button) {
        return;
      }

      activateChip(button);
      MarketChart.setRange(button.dataset.range);
    });
  };

  const handleEvaluation = (evaluation) => {
    updateInsightStrip(evaluation);
  };

  const init = async () => {
    bindMarketControls();
    await MarketChart.init(handleEvaluation);
  };

  return {
    init
  };
})();

document.addEventListener("DOMContentLoaded", App.init);
