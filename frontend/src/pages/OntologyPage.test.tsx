import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OntologyPage } from "./OntologyPage";
import { renderRoute } from "../test/render";

describe("OntologyPage — FR-013 / NFR-009", () => {
  it("provides a keyboard-accessible list and provenance detail", async () => {
    Object.defineProperty(window, "innerWidth", { value: 500, configurable: true });
    const user = userEvent.setup();
    renderRoute(<OntologyPage />, "/ontology");

    expect(await screen.findByRole("table")).toBeInTheDocument();
    expect((await screen.findAllByText("분기 접근권한 검토")).length).toBeGreaterThan(0);
    const detailButtons = screen.getAllByRole("button", { name: /상세/ });
    await user.click(detailButtons[0]!);
    expect(screen.getByRole("heading", { name: /분기 접근권한 검토|전자금융업무 운영규정/ })).toBeInTheDocument();
    expect(screen.getByText("근거 provenance")).toBeInTheDocument();
  });

  it("uses approved edge provenance when live nodes do not repeat source fields", async () => {
    Object.defineProperty(window, "innerWidth", { value: 500, configurable: true });
    const payload = {
      nodes: [
        { id: "obligation:efo-report", type: "Obligation", label: "사고 보고", security_class: "internal", properties: {} },
        { id: "org:efo-owner", type: "Organization", label: "전자금융운영부", security_class: "internal", properties: {} },
      ],
      edges: [
        {
          id: "edge:efo-report",
          type: "PERFORMED_BY",
          source: "obligation:efo-report",
          target: "org:efo-owner",
          source_document: "MOCK-EFO-001",
          source_locator: "제4조 제2항",
          review_status: "APPROVED",
        },
      ],
      truncated: false,
      publication_id: "mock-live",
      graph_watermark: "mock-live",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify(payload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    renderRoute(<OntologyPage />, "/ontology");

    expect(await screen.findByText("MOCK-EFO-001")).toBeInTheDocument();
    expect(screen.getByText("제4조 제2항")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /근거 조문 열기/ })).toHaveAttribute(
      "href",
      "/regulations/MOCK-EFO-001?locator=%EC%A0%9C4%EC%A1%B0%20%EC%A0%9C2%ED%95%AD",
    );
  });
});
