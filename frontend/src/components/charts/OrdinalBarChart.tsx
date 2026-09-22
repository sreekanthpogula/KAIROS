import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { cssVar } from '../../lib/colors'

interface Datum {
  label: string
  value: number
  color?: string
}

export function OrdinalBarChart({ data, height = 200 }: { data: Datum[]; height?: number }) {
  const grid = cssVar('--gridline')
  const muted = cssVar('--text-muted')
  const surface2 = cssVar('--surface-2')
  const border = cssVar('--border')
  const text = cssVar('--text-primary')
  const defaultColor = cssVar('--series-1')

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <CartesianGrid vertical={false} stroke={grid} strokeDasharray="3 3" />
        <XAxis dataKey="label" tick={{ fill: muted, fontSize: 11 }} axisLine={{ stroke: grid }} tickLine={false} />
        <YAxis tick={{ fill: muted, fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} width={32} />
        <Tooltip
          cursor={{ fill: grid, opacity: 0.4 }}
          contentStyle={{ backgroundColor: surface2, border: `1px solid ${border}`, borderRadius: 8, fontSize: 12, color: text }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={48}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.color ?? defaultColor} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
