import type { components } from '../../../api/schema'
import { dinhDangTien } from '../../../lib/dinhDang'
import { tienNgan } from './tongQuan'

type Diem = components['schemas']['DoanhThuNgay']
const R = 760
const C = 220
const LE = { t: 12, b: 24, l: 64, p: 8 }
const SO_VACH = 4

/** `2026-10-16` -> `16/10`. */
const ngayNgan = (ngay: string) => `${ngay.slice(8, 10)}/${ngay.slice(5, 7)}`

/**
 * Cột doanh thu theo ngày (SVG thuần) có vạch chia, nhãn trục tiền và nhãn ngày thưa. Cột cao nhất tô đậm.
 * Mỗi cột có `<title>` để rê chuột xem ngày, số đơn, doanh thu.
 */
export function BieuDoCotNgay({ diem }: { diem: readonly Diem[] }) {
  if (diem.length === 0) return null
  const giaTri = diem.map((d) => Number(d.doanh_thu))
  const lonNhat = Math.max(...giaTri)
  const max = Math.max(1, lonNhat)
  const rong = (R - LE.l - LE.p) / diem.length
  const cao = C - LE.t - LE.b
  const buocNhan = Math.max(1, Math.ceil(diem.length / 10))
  return (
    <svg role="img" aria-label="Biểu đồ doanh thu theo ngày" viewBox={`0 0 ${R} ${C}`} style={{ width: '100%' }}>
      {Array.from({ length: SO_VACH + 1 }, (_, i) => {
        const y = C - LE.b - (cao * i) / SO_VACH
        return (
          <g key={i}>
            <line x1={LE.l} y1={y} x2={R - LE.p} y2={y} stroke={i === 0 ? '#d9d9d9' : '#f0f0f0'} />
            <text x={LE.l - 6} y={y + 3} fontSize="10" textAnchor="end" fill="#8c8c8c">{tienNgan((max * i) / SO_VACH)}</text>
          </g>
        )
      })}
      {diem.map((d, i) => {
        const h = (giaTri[i]! / max) * cao
        const dinh = lonNhat > 0 && giaTri[i] === lonNhat
        return (
          <rect key={d.ngay} x={LE.l + i * rong + rong * 0.15} y={C - LE.b - h} width={Math.max(1, rong * 0.7)} height={h} rx={Math.min(3, rong * 0.2)} fill={dinh ? '#0958d9' : '#69b1ff'}>
            <title>{`${ngayNgan(d.ngay)}: ${d.so_don} đơn, ${dinhDangTien(d.doanh_thu)}`}</title>
          </rect>
        )
      })}
      {diem.map((d, i) =>
        (i % buocNhan === 0 && diem.length - 1 - i >= buocNhan / 2) || i === diem.length - 1 ? (
          <text key={d.ngay} x={LE.l + i * rong + rong / 2} y={C - 8} fontSize="10" textAnchor="middle" fill="#8c8c8c">{ngayNgan(d.ngay)}</text>
        ) : null,
      )}
    </svg>
  )
}
