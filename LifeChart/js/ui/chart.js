let chartInstance = null;

const COLORS = {
  wealth: '#58a6ff',
  happiness: '#d29922',
  health: '#3fb950',
  knowledge: '#bc8cff',
};

export function initChart() {
  const ctx = document.getElementById('life-chart');
  if (!ctx) return;

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { label: 'Wealth', data: [], borderColor: COLORS.wealth, backgroundColor: 'transparent', tension: 0.3, pointRadius: 2 },
        { label: 'Happiness', data: [], borderColor: COLORS.happiness, backgroundColor: 'transparent', tension: 0.3, pointRadius: 2 },
        { label: 'Health', data: [], borderColor: COLORS.health, backgroundColor: 'transparent', tension: 0.3, pointRadius: 2 },
        { label: 'Knowledge', data: [], borderColor: COLORS.knowledge, backgroundColor: 'transparent', tension: 0.3, pointRadius: 2 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1c2128',
          borderColor: '#30363d',
          borderWidth: 1,
          titleColor: '#e6edf3',
          bodyColor: '#8b949e',
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(48,54,61,0.5)' },
          ticks: { color: '#8b949e', font: { size: 10 } },
        },
        y: {
          grid: { color: 'rgba(48,54,61,0.5)' },
          ticks: { color: '#8b949e', font: { size: 10 } },
          min: 0,
        },
      },
    },
  });

  ['wealth', 'happiness', 'health', 'knowledge'].forEach((key, i) => {
    const checkbox = document.getElementById(`chart-${key}`);
    if (checkbox) {
      checkbox.addEventListener('change', () => {
        chartInstance.data.datasets[i].hidden = !checkbox.checked;
        chartInstance.update();
      });
    }
  });
}

export function updateChart(state) {
  if (!chartInstance) return;

  const history = state.history;
  const labels = history.map(h => `W${h.week}`);
  if (history.length === 0 || history[history.length - 1].week !== state.week) {
    labels.push(`W${state.week}`);
  }

  const datasets = {
    wealth: [...history.map(h => h.wealth), state.wealth],
    happiness: [...history.map(h => h.happiness), state.happiness],
    health: [...history.map(h => h.health), state.health],
    knowledge: [...history.map(h => h.knowledge), state.knowledge],
  };

  chartInstance.data.labels = labels;
  chartInstance.data.datasets[0].data = datasets.wealth;
  chartInstance.data.datasets[1].data = datasets.happiness;
  chartInstance.data.datasets[2].data = datasets.health;
  chartInstance.data.datasets[3].data = datasets.knowledge;
  chartInstance.update('none');
}
