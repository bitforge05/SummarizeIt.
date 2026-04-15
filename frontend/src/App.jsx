import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, MessageSquare, Loader2, FileUp, FileText } from 'lucide-react';
import './index.css';

const API_BASE = 'http://localhost:8000';

export default function App() {
  const [uploadedFile, setUploadedFile]   = useState(null);
  const [isProcessing, setIsProcessing]   = useState(false);
  const [processStatus, setProcessStatus] = useState('');
  const [isReady, setIsReady]             = useState(false);
  const [summary, setSummary]             = useState('');
  const [messages, setMessages]           = useState([]);
  const [input, setInput]                 = useState('');
  const [isThinking, setIsThinking]       = useState(false);
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const reset = () => { setSummary(''); setMessages([]); setIsReady(false); };

  const handleProcess = async () => {
    if (!uploadedFile) { alert('Please select a .txt or .pdf file.'); return; }
    reset();
    setIsProcessing(true);
    setProcessStatus('Reading document…');

    try {
      const formData = new FormData();
      formData.append('file', uploadedFile);
      const res = await fetch(`${API_BASE}/process-upload`, { method: 'POST', body: formData });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }

      setProcessStatus('Generating AI summary…');
      const sRes = await fetch(`${API_BASE}/summary`);
      const sData = await sRes.json();
      if (!sRes.ok) throw new Error(sData.detail);

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

  const handleSend = async () => {
    if (!input.trim() || isThinking) return;
    const q = input.trim();
    setInput('');
    setMessages(m => [...m, { role: 'user', text: q }]);
    setIsThinking(true);
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      });
      const d = await res.json();
      setMessages(m => [...m, { role: 'ai', text: d.answer }]);
    } catch {
      setMessages(m => [...m, { role: 'ai', text: 'Something went wrong. Try again.' }]);
    } finally {
      setIsThinking(false);
    }
  };

  const isPDF = uploadedFile?.name.endsWith('.pdf');

  return (
    <div className="app">
      <h1>Summarize<span>It.</span></h1>
      <p className="subtitle">Upload a document and get an instant AI summary + interactive Q&amp;A</p>

      {/* Upload bar */}
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

        <button className="btn" onClick={handleProcess} disabled={isProcessing}>
          {isProcessing ? <Loader2 size={18} className="spin" /> : 'Analyze'}
        </button>
      </div>

      <p className="formats-hint">Supported: .txt &nbsp;|&nbsp; .pdf</p>

      {/* Panels */}
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
          </div>

          <div className="chat-container">
            {messages.length === 0 && !isProcessing && (
              <p className="center-placeholder faded">Analyze a document, then ask questions here.</p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`message ${m.role}`}>{m.text}</div>
            ))}
            {isThinking && <div className="message ai typing">Thinking…</div>}
            <div ref={chatEndRef} />
          </div>

          <div className="chat-input-area">
            <input
              placeholder={isReady ? 'Ask a question about the document…' : 'Upload a document first…'}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              disabled={!isReady || isThinking}
            />
            <button className="btn icon-btn" onClick={handleSend} disabled={!isReady || isThinking}>
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
