import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QaPage } from "./QaPage";
import { renderRoute } from "../test/render";

describe("QaPage — FR-008/009/010", () => {
  it("renders a cited answer with a stable source link", async () => {
    const user = userEvent.setup();
    renderRoute(<QaPage />, "/qa");

    await user.type(screen.getByLabelText("규정 질문"), "중요정보시스템 접근권한은 얼마나 자주 검토해야 하나요?");
    await user.click(screen.getByRole("button", { name: "질문 전송" }));

    expect(await screen.findByText("근거 확인 완료")).toBeInTheDocument();
    expect(screen.getByText(/분기마다 검토해야 합니다/)).toBeInTheDocument();
    expect(screen.getByText("제5조 제1항")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /원문 열기/ })).toHaveAttribute("href", expect.stringContaining("locator=isp-art-5"));
  });

  it("shows an explicit abstention when evidence is insufficient", async () => {
    const user = userEvent.setup();
    renderRoute(<QaPage />, "/qa");

    await user.type(screen.getByLabelText("규정 질문"), "해외송금 수수료 한도는 얼마인가요?");
    await user.click(screen.getByRole("button", { name: "질문 전송" }));

    expect(await screen.findByText("답변 보류")).toBeInTheDocument();
    expect(screen.getByText("추측해서 답하지 않았습니다.")).toBeInTheDocument();
    expect(screen.queryByText("확인된 근거")).not.toBeInTheDocument();
  });

  it("flattens and deduplicates live backend retrieval lanes", async () => {
    const payload = {
      query_id: "query-live-1",
      status: "answered",
      answer: "접근권한은 분기마다 검토합니다. [1]",
      as_of: "2026-08-24",
      citations: [
        {
          index: 1,
          source_id: "src-1",
          document_id: "MOCK-ISP-001",
          version_id: "MOCK-ISP-001:v1.1",
          provision_id: "MOCK-ISP-001:v1.1:art-5/p-1",
          document_title: "정보보호 운영규정",
          version_label: "1.1",
          locator: "제5조 제1항",
          quote: "시스템 소유부서는 접근권한을 분기마다 검토한다.",
        },
      ],
      warnings: ["mock_data"],
      reason_code: null,
      suggested_actions: [],
      trace: {
        publication_id: "mock-live",
        graph_mode: "neo4j_projection",
        lanes: [["graph", "lexical", "relevance"], ["lexical", "vector"]],
      },
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
    const user = userEvent.setup();
    renderRoute(<QaPage />, "/qa");

    await user.type(screen.getByLabelText("규정 질문"), "접근권한 검토 주기는?");
    await user.click(screen.getByRole("button", { name: "질문 전송" }));
    await user.click(await screen.findByRole("button", { name: /검색 경로/ }));

    expect(screen.getByText("graph + lexical + relevance + vector")).toBeInTheDocument();
  });
});
