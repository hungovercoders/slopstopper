#!/usr/bin/env node
/*
 * Slopstopper portable static server — used by the local-first dynamic
 * check loop (smoke, accessibility, broken-links, SEO, CWV, DAST).
 *
 * Usage:
 *   node .ss/server.js                            # auto-detect SERVE_ROOT
 *   SERVE_ROOT=dist/client node .ss/server.js     # explicit root
 *   PORT=8000 node .ss/server.js                  # alternative port
 *
 * Auto-detect probes ./dist/client, ./dist, ./build, ./out, ./public, ./app
 * in that order and picks the first one containing index.html. Pretty URLs:
 * /foo → /foo.html or /foo/index.html (whichever exists).
 *
 * No security headers are applied; this is a local development convenience,
 * not a production server. If your DAST scan needs to assert headers, run
 * it against a deployed preview URL (Cloudflare Pages PR previews etc.)
 * instead of localhost.
 */

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
	console.error('Set SERVE_ROOT explicitly, e.g. SERVE_ROOT=dist/client node .ss/server.js');
	process.exit(1);
}

const SERVE_ROOT = findServeRoot();

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

const server = http.createServer((req, res) => { // nosemgrep: problem-based-packs.insecure-transport.js-node.using-http-server.using-http-server
	let urlPath = req.url.split('?')[0];
	try {
		urlPath = decodeURIComponent(urlPath);
	} catch (e) {
		res.writeHead(400);
		res.end('Bad Request');
		return;
	}

	const target = resolveCandidate(urlPath);
	if (!target) {
		res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
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
		res.writeHead(403);
		res.end('Forbidden');
		return;
	}

	const ext = path.extname(resolved).toLowerCase();
	const contentType = MIME[ext] || 'application/octet-stream';

	fs.readFile(resolved, (err, data) => {
		if (err) {
			res.writeHead(500);
			res.end('Internal Server Error');
			return;
		}
		res.writeHead(200, { 'Content-Type': contentType });
		res.end(data);
	});
});

server.listen(PORT, () => {
	console.log(`Slopstopper server: http://localhost:${PORT}`);
	console.log(`Serving from: ${path.relative(CWD, SERVE_ROOT) || '.'}`);
});
