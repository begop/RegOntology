interface AssetsBinding {
  fetch(request: Request): Promise<Response>;
}

interface Environment {
  ASSETS: AssetsBinding;
}

interface ExecutionContext {
  passThroughOnException(): void;
  waitUntil(promise: Promise<unknown>): void;
}

const SECURITY_HEADERS = {
  "Content-Security-Policy":
    "default-src 'self'; base-uri 'self'; connect-src 'self'; font-src 'self' data:; " +
    "form-action 'self'; frame-ancestors 'none'; img-src 'self' data: blob:; " +
    "object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'",
  "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
} as const;

function withSecurityHeaders(response: Response, isAppShell = false): Response {
  const headers = new Headers(response.headers);
  for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
    headers.set(name, value);
  }
  if (isAppShell) headers.set("Cache-Control", "private, no-cache");
  return new Response(response.body, {
    headers,
    status: response.status,
    statusText: response.statusText,
  });
}

const worker = {
  async fetch(
    request: Request,
    environment: Environment,
    _context: ExecutionContext,
  ): Promise<Response> {
    const assetResponse = await environment.ASSETS.fetch(request);
    if (assetResponse.status !== 404) return withSecurityHeaders(assetResponse);

    const acceptsHtml = request.headers.get("accept")?.includes("text/html") ?? false;
    if (!acceptsHtml || !["GET", "HEAD"].includes(request.method)) {
      return withSecurityHeaders(assetResponse);
    }

    const indexUrl = new URL("/index.html", request.url);
    const indexRequest = new Request(indexUrl, request);
    const indexResponse = await environment.ASSETS.fetch(indexRequest);
    return withSecurityHeaders(indexResponse, true);
  },
};

export default worker;
