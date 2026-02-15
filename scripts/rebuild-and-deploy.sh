#!/usr/bin/env bash
# Docker 이미지 재빌드 후 Kubernetes 재배포 (kubectl apply + rollout restart)
# 사용법: ./scripts/rebuild-and-deploy.sh [--dry-run] [session-service|agent|ui|all]
# 프로젝트 루트에서 실행하세요.
#
# selector 불변 오류가 나면 해당 Deployment를 삭제한 뒤 다시 실행하세요.
#   kubectl delete deployment block-diagram-ui -n block-diagram
#   kubectl delete deployment block-diagram-agent -n block-diagram
#   kubectl delete deployment block-diagram-session-service -n block-diagram

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

DRY_RUN=()
TARGET="all"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=(--dry-run=client)
      shift
      ;;
    session-service|agent|ui|all)
      TARGET="$1"
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

K8S_DIR="src/k8s"
K8S_NS="block-diagram"

# 1) Docker 이미지 빌드
echo "=== 1) Docker 이미지 빌드 ==="
"$SCRIPT_DIR/build-images.sh" "$TARGET"

# 2) Kustomize 적용
echo "=== 2) K8s 배포 (kubectl apply) ==="
if [[ "$TARGET" == "all" ]]; then
  kubectl apply -k "$K8S_DIR" "${DRY_RUN[@]}"
else
  kubectl apply -k "$K8S_DIR/$TARGET" "${DRY_RUN[@]}"
fi

# 3) 롤아웃 재시작 (새 이미지·ConfigMap 반영)
if [[ -z "${DRY_RUN[*]}" ]]; then
  echo "=== 3) Deployment 롤아웃 재시작 (새 이미지·ConfigMap 반영) ==="
  case "$TARGET" in
    session-service)
      kubectl rollout restart deployment/block-diagram-session-service -n "$K8S_NS" 2>/dev/null || true
      ;;
    agent)
      kubectl rollout restart deployment/block-diagram-agent -n "$K8S_NS" 2>/dev/null || true
      ;;
    ui)
      kubectl rollout restart deployment/block-diagram-ui -n "$K8S_NS" 2>/dev/null || true
      ;;
    all)
      kubectl rollout restart deployment/block-diagram-session-service -n "$K8S_NS" 2>/dev/null || true
      kubectl rollout restart deployment/block-diagram-agent -n "$K8S_NS" 2>/dev/null || true
      kubectl rollout restart deployment/block-diagram-ui -n "$K8S_NS" 2>/dev/null || true
      ;;
  esac
fi

echo "Done. (rebuild + deploy)"
