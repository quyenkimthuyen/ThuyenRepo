/* App controller: market chart and insight strip only. */
const App = (() => {
  const activateChip = (button) => {
    button.parentElement.querySelectorAll(".seg-btn").forEach((chip) => chip.classList.remove("active"));
    button.classList.add("active");
  };

  const activateAsset = (button) => {
    document.querySelectorAll(".asset-tab").forEach((tab) => {
      const isActive = tab === button;
      tab.classList.toggle("active", isActive);
      tab.setAttribute("aria-selected", String(isActive));
    });
  };

  const updateElliottChip = (snapshot) => {
    const chip = document.querySelector("#elliott-chip");
    if (!chip) {
      return;
    }

    if (!snapshot?.hasAnalysis || !snapshot.elliottLabel) {
      chip.textContent = "Elliott";
      chip.classList.remove("has-wave");
      chip.title = "Sóng Elliott · khung tuần 10 năm";
      return;
    }

    chip.textContent = snapshot.elliottLabel
      .replace(/^Sóng\s+/, "")
      .replace(/\s+tăng$/, " ↑")
      .replace(/\s+giảm$/, " ↓");
    chip.classList.add("has-wave");
    chip.title = snapshot.elliottLabel;
  };

  const updateInsightStrip = (snapshot) => {
    const zoneEl = document.querySelector("#insight-zone");
    const zoneNoteEl = document.querySelector("#insight-zone-note");
    const waveEl = document.querySelector("#insight-wave");
    const trendEl = document.querySelector("#insight-trend");
    const rsiEl = document.querySelector("#insight-rsi");
    const analysisMetaEl = document.querySelector("#insight-analysis-meta");

    if (!snapshot?.hasAnalysis) {
      zoneEl.textContent = "Chưa phân tích";
      zoneNoteEl.textContent = "Bấm Phân tích 10 năm để xây bản đồ tâm lý";
      waveEl.textContent = "—";
      trendEl.textContent = snapshot ? `${snapshot.trend > 0 ? "+" : ""}${snapshot.trend}%` : "—";
      trendEl.className = snapshot && snapshot.trend >= 0 ? "is-up" : snapshot ? "is-down" : "";
      rsiEl.textContent = snapshot ? String(snapshot.rsi) : "—";
      if (analysisMetaEl) {
        analysisMetaEl.textContent = "";
      }
      updateElliottChip(snapshot);
      return;
    }

    zoneEl.textContent = snapshot.label || snapshot.zone;
    zoneNoteEl.textContent = `Giai đoạn hiện tại · ${snapshot.confidence}% khớp cấu trúc sóng`;
    waveEl.textContent = snapshot.elliottLabel || "—";
    trendEl.textContent = `${snapshot.trend > 0 ? "+" : ""}${snapshot.trend}%`;
    trendEl.className = snapshot.trend >= 0 ? "is-up" : "is-down";
    rsiEl.textContent = String(snapshot.rsi);

    if (analysisMetaEl) {
      const analyzedAt = PsychologyEngine.formatAnalyzedAt(snapshot.analyzedAt);
      analysisMetaEl.textContent = analyzedAt
        ? `Bản đồ 10 năm · ${snapshot.weekCount} tuần · lưu ${analyzedAt}`
        : `Bản đồ 10 năm · ${snapshot.weekCount} tuần`;
    }

    updateElliottChip(snapshot);
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
      const button = event.target.closest(".seg-btn");
      if (!button) {
        return;
      }

      activateChip(button);
      MarketChart.setInterval(button.dataset.interval);
    });

    document.querySelector(".chart-mode-tabs").addEventListener("click", (event) => {
      const button = event.target.closest(".seg-btn");
      if (!button) {
        return;
      }

      activateChip(button);
      MarketChart.setChartMode(button.dataset.mode);
    });

    document.querySelector(".range-tabs").addEventListener("click", (event) => {
      const button = event.target.closest(".seg-btn");
      if (!button) {
        return;
      }

      activateChip(button);
      MarketChart.setRange(button.dataset.range);
    });

    document.querySelector(".rsi-toggles")?.addEventListener("click", (event) => {
      const button = event.target.closest(".rsi-toggle");
      if (!button) {
        return;
      }

      MarketChart.toggleRsiLine(button.dataset.rsi);
    });
  };

  const init = async () => {
    bindMarketControls();
    await MarketChart.init(updateInsightStrip);
  };

  return {
    init
  };
})();

document.addEventListener("DOMContentLoaded", App.init);
