export function formatDate(value: string | null, fallback = "현재"): string {
  if (!value) return fallback;
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(`${value}T00:00:00`));
}

export function classLabel(value: string): string {
  return {
    public: "공개",
    internal: "내부",
    restricted: "제한",
  }[value] ?? value;
}

export function nodeTypeLabel(type: string): string {
  return {
    RegulationDocument: "규정",
    Organization: "조직",
    Actor: "수행 주체",
    System: "시스템",
    Obligation: "의무",
    Prohibition: "금지",
    Permission: "허용",
    Exception: "예외",
    Control: "통제",
    Risk: "위험",
    DataCategory: "정보 분류",
  }[type] ?? type;
}

export function relationLabel(type: string): string {
  return {
    OWNED_BY: "소유",
    PERFORMED_BY: "수행 주체",
    TARGETS: "대상",
    IMPLEMENTED_BY: "구현 통제",
    MITIGATES: "위험 완화",
    RELATED_TO: "관련",
    HAS_EXCEPTION: "예외 보유",
    EXCEPTION_TO: "의무 예외",
    CROSS_REFERENCES: "상호 참조",
  }[type] ?? type;
}
