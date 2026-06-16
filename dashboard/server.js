const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3007;
const DATA_DIR = path.join(__dirname, 'data');
const PUBLIC_DIR = path.join(__dirname, 'public');

const MIME = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

function readJSON(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return null;
  }
}

function getAccountHistory(acctId) {
  const file = path.join(DATA_DIR, `${acctId}.json`);
  return readJSON(file);
}

function getPostedHistory() {
  const file = path.join(__dirname, '..', 'posted_history.json');
  return readJSON(file);
}

function getAccounts() {
  const file = path.join(__dirname, '..', 'accounts.json');
  return readJSON(file) || [];
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const pathname = url.pathname;

  // API routes
  if (pathname === '/api/summary') {
    const summary = readJSON(path.join(DATA_DIR, 'summary.json'));
    if (!summary) {
      // Build summary from individual files
      const accounts = getAccounts().filter(a => a.enabled !== false);
      const accountData = accounts.map(a => {
        const data = getAccountHistory(a.id);
        return data || { account_id: a.id, account_name: a.name, metrics: {} };
      });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        fetched_at: new Date().toISOString(),
        total_accounts: accountData.length,
        accounts: accountData
      }));
      return;
    }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(summary));
    return;
  }

  if (pathname.startsWith('/api/account/')) {
    const acctId = pathname.split('/')[3];
    const data = getAccountHistory(acctId);
    if (!data) {
      res.writeHead(404);
      res.end(JSON.stringify({ error: 'Account not found' }));
      return;
    }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(data));
    return;
  }

  if (pathname === '/api/posting-stats') {
    // Today's posting counts from posted_history.json
    const history = getPostedHistory();
    const today = new Date().toISOString().slice(0, 10);
    const stats = {};
    if (history) {
      for (const [acctId, pins] of Object.entries(history)) {
        if (Array.isArray(pins)) {
          const todayPins = pins.filter(p => (p.date || '').startsWith(today));
          const last30 = pins.filter(p => {
            const d = new Date(p.date);
            const cutoff = new Date();
            cutoff.setDate(cutoff.getDate() - 30);
            return d >= cutoff;
          });
          stats[acctId] = {
            today: todayPins.length,
            last_30_days: last30.length,
            all_time: pins.length,
            last_post: pins.length > 0 ? pins[pins.length - 1].date : null
          };
        }
      }
    }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ date: today, accounts: stats }));
    return;
  }

  if (pathname === '/api/accounts') {
    const accounts = getAccounts().map(a => ({
      id: a.id,
      name: a.name,
      enabled: a.enabled !== false,
      boards: (a.boards || []).length,
      products: (a.products || []).length
    }));
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(accounts));
    return;
  }

  // Static files
  let filePath = pathname === '/' ? '/index.html' : pathname;
  filePath = path.join(PUBLIC_DIR, filePath);
  
  if (!fs.existsSync(filePath)) {
    res.writeHead(404);
    res.end('Not found');
    return;
  }

  const ext = path.extname(filePath);
  res.writeHead(200, { 'Content-Type': MIME[ext] || 'text/plain' });
  fs.createReadStream(filePath).pipe(res);
});

server.listen(PORT, () => {
  console.log(`📊 Pinterest Empire Dashboard running at http://localhost:${PORT}`);
});
