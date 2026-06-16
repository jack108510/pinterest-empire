// Dashboard Frontend Logic

const API = '';
let summaryData = null;
let postingData = null;

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed: ${url}`);
  return res.json();
}

function formatNumber(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'k';
  return n.toLocaleString();
}

function changeClass(pct) {
  if (pct > 0) return 'positive';
  if (pct < 0) return 'negative';
  return '';
}

function changeText(pct) {
  if (pct === 0) return '';
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(0)}% vs prev 30d`;
}

async function loadData() {
  try {
    const [summary, posting] = await Promise.all([
      fetchJSON('/api/summary'),
      fetchJSON('/api/posting-stats')
    ]);
    summaryData = summary;
    postingData = posting;
    render();
  } catch (err) {
    console.error('Load error:', err);
    document.body.innerHTML = '<div style="padding:40px;text-align:center;color:#ff4757"><h2>Failed to load data</h2><p>Make sure the server is running and analytics have been fetched.</p></div>';
  }
}

function render() {
  renderHeader();
  renderEmpireTotals();
  renderPostingStatus();
  renderAccounts();
}

function renderHeader() {
  const el = document.getElementById('lastUpdated');
  if (summaryData.fetched_at) {
    const d = new Date(summaryData.fetched_at);
    el.textContent = `Last updated: ${d.toLocaleString()}`;
  }
}

function renderEmpireTotals() {
  const accounts = summaryData.accounts || [];
  
  const totals = {
    impressions: { value: 0, changes: [] },
    engagements: { value: 0, changes: [] },
    outbound_clicks: { value: 0, changes: [] },
    saves: { value: 0, changes: [] },
    total_audience: { value: 0, changes: [] }
  };

  accounts.forEach(a => {
    const m = a.metrics || {};
    for (const key of Object.keys(totals)) {
      if (m[key]) {
        totals[key].value += m[key].value || 0;
        if (m[key].change_pct) totals[key].changes.push(m[key].change_pct);
      }
    }
  });

  const labels = {
    impressions: ['totalImpressions', 'totalImpressionsChange'],
    engagements: ['totalEngagements', 'totalEngagementsChange'],
    outbound_clicks: ['totalClicks', 'totalClicksChange'],
    saves: ['totalSaves', 'totalSavesChange'],
    total_audience: ['totalAudience', 'totalAudienceChange']
  };

  for (const [key, [valId, chgId]] of Object.entries(labels)) {
    document.getElementById(valId).textContent = formatNumber(totals[key].value);
    const avgChg = totals[key].changes.length > 0
      ? totals[key].changes.reduce((a, b) => a + b, 0) / totals[key].changes.length
      : 0;
    const chgEl = document.getElementById(chgId);
    chgEl.textContent = changeText(avgChg);
    chgEl.className = `metric-change ${changeClass(avgChg)}`;
  }
}

function renderPostingStatus() {
  const grid = document.getElementById('postingGrid');
  const accounts = postingData.accounts || {};
  
  let html = '';
  for (const [acctId, stats] of Object.entries(accounts)) {
    const pct = Math.min(100, (stats.today / 100) * 100);
    const complete = stats.today >= 100;
    html += `
      <div class="posting-card">
        <div class="acct-name">${acctId}</div>
        <div class="pin-count" style="color: ${complete ? '#2ed573' : '#fff'}">${stats.today}</div>
        <div class="pin-label">pins today / 100</div>
        <div class="progress-bar">
          <div class="progress-fill ${complete ? 'complete' : ''}" style="width: ${pct}%"></div>
        </div>
        <div class="pin-label" style="margin-top:4px">30d: ${stats.last_30_days || 0} | All: ${stats.all_time || 0}</div>
      </div>
    `;
  }
  grid.innerHTML = html || '<p>No data</p>';
}

function renderAccounts() {
  const grid = document.getElementById('accountsGrid');
  const accounts = summaryData.accounts || [];

  let html = '';
  for (const acct of accounts) {
    const m = acct.metrics || {};
    const metric = (key) => {
      const d = m[key];
      if (!d) return '<div class="account-metric"><div class="val">—</div><div class="lbl">' + key.replace(/_/g, ' ') + '</div></div>';
      return `
        <div class="account-metric">
          <div class="val">${d.display || formatNumber(d.value)}</div>
          <div class="lbl">${key.replace(/_/g, ' ')}</div>
          <div class="chg ${changeClass(d.change_pct || 0)}">${d.change_pct ? `${d.change_pct > 0 ? '+' : ''}${d.change_pct.toFixed(0)}%` : ''}</div>
        </div>
      `;
    };

    html += `
      <div class="account-card">
        <div class="account-header">
          <div>
            <div class="name">${acct.account_name || acct.account_id}</div>
            <div class="handle">${acct.handle || acct.account_id}</div>
          </div>
          <div style="font-size:1.5rem">📌</div>
        </div>
        <div class="account-metrics">
          ${metric('impressions')}
          ${metric('engagements')}
          ${metric('outbound_clicks')}
          ${metric('saves')}
          ${metric('total_audience')}
          ${metric('engaged_audience')}
        </div>
      </div>
    `;
  }
  grid.innerHTML = html || '<p>No data</p>';
}

function refreshData() {
  loadData();
}

// Auto-refresh every 5 minutes
loadData();
setInterval(loadData, 5 * 60 * 1000);
