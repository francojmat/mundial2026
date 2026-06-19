const ORIGIN = "https://mundial2026-franco.fly.dev";

const ALLOWED = /^(\/mundial2026\.html|\/data\.json|\/flags\/.*\.(png|avif)|\/copa\.avif|\/)$/;

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Redirect root to the app
    if (path === "/" || path === "") {
      return Response.redirect(url.origin + "/mundial2026.html", 301);
    }

    // Block anything not explicitly allowed (source files, directory listing, etc.)
    if (!ALLOWED.test(path)) {
      return new Response("Not found", { status: 404 });
    }

    const originResp = await fetch(ORIGIN + path + url.search, {
      headers: { "User-Agent": "Cloudflare-Worker/Mundial2026" },
    });

    const headers = new Headers(originResp.headers);

    if (path.endsWith(".json")) {
      headers.set("Cache-Control", "public, max-age=30, s-maxage=30");
    } else if (path.endsWith(".html")) {
      headers.set("Cache-Control", "public, max-age=3600, s-maxage=3600");
    } else if (path.match(/\.(png|avif)$/)) {
      headers.set("Cache-Control", "public, max-age=86400, s-maxage=86400");
    }

    headers.set("X-Powered-By", "Mundial2026");

    return new Response(originResp.body, {
      status: originResp.status,
      headers,
    });
  },
};
