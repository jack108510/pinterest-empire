let summary = null;
let timeseries = null;

async function load() {
  try {
    const [sRes, tRes] = await Promise.all([
      fetch('data/summary.json'),
      fetch('data/timeseries.json'),
    ]);
    summary = await sRes.json();
    timeseries = await tRes.json();
    render();
  } catch (err) {
    console.error('Dashboard load error:', err);
    document.getElementById('kpis').innerHTML = `
      <div class="kpi">
        <div class="val">⚠️</div>
        <div class="lbl">Failed to load data</div>
      </div>`;
  }
}

function fmt(n) {
  if (!n || isNaN(n)) return '0';
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k';
  return Math.round(n).toLocaleString();
}

function render() {
  document.getElementById('updated').textContent =
    summary?.fetched_at
      ? new Date(summary.fetched_at).toLocaleDateString('en-US', {
          month: 'short', day: 'numeric', year: 'numeric'
        })
      : '—';

  const accounts = summary?.accounts || [];
  const connected = accounts.filter(
    a => {
      const m = a.metrics || {};
      return Object.keys(m).length > 0 && (m.impressions?.value || 0) > 0;
    }
  ).length;
  const total = accounts.length;

  // Use 30-day totals from summary instead of stale timeseries
  let totalImpressions = 0;
  let totalClicks = 0;
  let totalEngagements = 0;
  let totalSaves = 0;
  let totalAudience = 0;

  const accountCards = accounts.map(a => {
    const m = a.metrics || {};
    const imp = m.impressions?.value || 0;
    const eng = m.engagements?.value || 0;
    const clk = m.outbound_clicks?.value || 0;
    const sav = m.saves?.value || 0;
    const aud = m.total_audience?.value || 0;

    if (imp > 0) {
      totalImpressions += imp;
      totalClicks += clk;
      totalEngagements += eng;
      totalSaves += sav;
      totalAudience += aud;
    }

    const change = m.impressions?.change_pct || 0;
    const changeStr = change > 0 ? `+${change}%` : change < 0 ? `${change}%` : '';
    const changeClass = change > 0 ? 'pos' : change < 0 ? 'neg' : '';

    return `
      <div class="acct-card ${imp > 0 ? 'alive' : 'dead'}">
        <div class="acct-name">${a.account_name || a.account_id}</div>
        <div class="acct-id">${a.account_id}</div>
        <div class="acct-metrics">
          <span>👁 ${fmt(imp)}</span>
          <span>👆 ${fmt(clk)}</span>
          <span>💾 ${fmt(sav)}</span>
          <span class="${changeClass}">${changeStr}</span>
        </div>
      </div>`;
  }).join('');

  // KPIs — use 30-day totals
  document.getElementById('kpis').innerHTML = `
    <div class="kpi">
      <div class="val">${connected}/${total}</div>
      <div class="lbl">Accounts Active</div>
    </div>
    <div class="kpi">
      <div class="val">${fmt(totalImpressions)}</div>
      <div class="lbl">30-Day Impressions</div>
    </div>
    <div class="kpi">
      <div class="val">${fmt(totalClicks)}</div>
      <div class="lbl">30-Day Clicks</div>
    </div>
    <div class="kpi">
      <div class="val">$0</div>
      <div class="lbl">MRR</div>
    </div>
  `;

  // Chart — use timeseries if fresh, otherwise build from summary
  const daily = (timeseries?.combined || []).filter(d => d && d.impressions);
  let labels = [], cumulative = [];

  if (daily.length > 0) {
    let running = 0;
    for (const d of daily) {
      running += d.impressions || 0;
      labels.push(d.date.slice(5));
      cumulative.push(running);
    }
  } else {
    // Fallback: single point from summary totals
    labels = ['30d total'];
    cumulative = [totalImpressions];
  }

  const goalLine = labels.map(() => 1000000);
  const currentTotal = cumulative[cumulative.length - 1] || 0;
  const pct = ((currentTotal / 1000000) * 100).toFixed(1);

  document.querySelector('.goal').textContent =
    `${fmt(currentTotal)} / 1M (${pct}%)`;

  const ctx = document.getElementById('chart');
  if (window._chart) window._chart.destroy();
  window._chart = new Chart(ctx, {
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
                return fmt(ctx.parsed.y) + ' total';
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

  // Render account cards
  const cardsEl = document.getElementById('accounts');
  if (cardsEl) {
    cardsEl.innerHTML = `
      <div class="section-title">Accounts</div>
      <div class="acct-grid">${accountCards}</div>
    `;
  }
}

load();
