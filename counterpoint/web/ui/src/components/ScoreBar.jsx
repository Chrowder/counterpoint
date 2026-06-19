import { motion } from 'framer-motion'
import RiskPill from './RiskPill.jsx'
import { t } from '../i18n.js'

// 顶部评分卡:评级 / Risk 可靠性(从备忘录文本尽力提取)/ 证据引用数 / 流程进度。
// 中英备忘录措辞不同,两套模式都试:中文"可靠性…高/中/低",英文"reliability…High/Medium/Low"。
function reliabilityFrom(markdown) {
  if (!markdown) return null
  const zh = markdown.match(/可靠性[^\n。]*?(中低|中高|低|中|高)/)
  if (zh) return zh[1]
  const en = markdown.match(/reliabilit[^\n.]*?\b(Low|Medium|Moderate|High)\b/i)
  return en ? en[1] : null
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
      <Card label={t('sc_rating')}>
        {result?.rating ? <div style={{ marginTop: 8 }}><RiskPill rating={result.rating} /></div>
          : <div className="score-value" style={{ fontSize: 20, color: 'var(--text-faint)' }}>—</div>}
      </Card>
      <Card label={t('sc_reliability')} value={reliability || '—'} meta={t('sc_reliability_meta')} />
      <Card label={t('sc_cites')} value={cites} meta={t('sc_cites_meta')} />
      <Card label={t('sc_progress')} value={`${done}/${stages.length}`} meta={t('sc_progress_meta')} fill={done / stages.length} />
    </motion.div>
  )
}
