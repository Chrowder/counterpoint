import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import * as api from './api.js'
import ScoreBar from './components/ScoreBar.jsx'
import Timeline from './components/Timeline.jsx'
import RoomStream from './components/RoomStream.jsx'
import Memo from './components/Memo.jsx'

const EMPTY_STAGES = [
  { step: 1, key: 'evidence', title: '证据就绪', agent: 'Data Steward', status: 'pending' },
  { step: 2, key: 'theses', title: '多空盲评', agent: 'Bull / Bear', status: 'pending' },
  { step: 3, key: 'rebuttal', title: '交换反驳', agent: 'Bull / Bear', status: 'pending' },
  { step: 4, key: 'risk', title: '风险压测', agent: 'Risk Officer', status: 'pending' },
  { step: 5, key: 'memo', title: '综合备忘录', agent: 'Chair', status: 'pending' },
  { step: 6, key: 'signed', title: '人工签字', agent: '人类', status: 'pending' },
]

function Header({ ticker }) {
  return (
    <motion.header className="header" initial={{ opacity: 0, y: -14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
      <div className="brand">
        <div className="brand-mark">
          <svg viewBox="0 0 32 32">
            <path d="M6 23 L13 14 L18 18 L26 8" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="26" cy="8" r="2.8" fill="#fff" />
          </svg>
        </div>
        <div>
          <div className="brand-name">Counterpoint</div>
          <div className="brand-sub">对抗式投研台</div>
        </div>
      </div>
      {ticker && (
        <div className="ticker-chip">
          <div>
            <div className="ticker-symbol">{ticker}</div>
            <div className="ticker-company">多空跨模型对抗 · 人工签字</div>
          </div>
        </div>
      )}
    </motion.header>
  )
}

export default function App() {
  const [input, setInput] = useState('')
  const [ticker, setTicker] = useState(null)
  const [result, setResult] = useState({ found: false })
  const [stages, setStages] = useState(EMPTY_STAGES)
  const [messages, setMessages] = useState([])
  const [signer, setSigner] = useState('')
  const [signing, setSigning] = useState(false)
  const [running, setRunning] = useState(false)  // 研究进行中:禁掉"研究"按钮,防重复建房
  const [status, setStatus] = useState('')
  const timer = useRef(null)
  const cleaned = useRef(false)
  const busy = useRef(false)  // 同步守卫:挡住回车+点击的并发双发(state 更新异步,挡不住)

  async function tick(t) {
    const [prog, res, room] = await Promise.all([
      api.getProgress(t).catch(() => null),
      api.getResult(t).catch(() => null),
      api.getRoom(t).catch(() => null),
    ])
    if (prog?.stages) setStages(prog.stages)
    if (res) setResult(res)
    if (room?.messages) setMessages(room.messages)
    if (res?.found && res.signed) {
      setStatus(`✅ 已签字:${res.decision}(${res.signer || ''}) · 评级 ${res.rating || '—'}`)
      stop(); busy.current = false; setRunning(false)  // 解锁,可研究下一个
      if (!cleaned.current) { cleaned.current = true; api.cleanup(t).catch(() => {}) }  // 签字后清场,只一次
    } else if (res?.found) {
      setStatus('备忘录已生成,待人工签字。')
    }
  }

  function stop() { if (timer.current) { clearInterval(timer.current); timer.current = null } }

  async function start() {
    if (busy.current) return  // 已有研究在进行:挡住并发双发(回车+点击)
    const t = input.trim().toUpperCase()
    if (!t) return
    busy.current = true; setRunning(true)
    setTicker(t); setResult({ found: false }); setStages(EMPTY_STAGES); setMessages([])
    setSigning(false); cleaned.current = false
    setStatus('正在建房间并发起研究…')
    let res
    try { res = await api.startResearch(t) }
    catch (e) { setStatus('发起失败:' + e); busy.current = false; setRunning(false); return }
    if (res && res.ok === false) {
      setStatus('发起失败:' + (res.error || '')); setTicker(null); busy.current = false; setRunning(false); return
    }
    stop(); timer.current = setInterval(() => tick(t), 5000); tick(t)
  }

  async function doSignoff(decision) {
    if (signing) return
    if (!signer.trim()) { setStatus('请先填写签字人姓名(人工签字门需真实署名)'); return }
    setSigning(true); setStatus(`提交签字 ${decision}…`)
    const r = await api.signoff(ticker, decision, signer.trim(), '').catch((e) => ({ ok: false, message: String(e) }))
    if (!r.ok) { setStatus('签字失败:' + (r.error || r.message || '')); setSigning(false); return }
    setTimeout(() => tick(ticker), 1200)
  }

  useEffect(() => stop, [])

  const showSignoff = result.found && !result.signed
  return (
    <div className="app">
      <Header ticker={ticker} />

      <div className="searchbar">
        <input value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && start()}
          placeholder="输入股票代码,如 AAPL / NVDA / TSLA" autoComplete="off" disabled={running} />
        <button className="btn" onClick={start} disabled={running}>{running ? '研究中…' : '研究'}</button>
      </div>
      {status && <div style={{ color: 'var(--text-dim)', margin: '0 4px 18px', fontSize: 13 }}>{status}</div>}

      {ticker && <ScoreBar result={result} stages={stages} />}

      {ticker && (
        <div className="grid">
          <div>
            <Timeline stages={stages} />
            <RoomStream messages={messages} />
          </div>
          <div>
            <Memo result={result} />
            {result.signed && (
              <div className="signed-banner">✅ 已签字 {result.decision} · 签字人 {result.signer}</div>
            )}
            {showSignoff && (
              <div className="signoff-box">
                <div style={{ fontSize: 13, fontWeight: 600 }}>人工签字门</div>
                <div style={{ fontSize: 12, color: 'var(--text-faint)', marginTop: 4 }}>
                  备忘录须经真人审阅签字方可生效。
                </div>
                <div className="signoff-row">
                  <input placeholder="签字人姓名(必填)" value={signer} onChange={(e) => setSigner(e.target.value)} />
                  <button className="btn" disabled={signing} onClick={() => doSignoff('APPROVE')}>APPROVE</button>
                  <button className="btn btn-ghost" disabled={signing} onClick={() => doSignoff('REJECT')}>REJECT</button>
                  <button className="btn btn-ghost" disabled={signing} onClick={() => doSignoff('REVISE')}>REVISE</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="footer">Counterpoint · 多 agent 经 Band 对抗式投研 · 仅供教育研究,非投资建议</div>
    </div>
  )
}
