#!/usr/bin/env bash
# Kubernetes 배포: block-diagram 네임스페이스에 Kustomize로 리소스 적용
# 사용법: ./scripts/deploy-k8s.sh [--dry-run] [--agent-only|--ui-only]
# 프로젝트 루트에서 실행하세요.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

K8S_DIR="src/k8s"
DRY_RUN=()
SCOPE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=(--dry-run=client)
      shift
      ;;
    --agent-only)
      SCOPE="agent"
      shift
      ;;
    --ui-only)
      SCOPE="ui"
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

apply_once() {
  if [[ -n "$SCOPE" ]]; then
    APPLY_DIR="$K8S_DIR/$SCOPE"
    echo "Applying Kustomize: $APPLY_DIR"
    kubectl apply -k "$APPLY_DIR" "${DRY_RUN[@]}"
  else
    echo "Applying Kustomize: $K8S_DIR (전체)"
    kubectl apply -k "$K8S_DIR" "${DRY_RUN[@]}"
  fi
}

if [[ ${#DRY_RUN[@]} -gt 0 ]]; then
  apply_once
else
  set +e
  apply_once 2>&1 | tee /tmp/deploy-k8s.log
  APPLY_EXIT=${PIPESTATUS[0]}
  set -e
  if [[ $APPLY_EXIT -ne 0 ]]; then
    # StatefulSet spec(volumeClaimTemplates 등)은 변경 불가. 충돌 시 삭제 후 재적용
    if grep -q "Forbidden: updates to statefulset spec" /tmp/deploy-k8s.log 2>/dev/null; then
      echo "StatefulSet spec 변경 불가로 재생성합니다: block-diagram-llm"
      kubectl delete statefulset block-diagram-llm -n block-diagram --ignore-not-found=true
      apply_once
    else
      exit 1
    fi
  fi
fi

echo "Deploy done."
