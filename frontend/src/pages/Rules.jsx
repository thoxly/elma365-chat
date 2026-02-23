import { useState, useEffect } from 'react'
import { rulesApi } from '../api/client'

export default function Rules() {
  const [rules, setRules] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    setError('');
    rulesApi.list()
      .then((data) => setRules(data || {}))
      .catch((e) => { setError(e.message); setRules({}); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="placeholder">Загрузка...</p>;
  if (error) return <p className="error">Ошибка: {error}</p>;

  const entries = Object.entries(rules);
  return (
    <div className="rules-page">
      <h2>Правила ELMA365</h2>
      {entries.length === 0 && <p className="placeholder">Правил нет. Запустите миграцию: python scripts/migrate_rules_to_db.py</p>}
      <ul className="rules-list">
        {entries.map(([type, r]) => (
          <li key={type} className="rule-card">
            <strong>{type}</strong>
            <span className="rule-meta">v{r.version}</span>
            <pre className="rule-preview">{typeof r.content?.text === 'string' ? r.content.text.slice(0, 200) + '...' : JSON.stringify(r.content).slice(0, 200) + '...'}</pre>
          </li>
        ))}
      </ul>
    </div>
  )
}
