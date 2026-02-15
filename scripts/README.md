# scripts — Build and Deploy Scripts

Run from the project root.

## dev-local.sh (Local Development)

Starts the agent (in-memory sessions, no DB) and UI together.

```bash
# Configure LLM in .env (one of the following)
# - Gemini: GOOGLE_API_KEY
# - Local LLM (e.g. KServe): LLM_BASE_URL or KSERVE_URL (OpenAI-compatible base URL)
cp .env.example .env   # if needed
./scripts/dev-local.sh
```

| Target   | URL |
|----------|-----|
| **Agent** | http://localhost:8080 |
| **UI**    | http://localhost:3000 (API base is set to 8080) |

- If port 8080 is already in use, stop that process and run again.
- To stop: **Ctrl+C** — stops both agent and UI.

When done developing, deploy to k8s with `./scripts/rebuild-and-deploy.sh` or `deploy-k8s.sh`.

## build-images.sh

Builds Docker images.

```bash
./scripts/build-images.sh [session-service|agent|ui|all]
```

| Argument | Description |
|----------|-------------|
| `session-service` | Build session service image only → `block-diagram-session-service:latest` |
| `agent` | Build agent image only → `block-diagram-agent:latest` |
| `ui`    | Build UI image only → `block-diagram-ui:latest` |
| `all`   | Build session service + agent + UI (default) |

- Session service: built from `src/session-service/Dockerfile` (PostgreSQL connection, ADK-compatible session API)
- Agent: built from `src/agent/Dockerfile` (Python + ADK)
- UI: built from `src/ui/Dockerfile` (nginx + static files)

## rebuild-and-deploy.sh

Rebuilds Docker images and redeploys to Kubernetes. (build → kubectl apply → rollout restart)

```bash
./scripts/rebuild-and-deploy.sh [--dry-run] [session-service|agent|ui|all]
```

| Argument/option | Description |
|----------------|-------------|
| `session-service` | Build and deploy session service only |
| `agent`   | Build and deploy agent only |
| `ui`      | Build and deploy UI only |
| `all`     | Session service + agent + UI (default) |
| `--dry-run` | Dry-run apply only; build still runs |

- If you get **Deployment `spec.selector` immutable** errors, delete that Deployment and run again.  
  Example: `kubectl delete deployment block-diagram-ui -n block-diagram`

## deploy-k8s.sh

Applies resources to Kubernetes with Kustomize.

```bash
./scripts/deploy-k8s.sh [--dry-run] [--agent-only|--ui-only]
```

| Option          | Description |
|-----------------|-------------|
| (none)          | Apply all (`src/k8s`: namespace + agent + ui) |
| `--agent-only` | Apply agent only (`src/k8s/agent`) |
| `--ui-only`    | Apply UI only (`src/k8s/ui`) |
| `--dry-run`    | Show manifests that would be applied, without applying |

For agent Secret (`GOOGLE_API_KEY`) before deploy, see [src/k8s/README.md](../src/k8s/README.md).

- **StatefulSet (LLM)**: Some spec fields (e.g. volumeClaimTemplates) are immutable. If apply fails for that reason, the script deletes the `block-diagram-llm` StatefulSet and reapplies automatically. Existing PVCs with the same name are reused.

## port-forward-ingress.sh

Use when you want to reach **Ingress paths (e.g. UI) on localhost** by port-forwarding to the Ingress Controller. (Ingress alone does not bind to localhost.)

```bash
./scripts/port-forward-ingress.sh [local-port]
```

- Default local port: `8080` → http://localhost:8080
- If your Ingress Controller is not `ingress-nginx-controller` in namespace `ingress-nginx`, set env vars `INGRESS_NS` and `INGRESS_SVC`.
