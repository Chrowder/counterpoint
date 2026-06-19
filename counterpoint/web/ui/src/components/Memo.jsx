import { marked } from 'marked'
import { t } from '../i18n.js'

export default function Memo({ result }) {
  const found = result?.found
  return (
    <section className="panel">
      <div className="panel-head">
        <span className="panel-title"><span className="dot" />{t('memo_title')}</span>
        {found && result.rating && <span className="panel-tag">{t('memo_rating', { rating: result.rating })}</span>}
      </div>
      <div className="panel-body">
        {found ? (
          <div className="memo-md" dangerouslySetInnerHTML={{ __html: marked.parse(result.markdown || '') }} />
        ) : (
          <div className="stream-empty" style={{ padding: 40 }}>
            {t('memo_empty')}
          </div>
        )}
      </div>
    </section>
  )
}
