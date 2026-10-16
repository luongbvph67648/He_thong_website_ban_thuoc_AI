import { Alert, App, Button, Input, Space, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChoDoiLai } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangTien } from '../../../lib/dinhDang'

export type KetQuaMa = components['schemas']['KetQuaKiemTraMa']

/**
 * KTV04: ô nhập mã giảm giá. Chỉ XEM TRƯỚC số tiền giảm theo giỏ hiện tại (không dùng lượt mã); lượt chỉ bị tính khi
 * đặt hàng (T4.4). Thuốc kê đơn không bao giờ được giảm nên phần "được giảm" có thể nhỏ hơn tạm tính.
 */
export function OMaGiamGia({ khiDoi }: { khiDoi?: (kq: KetQuaMa | null) => void }) {
  const { message } = App.useApp()
  const [ma, setMa] = useState('')
  const [dangKiemTra, setDangKiemTra] = useState(false)
  const [kq, setKq] = useState<KetQuaMa | null>(null)

  async function kiemTra() {
    if (!ma.trim()) return
    setDangKiemTra(true)
    const r = await goi(() => api.POST('/api/v1/toi/ma-giam-gia/kiem-tra', { body: { ma: ma.trim() } }))
    setDangKiemTra(false)
    if (!r.ok) {
      void message.error(r.loi ? thongDiepChoDoiLai(r.loi) : 'Không kiểm tra được mã, vui lòng thử lại')
      return
    }
    setKq(r.data)
    khiDoi?.(r.data.hop_le ? r.data : null)
  }
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      <Space.Compact style={{ width: '100%', maxWidth: 360 }}>
        <Input
          aria-label="Mã giảm giá"
          placeholder="Nhập mã giảm giá"
          maxLength={30}
          value={ma}
          onChange={(e) => { setMa(e.target.value); setKq(null); khiDoi?.(null) }}
          onPressEnter={() => void kiemTra()}
        />
        <Button loading={dangKiemTra} disabled={!ma.trim()} onClick={() => void kiemTra()}>Áp dụng</Button>
      </Space.Compact>
      {kq?.hop_le && (
        <Alert
          type="success"
          showIcon
          message={`${kq.khuyen_mai?.ten ?? 'Mã giảm giá'}: giảm ${dinhDangTien(kq.giam)}`}
          description={<Typography.Text type="secondary">Tính trên {dinhDangTien(kq.co_so_giam)} sản phẩm được giảm. Thuốc kê đơn không được giảm giá.</Typography.Text>}
        />
      )}
      {kq && !kq.hop_le && <Alert type="warning" showIcon message={kq.ly_do ?? 'Mã không áp dụng được'} />}
    </Space>
  )
}
