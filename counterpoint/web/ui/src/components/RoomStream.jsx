import { useState } from 'react'
import { marked } from 'marked'

// Band 网站无法 iframe 嵌入(X-Frame-Options: SAMEORIGIN),改为原生直播房间消息——
// 我们读 Band 房间消息后自己渲染(markdown + 可展开),效果比嵌入更可控。
const SHORT = { 'Data Steward': 'Data', 'Risk Officer': 'Risk' }

function fmtTime(at) {
  if (!at) return ''
  try { return new Date(at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
  catch { return '' }
}

function Message({ m }) {
  const [open, setOpen] = useState(false)
  const long = (m.content || '').length > 240   // 长消息默认折叠,可展开
  return (
    <div className="msg">
      <div className="msg-head">
        <span className="agent-badge">{SHORT[m.sender] || m.sender}</span>
        <span className="msg-time">{fmtTime(m.at)}</span>
      </div>
      <div className={`msg-md ${long && !open ? 'clamp' : ''}`}
        dangerouslySetInnerHTML={{ __html: marked.parse(m.content || '') }} />
      {long && (
        <button className="msg-toggle" onClick={() => setOpen((v) => !v)}>
          {open ? '收起 ▲' : '展开全文 ▼'}
        </button>
      )}
    </div>
  )
}

export default function RoomStream({ messages }) {
  return (
    <section className="panel" style={{ marginTop: 22 }}>
      <div className="panel-head">
        <span className="panel-title"><span className="dot" />Band 房间直播</span>
        <span className="panel-tag">{messages.length} 条</span>
      </div>
      <div className="panel-body">
        {messages.length === 0 ? (
          <div className="stream-empty">尚无消息(研究发起后,agent 的发言会实时出现在这里)</div>
        ) : (
          <div className="stream">
            {messages.map((m, i) => <Message key={i} m={m} />)}
          </div>
        )}
      </div>
    </section>
  )
}
