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
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k';
  return n.toLocaleString();
}

function render() {
  document.getElementById('updated').textContent =
    new Date(summary.fetched_at).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });

  const connected = (summary.accounts || []).filter(
    a => Object.keys(a.metrics || {}).length > 0
  ).length;
  const total = (summary.accounts || []).length;

  const daily = timeseries.combined || [];
  const yesterday = daily.length >= 2 ? daily[daily.length - 2] : null;
  const yestImp = yesterday ? yesterday.impressions : 0;
  const yestClicks = yesterday ? yesterday.clicks : 0;

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
      <div class="val">$0</div>
      <div class="lbl">MRR</div>
    </div>
  `;

  // Build cumulative impressions (running total like a stock chart)
  let running = 0;
  const labels = [];
  const cumulative = [];
  for (const d of daily) {
    running += d.impressions;
    labels.push(d.date.slice(5)); // MM-DD
    cumulative.push(running);
  }

  // Goal line at 1,000,000
  const goalLine = labels.map(() => 1000000);
  const currentTotal = running;

  // Progress %
  const pct = ((currentTotal / 1000000) * 100).toFixed(1);

  // Update goal text
  document.querySelector('.goal').textContent =
    `${fmt(currentTotal)} / 1M (${pct}%)`;

  const ctx = document.getElementById('chart');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Cumulative Impressions',
          data: cumulative,
          borderColor: '#fff',
          backgroundColor: function(context) {
            const chart = context.chart;
            const { ctx, chartArea } = chart;
            if (!chartArea) return null;
            const g = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
            g.addColorStop(0, 'rgba(255,255,255,0.12)');
            g.addColorStop(1, 'rgba(255,255,255,0)');
            return g;
          },
          fill: true,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHoverColor: '#fff',
          tension: 0.3,
        },
        {
          label: 'Goal: 1M',
          data: goalLine,
          borderColor: 'rgba(255,255,255,0.2)',
          borderDash: [6, 6],
          borderWidth: 1.5,
          pointRadius: 0,
          fill: false,
        }
      ]
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
              if (ctx.datasetIndex === 0) {
                return ctx.parsed.y.toLocaleString() + ' total';
              }
              return 'Goal: 1,000,000';
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
