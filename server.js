/**
 * Static file server that reads security headers directly from netlify.toml.
 * netlify.toml is the single source of truth — no header duplication.
 * Used by DAST scanning and local development (`task start`).
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8080;
const ROOT = process.cwd();
const SERVE_ROOT = path.join(ROOT, 'app');

/**
 * Minimal parser for the [[headers]] sections of netlify.toml.
 * Returns an array of { for: string, values: Object } rules.
 */
function parseNetlifyHeaders(tomlPath) {
  let content;
  try {
    content = fs.readFileSync(tomlPath, 'utf8');
  } catch (e) {
    console.warn(`Warning: could not read ${tomlPath} (${e.message}) — no headers will be applied`);
    return [];
  }

  const rules = [];
  let current = null;
  let inValues = false;

  for (const raw of content.split('\n')) {
    const line = raw.trim();

    if (line === '[[headers]]') {
      current = { for: null, values: {} };
      rules.push(current);
      inValues = false;
      continue;
    }

    if (!current) continue;

    if (line === '[headers.values]') {
      inValues = true;
      continue;
    }

    // Any new section ends the values block for the current rule
    if (line.startsWith('[')) {
      inValues = false;
      continue;
    }

    // Parse key = "value" pairs; values may contain anything except an unescaped closing quote
    const match = line.match(/^([^=]+?)\s*=\s*"((?:[^"\\]|\\.)*)"$/);
    if (!match) continue;

    const [, key, value] = match;

    if (inValues) {
      current.values[key.trim()] = value;
    } else if (key.trim() === 'for') {
      current.for = value;
    }
  }

  return rules.filter(r => r.for !== null);
}

/**
 * Returns true if the Netlify path pattern matches the request URL path.
 * Supports exact paths and glob-style "/*" and "/prefix/*".
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

const HEADER_RULES = parseNetlifyHeaders(path.join(ROOT, 'netlify.toml'));

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
