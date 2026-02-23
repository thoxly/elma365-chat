import { useState, useEffect } from 'react'
import { templatesApi } from '../api/client'

export default function Templates() {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await templatesApi.list();
      setList(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message);
      setList([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) return <p className="placeholder">Загрузка...</p>;
  if (error) return <p className="error">Ошибка: {error}</p>;

  return (
    <div className="templates-page">
      <h2>Шаблоны заданий</h2>
      <button type="button" onClick={load} className="btn-secondary">Обновить</button>
      <ul className="templates-list">
        {list.map((t) => (
          <li key={t.id} className="template-card">
            <strong>{t.name}</strong>
            {t.description && <p>{t.description}</p>}
            <small>ID: {t.id}</small>
          </li>
        ))}
      </ul>
      {list.length === 0 && <p className="placeholder">Шаблонов пока нет. Создайте через API.</p>}
    </div>
  )
}
