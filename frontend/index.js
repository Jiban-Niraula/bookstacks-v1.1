const path = require('path');
require('dotenv').config();
const express = require('express');

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5000';
const PORT = process.env.PORT || 3000;

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

/**
 * Proxy every /api/* request straight through to the Python backend.
 * The frontend holds no business logic — it just forwards the request
 * (including the Authorization header, so JWT auth works end to end)
 * and relays the response back to the browser.
 */
app.use('/api', async (req, res) => {
  const url = `${BACKEND_URL}${req.originalUrl}`;

  try {
    const headers = { 'Content-Type': 'application/json' };
    if (req.headers.authorization) {
      headers['Authorization'] = req.headers.authorization;
    }

    const init = { method: req.method, headers };
    if (!['GET', 'HEAD'].includes(req.method)) {
      init.body = JSON.stringify(req.body || {});
    }

    const backendRes = await fetch(url, init);
    const data = await backendRes.json().catch(() => ({}));
    res.status(backendRes.status).json(data);
  } catch (err) {
    res.status(502).json({ error: `Backend unreachable at ${BACKEND_URL}. Is it running?` });
  }
});

app.listen(PORT, () => {
  console.log(`Frontend listening on port ${PORT}`);
  console.log(`Proxying /api/* to ${BACKEND_URL}`);
});
