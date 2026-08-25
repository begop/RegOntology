import {
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  CircleEllipsis,
  Clock3,
  Database,
  FileCheck2,
  FileSearch,
  GitBranch,
  HardDriveUpload,
  Layers3,
  LoaderCircle,
  Network,
  Play,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { Badge, DemoNotice, PageHeader } from "../components/ui";
import { demoIngestionJobs } from "../data/demo";

const steps = [
  { label: "Upload", icon: HardDriveUpload },
  { label: "Parse", icon: FileSearch },
  { label: "Review", icon: FileCheck2 },
  { label: "Enrich", icon: Sparkles },
  { label: "Validate", icon: ShieldCheck },
  { label: "Publish", icon: Database },
];

function jobState(state: (typeof demoIngestionJobs)[number]["state"]) {
  return {
    REVIEW_REQUIRED: { label: "검토 필요", tone: "warning" as const, icon: FileCheck2 },
    ENRICHING: { label: "Ontology 생성 중", tone: "brand" as const, icon: LoaderCircle },
    READY_TO_PUBLISH: { label: "게시 준비 완료", tone: "success" as const, icon: CheckCircle2 },
    FAILED: { label: "실패", tone: "danger" as const, icon: AlertTriangle },
  }[state];
}

export function AdminIngestionsPage() {
  const [selectedJob, setSelectedJob] = useState(demoIngestionJobs[0]!);
  const state = jobState(selectedJob.state);
  const StateIcon = state.icon;

  return (
    <div className="page admin-page">
      <PageHeader
        eyebrow="Curator workspace"
        title="수집 및 Publication"
        description="규정 원문 파싱부터 Ontology 검토, index·graph publication까지 상태를 추적합니다."
        actions={<><DemoNotice compact /><button className="button button--primary"><HardDriveUpload /> 새 규정 등록</button></>}
      />

      <section className="admin-metrics" aria-label="수집 운영 현황">
        <article><span className="metric-icon metric-icon--amber"><FileCheck2 /></span><div><p>검토 대기</p><strong>3</strong><span>Blocker 2건 포함</span></div></article>
        <article><span className="metric-icon metric-icon--blue"><LoaderCircle /></span><div><p>실행 중 job</p><strong>2</strong><span>Parser · Graph projection</span></div></article>
        <article><span className="metric-icon metric-icon--teal"><CheckCircle2 /></span><div><p>최근 Publication</p><strong>정상</strong><span>2026-08-24 09:30</span></div></article>
        <article><span className="metric-icon metric-icon--violet"><Network /></span><div><p>Graph watermark</p><strong>일치</strong><span>Nodes 24 · Edges 22</span></div></article>
      </section>

      <div className="admin-columns">
        <section className="panel ingestion-queue" aria-labelledby="queue-title">
          <div className="panel-heading"><div><p className="eyebrow">Ingestion queue</p><h2 id="queue-title">진행 중인 규정</h2></div><button className="icon-button" aria-label="새로고침"><RefreshCcw /></button></div>
          <div className="ingestion-table-wrap">
            <table className="ingestion-table">
              <thead><tr><th scope="col">규정 / Job</th><th scope="col">담당 부서</th><th scope="col">상태</th><th scope="col">진행률</th><th scope="col">업데이트</th><th scope="col"><span className="sr-only">선택</span></th></tr></thead>
              <tbody>{demoIngestionJobs.map((job) => { const presentation = jobState(job.state); const Icon = presentation.icon; return (
                <tr key={job.id} className={job.id === selectedJob.id ? "selected" : ""}>
                  <td><strong>{job.documentTitle}</strong><small>{job.id} · {job.version}</small></td>
                  <td>{job.ownerOrg}</td>
                  <td><Badge tone={presentation.tone}><Icon className={job.state === "ENRICHING" ? "spin" : ""} /> {presentation.label}</Badge>{job.issues ? <small className="issue-count">이슈 {job.issues}건</small> : null}</td>
                  <td><div className="progress-cell"><div className="progress-track"><span style={{ width: `${job.progress}%` }} /></div><small>{job.progress}%</small></div></td>
                  <td><time>{new Intl.DateTimeFormat("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(job.updatedAt))}</time></td>
                  <td><button onClick={() => setSelectedJob(job)} aria-label={`${job.documentTitle} 상세 보기`}><ArrowRight /></button></td>
                </tr>
              ); })}</tbody>
            </table>
          </div>
        </section>

        <aside className="panel ingestion-detail" aria-label="선택한 수집 job 상세">
          <div className="ingestion-detail__header"><div><p className="eyebrow">{selectedJob.id}</p><h2>{selectedJob.documentTitle}</h2><span>v{selectedJob.version} · {selectedJob.ownerOrg}</span></div><Badge tone={state.tone}><StateIcon className={selectedJob.state === "ENRICHING" ? "spin" : ""} /> {state.label}</Badge></div>
          <div className="pipeline-stepper" aria-label="수집 진행 단계">
            {steps.map(({ label, icon: Icon }, index) => {
              const current = selectedJob.state === "REVIEW_REQUIRED" ? 2 : selectedJob.state === "ENRICHING" ? 3 : selectedJob.state === "READY_TO_PUBLISH" ? 5 : 1;
              return <div key={label} className={index < current ? "complete" : index === current ? "current" : "pending"}><span>{index < current ? <Check /> : <Icon />}</span><small>{label}</small>{index < steps.length - 1 ? <i /> : null}</div>;
            })}
          </div>
          <section className="job-summary"><h3>검증 요약</h3><div className="validation-list"><div><span className="validation-icon validation-icon--ok"><Check /></span><p><strong>문서 구조</strong><small>7개 조문 · 18개 항 locator 확인</small></p></div><div><span className="validation-icon validation-icon--warning"><AlertTriangle /></span><p><strong>용어 연결 검토</strong><small>2개 제안에 담당자 확인 필요</small></p></div><div><span className="validation-icon validation-icon--ok"><Check /></span><p><strong>보안 등급</strong><small>Internal 파생 데이터 상속 확인</small></p></div></div></section>
          <section className="proposal-preview"><div className="section-title-inline"><h3>Ontology 제안</h3><Badge>12개</Badge></div><div><span className="node-swatch node-swatch--obligation" /><p><strong>분기 접근권한 검토</strong><small>Obligation · 제5조 제1항</small></p><Badge tone="success">96%</Badge></div><div><span className="node-swatch node-swatch--actor" /><p><strong>시스템 소유부서</strong><small>Actor · 제5조 제1항</small></p><Badge tone="success">94%</Badge></div></section>
          <button className="button button--primary button--full"><FileSearch /> 검토 화면 열기</button>
        </aside>
      </div>

      <section className="operations-strip" aria-label="Publication 운영 상태">
        <div><span className="operations-icon"><Layers3 /></span><div><p>Active publication</p><strong>mock-publication-2026-08-24</strong></div><Badge tone="success"><CheckCircle2 /> ACTIVE</Badge></div>
        <div><span className="operations-icon"><GitBranch /></span><div><p>PostgreSQL / pgvector / Neo4j</p><strong>동일 watermark 확인됨</strong></div><span className="status-dot status-dot--ok" /></div>
        <div><span className="operations-icon"><Clock3 /></span><div><p>다음 정기 평가</p><strong>2026-08-25 02:00 KST</strong></div><button className="button button--secondary"><Play /> 지금 실행</button></div>
      </section>
      <div className="admin-demo-note"><CircleEllipsis /><p><strong>데모 화면입니다.</strong> 실제 업로드·승인·게시 작업은 인증된 Curator/Admin 역할과 2인 승인을 요구합니다.</p></div>
    </div>
  );
}
