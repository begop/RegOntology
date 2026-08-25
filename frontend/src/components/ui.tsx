import { AlertTriangle, CheckCircle2, Database, Info, LoaderCircle, SearchX } from "lucide-react";
import type { ReactNode } from "react";

type BadgeTone = "neutral" | "brand" | "success" | "warning" | "danger" | "mock";

export function Badge({ children, tone = "neutral", className = "" }: { children: ReactNode; tone?: BadgeTone; className?: string }) {
  return <span className={`badge badge--${tone} ${className}`.trim()}>{children}</span>;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}

export function LoadingState({ label = "데이터를 확인하고 있습니다." }: { label?: string }) {
  return (
    <div className="state-panel" role="status" aria-live="polite">
      <LoaderCircle className="spin" aria-hidden="true" />
      <strong>{label}</strong>
      <span>잠시만 기다려 주세요.</span>
    </div>
  );
}

export function EmptyState({
  title = "표시할 결과가 없습니다.",
  description = "검색어나 필터를 바꿔 다시 확인해 주세요.",
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="state-panel">
      <SearchX aria-hidden="true" />
      <strong>{title}</strong>
      <span>{description}</span>
      {action}
    </div>
  );
}

export function ErrorState({ message = "데이터를 불러오지 못했습니다.", retry }: { message?: string; retry?: () => void }) {
  return (
    <div className="state-panel state-panel--error" role="alert">
      <AlertTriangle aria-hidden="true" />
      <strong>{message}</strong>
      <span>잠시 후 다시 시도하거나 서비스 상태를 확인해 주세요.</span>
      {retry ? <button className="button button--secondary" onClick={retry}>다시 시도</button> : null}
    </div>
  );
}

export function DemoNotice({ compact = false }: { compact?: boolean }) {
  return (
    <div className={compact ? "demo-notice demo-notice--compact" : "demo-notice"}>
      <Database aria-hidden="true" />
      <div>
        <strong>가상 규정 데이터</strong>
        {!compact ? <span>화면의 기관·규정·답변은 제품 검증용 예시이며 실제 업무 판단에 사용할 수 없습니다.</span> : null}
      </div>
    </div>
  );
}

export function StatusIcon({ status }: { status: "ok" | "warning" | "info" }) {
  if (status === "ok") return <CheckCircle2 aria-hidden="true" />;
  if (status === "warning") return <AlertTriangle aria-hidden="true" />;
  return <Info aria-hidden="true" />;
}
