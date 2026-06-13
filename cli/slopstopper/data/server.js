#!/usr/bin/env node
/*
 * Slopstopper portable static server — bundled inside slopstopper-cli
 * and run by `slopstopper serve`. Used by the local dynamic-check loop
 * (smoke, accessibility, broken-links, SEO, CWV, DAST). Adopters who
 * need to customise can eject with `slopstopper templates eject
 * server.js` and edit `.ss/server.js`; the CLI's `serve` subcommand
 * prefers the override.
 *
 * Usage:
 *   slopstopper serve                                # auto-detect SERVE_ROOT, no headers
 *   SERVE_ROOT=dist/client slopstopper serve         # explicit root
 *   PORT=8000 slopstopper serve                      # alternative port
 *   SS_SERVER_HEADERS=worker/headers.json slopstopper serve   # apply headers
 *
 * Auto-detect probes ./dist/client, ./dist, ./build, ./out, ./public,
 * ./app in that order and picks the first one containing index.html.
 * Pretty URLs: /foo → /foo.html or /foo/index.html (whichever exists).
 *
 * Headers (optional): if SS_SERVER_HEADERS is set (or ./worker/headers.json
 * exists), the file is read as a JSON array of {for: <path-pattern>,
 * values: {Header-Name: value}} rules and applied per-path. Pattern
 * syntax matches Cloudflare's headers rules: exact paths, or `/prefix/*`
 * / `/*` globs. Used by DAST scans that assert specific security
 * headers locally.
 */

'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = parseInt(process.env.PORT || '8080', 10);
const CWD = process.cwd();


function findServeRoot() {
	if (process.env.SERVE_ROOT) {
		const abs = path.resolve(CWD, process.env.SERVE_ROOT);
		if (!fs.existsSync(abs)) {
			console.error(`SERVE_ROOT=${process.env.SERVE_ROOT} does not exist (resolved to ${abs})`);
			process.exit(1);
		}
		return abs;
	}
	const candidates = ['dist/client', 'dist', 'build', 'out', 'public', 'app'];
	for (const candidate of candidates) {
		const abs = path.resolve(CWD, candidate);
		if (fs.existsSync(path.join(abs, 'index.html'))) return abs;
	}
	console.error(`Could not auto-detect SERVE_ROOT. Tried: ${candidates.join(', ')}`);
	console.error('Set SERVE_ROOT explicitly, e.g. SERVE_ROOT=dist/client slopstopper serve');
	process.exit(1);
}


function findHeadersFile() {
	if (process.env.SS_SERVER_HEADERS) {
		const abs = path.resolve(CWD, process.env.SS_SERVER_HEADERS);
		if (!fs.existsSync(abs)) {
			console.error(`SS_SERVER_HEADERS=${process.env.SS_SERVER_HEADERS} does not exist (resolved to ${abs})`);
			process.exit(1);
		}
		return abs;
	}
	// Auto-detect slopstopper.dev-shape header file. Adopters who use
	// a different format can convert to JSON and point SS_SERVER_HEADERS at it.
	const defaultPath = path.resolve(CWD, 'worker/headers.json');
	return fs.existsSync(defaultPath) ? defaultPath : null;
}


function loadHeaderRules(headersPath) {
	if (!headersPath) return [];
	try {
		const parsed = JSON.parse(fs.readFileSync(headersPath, 'utf8'));
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


function matchesPattern(pattern, urlPath) {
	if (pattern === '/*') return true;
	if (!pattern.endsWith('/*')) return pattern === urlPath;
	const prefix = pattern.slice(0, -1); // strip trailing *
	return urlPath.startsWith(prefix);
}


function headersForPath(rules, urlPath) {
	const result = {};
	for (const rule of rules) {
		if (matchesPattern(rule.for, urlPath)) {
			Object.assign(result, rule.values);
		}
	}
	return result;
}


const SERVE_ROOT = findServeRoot();
const HEADERS_PATH = findHeadersFile();
const HEADER_RULES = loadHeaderRules(HEADERS_PATH);


const MIME = {
	'.html': 'text/html; charset=utf-8',
	'.js': 'application/javascript',
	'.mjs': 'application/javascript',
	'.css': 'text/css',
	'.json': 'application/json',
	'.png': 'image/png',
	'.jpg': 'image/jpeg',
	'.jpeg': 'image/jpeg',
	'.gif': 'image/gif',
	'.webp': 'image/webp',
	'.svg': 'image/svg+xml',
	'.ico': 'image/x-icon',
	'.txt': 'text/plain; charset=utf-8',
	'.xml': 'application/xml; charset=utf-8',
	'.webmanifest': 'application/manifest+json',
	'.woff': 'font/woff',
	'.woff2': 'font/woff2',
};


function resolveCandidate(urlPath) {
	const stripped = urlPath.endsWith('/') ? urlPath.slice(0, -1) : urlPath;
	const candidates = stripped === ''
		? [path.join(SERVE_ROOT, 'index.html')]
		: [
			path.join(SERVE_ROOT, stripped),
			path.join(SERVE_ROOT, `${stripped}.html`),
			path.join(SERVE_ROOT, stripped, 'index.html'),
		];
	for (const candidate of candidates) {
		try {
			const stat = fs.statSync(candidate);
			if (stat.isFile()) return candidate;
		} catch (_) {
			/* not found, try next */
		}
	}
	return null;
}


const server = http.createServer((req, res) => {
	let urlPath = req.url.split('?')[0];
	try {
		urlPath = decodeURIComponent(urlPath);
	} catch (e) {
		res.writeHead(400);
		res.end('Bad Request');
		return;
	}

	const securityHeaders = headersForPath(HEADER_RULES, urlPath === '' ? '/' : urlPath);

	const target = resolveCandidate(urlPath);
	if (!target) {
		res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8', ...securityHeaders });
		res.end(`<h1>404 Not Found</h1><pre>${urlPath}</pre>`);
		return;
	}

	let resolved;
	try {
		resolved = fs.realpathSync(target);
	} catch (_) {
		resolved = target;
	}
	if (!resolved.startsWith(SERVE_ROOT + path.sep) && resolved !== SERVE_ROOT) {
		res.writeHead(403, securityHeaders);
		res.end('Forbidden');
		return;
	}

	const ext = path.extname(resolved).toLowerCase();
	const contentType = MIME[ext] || 'application/octet-stream';

	fs.readFile(resolved, (err, data) => {
		if (err) {
			res.writeHead(500, securityHeaders);
			res.end('Internal Server Error');
			return;
		}
		res.writeHead(200, { 'Content-Type': contentType, ...securityHeaders });
		res.end(data);
	});
});


server.listen(PORT, () => {
	console.log(`Slopstopper server: http://localhost:${PORT}`);
	console.log(`Serving from: ${path.relative(CWD, SERVE_ROOT) || '.'}`);
	if (HEADERS_PATH) {
		console.log(`Applying headers from: ${path.relative(CWD, HEADERS_PATH)} (${HEADER_RULES.length} rule${HEADER_RULES.length === 1 ? '' : 's'})`);
	}
});
