// 五档评级 → 颜色:Buy/Overweight 偏多(绿)、Hold 中性(黄)、Underweight/Sell 偏空(红)
const LEVEL = { Buy: 'low', Overweight: 'low', Hold: 'medium', Underweight: 'high', Sell: 'high' }

export default function RiskPill({ rating }) {
  if (!rating) return null
  const level = LEVEL[rating] || 'medium'
  return (
    <span className={`pill risk-${level}`}>
      <span className="pill-dot" />
      {rating}
    </span>
  )
}
