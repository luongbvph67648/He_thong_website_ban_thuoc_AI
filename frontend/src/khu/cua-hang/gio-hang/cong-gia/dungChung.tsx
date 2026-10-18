import { Alert, Button, Result, Typography } from 'antd'
import type { ReactNode } from 'react'
import { dinhDangTien } from '../../../../lib/dinhDang'
import type { GiaoDichGia, KetQua } from './hooks'
import { dongHoDemNguoc } from './quyTac'

export function BangMoPhong({ ten }: { ten: string }) {
  return (
    <Alert
      type="warning"
      showIcon
      message={`Môi trường mô phỏng: giao diện này giả lập cổng ${ten} để demo. Không có tiền thật và không kết nối ngân hàng.`}
    />
  )
}

export function TomTatDon({ gd, giayCon }: { gd: GiaoDichGia; giayCon: number }) {
  return (
    <div style={{ display: 'grid', gap: 8 }}>
      <Row nhan="Nhà cung cấp" gt="Nhà thuốc AI" />
      <Row nhan="Mã đơn hàng" gt={gd.ma_don} />
      <Row nhan="Mã giao dịch" gt={gd.giao_dich} />
      <Row nhan="Số tiền thanh toán" gt={<b style={{ fontSize: 22 }}>{dinhDangTien(gd.so_tien)}</b>} />
      <Row nhan="Giao dịch hết hạn sau" gt={<b style={{ color: giayCon < 60 ? '#cf1322' : undefined }}>{dongHoDemNguoc(giayCon)}</b>} />
    </div>
  )
}

function Row({ nhan, gt }: { nhan: string; gt: ReactNode }) {
  return (
    <div>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>{nhan}</Typography.Text>
      <div>{gt}</div>
    </div>
  )
}

export function ManKetQua({ ketQua, veTrangKetQua }: { ketQua: KetQua; veTrangKetQua: () => void }) {
  return (
    <Result
      status={ketQua.thanhCong ? 'success' : 'error'}
      title={ketQua.thanhCong ? 'Giao dịch thành công' : 'Giao dịch không thành công'}
      subTitle={
        (ketQua.thanhCong ? 'Cảm ơn bạn đã thanh toán.' : (ketQua.lyDo ?? 'Giao dịch đã bị hủy.')) + ' Đang quay lại cửa hàng…'
      }
      extra={<Button type="primary" onClick={veTrangKetQua}>Quay lại cửa hàng ngay</Button>}
    />
  )
}

export function HetHan({ veTrangKetQua }: { veTrangKetQua: () => void }) {
  return (
    <Result
      status="warning"
      title="Giao dịch đã hết hạn"
      subTitle="Đơn hàng sẽ tự hủy nếu quá hạn thanh toán. Bạn có thể quay lại cửa hàng để thanh toán lại."
      extra={<Button type="primary" onClick={veTrangKetQua}>Quay lại cửa hàng</Button>}
    />
  )
}
