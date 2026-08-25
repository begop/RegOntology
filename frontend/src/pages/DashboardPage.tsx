import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpenCheck,
  BotMessageSquare,
  CheckCircle2,
  Clock3,
  Network,
  Quote,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAppContext } from "../context/AppContext";
import { getRegulations, getSystemStatus } from "../lib/api";
import { formatDate } from "../lib/format";
import { Badge, DemoNotice, ErrorState, LoadingState, PageHeader } from "../components/ui";

const quickQuestions = [
  "중요정보시스템 접근권한은 얼마나 자주 검토하나요?",
  "중대한 전자금융사고는 언제 누구에게 보고하나요?",
  "긴급 접근계정 사용 후 무엇을 해야 하나요?",
];

export function DashboardPage() {
  const { asOf } = useAppContext();
  const navigate = useNavigate();
  const regulationsQuery = useQuery({
    queryKey: ["regulations", "dashboard", asOf],
    queryFn: () => getRegulations({ asOf }),
  });
  const statusQuery = useQuery({ queryKey: ["system-status"], queryFn: getSystemStatus, retry: false });

  return (
    <div className="page dashboard-page">
      <PageHeader
        eyebrow="Knowledge workspace"
        title="안녕하세요, 김준법님"
        description={`${formatDate(asOf)} 기준으로 검증된 규정 지식을 탐색하세요.`}
        actions={<DemoNotice compact />}
      />

      <section className="hero-panel" aria-labelledby="hero-title">
        <div className="hero-panel__content">
          <Badge tone="success"><Sparkles aria-hidden="true" /> 근거 확인형 AI</Badge>
          <h2 id="hero-title">규정에서 답을 찾고,<br />조문으로 바로 확인하세요.</h2>
          <p>문서 버전과 효력일을 반영해 질문을 분석하고, 모든 답변을 원문 조문과 지식 관계에 연결합니다.</p>
          <div className="hero-actions">
            <Link className="button button--primary" to="/qa">질문 시작하기 <ArrowRight /></Link>
            <Link className="button button--ghost-light" to="/regulations"><Search /> 규정 찾아보기</Link>
          </div>
        </div>
        <div className="hero-evidence" aria-label="근거 확인 예시">
          <div className="hero-evidence__head"><ShieldCheck /><span>Evidence chain</span><Badge tone="success">검증 완료</Badge></div>
          <div className="evidence-answer"><Quote /><p>시스템 소유부서는 접근권한을 <strong>분기마다</strong> 검토해야 합니다.</p></div>
          <div className="evidence-source"><span>[1]</span><div><strong>정보보호 운영규정</strong><small>v1.1 · 제5조 제1항</small></div><CheckCircle2 /></div>
          <div className="evidence-route"><span>질문 분석</span><i /><span>3-lane 검색</span><i /><span>Citation 검증</span></div>
        </div>
      </section>

      <section className="metric-grid" aria-label="서비스 현황">
        <article className="metric-card"><span className="metric-icon metric-icon--blue"><BookOpenCheck /></span><div><p>현재 유효 규정</p><strong>{regulationsQuery.data?.length ?? "—"}<small>건</small></strong><span>권한 범위 내 공개본</span></div></article>
        <article className="metric-card"><span className="metric-icon metric-icon--teal"><Network /></span><div><p>승인된 지식 관계</p><strong>14<small>개</small></strong><span>내부 공개 node 기준</span></div></article>
        <article className="metric-card"><span className="metric-icon metric-icon--violet"><BotMessageSquare /></span><div><p>인용 검증률</p><strong>100<small>%</small></strong><span>Mock QA 시나리오</span></div></article>
        <article className="metric-card"><span className="metric-icon metric-icon--amber"><Clock3 /></span><div><p>Graph watermark</p><strong className="metric-card__compact">동기화</strong><span>{statusQuery.data?.graphWatermark || "확인 중"}</span></div></article>
      </section>

      <div className="dashboard-columns">
        <section className="panel" aria-labelledby="recent-title">
          <div className="panel-heading"><div><p className="eyebrow">Regulation library</p><h2 id="recent-title">최근 유효 규정</h2></div><Link className="text-link" to="/regulations">전체 보기 <ArrowRight /></Link></div>
          {regulationsQuery.isPending ? <LoadingState label="규정 목록을 불러오고 있습니다." /> : null}
          {regulationsQuery.isError ? <ErrorState retry={() => void regulationsQuery.refetch()} /> : null}
          <div className="document-list">
            {regulationsQuery.data?.map((regulation) => (
              <Link className="document-row" to={`/regulations/${regulation.id}/versions/${encodeURIComponent(regulation.currentVersion.id)}`} key={regulation.id}>
                <span className="document-icon"><BookOpenCheck /></span>
                <span className="document-row__main"><strong>{regulation.title}</strong><small>{regulation.code} · {regulation.ownerOrg}</small></span>
                <span className="document-row__meta"><Badge tone="success">시행 중</Badge><small>v{regulation.currentVersion.label}</small></span>
                <ArrowRight aria-hidden="true" />
              </Link>
            ))}
          </div>
        </section>

        <section className="panel" aria-labelledby="quick-title">
          <div className="panel-heading"><div><p className="eyebrow">Start with a question</p><h2 id="quick-title">이렇게 물어보세요</h2></div></div>
          <div className="quick-question-list">
            {quickQuestions.map((question, index) => (
              <button key={question} onClick={() => navigate(`/qa?question=${encodeURIComponent(question)}`)}>
                <span>{index + 1}</span><p>{question}</p><ArrowRight aria-hidden="true" />
              </button>
            ))}
          </div>
          <div className="safe-answer-note"><ShieldCheck /><div><strong>근거가 부족하면 답변하지 않습니다.</strong><span>등록 규정에서 확인할 수 없는 내용은 보류 이유와 다음 행동을 안내합니다.</span></div></div>
        </section>
      </div>
    </div>
  );
}
