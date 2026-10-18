import { Alert, Button, Card, Input, QRCode, Space, Typography } from 'antd'
import { useState } from 'react'
import { dinhDangTien } from '../../../../lib/dinhDang'
import { BangMoPhong, HetHan, ManKetQua } from './dungChung'
import { useDemNguoc, useHoanTat, type GiaoDichGia } from './hooks'
import { PIN_THU_NGHIEM, SO_LAN_NHAP_TOI_DA, dongHoDemNguoc } from './quyTac'

/** Giao diện mô phỏng cổng MoMo: hiện mã QR, khách "quét" bằng khung điện thoại giả rồi nhập mã PIN. */
export default function GiaMomo({ gd }: { gd: GiaoDichGia }) {
  const giayCon = useDemNguoc(gd.het_han_luc)
  const { dang, ketQua, hoanTat, veTrangKetQua } = useHoanTat(gd.giao_dich)
  const [dienThoai, datDienThoai] = useState(false)
  const [pin, datPin] = useState('')
  const [loiPin, datLoiPin] = useState<string | null>(null)
  const [lanSai, datLanSai] = useState(0)

  if (ketQua) return <ManKetQua ketQua={ketQua} veTrangKetQua={veTrangKetQua} />
  if (giayCon <= 0) return <HetHan veTrangKetQua={veTrangKetQua} />

  function xacNhan() {
    if (pin !== PIN_THU_NGHIEM) {
      const lan = lanSai + 1
      datLanSai(lan)
      if (lan >= SO_LAN_NHAP_TOI_DA) void hoanTat(false, 'Bạn đã nhập sai mã PIN quá số lần cho phép.')
      else datLoiPin(`Mã PIN không đúng. Bạn còn ${SO_LAN_NHAP_TOI_DA - lan} lần thử.`)
      return
    }
    void hoanTat(true)
  }

  return (
    <div style={{ maxWidth: 520, margin: '0 auto', display: 'grid', gap: 16 }}>
      <BangMoPhong ten="MoMo" />
      <Card styles={{ header: { background: '#a50064' } }} title={<span style={{ color: '#fff' }}>MoMo · Thanh toán bằng mã QR (mô phỏng)</span>}>
        <Space orientation="vertical" align="center" style={{ width: '100%' }}>
          {!dienThoai ? (
            <>
              <Typography.Text>Đơn hàng <b>{gd.ma_don}</b> · Nhà thuốc AI</Typography.Text>
              <Typography.Title level={3} style={{ margin: 0, color: '#a50064' }}>{dinhDangTien(gd.so_tien)}</Typography.Title>
              <QRCode value={`momo://mo-phong?giao_dich=${encodeURIComponent(gd.giao_dich)}&so_tien=${gd.so_tien}`} size={200} color="#a50064" />
              <Typography.Text>Mã QR hết hạn sau <b>{dongHoDemNguoc(giayCon)}</b></Typography.Text>
              <Typography.Text type="secondary">1. Mở ứng dụng MoMo, chọn Quét mã. 2. Quét mã QR này. 3. Xác nhận thanh toán.</Typography.Text>
              <Button type="primary" style={{ background: '#a50064' }} onClick={() => datDienThoai(true)}>Mô phỏng: mở ứng dụng MoMo và quét mã</Button>
              <Button danger type="link" disabled={dang} onClick={() => void hoanTat(false, 'Bạn đã hủy giao dịch.')}>Hủy giao dịch</Button>
            </>
          ) : (
            <Card size="small" style={{ width: 300, borderRadius: 24, borderColor: '#a50064' }} title="Ví MoMo (điện thoại giả lập)">
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Typography.Text>Thanh toán cho <b>Nhà thuốc AI</b></Typography.Text>
                <Typography.Title level={4} style={{ margin: 0 }}>{dinhDangTien(gd.so_tien)}</Typography.Title>
                <Input.Password aria-label="Mã PIN" placeholder="Nhập mã PIN 6 số" inputMode="numeric" maxLength={6} value={pin} onChange={(e) => { datPin(e.target.value); datLoiPin(null) }} />
                {loiPin && <Alert type="error" showIcon message={loiPin} />}
                <Alert type="info" message={`Mã PIN thử nghiệm: ${PIN_THU_NGHIEM}`} />
                <Space>
                  <Button danger disabled={dang} onClick={() => void hoanTat(false, 'Bạn đã từ chối thanh toán trên ứng dụng MoMo.')}>Từ chối</Button>
                  <Button type="primary" style={{ background: '#a50064' }} loading={dang} disabled={pin.length !== 6} onClick={xacNhan}>Xác nhận</Button>
                </Space>
              </Space>
            </Card>
          )}
        </Space>
      </Card>
    </div>
  )
}
