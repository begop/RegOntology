import { fireEvent, screen } from "@testing-library/react";
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

  it("switches to the 3D canvas and keeps node selection synchronized with the detail and list views", async () => {
    Object.defineProperty(window, "innerWidth", { value: 500, configurable: true });
    class ResizeObserverMock {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);

    const canvasContext = {
      arc: vi.fn(),
      beginPath: vi.fn(),
      clearRect: vi.fn(),
      closePath: vi.fn(),
      fill: vi.fn(),
      fillRect: vi.fn(),
      fillText: vi.fn(),
      lineTo: vi.fn(),
      measureText: vi.fn((text: string) => ({ width: text.length * 6 })),
      moveTo: vi.fn(),
      quadraticCurveTo: vi.fn(),
      restore: vi.fn(),
      save: vi.fn(),
      setTransform: vi.fn(),
      stroke: vi.fn(),
    } as unknown as CanvasRenderingContext2D;
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(canvasContext);
    const user = userEvent.setup();
    renderRoute(<OntologyPage />, "/ontology");

    const twoDimensionalButton = await screen.findByRole("button", { name: "2D 그래프" });
    const threeDimensionalButton = screen.getByRole("button", { name: "3D 캔버스" });
    expect(twoDimensionalButton).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "접근 가능한 목록" })).toHaveAttribute("aria-pressed", "true");
    expect(threeDimensionalButton).toHaveAttribute("aria-pressed", "false");

    const searchInput = await screen.findByRole("textbox", { name: "Ontology 노드 검색" });
    await user.type(searchInput, "권한");
    threeDimensionalButton.focus();
    await user.keyboard("{Enter}");
    expect(threeDimensionalButton).toHaveAttribute("aria-pressed", "true");
    const canvas = screen.getByRole("img", { name: /3D 규정 온톨로지 캔버스/ });
    expect(canvas).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "3D 캔버스 카메라 조작" })).toBeInTheDocument();

    const browserZoomEvent = new WheelEvent("wheel", { deltaY: -100, ctrlKey: true, cancelable: true });
    fireEvent(canvas, browserZoomEvent);
    expect(browserZoomEvent.defaultPrevented).toBe(false);
    const canvasZoomEvent = new WheelEvent("wheel", { deltaY: -100, cancelable: true });
    fireEvent(canvas, canvasZoomEvent);
    expect(canvasZoomEvent.defaultPrevented).toBe(true);

    await user.selectOptions(screen.getByLabelText("키보드 노드 선택"), "control:접근권한검토");
    expect(screen.getByRole("heading", { name: "접근권한 정기 검토" })).toBeInTheDocument();
    expect(screen.getByText("선택한 노드: 접근권한 정기 검토")).toBeInTheDocument();

    fireEvent(canvas, new Event("contextlost", { cancelable: true }));
    expect(await screen.findByRole("alert")).toHaveTextContent("3D 캔버스를 초기화할 수 없습니다.");
    expect(screen.queryByLabelText("키보드 노드 선택")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "목록으로 전환" }));
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "접근 가능한 목록" })).toHaveAttribute("aria-pressed", "true");
    expect(searchInput).toHaveValue("권한");
    expect(screen.getByRole("heading", { name: "접근권한 정기 검토" })).toBeInTheDocument();
    getContext.mockRestore();
  });

  it("offers the accessible list when drawing the 3D canvas fails", async () => {
    Object.defineProperty(window, "innerWidth", { value: 500, configurable: true });
    const failingContext = {
      setTransform: vi.fn(() => {
        throw new Error("simulated canvas draw failure");
      }),
    } as unknown as CanvasRenderingContext2D;
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(failingContext);
    const user = userEvent.setup();
    renderRoute(<OntologyPage />, "/ontology");

    await user.click(await screen.findByRole("button", { name: "3D 캔버스" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("3D 캔버스를 초기화할 수 없습니다.");

    await user.click(screen.getByRole("button", { name: "목록으로 전환" }));
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "접근 가능한 목록" })).toHaveAttribute("aria-pressed", "true");
    getContext.mockRestore();
  });
});
