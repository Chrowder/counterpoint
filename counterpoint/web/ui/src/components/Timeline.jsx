import { motion } from 'framer-motion'

const STATUS_LABEL = { done: '已完成', active: '进行中', pending: '待进行' }

function StageItem({ s, index }) {
  return (
    <motion.div className="tl-item" initial={{ opacity: 0, x: -18 }} animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: 0.1 + index * 0.08, ease: 'easeOut' }}>
      <div className={`tl-node is-${s.status}`}>{s.status === 'done' ? '✓' : s.step}</div>
      <div className="tl-card">
        <div className="tl-top">
          <span className="tl-title">{s.title}</span>
          <span className={`tl-status is-${s.status}`}>{STATUS_LABEL[s.status]}</span>
        </div>
        <div className="tl-stage-agent">{s.agent}</div>
      </div>
    </motion.div>
  )
}

export default function Timeline({ stages }) {
  const done = stages.filter((s) => s.status === 'done').length
  return (
    <section className="panel">
      <div className="panel-head">
        <span className="panel-title"><span className="dot" />流水线进度</span>
        <span className="panel-tag">{done}/{stages.length} 完成</span>
      </div>
      <div className="panel-body">
        <div className="timeline">
          {stages.map((s, i) => <StageItem key={s.key} s={s} index={i} />)}
        </div>
      </div>
    </section>
  )
}
