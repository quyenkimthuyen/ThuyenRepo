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

  const syncModeToggle = () => {
    const mode = AppMode.getMode();
    document.querySelectorAll(".mode-tab").forEach((button) => {
      const isActive = button.dataset.mode === mode;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-selected", String(isActive));
    });

    document.body.classList.toggle("app-mode-pro", mode === "pro");
    document.body.classList.toggle("app-mode-basic", mode === "basic");
  };

  const syncRsiModeLabels = () => {
    const twoDayToggle = document.querySelector('.rsi-toggle[data-rsi="twoDay"]');
    if (twoDayToggle) {
      twoDayToggle.textContent = AppMode.isPro() ? "1D" : "2D";
      twoDayToggle.title = AppMode.isPro()
        ? "RSI 1 ngày (chuẩn Pro)"
        : "RSI 2 ngày (Basic)";
    }

    const rsiNote = document.querySelector("#insight-rsi + small");
    if (rsiNote) {
      rsiNote.textContent = AppMode.isPro() ? "1D · T · Th" : "2D · T · Th";
    }
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
      return;
    }

    const confidenceLabel = snapshot.confidenceLabel || "khớp cấu trúc sóng";
    zoneEl.textContent = snapshot.label || snapshot.zone;
    zoneNoteEl.textContent = `Giai đoạn hiện tại · ${snapshot.confidence}% ${confidenceLabel}`;

    let waveText = snapshot.elliottLabel || "—";
    if (AppMode.isPro() && snapshot.elliottValidated === false) {
      waveText += " (chưa xác thực)";
    }
    waveEl.textContent = waveText;

    trendEl.textContent = `${snapshot.trend > 0 ? "+" : ""}${snapshot.trend}%`;
    trendEl.className = snapshot.trend >= 0 ? "is-up" : "is-down";
    rsiEl.textContent = String(snapshot.rsi);

    if (analysisMetaEl) {
      const analyzedAt = PsychologyEngine.formatAnalyzedAt(snapshot.analyzedAt);
      const modeTag = AppMode.isPro() ? " · Pro" : " · Basic";
      analysisMetaEl.textContent = analyzedAt
        ? `Bản đồ 10 năm · ${snapshot.weekCount} tuần · lưu ${analyzedAt}${modeTag}`
        : `Bản đồ 10 năm · ${snapshot.weekCount} tuần${modeTag}`;
    }
  };

  const bindMarketControls = () => {
    document.querySelector(".mode-switch")?.addEventListener("click", (event) => {
      const button = event.target.closest(".mode-tab");
      if (!button) {
        return;
      }

      AppMode.setMode(button.dataset.mode);
      syncModeToggle();
      syncRsiModeLabels();
    });

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

  const updateMarketUI = (snapshot) => {
    updateInsightStrip(snapshot);
    syncRsiModeLabels();
    ProAnalysis.renderProBrief(
      document.querySelector("#pro-brief"),
      AppMode.isPro() ? snapshot?.proBrief : null
    );
    ProAnalysis.renderModeComparison(
      document.querySelector("#mode-compare"),
      snapshot?.modeComparison,
      snapshot?.appMode || AppMode.getMode()
    );

    if (AppMode.isPro()) {
      ProAnalysis.renderProPanel(
        document.querySelector("#investment-panel"),
        snapshot?.investment,
        snapshot?.crossAsset
      );
    } else {
      InvestmentAdvisor.renderPanel(document.querySelector("#investment-panel"), snapshot?.investment);
    }
  };

  const init = async () => {
    syncModeToggle();
    syncRsiModeLabels();
    bindMarketControls();
    await MarketChart.init(updateMarketUI);
  };

  return {
    init
  };
})();

document.addEventListener("DOMContentLoaded", App.init);
