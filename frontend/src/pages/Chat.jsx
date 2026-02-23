import { useState, useRef, useEffect } from 'react'
import { chatApi, templatesApi } from '../api/client'

const USER_ID = 'web-user';
const SESSION_ID = 'default-session';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [templateId, setTemplateId] = useState('');
  const [templates, setTemplates] = useState([]);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    templatesApi.list().then(setTemplates).catch(() => {});
  }, []);

  async function loadHistory() {
    try {
      const data = await chatApi.getHistory(SESSION_ID, USER_ID);
      setMessages(data.messages || []);
    } catch (e) {
      setMessages([{ role: 'assistant', content: `Ошибка загрузки: ${e.message}` }]);
    }
  }

  useEffect(() => { loadHistory(); }, []);

  async function send() {
    if (!input.trim() || loading) return;
    const userMsg = { role: 'user', content: input.trim() };
    setMessages((m) => [...m, userMsg]);
    setInput('');
    setLoading(true);
    try {
      const body = {
        user_id: USER_ID,
        session_id: SESSION_ID,
        message: input.trim(),
      };
      if (templateId) body.template_id = parseInt(templateId, 10);
      const res = await chatApi.sendMessage(body);
      setMessages((m) => [...m, { role: res.role, content: res.content }]);
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `Ошибка: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-header">
        <select
          value={templateId}
          onChange={(e) => setTemplateId(e.target.value)}
          className="template-select"
        >
          <option value="">Без шаблона</option>
          {templates.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        <button type="button" onClick={loadHistory} className="btn secondary">Обновить историю</button>
      </div>
      <div className="messages">
        {messages.length === 0 && (
          <p className="placeholder">Напишите сообщение или выберите шаблон и задайте вопрос.</p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message message-${msg.role}`}>
            <span className="message-role">{msg.role === 'user' ? 'Вы' : 'Ассистент'}</span>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        {loading && <div className="message message-assistant"><span className="message-role">Ассистент</span><div className="message-content">...</div></div>}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
          placeholder="Сообщение..."
          rows={2}
        />
        <button type="button" onClick={send} disabled={loading} className="btn primary">Отправить</button>
      </div>
    </div>
  )
}
