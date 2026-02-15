# src/k8s — Kubernetes Deployment

Manifests for deploying the agent, UI, and related services to Kubernetes. **All resources use the `block-diagram` namespace.**

## Folder Structure and Conventions

- **Per-service folders**: Each deployable (agent, UI, LLM, etc.) has its **own subfolder**. That service’s Deployment and Service (or e.g. KServe InferenceService) are managed there.
- **Root**: Shared resources (namespace, **shared Secret**), **Ingress** (external exposure for UI), and Kustomization.

| Path | Role |
|------|------|
| `k8s/` | Root. `namespace.yaml`, `secret.yaml`, `kustomization.yaml`. Apply with `kubectl apply -k src/k8s`. |
| `k8s/postgres/` | **PostgreSQL**: DB for session storage. PVC, Deployment, Service. **Session Service** connects via `SESSION_DB_*`. |
| `k8s/session-service/` | **Session Service** only: Deployment (PostgreSQL connection), Service (8081). Internal DNS: `block-diagram-session-service`. |
| `k8s/agent/` | **Agent** only: Deployment, Service (8080). Internal DNS: `block-diagram-agent`. Env: `SESSION_SERVICE_URL`; optionally `LLM_BASE_URL`. |
| `k8s/ui/` | **UI** only: Deployment, Service (80). Internal DNS: `block-diagram-ui`. |
| `k8s/llm/` | **LLM (Ollama)** only: Ollama StatefulSet + Service. `block-diagram` namespace, CPU-only (no GPU), OpenAI-compatible API (port 11434). Model persistence via volumeClaimTemplates. |

To add a new service, create `k8s/<service_name>/`, put that service’s manifests and `kustomization.yaml` there, and add `k8s/<service_name>` to the root `kustomization.yaml` resources.

## Resource Layout

### Root (`k8s/`)

| File | Description |
|------|-------------|
| `namespace.yaml` | Defines `block-diagram` namespace. |
| `secret.yaml` | `block-diagram-secrets`: `GOOGLE_API_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`. Referenced by agent and PostgreSQL. Replace secrets before deploy. |
| `ingress.yaml` | **Exposes UI via Ingress.** `/` → `block-diagram-ui`, `/api/run` → `block-diagram-agent`, `/api/apps` → `block-diagram-session-service` (session/event API). |
| `kustomization.yaml` | Includes namespace, secret, ingress, postgres, session-service, agent, ui, llm. Applies `block-diagram` namespace. |
| `KONG.md` | Kong Gateway / Ingress controller install and integration notes. |

### PostgreSQL (`k8s/postgres/`)

| File | Description |
|------|-------------|
| `pvc.yaml` | `postgres-data` PVC (1Gi). Persistent storage for session DB. |
| `deployment.yaml` | `block-diagram-postgres` Deployment. Image `postgres:16-alpine`, port 5432. Uses `block-diagram-secrets`. |
| `service.yaml` | `block-diagram-postgres` ClusterIP Service, 5432. Session Service connects to host `block-diagram-postgres`. |
| `kustomization.yaml` | Includes only the above. |

### Session Service (`k8s/session-service/`)

| File | Description |
|------|-------------|
| `deployment.yaml` | `block-diagram-session-service` Deployment. Image `block-diagram-session-service:latest`, port 8081. PostgreSQL via `SESSION_DB_*` env (from `block-diagram-secrets`). |
| `service.yaml` | `block-diagram-session-service` ClusterIP Service, 8081. |
| `kustomization.yaml` | Includes only the above. |

### Agent (`k8s/agent/`)

| File | Description |
|------|-------------|
| `deployment.yaml` | `block-diagram-agent` Deployment. Image `block-diagram-agent:latest`, port 8080. Env: `SESSION_SERVICE_URL=http://block-diagram-session-service:8081`. For in-memory, remove that env and add `SESSION_USE_MEMORY=true`. |
| `service.yaml` | `block-diagram-agent` ClusterIP Service, 8080. Kong용 업스트림 타임아웃(5분 read/write)은 Service 어노테이션 `konghq.com/connect-timeout`, `read-timeout`, `write-timeout`으로 설정. |
| `kustomization.yaml` | Includes only the above. |

### UI (`k8s/ui/`)

| File | Description |
|------|-------------|
| `deployment.yaml` | `block-diagram-ui` Deployment. Image `block-diagram-ui:latest`, port 80. |
| `service.yaml` | `block-diagram-ui` ClusterIP Service, 80. |
| `kustomization.yaml` | Includes only the above. |

### LLM (`k8s/llm/`)

| File | Description |
|------|-------------|
| `ollama-statefulset.yaml` | **Ollama** StatefulSet. Image `ollama/ollama`; pulls `qwen3-coder:30b` on startup. volumeClaimTemplates give each pod a PVC (10Gi) so the model persists across restarts. |
| `ollama-service.yaml` | Service `block-diagram-llm` (headless, 11434). For StatefulSet pod discovery and access. |
| `README.md` | How to apply (e.g. with `-k`). |

- **Service exposure**: Service `block-diagram-llm` (port 11434). Agent uses `LLM_BASE_URL=http://block-diagram-llm.block-diagram.svc.cluster.local:11434/v1`, `LLM_MODEL_NAME=qwen3-coder:30b`.
- **Ollama**: Runs on CPU only (no GPU), so usable on Docker Desktop etc.

**Agent–local LLM integration**: `src/agent` uses the endpoint at `LLM_BASE_URL` (or `KSERVE_URL`) when set (OpenAI-compatible); otherwise it uses Gemini (LiteLLM + ADK). For Ollama, use base URL `http://block-diagram-llm.block-diagram.svc.cluster.local:11434/v1` and `LLM_MODEL_NAME=qwen3-coder:30b`. With a local model only, `GOOGLE_API_KEY` is not required.

## How to Deploy

```bash
# Apply all (namespace + PostgreSQL + Session Service + agent + UI + LLM)
kubectl apply -k src/k8s

# PostgreSQL only
kubectl apply -k src/k8s/postgres
# … (session-service, agent, ui similarly)
# LLM only (Ollama StatefulSet + Service)
kubectl apply -f src/k8s/llm/
```

**When applying LLM**
- **Default is Ollama**: The command above deploys the Ollama StatefulSet and Service. CPU-only; model persistence via volumeClaimTemplates.

## Access

**UI is exposed via Ingress.** `/` → UI, `/api/run` → agent, `/api/apps` → Session Service. K8s Services are registered in internal DNS; the agent uses `SESSION_SERVICE_URL` from env to reach Session Service. Without Ingress, use port-forward.

**Port-forward**
```bash
# Session Service
kubectl port-forward -n block-diagram svc/block-diagram-session-service 8081:8081

# Agent
kubectl port-forward -n block-diagram svc/block-diagram-agent 8080:8080

# UI
kubectl port-forward -n block-diagram svc/block-diagram-ui 3000:80

# LLM (Ollama OpenAI-compatible API)
kubectl port-forward -n block-diagram svc/block-diagram-llm 11434:11434
# → http://localhost:11434/v1 locally
```

## Development Notes

- **Images**: Deployments reference `block-diagram-session-service:latest`, `block-diagram-agent:latest`, `block-diagram-ui:latest`. Build and push to a registry, or for Kind/Minikube use `docker load` / `kind load docker-image` etc.
- **Secret**: Secrets are managed in one place at root `k8s/secret.yaml` (`block-diagram-secrets`). Replace `GOOGLE_API_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` before deploy, or create via CI/CD with `kubectl create secret generic block-diagram-secrets ...`. Do not commit.
- **PostgreSQL**: Deployed in-cluster as `block-diagram-postgres` for session storage. Only **Session Service** connects via `SESSION_DB_*`; the agent uses Session Service at `SESSION_SERVICE_URL`, not the DB directly.
- **UI image**: Build an image that serves `src/ui` static files (e.g. nginx) and tag it as `block-diagram-ui:latest`.
- **Ingress**: Exposes UI externally. `/` → UI, `/api/run` → agent, `/api/apps` → Session Service. Use an Ingress controller such as Kong.
