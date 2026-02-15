# Block Diagram Agent (Python + Google ADK)
FROM python:3.12-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PORT=8080
EXPOSE 8080

# API 서버 (in-memory 또는 SESSION_SERVICE_URL 원격 세션)
CMD ["python", "-m", "uvicorn", "run_server:app", "--host", "0.0.0.0", "--port", "8080"]
