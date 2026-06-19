// 轻量 i18n:locale 由 ?lang= 或 localStorage 决定,默认 en(本分支默认英文)。无第三方依赖。
// UI 语言与后端 OUTPUT_LANG 解耦——界面文案、阶段标题全部前端按 key 映射,
// 不依赖后端返回的文案(后端文案只供非 UI 消费方/回退)。
const STR = {
  zh: {
    doc_title: 'Counterpoint · 对抗式投研台',
    brand_sub: '对抗式投研台',
    ticker_company: '多空跨模型对抗 · 人工签字',
    search_placeholder: '输入股票代码,如 AAPL / NVDA / TSLA',
    research: '研究',
    researching: '研究中…',
    // 状态行
    starting: '正在建房间并发起研究…',
    start_failed: '发起失败:{err}',
    bad_ticker: '请输入 1–5 位英文股票代码(如 AAPL / MSFT),不要用中文公司名',
    signed_status: '✅ 已签字:{decision}({signer}) · 评级 {rating}',
    memo_ready: '备忘录已生成,待人工签字。',
    need_signer: '请先填写签字人姓名(人工签字门需真实署名)',
    submitting_sign: '提交签字 {decision}…',
    sign_failed: '签字失败:{err}',
    // 签字区
    signed_banner: '✅ 已签字 {decision} · 签字人 {signer}',
    signoff_gate: '人工签字门',
    signoff_hint: '备忘录须经真人审阅签字方可生效。',
    signer_placeholder: '签字人姓名(必填)',
    footer: 'Counterpoint · 多 agent 经 Band 对抗式投研 · 仅供教育研究,非投资建议',
    // ScoreBar
    sc_rating: '评级',
    sc_reliability: 'Risk 可靠性',
    sc_reliability_meta: '基于现有证据下结论的可靠性',
    sc_cites: '证据引用',
    sc_cites_meta: '备忘录引用的独立证据条数 [E*]',
    sc_progress: '流程进度',
    sc_progress_meta: '盲评→反驳→压测→综合→签字',
    // Timeline
    tl_title: '流水线进度',
    tl_done: '{done}/{total} 完成',
    st_done: '已完成',
    st_active: '进行中',
    st_pending: '待进行',
    // Memo
    memo_title: '研究备忘录',
    memo_rating: '评级 {rating}',
    memo_download: '下载 Markdown',
    memo_empty: '研究进行中…多空盲评 → 反驳 → 风险压测 → 综合,约需数分钟。',
    // RoomStream
    room_title: 'Band 房间直播',
    room_count: '{n} 条',
    room_empty: '尚无消息(研究发起后,agent 的发言会实时出现在这里)',
    msg_collapse: '收起 ▲',
    msg_expand: '展开全文 ▼',
    // 阶段标题(按 stage.key)
    'stage.evidence': '证据就绪',
    'stage.theses': '多空盲评',
    'stage.rebuttal': '交换反驳',
    'stage.risk': '风险压测',
    'stage.memo': '综合备忘录',
    'stage.signed': '人工签字',
    // 阶段负责方(按 stage.key)
    'agent.evidence': 'Data Steward',
    'agent.theses': 'Bull / Bear',
    'agent.rebuttal': 'Bull / Bear',
    'agent.risk': 'Risk Officer',
    'agent.memo': 'Chair',
    'agent.signed': '人类',
  },
  en: {
    doc_title: 'Counterpoint · Adversarial Research Desk',
    brand_sub: 'Adversarial Research Desk',
    ticker_company: 'Cross-model bull/bear · human sign-off',
    search_placeholder: 'Enter a ticker, e.g. AAPL / NVDA / TSLA',
    research: 'Research',
    researching: 'Researching…',
    starting: 'Creating room and starting research…',
    start_failed: 'Start failed: {err}',
    bad_ticker: 'Enter a 1–5 letter ticker (e.g. AAPL / MSFT), not a company name',
    signed_status: '✅ Signed: {decision} ({signer}) · rating {rating}',
    memo_ready: 'Memo generated; awaiting human sign-off.',
    need_signer: 'Please enter the signer name first (the sign-off gate needs a real name)',
    submitting_sign: 'Submitting {decision} sign-off…',
    sign_failed: 'Sign-off failed: {err}',
    signed_banner: '✅ Signed {decision} · signer {signer}',
    signoff_gate: 'Human Sign-off Gate',
    signoff_hint: 'The memo takes effect only after a real person reviews and signs.',
    signer_placeholder: 'Signer name (required)',
    footer: 'Counterpoint · Multi-agent adversarial research via Band · For education/research only, not investment advice',
    sc_rating: 'Rating',
    sc_reliability: 'Risk Reliability',
    sc_reliability_meta: 'Reliability of any conclusion from current evidence',
    sc_cites: 'Evidence Cited',
    sc_cites_meta: 'Distinct evidence items cited [E*]',
    sc_progress: 'Pipeline Progress',
    sc_progress_meta: 'Blind → Rebut → Stress-test → Synthesize → Sign',
    tl_title: 'Pipeline Progress',
    tl_done: '{done}/{total} done',
    st_done: 'Done',
    st_active: 'In progress',
    st_pending: 'Pending',
    memo_title: 'Research Memo',
    memo_rating: 'Rating {rating}',
    memo_download: 'Download .md',
    memo_empty: 'Research in progress… blind review → rebuttal → risk stress-test → synthesis, ~a few minutes.',
    room_title: 'Band Room Live',
    room_count: '{n} msgs',
    room_empty: 'No messages yet (agent messages appear here live once research starts).',
    msg_collapse: 'Collapse ▲',
    msg_expand: 'Expand ▼',
    'stage.evidence': 'Evidence Ready',
    'stage.theses': 'Blind Review',
    'stage.rebuttal': 'Exchange Rebuttals',
    'stage.risk': 'Risk Stress-Test',
    'stage.memo': 'Synthesized Memo',
    'stage.signed': 'Human Sign-off',
    'agent.evidence': 'Data Steward',
    'agent.theses': 'Bull / Bear',
    'agent.rebuttal': 'Bull / Bear',
    'agent.risk': 'Risk Officer',
    'agent.memo': 'Chair',
    'agent.signed': 'Human',
  },
}

function detectLang() {
  const q = new URLSearchParams(window.location.search).get('lang')
  if (q === 'zh' || q === 'en') {
    try { localStorage.setItem('cp_lang', q) } catch { /* ignore */ }
    return q
  }
  let saved = null
  try { saved = localStorage.getItem('cp_lang') } catch { /* ignore */ }
  return saved === 'zh' ? 'zh' : 'en'  // 默认英文
}

export let LANG = detectLang()

export function setLang(l) {
  LANG = l === 'en' ? 'en' : 'zh'
  try { localStorage.setItem('cp_lang', LANG) } catch { /* ignore */ }
}

// t('key', {var}):取当前语言文案,缺失回落 zh 再回落 key 本身;{var} 占位替换。
export function t(key, vars) {
  let s = (STR[LANG] && STR[LANG][key]) ?? STR.zh[key] ?? key
  if (vars) for (const k in vars) s = s.replaceAll(`{${k}}`, vars[k])
  return s
}
