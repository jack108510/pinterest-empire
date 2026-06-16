let summary = null;
let timeseries = null;

async function load() {
  const [s, t] = await Promise.all([
    fetch('data/summary.json').then(r => r.json()),
    fetch('data/timeseries.json').then(r => r.json()),
  ]);
  summary = s;
  timeseries = t;
  render();
}

function fmt(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k';
  return n.toLocaleString();
}

function render() {
  // Updated
  document.getElementById('updated').textContent =
    new Date(summary.fetched_at).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });

  // Accounts connected
  const connected = (summary.accounts || []).filter(
    a => Object.keys(a.metrics || {}).length > 0
  ).length;
  const total = (summary.accounts || []).length;

  // Yesterday's stats from timeseries
  const daily = timeseries.combined || [];
  const yesterday = daily.length >= 2 ? daily[daily.length - 2] : null;
  const yestImp = yesterday ? yesterday.impressions : 0;
  const yestClicks = yesterday ? yesterday.clicks : 0;

  // MRR — placeholder, update when you have revenue data
  const mrr = '$0';

  // KPIs
  document.getElementById('kpis').innerHTML = `
    <div class="kpi">
      <div class="val">${connected}/${total}</div>
      <div class="lbl">Accounts Connected</div>
    </div>
    <div class="kpi">
      <div class="val">${fmt(yestImp)}</div>
      <div class="lbl">Views Yesterday</div>
    </div>
    <div class="kpi">
      <div class="val">${yestClicks}</div>
      <div class="lbl">Clicks Yesterday</div>
    </div>
    <div class="kpi">
      <div class="val">${mrr}</div>
      <div class="lbl">MRR</div>
    </div>
  `;

  // Chart
  const labels = daily.map(d => d.date.slice(5)); // MM-DD
  const impressions = daily.map(d => d.impressions);

  const ctx = document.getElementById('chart');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Daily Impressions',
        data: impressions,
        borderColor: '#fff',
        backgroundColor: function(context) {
          const chart = context.chart;
          const { ctx, chartArea } = chart;
          if (!chartArea) return null;
          const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
          gradient.addColorStop(0, 'rgba(255,255,255,0.15)');
          gradient.addColorStop(1, 'rgba(255,255,255,0)');
          return gradient;
        },
        fill: true,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverColor: '#fff',
        tension: 0.35,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#000',
          borderColor: '#333',
          borderWidth: 1,
          titleColor: '#fff',
          bodyColor: '#fff',
          padding: 12,
          callbacks: {
            label: function(ctx) {
              return ctx.parsed.y.toLocaleString() + ' impressions';
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#444', maxTicksLimit: 8, font: { size: 11 } },
          border: { color: '#222' },
        },
        y: {
          grid: { color: '#111' },
          ticks: {
            color: '#444',
            font: { size: 11 },
            callback: function(v) { return fmt(v); }
          },
          border: { display: false },
        }
      }
    }
  });
}

load();
