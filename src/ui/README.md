# Block Diagram UI

에이전트에 설명을 보내고, 생성된 Mermaid 다이어그램을 렌더링하는 간단한 웹 UI입니다.

## 사전 요구사항

- **에이전트가 8080에서 실행 중**이어야 합니다.

  ```bash
  cd ../agent
  export GOOGLE_API_KEY=your_key
  go run main.go web api webui
  ```

## 실행 방법

1. 이 디렉터리에서 정적 파일 서버를 띄웁니다.

   ```bash
   cd src/ui
   npx --yes serve . -p 3000
   ```

   또는 Python:

   ```bash
   python3 -m http.server 3000
   ```

2. 브라우저에서 **http://localhost:3000** 으로 접속합니다.

3. **API 주소**가 `http://localhost:8080` 인지 확인합니다. **새 세션**으로 대화를 시작한 뒤, 왼쪽에서 설명을 입력해 전송하면 오른쪽에 Mermaid 다이어그램이 렌더링됩니다. 세션을 추가·삭제·선택해 여러 그림을 관리할 수 있습니다.

## CORS

UI(예: 3000)와 에이전트(8080)가 다른 포트이면 브라우저 CORS 정책 때문에 요청이 막힐 수 있습니다.  
에이전트(ADK)가 CORS를 허용하지 않으면:

- 같은 머신에서 **에이전트 내장 웹 UI**를 쓰거나 (`http://localhost:8080`),
- 개발 시에만 **브라우저 확장**으로 CORS를 완화하거나,
- UI를 8080으로 서빙하는 리버스 프록시를 두는 방식으로 테스트할 수 있습니다.

## 파일

| 파일       | 설명 |
|------------|------|
| `index.html` | 좌(세션 목록·채팅) / 우(Mermaid 렌더) 레이아웃 |
| `style.css`  | 두 패널 레이아웃·다크 테마·반응형 |
| `app.js`     | 세션 CRUD·선택·채팅·`/api/run` 호출·Mermaid 추출·렌더링 |
