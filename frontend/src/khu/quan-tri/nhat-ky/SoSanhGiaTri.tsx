import { Typography } from 'antd'
import type { components } from '../../../api/schema'
import { BANG_SUC_KHOE, soSanhGiaTri } from '../../../lib/nhatKy'

type DongNhatKy = components['schemas']['NhatKyDoc']

function hienGiaTri(v: unknown): string {
  if (v === undefined) return '—'
  if (typeof v === 'string') return v
  if (Array.isArray(v) && v.every((x) => typeof x === 'string' || typeof x === 'number')) return v.length ? v.join(', ') : '(rỗng)'
  return JSON.stringify(v)
}

/** Giá trị cũ và mới của một dòng nhật ký, từng trường một; trường có đổi được tô nổi bật. */
export function SoSanhGiaTri({ dong }: { dong: DongNhatKy }) {
  const khung = { 'data-testid': `so-sanh-${dong.id}` }
  if (BANG_SUC_KHOE.has(dong.bang)) {
    return (
      <div {...khung}>
        <Typography.Text type="secondary">Giá trị không được lưu (dữ liệu sức khỏe). Nhật ký chỉ ghi ai đã thao tác trên hồ sơ nào và khi nào.</Typography.Text>
      </div>
    )
  }
  const dongSoSanh = soSanhGiaTri(dong.gia_tri_cu, dong.gia_tri_moi)
  if (dongSoSanh.length === 0) {
    return (
      <div {...khung}>
        <Typography.Text type="secondary">Dòng này không ghi giá trị cũ hay mới</Typography.Text>
      </div>
    )
  }
  return (
    <div {...khung}>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr style={{ textAlign: 'left' }}>
            <th style={{ padding: '4px 8px', width: '25%' }}>Trường</th>
            <th style={{ padding: '4px 8px', width: '37%' }}>Giá trị cũ</th>
            <th style={{ padding: '4px 8px' }}>Giá trị mới</th>
          </tr>
        </thead>
        <tbody>
          {dongSoSanh.map((d) => (
            <tr key={d.truong ?? '_'} data-doi={String(d.doi)} style={d.doi ? { background: '#fffbe6' } : undefined}>
              <td style={{ padding: '4px 8px' }}>{d.truong ? <code>{d.truong}</code> : 'Giá trị'}</td>
              <td style={{ padding: '4px 8px', wordBreak: 'break-word' }}>{hienGiaTri(d.cu)}</td>
              <td style={{ padding: '4px 8px', wordBreak: 'break-word', fontWeight: d.doi ? 600 : undefined }}>{hienGiaTri(d.moi)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
