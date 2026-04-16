import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send, Sparkles, MessageSquare, Loader2, FileUp, FileText,
  Key, LogOut, ChevronRight, Eye, EyeOff, CheckCircle2, AlertCircle,
  Globe, History, X, Clock, Trash2, Save, BookOpen, User, Lock,
} from 'lucide-react';
import './index.css';

// ── Constants ──────────────────────────────────────────────────────────────
const API_BASE   = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const LS_API_KEY = 'summarize_it_api_key';
const LS_TOKEN   = 'summarize_it_auth_token';
const LS_USER    = 'summarize_it_username';
const SCREEN     = { LANDING: 'landing', APP: 'app' };

// ════════════════════════════════════════════════════════════════════════════
// Root
// ════════════════════════════════════════════════════════════════════════════
export default function App() {
  const [screen, setScreen] = useState(SCREEN.LANDING);
  const [user,   setUser]   = useState(null);       // { username, token }
  const [apiKey, setApiKey] = useState('');

  // Load saved credentials on mount
  useEffect(() => {
    const savedKey = localStorage.getItem(LS_API_KEY);
    const savedToken = localStorage.getItem(LS_TOKEN);
    const savedUsername = localStorage.getItem(LS_USER);
    
    if (savedKey) setApiKey(savedKey);
    
    if (savedToken && savedUsername) {
      setUser({ username: savedUsername, token: savedToken });
      if (savedKey) {
        setScreen(SCREEN.APP);
      }
    }
  }, []);

  const saveApiKey = (key) => {
    const trimmed = key.trim();
    setApiKey(trimmed);
    localStorage.setItem(LS_API_KEY, trimmed);
  };

  const handleSignOut = () => {
    setUser(null);
    localStorage.removeItem(LS_TOKEN);
    localStorage.removeItem(LS_USER);
    setScreen(SCREEN.LANDING);
  };

  const handleAuthSuccess = (userData) => {
    setUser({ username: userData.username, token: userData.token });
    localStorage.setItem(LS_TOKEN, userData.token);
    localStorage.setItem(LS_USER, userData.username);
  };

  return (
    <div className="app">
      {screen === SCREEN.LANDING && (
        <LandingScreen
          user={user}
          apiKey={apiKey}
          onSaveKey={saveApiKey}
          onAuthSuccess={handleAuthSuccess}
          onEnterApp={() => setScreen(SCREEN.APP)}
          onSignOut={handleSignOut}
        />
      )}
      {screen === SCREEN.APP && (
        <MainApp
          user={user}
          apiKey={apiKey}
          onChangeKey={saveApiKey}
          onSignOut={handleSignOut}
          onGoLanding={() => setScreen(SCREEN.LANDING)}
        />
      )}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Landing Screen  (API key + Login/Register)
// ════════════════════════════════════════════════════════════════════════════
function LandingScreen({ user, apiKey: savedKey, onSaveKey, onAuthSuccess, onEnterApp, onSignOut }) {
  const [key,       setKey]       = useState(savedKey || '');
  const [showKey,   setShowKey]   = useState(false);
  const [keyError,  setKeyError]  = useState('');
  
  const [isLogin,   setIsLogin]   = useState(true);
  const [username,  setUsername]  = useState('');
  const [password,  setPassword]  = useState('');
  const [authBusy,  setAuthBusy]  = useState(false);
  const [authError, setAuthError] = useState('');

  const handleAuth = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setAuthError('Please fill in all fields.');
      return;
    }
    
    setAuthBusy(true);
    setAuthError('');
    
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Authentication failed');
      
      onAuthSuccess(data);
    } catch (e) {
      setAuthError(e.message);
    } finally {
      setAuthBusy(false);
    }
  };

  const handleContinue = (e) => {
    e.preventDefault();
    if (!key.trim()) { setKeyError('Please enter an API key.'); return; }
    if (!user) { setKeyError('Please sign in or register first.'); return; }
    setKeyError('');
    onSaveKey(key);
    onEnterApp();
  };

  return (
    <div className="fullscreen-center" style={{ padding: '1.5rem', overflowY: 'auto' }}>
      <div className="landing-card glass-panel" style={{ margin: 'auto' }}>

        {/* ── Brand ── */}
        <div className="landing-brand">
          <div className="landing-logo"><Sparkles size={30} color="#a78bfa" /></div>
          <h1 className="login-title">Summarize<span>It.</span></h1>
          <p className="login-subtitle">AI document analysis &amp; interactive Q&amp;A</p>
        </div>

        {/* ── Feature pills ── */}
        <ul className="login-features">
          <li><CheckCircle2 size={14} color="#a78bfa" /> Instant AI summaries</li>
          <li><Globe        size={14} color="#ec4899" /> Web search mode</li>
          <li><History      size={14} color="#34d399" /> Save &amp; restore sessions</li>
        </ul>

        <div className="landing-divider" />

        {/* ── Step 1: User Account ── */}
        <div className="landing-step">
          <p className="step-label">
            <History size={13} /> <strong>Step 1</strong> — Create Account or Login
          </p>

          {user ? (
            <div className="signed-in-row">
              <div className="avatar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <User size={16} />
              </div>
              <div style={{ flex: 1 }}>
                <p className="signed-in-name">{user.username}</p>
                <p className="signed-in-email" style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={onSignOut}>Sign out</p>
              </div>
              <CheckCircle2 size={18} color="#34d399" />
            </div>
          ) : (
            <form onSubmit={handleAuth} className="auth-form" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              <div className="apikey-input-wrap compact">
                <UserIconWrap>
                  <User size={14} color="#a78bfa" style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)' }}/>
                </UserIconWrap>
                <input
                  type="text"
                  placeholder="Username"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  style={{ paddingLeft: '2.5rem' }}
                />
              </div>
              <div className="apikey-input-wrap compact">
                <LockIconWrap>
                  <Lock size={14} color="#a78bfa" style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)' }}/>
                </LockIconWrap>
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  style={{ paddingLeft: '2.5rem' }}
                />
              </div>
              
              {authError && (
                <div className="apikey-error">
                  <AlertCircle size={13} /> {authError}
                </div>
              )}
              
              <button
                type="submit"
                className="btn full-width-btn compact-btn"
                disabled={authBusy}
              >
                {authBusy ? <Loader2 size={16} className="spin" /> : (isLogin ? 'Sign In' : 'Create Account')}
              </button>
              
              <p style={{ fontSize: '0.75rem', textAlign: 'center', marginTop: '0.2rem', color: 'var(--text-dim)' }}>
                {isLogin ? "Don't have an account? " : "Already have an account? "}
                <button 
                  type="button" 
                  onClick={() => { setIsLogin(!isLogin); setAuthError(''); }}
                  style={{ background: 'none', border: 'none', color: '#a78bfa', cursor: 'pointer', textDecoration: 'underline' }}
                >
                  {isLogin ? 'Register' : 'Login'}
                </button>
              </p>
            </form>
          )}
        </div>

        <div className="landing-divider" />

        {/* ── Step 2: API key ── */}
        <div className="landing-step">
          <p className="step-label"><Key size={13} /> <strong>Step 2</strong> — Enter your API key</p>
          <div className="apikey-input-wrap">
            <input
              id="api-key-input"
              type={showKey ? 'text' : 'password'}
              placeholder="Your API Key…"
              value={key}
              onChange={e => { setKey(e.target.value); setKeyError(''); }}
              autoComplete="off"
              spellCheck={false}
            />
            <button type="button" className="toggle-vis" onClick={() => setShowKey(s => !s)}>
              {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
          {keyError && (
            <div className="apikey-error">
              <AlertCircle size={13} /> {keyError}
            </div>
          )}
        </div>

        <div className="landing-divider" />

        {/* ── CTA ── */}
        <div className="landing-cta">
          <button
            id="continue-btn"
            className="btn full-width-btn"
            onClick={handleContinue}
          >
            Launch App <ChevronRight size={16} />
          </button>
        </div>

      </div>
    </div>
  );
}

const UserIconWrap = ({ children }) => <>{children}</>;
const LockIconWrap = ({ children }) => <>{children}</>;

// ════════════════════════════════════════════════════════════════════════════
// Session helpers (Backend REST API)
// ════════════════════════════════════════════════════════════════════════════

async function saveSession(userToken, session) {
  try {
    await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userToken}`
      },
      body: JSON.stringify(session)
    });
  } catch (e) {
    console.error('[Session] Save error:', e);
  }
}

async function loadSessions(userToken) {
  if (!userToken) return [];
  try {
    const res = await fetch(`${API_BASE}/sessions`, {
      headers: { 'Authorization': `Bearer ${userToken}` }
    });
    if (!res.ok) throw new Error('Failed to load');
    return await res.json();
  } catch (e) {
    console.error('[Session] Load error:', e);
    return [];
  }
}

async function deleteSession(userToken, sessionId) {
  if (!userToken) return;
  try {
    await fetch(`${API_BASE}/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${userToken}` }
    });
  } catch (e) {
    console.error('[Session] Delete error:', e);
  }
}

function newSessionId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

// ════════════════════════════════════════════════════════════════════════════
// Main App
// ════════════════════════════════════════════════════════════════════════════
function MainApp({ user, apiKey, onChangeKey, onSignOut, onGoLanding }) {
  // ── Core state ────────────────────────────────────────────────────────────
  const [uploadedFile, setUploadedFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processStatus, setProcessStatus] = useState('');
  const [isReady,   setIsReady]     = useState(false);
  const [summary,   setSummary]     = useState('');
  const [messages,  setMessages]    = useState([]);
  const [input,     setInput]       = useState('');
  const [isThinking, setIsThinking] = useState(false);

  // ── Web search ────────────────────────────────────────────────────────────
  const [webSearch, setWebSearch] = useState(false);

  // ── Sessions / history ────────────────────────────────────────────────────
  const [sessionId,  setSessionId]  = useState(() => newSessionId());
  const [sessions,   setSessions]   = useState([]);
  const [savingMsg,  setSavingMsg]  = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // ── Inline key edit ───────────────────────────────────────────────────────
  const [showKeyEdit, setShowKeyEdit] = useState(false);
  const [newKey,      setNewKey]      = useState(apiKey);
  const [showNewKey,  setShowNewKey]  = useState(false);

  const chatEndRef   = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => { setNewKey(apiKey); }, [apiKey]);

  // Load sessions on mount
  useEffect(() => {
    if (user?.token) loadSessions(user.token).then(setSessions);
  }, [user]);

  const authHeaders = useCallback(() => ({
    'X-Api-Key': apiKey,
    'Authorization': `Bearer ${user.token}`
  }), [apiKey, user.token]);

  // ── Check if auth failed ──────────────────────────────────────────────────
  const handleApiError = (errMessage) => {
    if (errMessage.includes('Authentication required') || errMessage.includes('expired') || errMessage.includes('Invalid session')) {
      alert("Session expired. Please log in again.");
      onSignOut();
      return true;
    }
    return false;
  };

  // ── Auto-save to Backend whenever messages or summary change ────────────
  useEffect(() => {
    if (!user?.token || (!summary && messages.length === 0)) return;
    setSavingMsg('Saving…');
    const timer = setTimeout(async () => {
      await saveSession(user.token, {
        id: sessionId,
        filename: uploadedFile?.name || 'Untitled',
        summary,
        messages,
        webSearch,
      });
      setSavingMsg('Saved ✓');
      // Refresh sidebar list silently
      loadSessions(user.token).then(setSessions);
      setTimeout(() => setSavingMsg(''), 2000);
    }, 1500);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summary, messages]);

  // ── Load a past session ───────────────────────────────────────────────────
  const restoreSession = (s) => {
    setSessionId(s.id);
    setSummary(s.summary || '');
    setMessages(s.messages || []);
    setWebSearch(s.webSearch || false);
    setIsReady(true);
    setSidebarOpen(false);
  };

  // ── New session ───────────────────────────────────────────────────────────
  const newSession = () => {
    setSessionId(newSessionId());
    setUploadedFile(null);
    setSummary('');
    setMessages([]);
    setIsReady(false);
    setWebSearch(false);
    setSidebarOpen(false);
  };

  // ── Delete session ────────────────────────────────────────────────────────
  const handleDeleteSession = async (e, s) => {
    e.stopPropagation();
    if (!user?.token) return;
    await deleteSession(user.token, s.id);
    setSessions(prev => prev.filter(x => x.id !== s.id));
  };

  const reset = () => { setSummary(''); setMessages([]); setIsReady(false); };

  // ── Process upload ────────────────────────────────────────────────────────
  const handleProcess = async () => {
    if (!uploadedFile) { alert('Please select a .txt or .pdf file.'); return; }
    reset();
    setIsProcessing(true);
    setProcessStatus('Reading document…');
    try {
      const formData = new FormData();
      formData.append('file', uploadedFile);
      const res = await fetch(`${API_BASE}/process-upload`, {
        method: 'POST',
        headers: authHeaders(),
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        if (!handleApiError(data.detail)) throw new Error(data.detail);
        return;
      }

      setProcessStatus('Generating AI summary…');
      const sRes  = await fetch(`${API_BASE}/summary`, { headers: authHeaders() });
      const sData = await sRes.json();
      if (!sRes.ok) {
        if (!handleApiError(sData.detail)) throw new Error(sData.detail);
        return;
      }

      setSummary(sData.summary);
      setIsReady(true);
      setMessages([{ role: 'ai', text: '✨ Document analyzed! Ask me anything about its content.' }]);
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
      setProcessStatus('');
    }
  };

  // ── Chat ──────────────────────────────────────────────────────────────────
  const handleSend = async () => {
    const q = input.trim();
    if (!q || isThinking) return;
    if (!isReady && !webSearch) { alert('Upload a document first, or enable Web Search.'); return; }
    setInput('');
    const wsLabel = webSearch ? ' 🌐' : '';
    setMessages(m => [...m, { role: 'user', text: q + wsLabel }]);
    setIsThinking(true);
    try {
      const chatHistory = messages.map(msg => ({ 
        role: msg.role === 'ai' ? 'assistant' : 'user', 
        content: msg.text.replace(' 🌐', '') 
      })).slice(-10); // Keep last 10 messages for context

      const endpoint = (!isReady && webSearch) ? '/web-search' : '/chat';
      const body     = endpoint === '/web-search'
        ? { question: q, history: chatHistory }
        : { question: q, web_search_enabled: webSearch, history: chatHistory };

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(body),
      });
      const d = await res.json();
      if (!res.ok) {
        if (!handleApiError(d.detail)) throw new Error(d.detail);
        return;
      }
      setMessages(m => [...m, { role: 'ai', text: d.answer }]);
    } catch (err) {
      setMessages(m => [...m, { role: 'ai', text: `Error: ${err.message}` }]);
    } finally {
      setIsThinking(false);
    }
  };

  const handleSaveKey = () => {
    if (newKey.trim()) onChangeKey(newKey.trim());
    setShowKeyEdit(false);
  };

  const isPDF = uploadedFile?.name.endsWith('.pdf');

  const chatEnabled = isReady || webSearch;

  return (
    <>
      {/* ════════════════════════════════════════════════════════════════════
          HISTORY SIDEBAR
          ════════════════════════════════════════════════════════════════════ */}
      {sidebarOpen && (
        <aside className="history-sidebar glass-panel">
          <div className="sidebar-header">
            <div className="sidebar-title">
              <History size={16} color="#a78bfa" />
              <span>Session History</span>
            </div>
            <button className="icon-close" onClick={() => setSidebarOpen(false)}>
              <X size={16} />
            </button>
          </div>

          <button className="btn new-session-btn" onClick={newSession}>
            <BookOpen size={14} /> New Session
          </button>

          <div className="session-list">
            {sessions.length === 0 && (
              <p className="no-sessions">No saved sessions yet.</p>
            )}
            {sessions.map(s => (
              <div
                key={s.id}
                className={`session-item ${s.id === sessionId ? 'active' : ''}`}
                onClick={() => restoreSession(s)}
              >
                <div className="session-item-info">
                  <FileText size={13} color="#a78bfa" />
                  <span className="session-filename">{s.filename || 'Untitled'}</span>
                </div>
                <div className="session-item-meta">
                  <Clock size={11} />
                  <span>{s.updatedAt ? new Date(s.updatedAt).toLocaleDateString() : 'Recent'}</span>
                  <button className="session-delete" onClick={e => handleDeleteSession(e, s)}>
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </aside>
      )}

      {/* ════════════════════════════════════════════════════════════════════
          TOP HEADER
          ════════════════════════════════════════════════════════════════════ */}
      <header className="app-header">
        <div className="app-header-left">
          <button
            className="header-chip"
            id="history-btn"
            onClick={() => setSidebarOpen(v => !v)}
            title="Session history"
          >
            <History size={13} />
            <span>History</span>
          </button>
          <div className="app-header-logo">
            <Sparkles size={17} color="#a78bfa" />
            <span>Summarize<em>It.</em></span>
          </div>
        </div>

        <div className="app-header-actions">
          {savingMsg && (
            <span className="save-indicator">
              <Save size={12} /> {savingMsg}
            </span>
          )}

          <button
            id="change-api-key-btn"
            className="header-chip"
            onClick={() => setShowKeyEdit(v => !v)}
            title="Change API key"
          >
            <Key size={13} />
            <span>API Key</span>
          </button>

          {user ? (
            <div className="header-user">
              <div className="avatar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <User size={16} />
              </div>
              <span className="header-username">{user.username}</span>
            </div>
          ) : null}

          <button id="sign-out-btn" className="header-chip danger" onClick={onSignOut} title="Sign out">
            <LogOut size={13} />
            <span>Exit</span>
          </button>
        </div>
      </header>

      {/* ── Inline API key editor ─────────────────────────────────────── */}
      {showKeyEdit && (
        <div className="key-edit-bar glass-panel">
          <Key size={14} color="#a78bfa" />
          <div className="apikey-input-wrap compact">
            <input
              id="header-api-key-input"
              type={showNewKey ? 'text' : 'password'}
              value={newKey}
              onChange={e => setNewKey(e.target.value)}
              placeholder="Your API Key…"
              autoComplete="off"
              spellCheck={false}
            />
            <button type="button" className="toggle-vis" onClick={() => setShowNewKey(s => !s)}>
              {showNewKey ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
          <button id="save-key-btn" className="btn compact-btn" onClick={handleSaveKey}>Save</button>
          <button className="btn compact-btn ghost" onClick={() => setShowKeyEdit(false)}>Cancel</button>
        </div>
      )}

      {/* ── Page title ──────────────────────────────────────────────────── */}
      <div className="main-title-block">
        <p className="subtitle">Upload a document for AI analysis — or ask anything with Web Search</p>
      </div>

      {/* ── Upload bar ──────────────────────────────────────────────────── */}
      <div className="input-section glass-panel">
        {isPDF
          ? <FileText size={20} style={{ color: '#f59e0b', flexShrink: 0 }} />
          : <FileUp   size={20} style={{ color: '#7c3aed', flexShrink: 0 }} />
        }
        <div className="file-input-wrapper">
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.pdf"
            id="file-upload-input"
            style={{ display: 'none' }}
            onChange={e => setUploadedFile(e.target.files[0] || null)}
          />
          <button className="file-choose-btn" onClick={() => fileInputRef.current.click()}>
            {uploadedFile
              ? <span className="file-name">
                  {uploadedFile.name}
                  <span className="file-size">({(uploadedFile.size / 1024).toFixed(0)} KB)</span>
                </span>
              : 'Choose a .txt or .pdf file…'}
          </button>
        </div>
        <button id="analyze-btn" className="btn" onClick={handleProcess} disabled={isProcessing}>
          {isProcessing ? <Loader2 size={18} className="spin" /> : 'Analyze'}
        </button>
      </div>

      <p className="formats-hint">Supported: .txt &nbsp;|&nbsp; .pdf</p>

      {/* ── Two-column panels ───────────────────────────────────────────── */}
      <div className="app-container">

        {/* Summary panel */}
        <div className="glass-panel">
          <div className="panel-header">
            <Sparkles size={20} color="#7c3aed" />
            <h2>Summary</h2>
          </div>
          <div className="summary-content">
            {isProcessing ? (
              <div className="center-placeholder">
                <Loader2 size={38} className="spin" />
                <p>{processStatus}</p>
              </div>
            ) : summary ? (
              <div dangerouslySetInnerHTML={{ __html:
                summary
                  .replace(/\n\n/g, '<br/><br/>')
                  .replace(/\n/g, '<br/>')
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  .replace(/^### (.*?)(<br\/>|$)/gm, '<h4>$1</h4>')
                  .replace(/^## (.*?)(<br\/>|$)/gm,  '<h3>$1</h3>')
              }} />
            ) : (
              <p className="center-placeholder faded">Summary will appear here after upload.</p>
            )}
          </div>
        </div>

        {/* Chat panel */}
        <div className="glass-panel">
          <div className="panel-header">
            <MessageSquare size={20} color="#ec4899" />
            <h2>Ask the Document</h2>

            {/* Web Search toggle */}
            <div className="web-search-toggle">
              <span className="ws-label">
                <Globe size={13} color={webSearch ? '#34d399' : '#6b7280'} />
                Web Search
              </span>
              <button
                id="web-search-toggle-btn"
                className={`toggle-switch ${webSearch ? 'on' : ''}`}
                onClick={() => setWebSearch(v => !v)}
                title={webSearch ? 'Web search ON' : 'Web search OFF'}
              >
                <span className="toggle-knob" />
              </button>
            </div>
          </div>

          {webSearch && (
            <div className="web-search-banner">
              <Globe size={13} /> Web search is <strong>ON</strong> — answers will include live web results
              {!isReady && <span className="ws-no-doc"> (no document loaded)</span>}
            </div>
          )}

          <div className="chat-container">
            {messages.length === 0 && !isProcessing && (
              <p className="center-placeholder faded">
                {webSearch ? 'Web search is active — ask me anything!' : 'Analyze a document, then ask questions here.'}
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`message ${m.role}`}>{m.text}</div>
            ))}
            {isThinking && <div className="message ai typing">Thinking…</div>}
            <div ref={chatEndRef} />
          </div>

          <div className="chat-input-area">
            <input
              id="chat-input"
              placeholder={
                webSearch && !isReady
                  ? 'Ask anything — searching the web…'
                  : chatEnabled
                    ? 'Ask a question about the document…'
                    : 'Upload a document or enable Web Search…'
              }
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              disabled={(!chatEnabled) || isThinking}
            />
            <button
              id="send-btn"
              className="btn icon-btn"
              onClick={handleSend}
              disabled={(!chatEnabled) || isThinking}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
