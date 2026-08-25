import { useQuery } from "@tanstack/react-query";
import { BookOpenText, CalendarDays, ChevronRight, Filter, Search, SlidersHorizontal, X } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Badge, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAppContext } from "../context/AppContext";
import { getRegulations } from "../lib/api";
import { classLabel, formatDate } from "../lib/format";

export function RegulationsPage() {
  const { asOf } = useAppContext();
  const [params, setParams] = useSearchParams();
  const [draft, setDraft] = useState(params.get("q") ?? "");
  const query = params.get("q") ?? "";
  const ownerOrg = params.get("owner") ?? "";
  const securityClass = params.get("class") ?? "";

  useEffect(() => setDraft(query), [query]);

  const regulationsQuery = useQuery({
    queryKey: ["regulations", query, ownerOrg, securityClass, asOf],
    queryFn: () => getRegulations({ query, ownerOrg, securityClass, asOf }),
  });

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    updateParam("q", draft.trim());
  }

  function resetFilters() {
    setDraft("");
    setParams({});
  }

  const hasFilters = Boolean(query || ownerOrg || securityClass);

  return (
    <div className="page regulations-page">
      <PageHeader eyebrow="Regulation library" title="규정 라이브러리" description="문서, 효력일, 담당 부서와 조문 키워드로 유효한 규정을 탐색합니다." />

      <section className="search-surface" aria-label="규정 검색 조건">
        <form className="library-search" onSubmit={submitSearch} role="search">
          <Search aria-hidden="true" />
          <input type="search" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="예: 접근권한, 사고 보고, 로그 보관" aria-label="규정 검색어" />
          {draft ? <button type="button" className="clear-input" onClick={() => setDraft("")} aria-label="검색어 지우기"><X /></button> : null}
          <button className="button button--primary" type="submit">검색</button>
        </form>
        <div className="filter-row">
          <span className="filter-label"><SlidersHorizontal /> 필터</span>
          <label><span>담당 부서</span><select value={ownerOrg} onChange={(event) => updateParam("owner", event.target.value)}><option value="">전체 부서</option><option>정보보호부</option><option>전자금융운영부</option></select></label>
          <label><span>보안 등급</span><select value={securityClass} onChange={(event) => updateParam("class", event.target.value)}><option value="">접근 가능한 전체</option><option value="internal">내부</option><option value="restricted">제한</option></select></label>
          <div className="asof-chip"><CalendarDays /> 기준일 <strong>{formatDate(asOf)}</strong></div>
          {hasFilters ? <button className="button button--text" onClick={resetFilters}><X /> 필터 초기화</button> : null}
        </div>
      </section>

      <div className="results-toolbar">
        <div><strong>{regulationsQuery.data?.length ?? 0}</strong>개의 규정 <span>· 권한 및 기준일 적용</span></div>
        <span className="result-safety"><Filter /> 검색 후보 생성 전에 접근 범위가 적용됩니다.</span>
      </div>

      {regulationsQuery.isPending ? <LoadingState label="유효 규정을 검색하고 있습니다." /> : null}
      {regulationsQuery.isError ? <ErrorState retry={() => void regulationsQuery.refetch()} /> : null}
      {regulationsQuery.data?.length === 0 ? <EmptyState action={<button className="button button--secondary" onClick={resetFilters}>전체 규정 보기</button>} /> : null}

      <section className="regulation-grid" aria-label="규정 검색 결과">
        {regulationsQuery.data?.map((regulation) => (
          <article className="regulation-card" key={regulation.id}>
            <div className="regulation-card__top">
              <span className="document-icon document-icon--large"><BookOpenText /></span>
              <div className="regulation-card__badges"><Badge tone="mock">MOCK</Badge><Badge tone="neutral">{classLabel(regulation.securityClass)}</Badge></div>
            </div>
            <p className="regulation-code">{regulation.code}</p>
            <h2>{regulation.title}</h2>
            <p className="regulation-snippet">{regulation.snippet || "규정 원문과 버전별 조문을 확인할 수 있습니다."}</p>
            <dl className="regulation-facts">
              <div><dt>현재 버전</dt><dd><Badge tone="success">v{regulation.currentVersion.label} 시행 중</Badge></dd></div>
              <div><dt>시행 기간</dt><dd>{formatDate(regulation.currentVersion.effectiveFrom)} — {formatDate(regulation.currentVersion.effectiveTo)}</dd></div>
              <div><dt>담당 부서</dt><dd>{regulation.ownerOrg}</dd></div>
            </dl>
            <div className="tag-row">{regulation.tags.slice(0, 4).map((tag) => <span key={tag}>#{tag}</span>)}</div>
            <Link className="regulation-card__link" to={`/regulations/${regulation.id}/versions/${encodeURIComponent(regulation.currentVersion.id)}`}>
              원문 및 조문 보기 <ChevronRight />
            </Link>
          </article>
        ))}
      </section>
    </div>
  );
}
