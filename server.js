/**
 * Static file server that reads security headers from worker/headers.json.
 *
 * worker/headers.json is the single source of truth — the Cloudflare Worker
 * (worker/index.ts) and the CSP-drift gate (.ss/scripts/check-csp-exceptions.py)
 * read the same file. Used by DAST scanning and local development (`task start`).
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8080;
const ROOT = process.cwd();
const SERVE_ROOT = path.join(ROOT, 'app');
const HEADERS_PATH = path.join(ROOT, 'worker', 'headers.json');

function loadHeaderRules(headersPath) {
  try {
    const raw = fs.readFileSync(headersPath, 'utf8');
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      console.warn(`Warning: ${headersPath} is not an array — no headers will be applied`);
      return [];
    }
    return parsed.filter(r => r && typeof r.for === 'string' && r.values && typeof r.values === 'object');
  } catch (e) {
    console.warn(`Warning: could not read ${headersPath} (${e.message}) — no headers will be applied`);
    return [];
  }
}

/**
 * Returns true if the path pattern matches the request URL path.
 * Supports exact paths and glob-style "/*" and "/prefix/*" — same semantics
 * as the Cloudflare Worker.
 */
function matchesPattern(pattern, urlPath) {
  if (pattern === '/*') return true;
  if (!pattern.endsWith('/*')) return pattern === urlPath;
  const prefix = pattern.slice(0, -1); // strip trailing *
  return urlPath.startsWith(prefix);
}

/**
 * Collect all matching headers for a given URL path, applying rules in order.
 */
function headersForPath(rules, urlPath) {
  const result = {};
  for (const rule of rules) {
    if (matchesPattern(rule.for, urlPath)) {
      Object.assign(result, rule.values);
    }
  }
  return result;
}

const HEADER_RULES = loadHeaderRules(HEADERS_PATH);

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain',
  '.xml': 'application/xml; charset=utf-8',
  '.webmanifest': 'application/manifest+json',
};

const server = http.createServer((req, res) => { // nosemgrep: problem-based-packs.insecure-transport.js-node.using-http-server.using-http-server
  // Compute headers for the global catch-all rule first (used for early error responses)
  const globalHeaders = headersForPath(HEADER_RULES, '/');

  let urlPath = req.url.split('?')[0];
  try {
    urlPath = decodeURIComponent(urlPath);
  } catch (e) {
    res.writeHead(400, globalHeaders);
    res.end('Bad Request');
    return;
  }

  // Pretty-URL: /feedback → /feedback.html. Worker does the same redirect.
  if (urlPath === '/feedback') {
    res.writeHead(301, { Location: '/feedback.html', ...globalHeaders });
    res.end();
    return;
  }

  if (urlPath === '/') urlPath = '/index.html';

  const securityHeaders = headersForPath(HEADER_RULES, urlPath);

  // Prevent directory traversal
  const filePath = path.resolve(SERVE_ROOT, urlPath.slice(1)); // nosemgrep: javascript.lang.security.audit.path-traversal.path-join-resolve-traversal.path-join-resolve-traversal
  let safePath;
  try {
    safePath = fs.realpathSync(filePath);
  } catch (e) {
    safePath = filePath;
  }
  if (!safePath.startsWith(SERVE_ROOT + path.sep) && safePath !== SERVE_ROOT) {
    res.writeHead(403, securityHeaders);
    res.end('Forbidden');
    return;
  }

  const ext = path.extname(safePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(safePath, (err, data) => {
    if (err) {
      if (err.code === 'ENOENT') {
        res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8', ...securityHeaders });
        res.end('<h1>404 Not Found</h1>');
      } else {
        res.writeHead(500, securityHeaders);
        res.end('Internal Server Error');
      }
      return;
    }
    res.writeHead(200, { 'Content-Type': contentType, ...securityHeaders });
    res.end(data);
  });
});

server.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
