import type { components } from '../../../api/schema'
import { dinhDangTien } from '../../../lib/dinhDang'

type Diem = components['schemas']['DoanhThuNgay']
const R = 720
const C = 200
const LE = { t: 10, b: 24, l: 8, p: 8 }

/** Cột doanh thu theo ngày (SVG thuần). Mỗi cột có `<title>` để rê chuột xem ngày, số đơn, doanh thu. */
export function BieuDoCotNgay({ diem }: { diem: readonly Diem[] }) {
  if (diem.length === 0) return null
  const max = Math.max(1, ...diem.map((d) => Number(d.doanh_thu)))
  const rong = (R - LE.l - LE.p) / diem.length
  const cao = C - LE.t - LE.b
  return (
    <svg role="img" aria-label="Biểu đồ doanh thu theo ngày" viewBox={`0 0 ${R} ${C}`} style={{ width: '100%', maxWidth: R }}>
      <line x1={LE.l} y1={C - LE.b} x2={R - LE.p} y2={C - LE.b} stroke="#d9d9d9" />
      {diem.map((d, i) => {
        const h = (Number(d.doanh_thu) / max) * cao
        return (
          <rect key={d.ngay} x={LE.l + i * rong + 0.5} y={C - LE.b - h} width={Math.max(1, rong - 1)} height={h} fill="#1677ff">
            <title>{`${d.ngay}: ${d.so_don} đơn, ${dinhDangTien(d.doanh_thu)}`}</title>
          </rect>
        )
      })}
      <text x={LE.l} y={C - 8} fontSize="10" fill="#8c8c8c">{diem[0]!.ngay}</text>
      <text x={R - LE.p} y={C - 8} fontSize="10" textAnchor="end" fill="#8c8c8c">{diem[diem.length - 1]!.ngay}</text>
    </svg>
  )
}
