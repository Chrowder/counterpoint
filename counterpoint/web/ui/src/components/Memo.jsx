import { marked } from 'marked'

export default function Memo({ result }) {
  const found = result?.found
  return (
    <section className="panel">
      <div className="panel-head">
        <span className="panel-title"><span className="dot" />研究备忘录</span>
        {found && result.rating && <span className="panel-tag">评级 {result.rating}</span>}
      </div>
      <div className="panel-body">
        {found ? (
          <div className="memo-md" dangerouslySetInnerHTML={{ __html: marked.parse(result.markdown || '') }} />
        ) : (
          <div className="stream-empty" style={{ padding: 40 }}>
            研究进行中…多空盲评 → 反驳 → 风险压测 → 综合,约需数分钟。
          </div>
        )}
      </div>
    </section>
  )
}
