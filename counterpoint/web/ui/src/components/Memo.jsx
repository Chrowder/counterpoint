import { marked } from 'marked'
import { t } from '../i18n.js'

// 把备忘录 markdown 存成本地 .md 文件,文件名用后端的 memo_file(<TICKER>-<日期>.md)
function downloadMemo(result) {
  const name = result.memo_file || `${result.ticker || 'memo'}.md`
  const blob = new Blob([result.markdown || ''], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export default function Memo({ result }) {
  const found = result?.found
  return (
    <section className="panel">
      <div className="panel-head">
        <span className="panel-title"><span className="dot" />{t('memo_title')}</span>
        <span className="panel-head-right">
          {found && result.rating && <span className="panel-tag">{t('memo_rating', { rating: result.rating })}</span>}
          {found && result.markdown && (
            <button className="memo-dl" onClick={() => downloadMemo(result)} title={t('memo_download')}>
              ↓ {t('memo_download')}
            </button>
          )}
        </span>
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
