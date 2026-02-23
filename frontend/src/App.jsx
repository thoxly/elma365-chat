import { useState } from 'react'
import Chat from './pages/Chat'
import Templates from './pages/Templates'
import Rules from './pages/Rules'
import './App.css'

const PAGES = { chat: 'Чат', templates: 'Шаблоны', rules: 'Правила' };

function App() {
  const [page, setPage] = useState('chat');

  return (
    <div className="app">
      <nav className="nav">
        <h1 className="logo">ELMA365 Chat</h1>
        {Object.entries(PAGES).map(([key, label]) => (
          <button
            key={key}
            className={page === key ? 'nav-btn active' : 'nav-btn'}
            onClick={() => setPage(key)}
          >
            {label}
          </button>
        ))}
      </nav>
      <main className="main">
        {page === 'chat' && <Chat />}
        {page === 'templates' && <Templates />}
        {page === 'rules' && <Rules />}
      </main>
    </div>
  )
}

export default App
