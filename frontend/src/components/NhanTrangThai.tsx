import { Tag } from 'antd'
import { nhanTrangThai, type LoaiTrangThai } from '../lib/trangThai'

/** Nhãn màu của một trạng thái (đơn hàng, thanh toán, kênh bán), dùng bảng chung ở `lib/trangThai.ts`. */
export function NhanTrangThai({ loai, giaTri }: { loai: LoaiTrangThai; giaTri: string | null | undefined }) {
  const { nhan, mau } = nhanTrangThai(loai, giaTri)
  return <Tag color={mau}>{nhan}</Tag>
}
