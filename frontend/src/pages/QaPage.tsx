import { useMutation } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  BookOpenText,
  Bot,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  Clock3,
  ExternalLink,
  GitBranch,
  LoaderCircle,
  MessageSquareText,
  Network,
  SearchCheck,
  Send,
  ShieldCheck,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  UserRound,
} from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Badge, DemoNotice, PageHeader } from "../components/ui";
import { useAppContext } from "../context/AppContext";
import { askQuestion } from "../lib/api";
import { formatDate } from "../lib/format";
import type { Citation, QaResponse } from "../lib/types";

interface ChatTurn {
  id: string;
  question: string;
  response?: QaResponse;
}

const examples = [
  "중요정보시스템 접근권한은 얼마나 자주 누가 검토해야 하나요?",
  "중대한 전자금융사고는 몇 분 안에 누구에게 보고해야 하나요?",
  "해외송금 수수료 한도는 얼마인가요?",
];

function statusPresentation(response: QaResponse) {
  if (response.status === "answered") return { label: "근거 확인 완료", tone: "success" as const, icon: CheckCircle2 };
  if (response.status === "partially_answered") return { label: "부분 근거로 답변", tone: "warning" as const, icon: AlertCircle };
  if (response.reasonCode === "access_limited") return { label: "접근 범위 밖", tone: "danger" as const, icon: ShieldCheck };
  return { label: "답변 보류", tone: "warning" as const, icon: CircleHelp };
}

function citationLink(citation: Citation): string {
  return `/regulations/${citation.documentId}/versions/${encodeURIComponent(citation.versionId)}?locator=${encodeURIComponent(citation.provisionId)}`;
}

function AnswerCard({ response }: { response: QaResponse }) {
  const [feedback, setFeedback] = useState<"helpful" | "not_helpful" | null>(null);
  const [traceOpen, setTraceOpen] = useState(false);
  const presentation = statusPresentation(response);
  const StatusIcon = presentation.icon;
  const isAbstained = response.status === "abstained";

  return (
    <article className={`answer-card answer-card--${response.status}`} aria-label={`답변 상태: ${presentation.label}`}>
      <header className="answer-card__header">
        <Badge tone={presentation.tone}><StatusIcon aria-hidden="true" /> {presentation.label}</Badge>
        <span><Clock3 /> 적용 기준일 {formatDate(response.asOf)}</span>
      </header>
      <div className="answer-card__body">
        <p className="answer-lead">{response.answer}</p>
        {isAbstained ? (
          <div className="abstention-panel">
            <div className="abstention-panel__icon"><ShieldCheck /></div>
            <div>
              <strong>추측해서 답하지 않았습니다.</strong>
              <p>{response.reasonCode === "access_limited" ? "제한 문서의 존재나 내용을 암시하지 않고 현재 접근 범위만 평가했습니다." : "확인 가능한 조문 근거가 답변 기준을 충족하지 못했습니다."}</p>
              {response.suggestedActions?.length ? <ul>{response.suggestedActions.map((action) => <li key={action}>{action}</li>)}</ul> : null}
            </div>
          </div>
        ) : (
          <>
            <div className="citation-heading"><div><SearchCheck /><span>확인된 근거</span><Badge tone="success">{response.citations.length}개</Badge></div><span>주장을 지지하는 조문만 표시합니다.</span></div>
            <div className="citation-list">
              {response.citations.map((citation) => (
                <article className="citation-card" key={`${citation.index}-${citation.provisionId}`}>
                  <div className="citation-index">[{citation.index}]</div>
                  <div className="citation-card__content">
                    <div className="citation-card__title"><strong>{citation.documentTitle}</strong><Badge>v{citation.versionLabel}</Badge><span>{citation.locator}</span></div>
                    <blockquote>“{citation.quote}”</blockquote>
                    <div className="citation-card__actions">
                      <Link to={citationLink(citation)}><BookOpenText /> 원문 열기 <ExternalLink /></Link>
                      <Link to={`/ontology?document=${citation.documentId}`}><Network /> 관계 보기</Link>
                    </div>
                  </div>
                  <Check aria-label="인용 검증됨" />
                </article>
              ))}
            </div>
          </>
        )}
      </div>
      <footer className="answer-card__footer">
        <div className="feedback-control" aria-label="답변 평가">
          {feedback ? <span className="feedback-sent"><Check /> 의견이 반영되었습니다.</span> : <><span>이 답변이 도움이 되었나요?</span><button onClick={() => setFeedback("helpful")}><ThumbsUp /> 도움이 됨</button><button onClick={() => setFeedback("not_helpful")}><ThumbsDown /> 문제 있음</button></>}
        </div>
        <button className="trace-toggle" onClick={() => setTraceOpen((value) => !value)} aria-expanded={traceOpen}><GitBranch /> 검색 경로 <ChevronDown /></button>
      </footer>
      {traceOpen ? (
        <div className="trace-panel">
          <div><span>Publication</span><code>{response.trace.publicationId}</code></div>
          <div><span>검색 lane</span><strong>{response.trace.lanes?.join(" + ") || "권한 범위 내 검색"}</strong></div>
          <div><span>Graph mode</span><Badge tone={response.trace.graphMode === "healthy" ? "success" : "warning"}>{response.trace.graphMode}</Badge></div>
          <p>모델 내부 추론이나 권한 밖 source는 표시하지 않습니다.</p>
        </div>
      ) : null}
    </article>
  );
}

export function QaPage() {
  const { asOf } = useAppContext();
  const [params] = useSearchParams();
  const [question, setQuestion] = useState(params.get("question") ?? "");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const mutation = useMutation({
    mutationFn: ({ value, turnId }: { value: string; turnId: string }) => askQuestion(value, asOf).then((response) => ({ response, turnId })),
    onSuccess: ({ response, turnId }) => setTurns((current) => current.map((turn) => (turn.id === turnId ? { ...turn, response } : turn))),
  });

  useEffect(() => {
    const incoming = params.get("question");
    if (incoming) setQuestion(incoming);
  }, [params]);

  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), [turns, mutation.isPending]);

  function submit(event?: FormEvent) {
    event?.preventDefault();
    const value = question.trim();
    if (!value || mutation.isPending) return;
    const turnId = `turn-${Date.now()}`;
    setTurns((current) => [...current, { id: turnId, question: value }]);
    setQuestion("");
    mutation.mutate({ value, turnId });
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <div className="page qa-page">
      <PageHeader eyebrow="Grounded QA" title="규정 QA" description="질문마다 유효한 규정을 다시 검색하고, 검증된 조문 근거와 함께 답합니다." actions={<DemoNotice compact />} />

      <div className="qa-layout">
        <section className="chat-workspace" aria-label="규정 QA 대화">
          <div className="chat-intro">
            <span className="assistant-avatar"><Bot /></span>
            <div><Badge tone="brand"><Sparkles /> RegOntology Assistant</Badge><h2>무엇을 확인해 드릴까요?</h2><p>업무 대상과 상황을 구체적으로 적으면 더 정확한 조문을 찾을 수 있습니다.</p></div>
          </div>

          {turns.length === 0 ? (
            <div className="question-suggestions" aria-label="예시 질문">
              {examples.map((example) => <button key={example} onClick={() => setQuestion(example)}><MessageSquareText /><span>{example}</span><ArrowRight /></button>)}
            </div>
          ) : null}

          <div className="conversation" aria-live="polite">
            {turns.map((turn, index) => (
              <div className="conversation-turn" key={turn.id}>
                <div className="user-message"><div><UserRound /></div><p>{turn.question}</p></div>
                {turn.response ? <div className="assistant-message"><span className="assistant-avatar assistant-avatar--small"><Bot /></span><AnswerCard response={turn.response} /></div> : index === turns.length - 1 && mutation.isPending ? (
                  <div className="retrieval-progress" role="status"><span className="assistant-avatar assistant-avatar--small"><Bot /></span><div><div className="retrieval-progress__top"><LoaderCircle className="spin" /><strong>근거를 확인하고 있습니다.</strong></div><ol><li className="done"><Check /> 질문 의도·효력일 분석</li><li className="active"><LoaderCircle className="spin" /> Lexical · Vector · Graph 검색</li><li>인용 지지 여부 검증</li></ol></div></div>
                ) : null}
              </div>
            ))}
            {mutation.isError ? <div className="chat-error" role="alert"><AlertCircle /><div><strong>질문을 처리하지 못했습니다.</strong><span>잠시 후 다시 질문해 주세요.</span></div></div> : null}
            <div ref={bottomRef} />
          </div>

          <form className="qa-composer" onSubmit={submit}>
            <label htmlFor="qa-question" className="sr-only">규정 질문</label>
            <textarea id="qa-question" rows={2} value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={handleKeyDown} placeholder="예: 중요정보시스템 접근권한은 얼마나 자주 검토해야 하나요?" maxLength={1000} />
            <div className="composer-footer"><span><ShieldCheck /> 권한 범위 · {formatDate(asOf)} 기준</span><span>{question.length}/1000</span><button className="send-button" disabled={!question.trim() || mutation.isPending} aria-label="질문 전송"><Send /></button></div>
          </form>
          <p className="qa-disclaimer">답변은 등록된 규정의 탐색을 돕는 참고 정보입니다. 최종 업무 판단은 담당 부서에 확인하세요.</p>
        </section>

        <aside className="qa-side-panel" aria-label="질문 도움말">
          <section><h2><ShieldCheck /> 답변 원칙</h2><ul><li><CheckCircle2 /> 유효 버전과 기준일 확인</li><li><CheckCircle2 /> 모든 규정 주장에 조문 인용</li><li><CheckCircle2 /> 근거 부족·권한 밖 답변 보류</li></ul></section>
          <section><h2><Clock3 /> 현재 컨텍스트</h2><dl><div><dt>적용 기준일</dt><dd>{formatDate(asOf)}</dd></div><div><dt>문서 범위</dt><dd>접근 가능한 전체</dd></div><div><dt>검색 방식</dt><dd>Hybrid + Graph</dd></div></dl></section>
          <section className="qa-tips"><h2><Sparkles /> 더 좋은 질문</h2><p>“누가”, “언제까지”, “어떤 경우”처럼 주체와 조건을 함께 적어보세요.</p></section>
        </aside>
      </div>
    </div>
  );
}
