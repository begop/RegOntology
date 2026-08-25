import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, BotMessageSquare, CalendarDays, ChevronRight, GitCompareArrows, Network, ShieldCheck } from "lucide-react";
import { useEffect } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Badge, ErrorState, LoadingState } from "../components/ui";
import { useAppContext } from "../context/AppContext";
import { getRegulationDetail } from "../lib/api";
import { classLabel, formatDate } from "../lib/format";

export function RegulationDetailPage() {
  const { documentId = "", versionId } = useParams();
  const decodedVersionId = versionId ? decodeURIComponent(versionId) : undefined;
  const [params, setParams] = useSearchParams();
  const locator = params.get("locator") ?? "";
  const { asOf } = useAppContext();
  const navigate = useNavigate();
  const detailQuery = useQuery({
    queryKey: ["regulation-detail", documentId, decodedVersionId, asOf],
    queryFn: () => getRegulationDetail(documentId, decodedVersionId, asOf),
    enabled: Boolean(documentId),
  });

  useEffect(() => {
    if (!locator || !detailQuery.data) return;
    const target = detailQuery.data.provisions.find((item) => item.locator === locator || item.id === locator);
    if (!target) return;
    window.setTimeout(() => document.getElementById(target.id)?.scrollIntoView({ block: "center" }), 50);
  }, [detailQuery.data, locator]);

  if (detailQuery.isPending) return <div className="page"><LoadingState label="규정 원문을 불러오고 있습니다." /></div>;
  if (detailQuery.isError || !detailQuery.data) return <div className="page"><ErrorState message="규정 원문을 불러오지 못했습니다." retry={() => void detailQuery.refetch()} /></div>;

  const regulation = detailQuery.data;
  const otherVersion = regulation.versions.find((item) => item.id !== regulation.currentVersion.id);

  function chooseLocator(nextLocator: string) {
    const next = new URLSearchParams(params);
    next.set("locator", nextLocator);
    setParams(next, { replace: true });
  }

  return (
    <div className="detail-page">
      <div className="detail-breadcrumbs">
        <Link to="/regulations"><ArrowLeft /> 규정 라이브러리</Link><ChevronRight /><span>{regulation.title}</span>
      </div>
      <header className="detail-header">
        <div>
          <div className="detail-header__badges"><Badge tone="mock">MOCK DATA</Badge><Badge tone="success">PUBLISHED</Badge><Badge>{classLabel(regulation.securityClass)}</Badge></div>
          <h1>{regulation.title}</h1>
          <p>{regulation.code} · {regulation.ownerOrg} · {regulation.institution}</p>
        </div>
        <div className="detail-header__actions">
          {otherVersion ? (
            <button className="button button--secondary" onClick={() => navigate(`/regulations/${documentId}/versions/${encodeURIComponent(otherVersion.id)}?compare=${encodeURIComponent(regulation.currentVersion.id)}`)}>
              <GitCompareArrows /> v{otherVersion.label} 비교 기준
            </button>
          ) : null}
          <button className="button button--primary" onClick={() => navigate(`/qa?question=${encodeURIComponent(`${regulation.title}의 핵심 의무를 알려주세요.`)}`)}><BotMessageSquare /> 이 규정에 질문</button>
        </div>
      </header>

      <div className="version-strip">
        <div><CalendarDays /><span>표시 버전</span><strong>v{regulation.currentVersion.label}</strong><Badge tone={regulation.currentVersion.status === "PUBLISHED" ? "success" : "neutral"}>{regulation.currentVersion.status === "PUBLISHED" ? "시행 중" : "대체됨"}</Badge></div>
        <div><span>효력 기간</span><strong>{formatDate(regulation.currentVersion.effectiveFrom)} — {formatDate(regulation.currentVersion.effectiveTo)}</strong></div>
        <div><span>조회 기준일</span><strong>{formatDate(asOf)}</strong></div>
        <label><span>버전 변경</span><select value={regulation.currentVersion.id} onChange={(event) => navigate(`/regulations/${documentId}/versions/${encodeURIComponent(event.target.value)}`)}>{regulation.versions.map((version) => <option key={version.id} value={version.id}>v{version.label} · {formatDate(version.effectiveFrom)}</option>)}</select></label>
      </div>

      {params.get("compare") ? <div className="compare-notice"><GitCompareArrows /><div><strong>버전 비교 기준이 설정되었습니다.</strong><span>자동 구조 비교는 검토 대상을 좁히기 위한 참고 정보이며 규정 영향에 대한 최종 판단이 아닙니다.</span></div><button className="button button--text" onClick={() => { const next = new URLSearchParams(params); next.delete("compare"); setParams(next); }}>닫기</button></div> : null}

      <div className="regulation-detail-layout">
        <aside className="toc-panel" aria-label="조문 목차">
          <div className="toc-panel__heading"><span>조문 목차</span><small>{regulation.provisions.length}개 조문</small></div>
          <nav>{regulation.provisions.map((provision) => <button className={locator === provision.locator || locator === provision.id ? "active" : ""} key={provision.id} onClick={() => chooseLocator(provision.locator)}><span>{provision.locator}</span><small>{provision.title}</small></button>)}</nav>
        </aside>

        <article className="regulation-body" aria-label={`${regulation.title} 원문`}>
          <div className="chapter-heading"><span>제2장</span><h2>계정 및 접근권한</h2></div>
          {regulation.provisions.map((provision) => {
            const highlighted = locator === provision.locator || locator === provision.id;
            return (
              <section id={provision.id} className={`provision ${highlighted ? "provision--highlighted" : ""}`} key={provision.id} tabIndex={highlighted ? -1 : undefined}>
                <div className="provision__heading"><h2>{provision.locator} <span>({provision.title})</span></h2>{highlighted ? <Badge tone="success">인용 위치</Badge> : null}</div>
                <ol>{provision.paragraphs.map((paragraph, index) => <li key={`${provision.id}-${index}`}><span>{index + 1}</span><p>{paragraph}</p></li>)}</ol>
                <div className="provision__footer"><div className="concept-chips">{provision.concepts.map((concept) => <span key={concept}>{concept}</span>)}</div><button onClick={() => navigate(`/qa?question=${encodeURIComponent(`${regulation.title} ${provision.locator}의 적용 기준을 설명해 주세요.`)}`)}><BotMessageSquare /> 이 조문으로 질문</button></div>
              </section>
            );
          })}
        </article>

        <aside className="metadata-panel" aria-label="규정 메타데이터와 관계">
          <section><h2>문서 정보</h2><dl><div><dt>담당 부서</dt><dd>{regulation.ownerOrg}</dd></div><div><dt>보안 등급</dt><dd>{classLabel(regulation.securityClass)}</dd></div><div><dt>문서 유형</dt><dd>{regulation.documentType}</dd></div><div><dt>버전 수</dt><dd>{regulation.versions.length}개</dd></div></dl></section>
          <section><div className="section-title-inline"><h2>연결된 Ontology</h2><Network /></div><div className="ontology-summary"><div><strong>{regulation.relatedNodeIds.length}</strong><span>검토된 개념</span></div><div><strong>{Math.max(regulation.relatedNodeIds.length - 1, 1)}</strong><span>관련 관계</span></div></div><Link className="button button--secondary button--full" to={`/ontology?document=${regulation.id}`}><Network /> 관계 탐색하기</Link></section>
          <section className="source-integrity"><ShieldCheck /><div><strong>원문 무결성 확인됨</strong><span>Published snapshot과 연결된 읽기 전용 원문입니다.</span></div></section>
        </aside>
      </div>
    </div>
  );
}
