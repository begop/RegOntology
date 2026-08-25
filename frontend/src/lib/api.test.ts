import { describe, expect, it, vi } from "vitest";
import { getSystemStatus } from "./api";

describe("public system status — FR-017", () => {
  it("uses public health and response watermarks without calling the admin endpoint", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      void input;
      return new Response(
        JSON.stringify({
          status: "ok",
          service: "regontology-api",
          mode: "postgresql",
          publication_id: "publication-live",
          graph_status: "healthy",
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
            "X-Publication-ID": "publication-live",
            "X-Graph-Watermark": "graph-live",
          },
        },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getSystemStatus()).resolves.toEqual({
      api: "healthy",
      graph: "healthy",
      publicationId: "publication-live",
      graphWatermark: "graph-live",
      mode: "live",
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/health");
  });

  it("keeps API and graph degradation states separate", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            status: "degraded",
            mode: "postgresql",
            publication_id: "publication-live",
            graph_status: "stale",
            graph_publication_id: "publication-old",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(getSystemStatus()).resolves.toMatchObject({
      api: "degraded",
      graph: "stale",
      mode: "live",
    });
  });
});
