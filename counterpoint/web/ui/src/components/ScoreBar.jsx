import { motion } from 'framer-motion'
import RiskPill from './RiskPill.jsx'

// 顶部评分卡:评级 / Risk 可靠性(从备忘录文本尽力提取)/ 证据引用数 / 流程进度。
function reliabilityFrom(markdown) {
  if (!markdown) return null
  const m = markdown.match(/可靠性[^\n。]*?(低|中低|中|中高|高|Low|Moderate|High)/)
  return m ? m[1] : null
}
function citationCount(markdown) {
  if (!markdown) return 0
  return new Set((markdown.match(/\[E\d+\]/g) || [])).size
}

function Card({ label, value, meta, children, fill }) {
  return (
    <div className="score-card">
      <div className="score-label">{label}</div>
      {value !== undefined && <div className="score-value">{value}</div>}
      {children}
      {meta && <div className="score-meta">{meta}</div>}
      {fill !== undefined && (
        <div className="score-track">
          <motion.div className="score-fill" initial={{ width: 0 }}
            animate={{ width: `${Math.round(fill * 100)}%` }} transition={{ duration: 0.7 }} />
        </div>
      )}
    </div>
  )
}

export default function ScoreBar({ result, stages }) {
  const md = result?.markdown
  const done = stages.filter((s) => s.status === 'done').length
  const reliability = reliabilityFrom(md)
  const cites = citationCount(md)
  return (
    <motion.div className="scorebar" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}>
      <Card label="评级">
        {result?.rating ? <div style={{ marginTop: 8 }}><RiskPill rating={result.rating} /></div>
          : <div className="score-value" style={{ fontSize: 20, color: 'var(--text-faint)' }}>—</div>}
      </Card>
      <Card label="Risk 可靠性" value={reliability || '—'} meta="基于现有证据下结论的可靠性" />
      <Card label="证据引用" value={cites} meta="备忘录引用的独立证据条数 [E*]" />
      <Card label="流程进度" value={`${done}/${stages.length}`} meta="盲评→反驳→压测→综合→签字" fill={done / stages.length} />
    </motion.div>
  )
}
