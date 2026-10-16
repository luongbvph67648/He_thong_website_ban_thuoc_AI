import { Timeline, Typography } from 'antd'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { nhanTrangThai } from '../../../lib/trangThai'

interface Moc {
  den_trang_thai: string
  thoi_diem: string
  ghi_chu?: string | null
  nguoi_thuc_hien?: string | null
}

/** Dòng thời gian trạng thái đơn, dùng chung cho khách (không có người thực hiện) và nội bộ. */
export default function LichSuTrangThai({ moc }: { moc: readonly Moc[] }) {
  return (
    <Timeline
      items={moc.map((m, i) => ({
        key: i,
        children: (
          <>
            <Typography.Text strong>{nhanTrangThai('don_hang', m.den_trang_thai).nhan}</Typography.Text>
            <br />
            <Typography.Text type="secondary">
              {dinhDangNgay(m.thoi_diem, 'ngayGio')}
              {m.nguoi_thuc_hien ? ` · ${m.nguoi_thuc_hien}` : ''}
            </Typography.Text>
            {m.ghi_chu && <div>{m.ghi_chu}</div>}
          </>
        ),
      }))}
    />
  )
}
