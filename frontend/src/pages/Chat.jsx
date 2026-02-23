import { useState, useRef, useEffect } from 'react'
import { chatApi, templatesApi } from '../api/client'

export default function Chat({ sessionId, userId, onSessionTitle }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [templateId, setTemplateId] = useState('')
  const [templates, setTemplates] = useState([])
  const [toolsOpen, setToolsOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const bottomRef = useRef(null)
  const fileInputRef = useRef(null)
  const titleSetRef = useRef(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    templatesApi.list().then(setTemplates).catch(() => {})
  }, [])

  async function loadHistory() {
    try {
      const data = await chatApi.getHistory(sessionId, userId)
      setMessages(data.messages || [])
    } catch {
      setMessages([])
    }
  }

  useEffect(() => {
    titleSetRef.current = false
    loadHistory()
  }, [sessionId])

  async function send() {
    if (!input.trim() || loading) return
    const text = input.trim()
    const userMsg = { role: 'user', content: text }
    setMessages((m) => [...m, userMsg])
    setInput('')
    setLoading(true)
    if (!titleSetRef.current && onSessionTitle) {
      titleSetRef.current = true
      onSessionTitle(sessionId, text.slice(0, 50) + (text.length > 50 ? '…' : ''))
    }
    try {
      const body = {
        user_id: userId,
        session_id: sessionId,
        message: text,
      }
      if (templateId) body.template_id = parseInt(templateId, 10)
      const res = await chatApi.sendMessage(body)
      setMessages((m) => [...m, { role: res.role, content: res.content }])
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `Ошибка: ${e.message}` }])
    } finally {
      setLoading(false)
    }
  }

  async function handleFile(e) {
    const file = e.target.files?.[0]
    if (!file || uploading) return
    setUploading(true)
    try {
      await chatApi.uploadDocument(userId, sessionId, file)
      await loadHistory()
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', content: `Ошибка загрузки: ${err.message}` }])
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  return (
    <div className="chat-layout">
      <div className="chat-messages">
        <div className="chat-messages-inner">
          {messages.length === 0 && (
            <p className="chat-placeholder">
              Напишите сообщение или откройте инструменты для шаблона и загрузки файла.
            </p>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`message message-${msg.role}`}>
              <span className="message-role">
                {msg.role === 'user' ? 'Вы' : 'Ассистент'}
              </span>
              <div className="message-content">{msg.content}</div>
            </div>
          ))}
          {loading && (
            <div className="message message-assistant">
              <span className="message-role">Ассистент</span>
              <div className="message-content">…</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>
      <div className="chat-input-wrap">
        <div className="chat-input-inner">
          <div className="chat-tools">
            <button
              type="button"
              className={`btn-tools ${toolsOpen ? 'open' : ''}`}
              onClick={() => setToolsOpen((v) => !v)}
            >
              Инструменты
            </button>
            {toolsOpen && (
              <div className="chat-tools-panel">
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
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.md,.json"
                  style={{ display: 'none' }}
                  onChange={handleFile}
                />
                <button
                  type="button"
                  className="btn-tools"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                >
                  {uploading ? 'Загрузка…' : 'Файл'}
                </button>
              </div>
            )}
          </div>
          <div className="chat-input-row">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) =>
                e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())
              }
              placeholder="Сообщение..."
              rows={2}
            />
            <button
              type="button"
              className="btn-send"
              onClick={send}
              disabled={loading}
            >
              Отправить
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
