# LLM (Ollama 컨테이너)

**Ollama**를 StatefulSet·Service로 배포합니다. GPU 없이 CPU만으로 동작하며, OpenAI 호환 API(port 11434)를 제공합니다. StatefulSet의 volumeClaimTemplates로 모델이 영속되어 재시작 후에도 다시 풀하지 않습니다.

## 적용 방법

```bash
# LLM만 적용
kubectl apply -f src/k8s/llm/

# 또는 전체 스택과 함께 (루트 kustomization에 llm 리소스 포함)
kubectl apply -k src/k8s
```

## 전제 조건

- StatefulSet + Service만 사용하므로 Docker Desktop Kubernetes 등 어디서나 적용 가능.
- 이미지 `ollama/ollama:latest`가 풀 가능해야 함.
- 최초 기동 시 `ollama pull qwen3-coder:30b`가 실행되며, 모델 다운로드로 수 분 걸릴 수 있음. volumeClaimTemplates로 PVC가 생성되어 재시작 후에는 모델을 다시 받지 않음.

## 에이전트 연동

에이전트 Deployment에 환경 변수 추가:

- `LLM_BASE_URL=http://block-diagram-llm.block-diagram.svc.cluster.local:11434/v1`
- `LLM_MODEL_NAME=qwen3-coder:30b`
