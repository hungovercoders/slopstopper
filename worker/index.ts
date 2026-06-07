// Cloudflare Worker entrypoint for the SlopStopper site.
//
// Serves static assets from the [assets] binding and applies the per-path
// security headers defined in worker/headers.json. That JSON is the single
// source of truth — server.js (local dev) and check-csp-exceptions.py
// (drift gate) read the same file.

import headersConfig from "./headers.json";

type HeaderRule = { for: string; values: Record<string, string> };

const RULES = headersConfig as HeaderRule[];

function matchesPattern(pattern: string, urlPath: string): boolean {
  if (pattern === "/*") return true;
  if (!pattern.endsWith("/*")) return pattern === urlPath;
  const prefix = pattern.slice(0, -1);
  return urlPath.startsWith(prefix);
}

function headersForPath(urlPath: string): Record<string, string> {
  const result: Record<string, string> = {};
  for (const rule of RULES) {
    if (matchesPattern(rule.for, urlPath)) {
      Object.assign(result, rule.values);
    }
  }
  return result;
}

interface Env {
  ASSETS: Fetcher;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Pretty-URL: /feedback → /feedback.html (kept in sync with server.js).
    if (url.pathname === "/feedback") {
      return Response.redirect(`${url.origin}/feedback.html`, 301);
    }

    // html_handling: "none" disables the auto root → index.html lookup, so
    // rewrite explicitly. Path matching for headers still uses the original
    // pathname ("/"), so the /* rule applies as expected.
    const assetRequest =
      url.pathname === "/"
        ? new Request(new URL("/index.html", url.origin).toString(), request)
        : request;

    const response = await env.ASSETS.fetch(assetRequest);
    const next = new Response(response.body, response);
    for (const [name, value] of Object.entries(headersForPath(url.pathname))) {
      next.headers.set(name, value);
    }
    return next;
  },
};
