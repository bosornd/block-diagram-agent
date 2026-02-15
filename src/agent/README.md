# Block Diagram Agent (ADK + Python)

ADK를 사용한 다이어그램 생성 에이전트. 사용자 설명을 받아 Mermaid 블록/플로우차트 코드를 생성합니다. Pydantic `DiagramResponse`로 title / message / mermaid 를 구분해 출력합니다.

## 요구 사항

- Python 3.10+
- [Gemini API 키](https://aistudio.google.com/app/apikey)

## 로컬 실행

```bash
# 의존성
pip install -r requirements.txt

# API 키 설정 후 실행 (API 서버 http://localhost:8080)
export GOOGLE_API_KEY=your_api_key
export SESSION_USE_MEMORY=true
python -m uvicorn run_server:app --host 0.0.0.0 --port 8080
```

`.env` 사용 시:

```bash
cp .env.example .env   # .env에 GOOGLE_API_KEY 설정
source .env
export SESSION_USE_MEMORY=true
python -m uvicorn run_server:app --host 0.0.0.0 --port 8080
```

또는 프로젝트 루트에서 `./scripts/dev-local.sh` 로 에이전트 + UI 한 번에 실행.

## 컨테이너 빌드 및 실행

```bash
# 이미지 빌드 (프로젝트 루트에서)
docker build -t block-diagram-agent src/agent

# 실행 (API 키·세션 URL은 환경변수로 전달)
docker run --rm -p 8080:8080 \
  -e GOOGLE_API_KEY=your_api_key \
  -e SESSION_SERVICE_URL="http://session-service:8081" \
  block-diagram-agent
```

에이전트는 포트 8080에서 API만 제공합니다. UI는 별도로 서빙(예: `./scripts/dev-local.sh` 또는 K8s 배포) 후 에이전트 주소를 8080으로 설정해 사용합니다.
