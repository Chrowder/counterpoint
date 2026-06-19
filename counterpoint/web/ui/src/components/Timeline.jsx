import { motion } from 'framer-motion'
import { t } from '../i18n.js'

const STATUS_KEY = { done: 'st_done', active: 'st_active', pending: 'st_pending' }

function StageItem({ s, index }) {
  return (
    <motion.div className="tl-item" initial={{ opacity: 0, x: -18 }} animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: 0.1 + index * 0.08, ease: 'easeOut' }}>
      <div className={`tl-node is-${s.status}`}>{s.status === 'done' ? '✓' : s.step}</div>
      <div className="tl-card">
        <div className="tl-top">
          <span className="tl-title">{t(`stage.${s.key}`)}</span>
          <span className={`tl-status is-${s.status}`}>{t(STATUS_KEY[s.status])}</span>
        </div>
        <div className="tl-stage-agent">{t(`agent.${s.key}`)}</div>
      </div>
    </motion.div>
  )
}

export default function Timeline({ stages }) {
  const done = stages.filter((s) => s.status === 'done').length
  return (
    <section className="panel">
      <div className="panel-head">
        <span className="panel-title"><span className="dot" />{t('tl_title')}</span>
        <span className="panel-tag">{t('tl_done', { done, total: stages.length })}</span>
      </div>
      <div className="panel-body">
        <div className="timeline">
          {stages.map((s, i) => <StageItem key={s.key} s={s} index={i} />)}
        </div>
      </div>
    </section>
  )
}
