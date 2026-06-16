let data = null;

async function load() {
  const res = await fetch('data/summary.json');
  data = await res.json();
  render();
}

function fmt(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k';
  return n.toLocaleString();
}

function render() {
  const accounts = data.accounts || [];

  // Last updated
  document.getElementById('updated').textContent =
    'Updated ' + new Date(data.fetched_at).toLocaleString();

  // Empire total
  let totalImp = 0, totalEng = 0, totalClicks = 0, totalSaves = 0, totalAud = 0;
  accounts.forEach(a => {
    const m = a.metrics || {};
    totalImp += (m.impressions||{}).value || 0;
    totalEng += (m.engagements||{}).value || 0;
    totalClicks += (m.outbound_clicks||{}).value || 0;
    totalSaves += (m.saves||{}).value || 0;
    totalAud += (m.total_audience||{}).value || 0;
  });

  document.getElementById('totalImpressions').textContent = fmt(totalImp);
  document.getElementById('subStats').innerHTML = `
    <div class="sub-stat"><strong>${fmt(totalEng)}</strong> engagements</div>
    <div class="sub-stat"><strong>${fmt(totalClicks)}</strong> clicks</div>
    <div class="sub-stat"><strong>${fmt(totalSaves)}</strong> saves</div>
    <div class="sub-stat"><strong>${fmt(totalAud)}</strong> audience</div>
  `;

  // Accounts
  const html = accounts.map(a => {
    const m = a.metrics || {};
    const imp = (m.impressions||{}).display || '—';
    const impChg = (m.impressions||{}).change_pct || 0;
    const eng = (m.engagements||{}).display || '—';
    const saves = (m.saves||{}).display || '—';

    const hasData = Object.keys(m).length > 0;
    const name = a.account_name || a.account_id;
    const handle = a.handle || a.account_id;

    return `
      <div class="account">
        <div class="account-info">
          <h3>${name}</h3>
          <p>@${handle}</p>
          ${hasData ? '' : '<div class="warning">⚠️ Needs business account</div>'}
        </div>
        <div class="account-stats">
          <div class="stat">
            <div class="val">${imp}</div>
            <div class="lbl">Impressions</div>
            ${impChg ? `<div class="chg ${impChg > 0 ? 'up' : 'down'}">${impChg > 0 ? '+' : ''}${impChg}%</div>` : ''}
          </div>
          <div class="stat">
            <div class="val">${eng}</div>
            <div class="lbl">Engagements</div>
          </div>
          <div class="stat">
            <div class="val">${saves}</div>
            <div class="lbl">Saves</div>
          </div>
        </div>
      </div>
    `;
  }).join('');

  document.getElementById('accounts').innerHTML = html;
}

load();
