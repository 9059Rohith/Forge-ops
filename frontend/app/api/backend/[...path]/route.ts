type ProxyContext = {
  params: Promise<{ path: string[] }>;
};

const FORWARDED_REQUEST_HEADERS = [
  "content-type",
  "x-request-id",
  "webhook-id",
  "webhook-signature",
  "webhook-timestamp",
  "x-hub-signature-256",
  "x-github-event",
];

const FORWARDED_RESPONSE_HEADERS = ["content-type", "cache-control", "x-request-id"];
const MAX_REQUEST_BODY_BYTES = 1_000_000;
const DEFAULT_PROXY_TIMEOUT_MS = 30_000;

function configuredBackendUrl() {
  const value = new URL(process.env.BACKEND_URL || "http://127.0.0.1:8000");
  if (!["http:", "https:"].includes(value.protocol) || value.username || value.password) {
    throw new TypeError("BACKEND_URL must be an HTTP(S) origin without credentials");
  }
  return value;
}

function proxyTimeoutMs() {
  const configured = Number(process.env.BACKEND_PROXY_TIMEOUT_MS);
  return Number.isFinite(configured) && configured > 0
    ? Math.min(configured, 120_000)
    : DEFAULT_PROXY_TIMEOUT_MS;
}

function isTimeoutError(cause: unknown) {
  if (cause instanceof Error && cause.name === "TimeoutError") return true;
  return (
    cause instanceof Error
    && cause.cause instanceof Error
    && cause.cause.name === "TimeoutError"
  );
}

export async function proxyRequest(request: Request, context: ProxyContext) {
  let upstreamUrl: URL;
  try {
    const { path } = await context.params;
    if (!path.length || !["api", "healthz", "readyz"].includes(path[0])) {
      return Response.json({ detail: "Backend route not found." }, { status: 404 });
    }
    const incomingUrl = new URL(request.url);
    upstreamUrl = new URL(
      `/${path.map(encodeURIComponent).join("/")}`,
      configuredBackendUrl(),
    );
    upstreamUrl.search = incomingUrl.search;
  } catch {
    return Response.json(
      { detail: "ForgeGuard API is unavailable. Check the server BACKEND_URL setting." },
      { status: 503 },
    );
  }

  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  try {
    const declaredLength = Number(request.headers.get("content-length"));
    if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BODY_BYTES) {
      return Response.json({ detail: "Request body is too large." }, { status: 413 });
    }
    const body =
      request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.arrayBuffer();
    if (body && body.byteLength > MAX_REQUEST_BODY_BYTES) {
      return Response.json({ detail: "Request body is too large." }, { status: 413 });
    }
    const upstream = await fetch(upstreamUrl, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(proxyTimeoutMs()),
    });
    const responseHeaders = new Headers();
    for (const name of FORWARDED_RESPONSE_HEADERS) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (cause) {
    if (isTimeoutError(cause)) {
      return Response.json(
        { detail: "ForgeGuard API timed out. Try again." },
        { status: 504 },
      );
    }
    return Response.json(
      { detail: "ForgeGuard API is unavailable. Check the service connection and try again." },
      { status: 503 },
    );
  }
}

export const dynamic = "force-dynamic";
export const GET = proxyRequest;
export const POST = proxyRequest;
export const HEAD = proxyRequest;
