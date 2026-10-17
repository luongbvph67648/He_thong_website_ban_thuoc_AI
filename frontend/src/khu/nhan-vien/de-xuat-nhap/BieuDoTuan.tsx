import type { components } from '../../../api/schema'

type Diem = components['schemas']['DiemTuan']

const R = 640
const C = 220
const LE = { t: 12, b: 28, l: 36, p: 8 }

/** Biểu đồ cột theo tuần: lịch sử xuất (xanh đậm) và dự báo (xanh nhạt, viền nét đứt). SVG thuần, không phụ thuộc thư viện. */
export function BieuDoTuan({ lichSu, duBao, donVi }: { lichSu: readonly Diem[]; duBao: readonly Diem[]; donVi: string }) {
  const tat = [...lichSu.map((d) => ({ ...d, du_bao: false })), ...duBao.map((d) => ({ ...d, du_bao: true }))]
  const max = Math.max(1, ...tat.map((d) => d.so_luong))
  const rong = (R - LE.l - LE.p) / tat.length
  const cao = C - LE.t - LE.b
  return (
    <svg role="img" aria-label={`Biểu đồ lịch sử xuất và dự báo theo tuần (${donVi})`} viewBox={`0 0 ${R} ${C}`} style={{ width: '100%', maxWidth: R }}>
      <line x1={LE.l} y1={C - LE.b} x2={R - LE.p} y2={C - LE.b} stroke="#d9d9d9" />
      <text x={LE.l - 4} y={LE.t + 8} fontSize="10" textAnchor="end" fill="#8c8c8c">{max}</text>
      <text x={LE.l - 4} y={C - LE.b} fontSize="10" textAnchor="end" fill="#8c8c8c">0</text>
      {tat.map((d, i) => {
        const h = (d.so_luong / max) * cao
        return (
          <rect key={`${d.tuan_bat_dau}-${d.du_bao}`} x={LE.l + i * rong + 1} y={C - LE.b - h} width={Math.max(1, rong - 2)} height={h}
            fill={d.du_bao ? '#91caff' : '#1677ff'} stroke={d.du_bao ? '#1677ff' : 'none'} strokeDasharray={d.du_bao ? '3 2' : undefined}>
            <title>{`Tuần ${d.tuan_bat_dau}: ${d.so_luong} ${donVi}${d.du_bao ? ' (dự báo)' : ''}`}</title>
          </rect>
        )
      })}
      <text x={LE.l} y={C - 10} fontSize="10" fill="#8c8c8c">{lichSu[0]?.tuan_bat_dau}</text>
      <text x={R - LE.p} y={C - 10} fontSize="10" textAnchor="end" fill="#8c8c8c">{duBao[duBao.length - 1]?.tuan_bat_dau}</text>
    </svg>
  )
}
