(function () {
  const APP_NAME = 'diagram_agent';
  const USER_ID = 'ui-user';

  const newSessionBtn = document.getElementById('newSession');
  const deleteSessionBtn = document.getElementById('deleteSession');
  const sessionListEl = document.getElementById('sessionList');
  const chatMessagesEl = document.getElementById('chatMessages');
  const chatInputEl = document.getElementById('chatInput');
  const chatStatusEl = document.getElementById('chatStatus');
  const diagramPlaceholder = document.getElementById('diagramPlaceholder');
  const diagramViewport = document.getElementById('diagramViewport');
  const diagramEl = document.getElementById('diagram');
  const diagramContainer = document.getElementById('diagramContainer');
  const sessionListEmptyEl = document.getElementById('sessionListEmpty');

  let sessions = [];
  let currentSessionId = null;

  let diagramScale = 1;
  let diagramTx = 0;
  let diagramTy = 0;
  let diagramDrag = { active: false, startX: 0, startY: 0, startTx: 0, startTy: 0 };

  // Agent API (run 등). 기본값: 개발 시 8080, 배포 시 현재 origin.
  function apiBase() {
    if (window.AGENT_API_BASE) return window.AGENT_API_BASE.replace(/\/$/, '');
    if (window.location.port === '3000') return 'http://localhost:8080';
    return (window.location.origin || 'http://localhost:8080').replace(/\/$/, '');
  }

  // 세션 API (목록/생성/조회/삭제). 미설정 시 agent와 동일.
  function sessionApiBase() {
    if (window.SESSION_API_BASE) return window.SESSION_API_BASE.replace(/\/$/, '');
    return apiBase();
  }

  function apiUrl(path) {
    const base = apiBase();
    const prefix = base.endsWith('/api') ? base : base + '/api';
    return prefix.startsWith('http') ? prefix + path : base + '/api' + path;
  }

  function sessionApiUrl(path) {
    const base = sessionApiBase();
    const prefix = base.endsWith('/api') ? base : base + '/api';
    return prefix.startsWith('http') ? prefix + path : base + '/api' + path;
  }

  function setStatus(msg, type) {
    chatStatusEl.textContent = msg;
    chatStatusEl.className = 'status' + (type ? ' ' + type : '');
  }

  function applyDiagramTransform() {
    diagramViewport.style.transform = `translate(${diagramTx}px, ${diagramTy}px) scale(${diagramScale})`;
  }

  function resetDiagramTransform() {
    diagramScale = 1;
    diagramTx = 0;
    diagramTy = 0;
    applyDiagramTransform();
  }

  function setupDiagramPanZoom() {
    diagramContainer.addEventListener('wheel', (e) => {
      if (diagramViewport.hidden) return;
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.12 : 0.12;
      diagramScale = Math.min(4, Math.max(0.25, diagramScale + delta));
      applyDiagramTransform();
    }, { passive: false });

    diagramContainer.addEventListener('mousedown', (e) => {
      if (diagramViewport.hidden || e.button !== 0) return;
      diagramDrag.active = true;
      diagramDrag.startX = e.clientX;
      diagramDrag.startY = e.clientY;
      diagramDrag.startTx = diagramTx;
      diagramDrag.startTy = diagramTy;
    });
    document.addEventListener('mousemove', (e) => {
      if (!diagramDrag.active) return;
      diagramTx = diagramDrag.startTx + (e.clientX - diagramDrag.startX);
      diagramTy = diagramDrag.startTy + (e.clientY - diagramDrag.startY);
      applyDiagramTransform();
    });
    document.addEventListener('mouseup', () => {
      diagramDrag.active = false;
    });
  }

  function setLoading(loading) {
    chatInputEl.disabled = loading || !currentSessionId;
    if (loading) setStatus('처리 중…', 'loading');
  }

  async function listSessions() {
    const res = await fetch(sessionApiUrl(`/apps/${APP_NAME}/users/${USER_ID}/sessions`));
    if (!res.ok) throw new Error('세션 목록 조회 실패: ' + res.status);
    return res.json();
  }

  async function createSession() {
    const res = await fetch(sessionApiUrl(`/apps/${APP_NAME}/users/${USER_ID}/sessions`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ state: {}, events: [] }),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error('세션 생성 실패: ' + res.status + (text ? ' ' + text.slice(0, 150) : ''));
    }
    return res.json();
  }

  async function getSession(sessionId) {
    const res = await fetch(sessionApiUrl(`/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionId}`));
    if (!res.ok) throw new Error('세션 조회 실패: ' + res.status);
    return res.json();
  }

  async function deleteSession(sessionId) {
    const res = await fetch(sessionApiUrl(`/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionId}`), {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('세션 삭제 실패: ' + res.status);
  }

  async function runAgent(sessionId, text) {
    const res = await fetch(apiUrl('/run'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        appName: APP_NAME,
        sessionId: sessionId,
        userId: USER_ID,
        streaming: false, // 비스트리밍으로 응답 받아 afterModelCallback 등 동작 확인용
        newMessage: {
          role: 'user',
          parts: [{ text: text }],
        },
      }),
    });
    if (!res.ok) {
      const errBody = await res.text();
      throw new Error('실행 오류 ' + res.status + (errBody ? ': ' + errBody.slice(0, 200) : ''));
    }
    return res.json();
  }

  function stripJsonCodeFence(s) {
    let t = (s || '').trim();
    if (t.startsWith('```json')) t = t.slice(7).trim();
    else if (t.startsWith('```')) t = t.slice(3).trim();
    if (t.endsWith('```')) t = t.slice(0, -3).trim();
    return t.trim();
  }

  function parseMermaidJson(text) {
    const t = stripJsonCodeFence((text || '').trim());
    for (const raw of [t, t.replace(/\s*---[\s\S]*$/, '')]) {
      try {
        const j = JSON.parse(raw);
        if (j && typeof j.mermaid === 'string') return j;
      } catch (_) {}
      const start = raw.indexOf('{');
      const end = raw.lastIndexOf('}');
      if (start !== -1 && end > start) {
        try {
          const j = JSON.parse(raw.slice(start, end + 1));
          if (j && typeof j.mermaid === 'string') return j;
        } catch (_) {}
      }
    }
    return null;
  }

  function extractMermaid(text) {
    const j = parseMermaidJson(text);
    if (j) return j.mermaid.trim();
    const match = (text || '').match(/```mermaid\s*([\s\S]*?)```/);
    return match ? match[1].trim() : null;
  }

  function modelMessageDisplayText(text) {
    const j = parseMermaidJson(text);
    if (j) return (j.message && j.message.trim()) ? j.message.trim() : '다이어그램을 생성했습니다.';
    return (text || '').trim();
  }

  function collectModelText(events) {
    if (!Array.isArray(events) || !events.length) return '';
    let text = '';
    for (const ev of events) {
      const content = ev.content || (ev.message && ev.message.content);
      if (!content) continue;
      const parts = content.parts;
      const list = Array.isArray(parts) ? parts : [];
      for (const p of list) {
        if (p.text) text += p.text;
      }
      if (content.text) text += content.text;
    }
    return text;
  }

  function getEventText(ev) {
    const content = ev.content || ev.message?.content;
    if (!content) return '';
    if (typeof content === 'string') return content.trim();
    let text = '';
    const parts = content.parts;
    if (Array.isArray(parts)) {
      for (const p of parts) {
        if (p && p.text) text += p.text;
      }
    }
    if (content.text) text += content.text;
    return text;
  }

  /** 연속된 같은 작성자 이벤트를 묶어서 메시지 목록으로 만든다. (스트리밍 조각 합침) */
  function eventsToChatMessages(events) {
    const list = [];
    let current = { role: null, text: '' };
    for (const ev of events || []) {
      const author = (ev.author || '').toLowerCase();
      const text = getEventText(ev);
      if (!text.trim()) continue;
      const role = author === 'user' ? 'user' : 'model';
      if (current.role === role) {
        current.text += text;
      } else {
        if (current.role !== null) {
          const displayText = current.role === 'model' ? modelMessageDisplayText(current.text) : current.text.trim();
          list.push({ role: current.role, text: displayText });
        }
        current = { role, text };
      }
    }
    if (current.role !== null) {
      const displayText = current.role === 'model' ? modelMessageDisplayText(current.text) : current.text.trim();
      list.push({ role: current.role, text: displayText });
    }
    return list;
  }

  /** 첫 번째 사용자 메시지 요약 (세션 라벨 폴백용, 최대 28자). LLM이 제목을 안 넣었을 때 사용. */
  function getFirstUserMessageSummary(events) {
    for (const ev of events || []) {
      if ((ev.author || '').toLowerCase() !== 'user') continue;
      const text = getEventText(ev).trim();
      if (!text) continue;
      const maxLen = 28;
      return text.length <= maxLen ? text : text.slice(0, maxLen) + '…';
    }
    return '';
  }

  /**
   * 이벤트에서 가장 최근 모델 응답에 포함된 mermaid 코드만 반환.
   * 이벤트 순서에 관계없이 시간순으로 정렬한 뒤, 마지막으로 mermaid가 나온 턴을 사용.
   */
  function getLatestMermaidFromEvents(events) {
    const raw = events || [];
    const withIndex = raw.map((ev, i) => ({ ev, i }));
    const timeOf = (x) => x.ev.time ?? x.ev.Time ?? x.i;
    withIndex.sort((a, b) => timeOf(a) - timeOf(b));
    let modelText = '';
    let lastCode = '';
    const isUser = (ev) => (ev.author || '').toLowerCase() === 'user';
    for (const { ev } of withIndex) {
      const text = getEventText(ev);
      if (isUser(ev)) {
        if (modelText.trim()) {
          const code = extractMermaid(modelText);
          if (code) lastCode = code;
          modelText = '';
        }
        continue;
      }
      if (text) modelText += text;
    }
    if (modelText.trim()) {
      const code = extractMermaid(modelText);
      if (code) lastCode = code;
    }
    return lastCode;
  }

  function renderSessionList() {
    sessionListEmptyEl.hidden = sessions.length > 0;
    sessionListEl.innerHTML = '';
    const sorted = [...sessions].sort((a, b) => (b.lastUpdateTime || 0) - (a.lastUpdateTime || 0));
    for (let i = 0; i < sorted.length; i++) {
      const s = sorted[i];
      const label = s.title || (s.state && s.state.title) || getFirstUserMessageSummary(s.events) || `그림 ${sorted.length - i}`;
      const li = document.createElement('li');
      li.className = 'session-item' + (s.id === currentSessionId ? ' active' : '');
      li.textContent = label;
      li.dataset.sessionId = s.id;
      li.setAttribute('role', 'button');
      li.setAttribute('tabindex', '0');
      li.addEventListener('click', () => selectSession(s.id));
      li.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          selectSession(s.id);
        }
      });
      sessionListEl.appendChild(li);
    }
    deleteSessionBtn.disabled = !currentSessionId;
  }

  async function selectSession(sessionId) {
    currentSessionId = sessionId;
    renderSessionList();
    setStatus('', '');
    chatMessagesEl.innerHTML = '';
    diagramPlaceholder.hidden = false;
    diagramViewport.hidden = true;
    diagramContainer.classList.remove('has-diagram');
    diagramEl.innerHTML = '';

    if (!sessionId) {
      chatInputEl.placeholder = '새 세션을 만들거나 목록에서 세션을 선택하세요.';
      diagramPlaceholder.hidden = false;
      diagramViewport.hidden = true;
      diagramContainer.classList.remove('has-diagram');
      return;
    }

    chatInputEl.placeholder = '다이어그램 설명을 입력하세요… (Enter 전송)';
    setStatus('불러오는 중…', 'loading');

    try {
      const session = await getSession(sessionId);
      const messages = eventsToChatMessages(session.events || []);
      for (const msg of messages) {
        const div = document.createElement('div');
        div.className = 'chat-msg ' + msg.role;
        const who = document.createElement('span');
        who.className = 'chat-role';
        who.textContent = msg.role === 'user' ? '나' : '에이전트';
        const body = document.createElement('div');
        body.className = 'chat-body';
        body.textContent = msg.text;
        div.appendChild(who);
        div.appendChild(body);
        chatMessagesEl.appendChild(div);
      }
      chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;

      const mermaidCode = getLatestMermaidFromEvents(session.events || []);
      if (mermaidCode) {
        diagramPlaceholder.hidden = true;
        diagramViewport.hidden = false;
        diagramContainer.classList.add('has-diagram');
        resetDiagramTransform();
        await renderMermaid(mermaidCode);
      } else {
        diagramPlaceholder.hidden = false;
        diagramViewport.hidden = true;
        diagramContainer.classList.remove('has-diagram');
      }
      setStatus('', '');
      chatInputEl.focus();
    } catch (err) {
      setStatus('오류: ' + (err.message || String(err)), 'error');
    }
  }

  async function renderMermaid(code) {
    diagramEl.innerHTML = '';
    const block = document.createElement('div');
    block.className = 'mermaid';
    block.textContent = code;
    diagramEl.appendChild(block);
    try {
      await mermaid.run({
        nodes: [block],
        suppressErrors: false,
      });
    } catch (e) {
      diagramEl.innerHTML = '';
      const errDiv = document.createElement('div');
      errDiv.className = 'mermaid-error';
      errDiv.textContent = '다이어그램 렌더 오류: ' + (e.message || String(e));
      diagramEl.appendChild(errDiv);
    }
  }

  async function refreshSessionList() {
    try {
      sessions = await listSessions();
      console.log('[DEBUG] refreshSessionList: sessions=', sessions.length, sessions.map((s) => ({ id: s.id, state: s.state, title: s.state && s.state.title })));
      renderSessionList();
    } catch (err) {
      setStatus('세션 목록 조회 실패: ' + (err.message || String(err)), 'error');
      sessions = [];
      renderSessionList();
    }
  }

  newSessionBtn.addEventListener('click', async () => {
    setLoading(true);
    try {
      const session = await createSession();
      await refreshSessionList();
      await selectSession(session.id);
      setStatus('새 세션을 만들었습니다.', 'success');
    } catch (err) {
      setStatus('오류: ' + (err.message || String(err)), 'error');
    } finally {
      setLoading(false);
    }
  });

  deleteSessionBtn.addEventListener('click', async () => {
    if (!currentSessionId) return;
    if (!confirm('이 세션을 삭제할까요?')) return;
    setLoading(true);
    try {
      await deleteSession(currentSessionId);
      const prevId = currentSessionId;
      await refreshSessionList();
      currentSessionId = null;
      const remaining = sessions.filter((s) => s.id !== prevId);
      if (remaining.length) {
        await selectSession(remaining[0].id);
      } else {
        await selectSession(null);
      }
      setStatus('세션을 삭제했습니다.', 'success');
    } catch (err) {
      setStatus('오류: ' + (err.message || String(err)), 'error');
    } finally {
      setLoading(false);
    }
  });

  chatInputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  async function sendMessage() {
    const text = (chatInputEl.value || '').trim();
    if (!text || !currentSessionId) return;

    const userDiv = document.createElement('div');
    userDiv.className = 'chat-msg user';
    userDiv.innerHTML = '<span class="chat-role">나</span><div class="chat-body">' + escapeHtml(text) + '</div>';
    chatMessagesEl.appendChild(userDiv);
    chatInputEl.value = '';
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;

    setLoading(true);
    try {
      const events = await runAgent(currentSessionId, text);
      const fullText = collectModelText(events);
      console.log('[DEBUG] sendMessage: model response fullText=', fullText);
      let parsed = null;
      try {
        parsed = JSON.parse(stripJsonCodeFence(fullText));
        console.log('[DEBUG] sendMessage: parsed JSON=', { message: parsed.message, mermaid: parsed.mermaid ? '(present)' : null, title: parsed.title });
      } catch (e) {
        console.log('[DEBUG] sendMessage: JSON parse failed', e);
      }

      const mermaidCode = extractMermaid(fullText);

      const modelDiv = document.createElement('div');
      modelDiv.className = 'chat-msg model';
      modelDiv.innerHTML =
        '<span class="chat-role">에이전트</span><div class="chat-body">' +
        escapeHtml(modelMessageDisplayText(fullText) || '(응답 없음)') +
        '</div>';
      chatMessagesEl.appendChild(modelDiv);
      chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;

      if (mermaidCode) {
        diagramPlaceholder.hidden = true;
        diagramViewport.hidden = false;
        diagramContainer.classList.add('has-diagram');
        resetDiagramTransform();
        await renderMermaid(mermaidCode);
        setStatus('다이어그램을 반영했습니다.', 'success');
      } else {
        setStatus('응답에서 다이어그램을 찾지 못했습니다.', 'error');
      }
      // 세션 제목: 모델이 JSON으로 준 title을 UI에서 파싱해 Session Service events API로 state 갱신
      if (parsed && parsed.title) {
        try {
          const title = String(parsed.title).trim().slice(0, 25);
          const eventsUrl = sessionApiUrl(`/apps/${APP_NAME}/users/${USER_ID}/sessions/${currentSessionId}/events`);
          const res = await fetch(eventsUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              id: crypto.randomUUID(),
              time: Math.floor(Date.now() / 1000),
              actions: { stateDelta: { title } },
            }),
          });
          if (!res.ok) console.warn('[DEBUG] set session title via events: ', res.status, await res.text().catch(() => ''));
        } catch (e) {
          console.warn('[DEBUG] set session title via events failed:', e.message);
        }
      }
      await refreshSessionList();
      const current = sessions.find((s) => s.id === currentSessionId);
      console.log('[DEBUG] sendMessage: after refresh, current session=', current ? { id: current.id, state: current.state, 'state?.title': current.state && current.state.title } : null);
    } catch (err) {
      setStatus('오류: ' + (err.message || String(err)), 'error');
      const errDiv = document.createElement('div');
      errDiv.className = 'chat-msg model error';
      errDiv.innerHTML = '<span class="chat-role">에이전트</span><div class="chat-body">' + escapeHtml(err.message || String(err)) + '</div>';
      chatMessagesEl.appendChild(errDiv);
      chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
    } finally {
      setLoading(false);
      chatInputEl.focus();
    }
  }

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    securityLevel: 'loose',
  });

  setupDiagramPanZoom();

  refreshSessionList().then(() => {
    if (sessions.length && !currentSessionId) {
      const latest = [...sessions].sort((a, b) => (b.lastUpdateTime || 0) - (a.lastUpdateTime || 0))[0];
      if (latest) selectSession(latest.id);
    } else if (!sessions.length) {
      selectSession(null);
    }
  });
})();
