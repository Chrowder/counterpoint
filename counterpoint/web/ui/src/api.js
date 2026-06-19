// 前端 → FastAPI 后端的薄封装。开发态经 vite proxy 到 :8000,生产态同源。
const json = (r) => r.json()

export const startResearch = (ticker) =>
  fetch('/api/research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker }),
  }).then(json)

export const getResult = (ticker) => fetch(`/api/result/${ticker}`).then(json)
export const getProgress = (ticker) => fetch(`/api/progress/${ticker}`).then(json)
export const getRoom = (ticker) => fetch(`/api/room/${ticker}`).then(json)

export const signoff = (ticker, decision, signer, comments) =>
  fetch('/api/signoff', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker, decision, signer, comments }),
  }).then(json)

export const cleanup = (ticker) => fetch(`/api/cleanup/${ticker}`, { method: 'POST' }).then(json)
