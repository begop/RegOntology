import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DashboardPage } from "./DashboardPage";
import { renderRoute } from "../test/render";

describe("DashboardPage — T-150/T-160", () => {
  it("shows the evidence-first workspace and demo regulations", async () => {
    renderRoute(<DashboardPage />);

    expect(screen.getByRole("heading", { name: "안녕하세요, 김준법님" })).toBeInTheDocument();
    expect(screen.getByText("근거가 부족하면 답변하지 않습니다.")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /정보보호 운영규정/ })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /전자금융업무 운영규정/ })).toBeInTheDocument();
  });
});
