import { createServer, type Server } from "node:http";
import { afterEach, describe, expect, it } from "vitest";

import { proxyRequest } from "@/app/api/backend/[...path]/route";

let server: Server | undefined;
const originalBackendUrl = process.env.BACKEND_URL;
const originalProxyTimeout = process.env.BACKEND_PROXY_TIMEOUT_MS;

afterEach(async () => {
  if (originalBackendUrl === undefined) delete process.env.BACKEND_URL;
  else process.env.BACKEND_URL = originalBackendUrl;
  if (originalProxyTimeout === undefined) delete process.env.BACKEND_PROXY_TIMEOUT_MS;
  else process.env.BACKEND_PROXY_TIMEOUT_MS = originalProxyTimeout;
  if (server) {
    await new Promise<void>((resolve, reject) =>
      server?.close((error) => (error ? reject(error) : resolve())),
    );
    server = undefined;
  }
});

describe("backend proxy", () => {
  it("forwards the request path, query, body, and upstream response", async () => {
    server = createServer((request, response) => {
      const chunks: Buffer[] = [];
      request.on("data", (chunk: Buffer) => chunks.push(chunk));
      request.on("end", () => {
        response.writeHead(202, { "Content-Type": "application/json" });
        response.end(
          JSON.stringify({
            method: request.method,
            url: request.url,
            body: Buffer.concat(chunks).toString("utf8"),
          }),
        );
      });
    });
    await new Promise<void>((resolve) => server?.listen(0, "127.0.0.1", resolve));
    const address = server.address();
    if (!address || typeof address === "string") throw new Error("Expected TCP server address");
    process.env.BACKEND_URL = `http://127.0.0.1:${address.port}`;

    const response = await proxyRequest(
      new Request("http://frontend.local/api/backend/api/tasks?trace=1", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: '{"repo_url":"C:/projects/checkout"}',
      }),
      { params: Promise.resolve({ path: ["api", "tasks"] }) },
    );

    expect(response.status).toBe(202);
    expect(await response.json()).toEqual({
      method: "POST",
      url: "/api/tasks?trace=1",
      body: '{"repo_url":"C:/projects/checkout"}',
    });
  });

  it("returns an actionable JSON response when the backend cannot be reached", async () => {
    process.env.BACKEND_URL = "http://127.0.0.1:1";

    const response = await proxyRequest(
      new Request("http://frontend.local/api/backend/healthz"),
      { params: Promise.resolve({ path: ["healthz"] }) },
    );

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "ForgeGuard API is unavailable. Check the service connection and try again.",
    });
  });

  it("rejects paths outside the dashboard backend surface", async () => {
    const response = await proxyRequest(
      new Request("http://frontend.local/api/backend/internal/secrets"),
      { params: Promise.resolve({ path: ["internal", "secrets"] }) },
    );

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Backend route not found." });
  });

  it("returns an actionable response for malformed backend configuration", async () => {
    process.env.BACKEND_URL = "not a URL";

    const response = await proxyRequest(
      new Request("http://frontend.local/api/backend/healthz"),
      { params: Promise.resolve({ path: ["healthz"] }) },
    );

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "ForgeGuard API is unavailable. Check the server BACKEND_URL setting.",
    });
  });

  it("rejects oversized request bodies before contacting the backend", async () => {
    process.env.BACKEND_URL = "http://127.0.0.1:1";

    const response = await proxyRequest(
      new Request("http://frontend.local/api/backend/api/tasks", {
        method: "POST",
        body: "x".repeat(1_000_001),
      }),
      { params: Promise.resolve({ path: ["api", "tasks"] }) },
    );

    expect(response.status).toBe(413);
    expect(await response.json()).toEqual({ detail: "Request body is too large." });
  });

  it("returns a gateway timeout when the backend stops responding", async () => {
    server = createServer(() => undefined);
    await new Promise<void>((resolve) => server?.listen(0, "127.0.0.1", resolve));
    const address = server.address();
    if (!address || typeof address === "string") throw new Error("Expected TCP server address");
    process.env.BACKEND_URL = `http://127.0.0.1:${address.port}`;
    process.env.BACKEND_PROXY_TIMEOUT_MS = "25";

    const response = await proxyRequest(
      new Request("http://frontend.local/api/backend/healthz"),
      { params: Promise.resolve({ path: ["healthz"] }) },
    );

    expect(response.status).toBe(504);
    expect(await response.json()).toEqual({
      detail: "ForgeGuard API timed out. Try again.",
    });
  });
});
