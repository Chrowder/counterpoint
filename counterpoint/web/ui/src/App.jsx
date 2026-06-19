import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import * as realApi from './api.js'
import * as demoApi from './demoApi.js'
import { t, LANG, setLang } from './i18n.js'

// 纯客户端 demo 开关:构建期 VITE_DEMO=1(Vercel 静态部署),或运行期加 ?demo=1。
// 开启后所有 api 调用走前端 fixture 回放,不连后端/Band。
export const DEMO = import.meta.env.VITE_DEMO === '1' || new URLSearchParams(window.location.search).has('demo')
const api = DEMO ? demoApi : realApi
import ScoreBar from './components/ScoreBar.jsx'
import Timeline from './components/Timeline.jsx'
import RoomStream from './components/RoomStream.jsx'
import Memo from './components/Memo.jsx'

// 阶段骨架:只保留 key/step/status,标题与负责方由 Timeline 按 key 本地化(见 i18n.js)。
const EMPTY_STAGES = [
  { step: 1, key: 'evidence', status: 'pending' },
  { step: 2, key: 'theses', status: 'pending' },
  { step: 3, key: 'rebuttal', status: 'pending' },
  { step: 4, key: 'risk', status: 'pending' },
  { step: 5, key: 'memo', status: 'pending' },
  { step: 6, key: 'signed', status: 'pending' },
]

// 把当前 ticker 写进 URL(?ticker=),刷新后可恢复;不动其它查询参数
function setUrlTicker(tk) {
  const u = new URL(window.location)
  if (tk) u.searchParams.set('ticker', tk)
  else u.searchParams.delete('ticker')
  window.history.replaceState(null, '', u)
}

function LangToggle({ lang, onToggle }) {
  return (
    <button className="lang-toggle" onClick={onToggle} title="中文 / English">
      {lang === 'zh' ? 'EN' : '中'}
    </button>
  )
}

function Header({ ticker, lang, onToggleLang }) {
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
          <div className="brand-name">Counterpoint {DEMO && <span className="demo-badge">DEMO</span>}</div>
          <div className="brand-sub">{t('brand_sub')}</div>
        </div>
      </div>
      <div className="header-right">
        {ticker && (
          <div className="ticker-chip">
            <div>
              <div className="ticker-symbol">{ticker}</div>
              <div className="ticker-company">{t('ticker_company')}</div>
            </div>
          </div>
        )}
        <LangToggle lang={lang} onToggle={onToggleLang} />
      </div>
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
  const [status, setStatus] = useState(DEMO ? t('demo_hint') : '')
  const [lang, setLangState] = useState(LANG)  // 切换语言时驱动整树重渲染
  const timer = useRef(null)
  const cleaned = useRef(false)
  const busy = useRef(false)  // 同步守卫:挡住回车+点击的并发双发(state 更新异步,挡不住)

  function toggleLang() {
    const next = lang === 'zh' ? 'en' : 'zh'
    setLang(next); setLangState(next)
  }

  async function tick(tk) {
    const [prog, res, room] = await Promise.all([
      api.getProgress(tk).catch(() => null),
      api.getResult(tk).catch(() => null),
      api.getRoom(tk).catch(() => null),
    ])
    if (prog?.stages) setStages(prog.stages)
    if (res) setResult(res)
    if (room?.messages) setMessages(room.messages)
    if (res?.found && res.signed) {
      setStatus(t('signed_status', { decision: res.decision, signer: res.signer || '', rating: res.rating || '—' }))
      stop(); busy.current = false; setRunning(false)  // 解锁,可研究下一个
      if (!cleaned.current) { cleaned.current = true; api.cleanup(tk).catch(() => {}) }  // 签字后清场,只一次
    } else if (res?.found) {
      setStatus(t('memo_ready'))
    }
  }

  function stop() { if (timer.current) { clearInterval(timer.current); timer.current = null } }

  async function start() {
    if (busy.current) return  // 已有研究在进行:挡住并发双发(回车+点击)
    const tk = input.trim().toUpperCase()
    if (!tk) return
    if (!/^[A-Z]{1,5}$/.test(tk)) { setStatus(t('bad_ticker')); return }  // 本地校验,提示随 UI 语言
    busy.current = true; setRunning(true)
    setTicker(tk); setResult({ found: false }); setStages(EMPTY_STAGES); setMessages([])
    setSigning(false); cleaned.current = false
    setStatus(t('starting'))
    let res
    try { res = await api.startResearch(tk) }
    catch (e) { setStatus(t('start_failed', { err: e })); busy.current = false; setRunning(false); return }
    if (res && res.ok === false) {
      setStatus(t('start_failed', { err: res.error || '' })); setTicker(null); busy.current = false; setRunning(false); return
    }
    setUrlTicker(tk)  // 写进 URL,刷新可恢复
    stop(); timer.current = setInterval(() => tick(tk), 5000); tick(tk)
  }

  // 刷新/直达恢复:先探该轮是否在跑(有房间消息)或已完成(有结果),是才接管轮询,
  // 避免对一个并未发起的 ticker 卡在"研究中"。仅预填则只填输入框、不锁定。
  async function resume(tk) {
    const [res, room] = await Promise.all([
      api.getResult(tk).catch(() => null),
      api.getRoom(tk).catch(() => null),
    ])
    setInput(tk)
    const active = (res && res.found) || (room?.messages?.length)
    if (!active) return
    setTicker(tk); busy.current = true; setRunning(true); cleaned.current = false; setSigning(false)
    stop(); timer.current = setInterval(() => tick(tk), 5000); tick(tk)
  }

  async function doSignoff(decision) {
    if (signing) return
    if (!signer.trim()) { setStatus(t('need_signer')); return }
    setSigning(true); setStatus(t('submitting_sign', { decision }))
    const r = await api.signoff(ticker, decision, signer.trim(), '').catch((e) => ({ ok: false, message: String(e) }))
    if (!r.ok) { setStatus(t('sign_failed', { err: r.error || r.message || '' })); setSigning(false); return }
    setTimeout(() => tick(ticker), 1200)
  }

  useEffect(() => stop, [])
  useEffect(() => { document.title = t('doc_title') }, [lang])  // 标签页标题随 UI 语言
  useEffect(() => {  // 挂载时按 URL 的 ?ticker 恢复(只跑一次)
    const tk = (new URLSearchParams(window.location.search).get('ticker') || '').trim().toUpperCase()
    if (/^[A-Z]{1,5}$/.test(tk)) resume(tk)
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  const showSignoff = result.found && !result.signed
  return (
    <div className="app">
      <Header ticker={ticker} lang={lang} onToggleLang={toggleLang} />

      <div className="searchbar">
        <input value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && start()}
          placeholder={t('search_placeholder')} autoComplete="off" disabled={running} />
        <button className="btn" onClick={start} disabled={running}>{running ? t('researching') : t('research')}</button>
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
              <div className="signed-banner">{t('signed_banner', { decision: result.decision, signer: result.signer })}</div>
            )}
            {showSignoff && (
              <div className="signoff-box">
                <div style={{ fontSize: 13, fontWeight: 600 }}>{t('signoff_gate')}</div>
                <div style={{ fontSize: 12, color: 'var(--text-faint)', marginTop: 4 }}>
                  {t('signoff_hint')}
                </div>
                <div className="signoff-row">
                  <input placeholder={t('signer_placeholder')} value={signer} onChange={(e) => setSigner(e.target.value)} />
                  <button className="btn" disabled={signing} onClick={() => doSignoff('APPROVE')}>APPROVE</button>
                  <button className="btn btn-ghost" disabled={signing} onClick={() => doSignoff('REJECT')}>REJECT</button>
                  <button className="btn btn-ghost" disabled={signing} onClick={() => doSignoff('REVISE')}>REVISE</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="footer">{t('footer')}</div>
    </div>
  )
}
