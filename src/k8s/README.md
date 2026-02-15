# Kubernetes 배포 (block-diagram)

모든 리소스는 `block-diagram` 네임스페이스에 배포됩니다. 서비스별 매니페스트는 `agent/`, `ui/` 폴더에 있습니다. 자세한 규칙은 [AGENTS.md](./AGENTS.md)를 참고하세요.

## 사전 요구 사항

- **이미지 빌드** (프로젝트 루트에서):
  ```bash
  ./scripts/build-images.sh          # 에이전트 + UI 모두
  ./scripts/build-images.sh agent    # 에이전트만
  ./scripts/build-images.sh ui       # UI만
  ```
  또는 직접: `docker build -t block-diagram-agent:latest src/agent`, `docker build -t block-diagram-ui:latest src/ui`
- 클러스터에서 이미지를 쓰려면 레지스트리에 푸시하거나, 로컬 테스트 시 `kind`/`minikube`에 이미지 로드

## Secret 설정 (에이전트)

실제 API 키로 Secret을 생성한 뒤 배포하세요.

```bash
kubectl create secret generic agent-secrets \
  --from-literal=GOOGLE_API_KEY=your_actual_key \
  -n block-diagram \
  --dry-run=client -o yaml | kubectl apply -f -
```

또는 `agent/secret.yaml`의 `GOOGLE_API_KEY` 값을 실제 키로 바꾼 뒤 적용 (저장소에 커밋하지 말 것).

## 배포

```bash
# 스크립트 사용 (프로젝트 루트에서)
./scripts/deploy-k8s.sh              # 전체 적용
./scripts/deploy-k8s.sh --agent-only # 에이전트만
./scripts/deploy-k8s.sh --ui-only    # UI만
./scripts/deploy-k8s.sh --dry-run    # 적용 예시만 출력

# 직접 kubectl
kubectl apply -k src/k8s
kubectl apply -k src/k8s/agent
kubectl apply -k src/k8s/ui
```

## 접속

- **UI를 Ingress로 외부 노출** (`ingress.yaml`): `/` → UI, `/api/run` → 에이전트, `/api/apps` → Session Service(세션·이벤트 API).
- 에이전트는 env `SESSION_SERVICE_URL=http://block-diagram-session-service:8081`로 Session Service에 접근.

## 포트포워드 (로컬 접속)

```bash
# 에이전트 (웹 UI + API)
kubectl port-forward -n block-diagram svc/block-diagram-agent 8080:8080

# UI
kubectl port-forward -n block-diagram svc/block-diagram-ui 3000:80
```

- 에이전트: http://localhost:8080  
- UI: http://localhost:3000 (UI에서 API 주소를 에이전트로 맞춰 사용)

클러스터 내부에서는 서비스 이름으로 접근: `http://block-diagram-agent:8080`, `http://block-diagram-session-service:8081`, `http://block-diagram-ui:80`.

## 삭제

```bash
kubectl delete -k src/k8s
```
