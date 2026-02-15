#!/usr/bin/env bash
# 로컬 개발: 에이전트(localhost:8080) + UI(localhost:3000) 한 번에 실행
# 사용법: ./scripts/dev-local.sh
# 프로젝트 루트에서 실행. .env 또는 환경변수: GOOGLE_API_KEY( Gemini ) 또는 LLM_BASE_URL/KSERVE_URL( 로컬 LLM ).
# 종료: Ctrl+C

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

# .env 로드
if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT_DIR/.env"
  set +a
fi

# LLM 미설정 시: Gemini 키 없으면 로컬 Ollama 기본값 사용
if [[ -z "${LLM_BASE_URL:-}" ]] && [[ -z "${KSERVE_URL:-}" ]]; then
  if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
    : # Gemini 사용
  else
    export LLM_BASE_URL="http://localhost:11434/v1"
    export LLM_MODEL_NAME="${LLM_MODEL_NAME:-qwen3-coder:30b}"
    echo "LLM: 로컬 Ollama 기본값 사용 (localhost:11434). Gemini 쓰려면 .env에 GOOGLE_API_KEY를 넣으세요."
  fi
fi
if [[ -z "${GOOGLE_API_KEY:-}" ]] && [[ -z "${LLM_BASE_URL:-}" ]] && [[ -z "${KSERVE_URL:-}" ]]; then
  echo "GOOGLE_API_KEY 또는 LLM_BASE_URL/KSERVE_URL 중 하나가 필요합니다. .env에 넣거나 export 하세요." >&2
  exit 1
fi

# 8080 사용 중이면 안내 후 종료
port_in_use() {
  if command -v nc &>/dev/null; then
    nc -z 127.0.0.1 "$1" 2>/dev/null
  else
    curl -s -o /dev/null --connect-timeout 1 "http://127.0.0.1:$1/" 2>/dev/null
  fi
}
if port_in_use 8080; then
  echo "포트 8080이 이미 사용 중입니다. 에이전트/해당 프로세스를 종료한 뒤 다시 실행하세요." >&2
  exit 1
fi

AGENT_PID=""
cleanup() {
  if [[ -n "$AGENT_PID" ]] && kill -0 "$AGENT_PID" 2>/dev/null; then
    echo "에이전트 종료 중... (PID $AGENT_PID)"
    kill "$AGENT_PID" 2>/dev/null || true
    wait "$AGENT_PID" 2>/dev/null || true
  fi
  exit 0
}
trap cleanup SIGINT SIGTERM

# 에이전트: localhost:8080, in-memory 세션
export SESSION_USE_MEMORY=true
echo "=== 에이전트 시작 (http://localhost:8080, in-memory 세션) ==="
(cd "$ROOT_DIR/src/agent" && python -m uvicorn run_server:app --host 0.0.0.0 --port 8080) &
AGENT_PID=$!

# 에이전트 기동 대기 (최대 약 4초, ADK는 보통 곧 뜸)
for i in {1..8}; do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ 2>/dev/null | grep -q 200; then
    break
  fi
  if ! kill -0 "$AGENT_PID" 2>/dev/null; then
    echo "에이전트가 비정상 종료되었습니다." >&2
    exit 1
  fi
  sleep 0.5
done

# UI: localhost:3000
# WSL 등에서 npx serve + cd 시 UNC 경로 오류가 나므로, Python 우선 사용. 없으면 npx(루트에서 상대경로로 서빙).
echo "=== UI 시작 (http://localhost:3000) ==="
echo "  에이전트 API: http://localhost:8080"
echo "  종료: Ctrl+C"
echo ""

if command -v python3 &>/dev/null; then
  python3 -m http.server 3000 --directory "$ROOT_DIR/src/ui"
elif command -v npx &>/dev/null; then
  npx --yes serve src/ui -p 3000
else
  echo "python3 또는 npx 가 필요합니다." >&2
  exit 1
fi
