/* App controller: wires navigation, charts, probabilities, dashboard, and storage. */
const App = (() => {
  let latestEvaluation = null;

  const setActiveScreen = (target) => {
    document.querySelectorAll(".screen").forEach((screen) => {
      screen.classList.toggle("active", screen.dataset.screen === target);
    });

    document.querySelectorAll(".nav-item").forEach((button) => {
      button.classList.toggle("active", button.dataset.target === target);
    });
  };

  const bindNavigation = () => {
    document.querySelector(".bottom-nav").addEventListener("click", (event) => {
      const button = event.target.closest(".nav-item");
      if (!button) {
        return;
      }
      setActiveScreen(button.dataset.target);
    });
  };

  const activateChip = (button) => {
    button.parentElement.querySelectorAll(".chip").forEach((chip) => chip.classList.remove("active"));
    button.classList.add("active");
  };

  const bindMarketControls = () => {
    document.querySelector("#asset-select").addEventListener("change", (event) => {
      MarketChart.setAsset(event.target.value);
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

  const updateDashboard = (entries) => {
    const latestEntry = entries[0];
    const biasSummary = BiasAnalyzer.summarize(entries);

    document.querySelector("#dashboard-sentiment").textContent = latestEvaluation
      ? `${latestEvaluation.possibleZone} ${latestEvaluation.confidence}%`
      : "Observing";
    document.querySelector("#dashboard-emotion").textContent = latestEntry
      ? latestEntry.emotion
      : "No journal yet";
    document.querySelector("#dashboard-bias").textContent = biasSummary.mostCommonBias;
    document.querySelector("#dashboard-notes").textContent = String(entries.length);
  };

  const refreshReflectionViews = (entries) => {
    const biasSummary = BiasAnalyzer.render(document.querySelector("#bias-summary"), entries);
    updateDashboard(entries);
    return biasSummary;
  };

  const handleEvaluation = (evaluation) => {
    latestEvaluation = evaluation;
    PsychologyEngine.renderCycle(document.querySelector("#cycle-path"), evaluation.possibleZone);
    PsychologyEngine.renderProbabilities(
      document.querySelector("#probability-cards"),
      document.querySelector("#radar-visual"),
      evaluation.probabilities
    );
    updateDashboard(JournalStore.read());
  };

  const bindSettings = () => {
    document.querySelector("#clear-journal").addEventListener("click", () => {
      const confirmed = confirm("Clear all local journal entries?");
      if (!confirmed) {
        return;
      }
      const entries = JournalStore.clear();
      JournalUI.refresh();
      refreshReflectionViews(entries);
    });
  };

  const init = async () => {
    bindNavigation();
    bindMarketControls();
    bindSettings();
    JournalUI.init(refreshReflectionViews);
    await MarketChart.init(handleEvaluation);
  };

  return {
    init
  };
})();

document.addEventListener("DOMContentLoaded", App.init);
