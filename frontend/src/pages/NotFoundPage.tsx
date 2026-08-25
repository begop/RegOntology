import { ArrowLeft, SearchX } from "lucide-react";
import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="not-found">
      <span><SearchX /></span>
      <p className="eyebrow">404 · Not found</p>
      <h1>요청한 화면을 찾을 수 없습니다.</h1>
      <p>주소가 바뀌었거나 현재 접근 범위에서 표시할 수 없는 리소스입니다.</p>
      <Link className="button button--primary" to="/"><ArrowLeft /> 홈으로 돌아가기</Link>
    </div>
  );
}
