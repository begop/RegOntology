import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { extname, join } from "node:path";
import { pathToFileURL } from "node:url";

const root = new URL("../dist/", import.meta.url);
const workerUrl = new URL("server/index.js", root);
workerUrl.searchParams.set("verify", `${process.pid}-${Date.now()}`);
const { default: worker } = await import(workerUrl.href);

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
};

const environment = {
  ASSETS: {
    async fetch(request) {
      const pathname = new URL(request.url).pathname.replace(/^\/+/, "");
      try {
        const body = await readFile(new URL(pathname, root));
        return new Response(request.method === "HEAD" ? null : body, {
          headers: { "Content-Type": contentTypes[extname(pathname)] ?? "application/octet-stream" },
        });
      } catch {
        return new Response("Not found", { status: 404 });
      }
    },
  },
};

const context = { passThroughOnException() {}, waitUntil() {} };
const routeResponse = await worker.fetch(
  new Request("https://regontology.example/ontology", { headers: { accept: "text/html" } }),
  environment,
  context,
);
assert.equal(routeResponse.status, 200);
assert.match(routeResponse.headers.get("content-type") ?? "", /^text\/html\b/i);
assert.equal(routeResponse.headers.get("x-content-type-options"), "nosniff");
assert.match(await routeResponse.text(), /<div id="root"><\/div>/);

const apiResponse = await worker.fetch(
  new Request("https://regontology.example/api/v1/health", {
    headers: { accept: "application/json" },
  }),
  environment,
  context,
);
assert.equal(apiResponse.status, 404);

console.log(`Worker verification passed: ${join("dist", "server", "index.js")}`);
assert.equal(pathToFileURL(new URL("index.html", root).pathname).protocol, "file:");
