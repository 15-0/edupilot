import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

const AXIS = { stroke: 'transparent', tick: { fill: '#7180a8', fontSize: 12 }, tickLine: false }
const GRID = <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />

function TooltipBox({ active, payload, label, unit, labelKey }) {
  if (!active || !payload?.length) return null
  const p = payload[0]
  return (
    <div className="rounded-lg border border-white/10 bg-[#0e1740] px-3 py-2 text-xs shadow-xl">
      <p className="font-medium text-white">{labelKey ? p.payload[labelKey] : label}</p>
      <p className="mt-0.5 text-ink-2">{p.value}{unit}</p>
    </div>
  )
}

/** Single-series bar chart. */
export function BarSeries({ data, x, y, color = '#22d3ee', unit = '', height = 240, domain }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        {GRID}
        <XAxis dataKey={x} {...AXIS} interval="preserveStartEnd" />
        <YAxis {...AXIS} domain={domain} />
        <Tooltip cursor={{ fill: 'rgba(255,255,255,0.04)' }} content={<TooltipBox unit={unit} />} />
        <Bar dataKey={y} fill={color} radius={[4, 4, 0, 0]} maxBarSize={36} />
      </BarChart>
    </ResponsiveContainer>
  )
}

/** Single-series line chart (percentages by default). */
export function LineSeries({ data, x, y, color = '#a78bfa', unit = '%', height = 240, labelKey, refY }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
        {GRID}
        <XAxis dataKey={x} {...AXIS} interval="preserveStartEnd" />
        <YAxis {...AXIS} domain={[0, 100]} />
        {refY != null && <ReferenceLine y={refY} stroke="rgba(255,255,255,0.25)" strokeDasharray="4 4" />}
        <Tooltip cursor={{ stroke: 'rgba(255,255,255,0.2)' }} content={<TooltipBox unit={unit} labelKey={labelKey} />} />
        <Line type="monotone" dataKey={y} stroke={color} strokeWidth={2} dot={{ r: 4, fill: color, stroke: '#0b1437', strokeWidth: 2 }} activeDot={{ r: 6 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}
