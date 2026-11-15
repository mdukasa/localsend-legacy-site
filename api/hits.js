// Old-school hit counter: adds one per page load and returns the total.
// Stores a single number in Upstash Redis. No cookies, no IP addresses, nothing else.
const KEY = 'localsend-legacy-site:hits';

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) return res.status(503).json({ error: 'counter not configured' });

  // POST counts a visit; GET only reads the total.
  const cmd = req.method === 'POST' ? 'incr' : 'get';
  try {
    const r = await fetch(`${url}/${cmd}/${encodeURIComponent(KEY)}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    const body = await r.json();
    if (!r.ok) throw new Error(body.error || r.status);
    res.status(200).json({ hits: Number(body.result) || 0 });
  } catch (e) {
    res.status(502).json({ error: 'counter unavailable' });
  }
};
