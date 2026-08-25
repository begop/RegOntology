import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RegulationsPage } from "./RegulationsPage";
import { renderRoute } from "../test/render";

describe("RegulationsPage — FR-011 / AC-NFR-003-01", () => {
  it("restores a URL search and filters the demo library", async () => {
    renderRoute(<RegulationsPage />, "/regulations?q=접근권한");

    expect(screen.getByRole("searchbox", { name: "규정 검색어" })).toHaveValue("접근권한");
    expect(await screen.findByRole("heading", { name: "정보보호 운영규정" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "전자금융업무 운영규정" })).not.toBeInTheDocument();
  });
});
