// 纯客户端 demo:把后端 demo.py 的「按时间渐进揭示」搬到前端,接口与 api.js 同形。
// 这样整站可作为纯静态部署(Vercel)——零后端、零 Band、零密钥、零 token。
// demo-fixture.json 是 web/fixtures/demo.json 的副本(让构建自包含,不依赖 ui/ 之外的文件)。
import fixture from './demo-fixture.json'

const REVEALABLE = fixture.messages.slice(0, 7)  // 末条人类签字留给 UI 触发
const STEP_MS = 3000                              // 每 3 秒亮一条
const MEMO_AT = STEP_MS * REVEALABLE.length       // 辩论全亮 → 备忘录就绪

const state = {}  // ticker -> { start, signed, decision, signer }

function elapsed(tk) {
  const s = state[tk]
  return s ? Date.now() - s.start : 0
}

function revealed(tk) {
  const n = Math.floor(elapsed(tk) / STEP_MS) + 1
  return REVEALABLE.slice(0, Math.max(0, Math.min(n, REVEALABLE.length)))
}

const STAGE_KEYS = ['evidence', 'theses', 'rebuttal', 'risk', 'memo', 'signed']

// 与后端 progress.derive_progress 一致:按各方发言条数粗粒度推导阶段。
function deriveProgress(messages, memoDone, signed) {
  const c = {}
  for (const m of messages) { const n = (m.sender || '').trim(); c[n] = (c[n] || 0) + 1 }
  const bull = c['Bull'] || 0, bear = c['Bear'] || 0
  const st = {
    evidence: (c['Data Steward'] || 0) >= 1 ? 'done' : 'pending',
    theses: (bull >= 1 && bear >= 1) ? 'done' : ((bull || bear) ? 'active' : 'pending'),
    rebuttal: (bull >= 2 && bear >= 2) ? 'done' : ((bull >= 2 || bear >= 2) ? 'active' : 'pending'),
    risk: (c['Risk Officer'] || 0) >= 1 ? 'done' : 'pending',
    memo: memoDone ? 'done' : 'pending',
    signed: signed ? 'done' : 'pending',
  }
  const events = STAGE_KEYS.map((key, i) => ({ step: i + 1, key, status: st[key] }))
  for (let i = 0; i < events.length; i++) {  // 第一个"前一步已完成、自己 pending"标 active
    if (events[i].status === 'pending' && (i === 0 || events[i - 1].status === 'done')) {
      events[i].status = 'active'; break
    }
  }
  return events
}

export function startResearch(tk) {
  state[tk] = { start: Date.now(), signed: false, decision: null, signer: null }
  return Promise.resolve({ ticker: tk, room_id: 'DEMO', status: 'started' })
}

export function getRoom(tk) {
  return Promise.resolve({ ticker: tk, messages: revealed(tk) })
}

export function getProgress(tk) {
  const s = state[tk]
  const memoDone = !!s && elapsed(tk) >= MEMO_AT
  const signed = !!s && s.signed
  return Promise.resolve({ ticker: tk, stages: deriveProgress(revealed(tk), memoDone, signed) })
}

export function getResult(tk) {
  const s = state[tk]
  if (!s || elapsed(tk) < MEMO_AT) return Promise.resolve({ found: false, ticker: tk })
  return Promise.resolve({
    found: true, ticker: tk, memo_file: `${fixture.ticker || 'DEMO'}.md`,
    markdown: fixture.memo_markdown, rating: fixture.rating, reflection: '',
    signed: s.signed, decision: s.decision, signer: s.signer, comments: '',
  })
}

export function signoff(tk, decision, signer) {
  const s = state[tk]
  if (!s || elapsed(tk) < MEMO_AT) return Promise.resolve({ ok: false, error: 'demo: memo not ready' })
  s.signed = true; s.decision = String(decision).toUpperCase(); s.signer = signer
  return Promise.resolve({ ok: true, message: 'demo recorded (no real file written)' })
}

export function cleanup(tk) {
  delete state[tk]
  return Promise.resolve({ ok: true, room_id: 'DEMO' })
}
