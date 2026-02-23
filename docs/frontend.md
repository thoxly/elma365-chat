# Frontend (Vite + React)

## Структура

- **frontend/** — корень приложения для Vercel (Root Directory = `frontend`)
- **src/App.jsx** — навигация и выбор страницы (Чат, Шаблоны, Правила)
- **src/pages/** — Chat.jsx, Templates.jsx, Rules.jsx
- **src/api/client.js** — API-клиент (chatApi, templatesApi, rulesApi), базовый URL из `VITE_API_URL`
- **vercel.json** — конфиг сборки и SPA rewrites

## Запуск

```bash
cd frontend
npm install
npm run dev
```

Сборка: `npm run build`. Результат в `dist/`.

## Переменные окружения

- **VITE_API_URL** — URL бэкенда (на Vercel задаётся в настройках проекта). По умолчанию `http://localhost:8000`.
