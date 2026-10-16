import { Alert, Tag, Typography } from 'antd'
import type { ReactNode } from 'react'
import type { components } from '../api/schema'

type TinNhan = components['schemas']['TinNhanAnDanh']

const NHAN_VAI_TRO: Record<TinNhan['vai_tro'], string> = { khach: 'Khách', ai: 'Trợ lý AI', duoc_si: 'Dược sĩ', he_thong: 'Hệ thống' }
const NHAN_KET_QUA_DANH_GIA: Record<string, [string, string]> = {
  huu_ich: ['Khách: hữu ích', 'green'],
  khong_huu_ich: ['Khách: không hữu ích', 'red'],
  dung: ['Dược sĩ: đúng', 'green'],
  sai: ['Dược sĩ: sai', 'red'],
}

/** Nội dung hội thoại đã ẩn danh (DS12, AD11). `hanhDong` vẽ thêm điều khiển dưới từng tin (ví dụ nút đánh giá). */
export function HoiThoaiAnDanh({ tin, hanhDong }: { tin: readonly TinNhan[]; hanhDong?: (t: TinNhan) => ReactNode }) {
  return (
    <div role="log" aria-label="Nội dung hội thoại đã ẩn danh" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <Alert type="info" showIcon title="Đã che số điện thoại, email và tên. Không hiển thị thông tin định danh khách." />
      {tin.map((t) => (
        <div key={t.id} style={{ borderLeft: `3px solid ${t.vai_tro === 'ai' ? '#1677ff' : t.vai_tro === 'khach' ? '#52c41a' : '#d9d9d9'}`, paddingLeft: 8 }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {NHAN_VAI_TRO[t.vai_tro]}
            {t.y_dinh ? ` · ${t.y_dinh}` : ''}
          </Typography.Text>
          {t.dau_hieu_nguy_hiem && <Tag color="red" style={{ marginLeft: 8 }}>Dấu hiệu nguy hiểm</Tag>}
          <div style={{ whiteSpace: 'pre-wrap' }}>{t.noi_dung}</div>
          {t.danh_gia.map((d, i) => {
            const [nhan, mau] = NHAN_KET_QUA_DANH_GIA[d.ket_qua] ?? [d.ket_qua, 'default']
            return (
              <div key={i}>
                <Tag color={mau}>{nhan}</Tag>
                {d.ghi_chu && <Typography.Text type="secondary">Nội dung đúng: {d.ghi_chu}</Typography.Text>}
              </div>
            )
          })}
          {hanhDong?.(t)}
        </div>
      ))}
    </div>
  )
}
