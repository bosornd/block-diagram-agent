#!/usr/bin/env bash
# Docker 이미지 빌드: 세션 서비스, 에이전트, UI
# 사용법: ./scripts/build-images.sh [session-service|agent|ui|all]   (기본값: all)
# 프로젝트 루트에서 실행하세요.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

TARGET="${1:-all}"
SESSION_IMAGE="block-diagram-session-service:latest"
AGENT_IMAGE="block-diagram-agent:latest"
UI_IMAGE="block-diagram-ui:latest"

build_session_service() {
  echo "Building session-service image: $SESSION_IMAGE"
  docker build -t "$SESSION_IMAGE" src/session-service
  echo "Done: $SESSION_IMAGE"
}

build_agent() {
  echo "Building agent image: $AGENT_IMAGE"
  docker build -t "$AGENT_IMAGE" src/agent
  echo "Done: $AGENT_IMAGE"
}

build_ui() {
  echo "Building UI image: $UI_IMAGE"
  docker build -t "$UI_IMAGE" src/ui
  echo "Done: $UI_IMAGE"
}

case "$TARGET" in
  session-service)
    build_session_service
    ;;
  agent)
    build_agent
    ;;
  ui)
    build_ui
    ;;
  all)
    build_session_service
    build_agent
    build_ui
    ;;
  *)
    echo "Usage: $0 [session-service|agent|ui|all]" >&2
    echo "  session-service - 세션 서비스 이미지만 빌드" >&2
    echo "  agent           - 에이전트 이미지만 빌드" >&2
    echo "  ui              - UI 이미지만 빌드" >&2
    echo "  all             - 세션 서비스 + 에이전트 + UI 모두 빌드 (기본값)" >&2
    exit 1
    ;;
esac
