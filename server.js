/**
 * Static file server that reads security headers from app/_headers.
 *
 * app/_headers is the single source of truth post-Phase-0 migration —
 * Cloudflare serves it natively in production, and the CSP-drift gate
 * (.ss/scripts/check-csp-exceptions.py) parses the same file. Used by
 * DAST scanning and local development (`task start`).
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8080;
const ROOT = process.cwd();
const SERVE_ROOT = path.join(ROOT, 'app');
const HEADERS_PATH = path.join(ROOT, 'app', '_headers');

/**
 * Parse a Cloudflare `_headers` file into a list of {for, values} rules
 * — same {for, values} shape used elsewhere in this file. Format:
 *   /path-pattern
 *     Header-Name: value
 *     Another-Header: value
 *
 *   /other-pattern
 *     ...
 * Path patterns are at column 0; header lines are indented; '#' is a comment.
 */
function loadHeaderRules(headersPath) {
  let raw;
  try {
    raw = fs.readFileSync(headersPath, 'utf8');
  } catch (e) {
    console.warn(`Warning: could not read ${headersPath} (${e.message}) — no headers will be applied`);
    return [];
  }
  const rules = [];
  let currentPath = null;
  let currentValues = {};
  const flush = () => {
    if (currentPath !== null) rules.push({ for: currentPath, values: currentValues });
    currentPath = null;
    currentValues = {};
  };
  for (const line of raw.split('\n')) {
    const stripped = line.trim();
    if (!stripped || stripped.startsWith('#')) continue;
    if (!line.startsWith(' ') && !line.startsWith('\t')) {
      flush();
      currentPath = stripped;
    } else if (currentPath !== null) {
      const colon = stripped.indexOf(':');
      if (colon > 0) {
        const name = stripped.slice(0, colon).trim();
        const value = stripped.slice(colon + 1).trim();
        currentValues[name] = value;
      }
    }
  }
  flush();
  return rules;
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
