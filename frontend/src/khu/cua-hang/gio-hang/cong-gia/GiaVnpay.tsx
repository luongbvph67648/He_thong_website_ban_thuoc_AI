import { Alert, Button, Card, Col, Input, QRCode, Radio, Row, Select, Space, Steps, Table, Typography } from 'antd'
import { useState } from 'react'
import { BangMoPhong, HetHan, ManKetQua, TomTatDon } from './dungChung'
import { useDemNguoc, useHoanTat, type GiaoDichGia } from './hooks'
import { LY_DO_THAT_BAI, OTP_THU_NGHIEM, SO_LAN_NHAP_TOI_DA, THE_THU_NGHIEM, kiemTraThe, type KetQuaThe } from './quyTac'

const NGAN_HANG = ['NCB', 'Vietcombank', 'BIDV', 'Techcombank', 'MB Bank', 'ACB']
type Buoc = 'chon' | 'the' | 'qr' | 'otp'

/** Giao diện mô phỏng cổng VNPay: chọn phương thức, nhập thẻ nội địa, OTP (hoặc quét QR), rồi báo IPN cho máy chủ. */
export default function GiaVnpay({ gd }: { gd: GiaoDichGia }) {
  const giayCon = useDemNguoc(gd.het_han_luc)
  const { dang, ketQua, hoanTat, veTrangKetQua } = useHoanTat(gd.giao_dich)
  const [buoc, datBuoc] = useState<Buoc>('chon')
  const [phuongThuc, datPhuongThuc] = useState<'the' | 'qr'>('the')
  const [nganHang, datNganHang] = useState('NCB')
  const [the, datThe] = useState({ soThe: '', ten: '', ngay: '' })
  const [loiThe, datLoiThe] = useState<string | null>(null)
  const [ketQuaThe, datKetQuaThe] = useState<Exclude<KetQuaThe, 'sai_thong_tin'>>('hop_le')
  const [otp, datOtp] = useState('')
  const [loiOtp, datLoiOtp] = useState<string | null>(null)
  const [lanSai, datLanSai] = useState(0)

  if (ketQua) return <ManKetQua ketQua={ketQua} veTrangKetQua={veTrangKetQua} />
  if (giayCon <= 0) return <HetHan veTrangKetQua={veTrangKetQua} />

  function tiepTucThe() {
    const kq = kiemTraThe(the)
    if (kq === 'sai_thong_tin') {
      datLoiThe('Thông tin thẻ không chính xác. Vui lòng kiểm tra lại số thẻ, tên chủ thẻ và ngày phát hành.')
      return
    }
    datLoiThe(null)
    datKetQuaThe(kq)
    datBuoc('otp')
  }

  function xacNhanOtp() {
    if (otp.trim() !== OTP_THU_NGHIEM) {
      const lan = lanSai + 1
      datLanSai(lan)
      if (lan >= SO_LAN_NHAP_TOI_DA) void hoanTat(false, 'Bạn đã nhập sai mã OTP quá số lần cho phép.')
      else datLoiOtp(`Mã OTP không đúng. Bạn còn ${SO_LAN_NHAP_TOI_DA - lan} lần thử.`)
      return
    }
    if (ketQuaThe === 'hop_le') void hoanTat(true)
    else void hoanTat(false, LY_DO_THAT_BAI[ketQuaThe])
  }

  const chi = buoc === 'chon' ? 0 : buoc === 'otp' ? 2 : 1
  return (
    <div style={{ maxWidth: 960, margin: '0 auto', display: 'grid', gap: 16 }}>
      <BangMoPhong ten="VNPay" />
      <Card styles={{ header: { background: '#005baa' } }} title={<span style={{ color: '#fff' }}>VNPAY · Cổng thanh toán (mô phỏng)</span>}>
        <Row gutter={24}>
          <Col xs={24} md={9}>
            <Card size="small" title="Thông tin đơn hàng"><TomTatDon gd={gd} giayCon={giayCon} /></Card>
          </Col>
          <Col xs={24} md={15}>
            <Steps size="small" current={chi} items={[{ title: 'Phương thức' }, { title: 'Thông tin' }, { title: 'Xác thực OTP' }]} style={{ marginBottom: 16 }} />
            {buoc === 'chon' && (
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Typography.Text strong>Chọn phương thức thanh toán</Typography.Text>
                <Radio.Group value={phuongThuc} onChange={(e) => datPhuongThuc(e.target.value)}>
                  <Space orientation="vertical">
                    <Radio value="the">Thẻ nội địa và tài khoản ngân hàng</Radio>
                    <Radio value="qr">Ứng dụng Mobile Banking quét mã QR</Radio>
                    <Radio value="quoc_te" disabled>Thẻ thanh toán quốc tế (chưa hỗ trợ trong bản mô phỏng)</Radio>
                  </Space>
                </Radio.Group>
                <Button type="primary" onClick={() => datBuoc(phuongThuc)}>Tiếp tục</Button>
              </Space>
            )}
            {buoc === 'the' && (
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Typography.Text strong>Thẻ nội địa</Typography.Text>
                <Select aria-label="Ngân hàng" value={nganHang} onChange={datNganHang} options={NGAN_HANG.map((n) => ({ value: n, label: n }))} />
                <Input aria-label="Số thẻ" placeholder="Số thẻ" inputMode="numeric" maxLength={25} value={the.soThe} onChange={(e) => datThe({ ...the, soThe: e.target.value })} />
                <Input aria-label="Tên chủ thẻ" placeholder="Tên chủ thẻ (không dấu)" maxLength={60} value={the.ten} onChange={(e) => datThe({ ...the, ten: e.target.value })} />
                <Input aria-label="Ngày phát hành" placeholder="Ngày phát hành (MM/YY)" maxLength={5} value={the.ngay} onChange={(e) => datThe({ ...the, ngay: e.target.value })} />
                {loiThe && <Alert type="error" showIcon message={loiThe} />}
                <Space>
                  <Button onClick={() => datBuoc('chon')}>Quay lại</Button>
                  <Button type="primary" disabled={!the.soThe || !the.ten || !the.ngay} onClick={tiepTucThe}>Tiếp tục</Button>
                </Space>
                <Alert
                  type="info"
                  message="Thẻ thử nghiệm (môi trường mô phỏng)"
                  description={
                    <Table
                      size="small"
                      pagination={false}
                      rowKey="soThe"
                      dataSource={THE_THU_NGHIEM}
                      columns={[
                        { title: 'Số thẻ', dataIndex: 'soThe' },
                        { title: 'Tên', dataIndex: 'ten' },
                        { title: 'Ngày', dataIndex: 'ngay' },
                        { title: 'Kết quả', dataIndex: 'mo_ta' },
                      ]}
                    />
                  }
                />
              </Space>
            )}
            {buoc === 'qr' && (
              <Space orientation="vertical" align="center" style={{ width: '100%' }}>
                <Typography.Text strong>Quét mã QR bằng ứng dụng Mobile Banking</Typography.Text>
                <QRCode value={`vnpayqr://mo-phong?giao_dich=${encodeURIComponent(gd.giao_dich)}&so_tien=${gd.so_tien}`} size={180} />
                <Typography.Text type="secondary">Bản mô phỏng: bấm nút dưới để giả lập khách đã quét và xác nhận trên điện thoại.</Typography.Text>
                <Space>
                  <Button onClick={() => datBuoc('chon')}>Quay lại</Button>
                  <Button type="primary" loading={dang} onClick={() => void hoanTat(true)}>Mô phỏng: đã quét và thanh toán</Button>
                </Space>
              </Space>
            )}
            {buoc === 'otp' && (
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Typography.Text strong>Xác thực giao dịch</Typography.Text>
                <Typography.Text>Mã OTP đã được gửi tới số điện thoại đăng ký với ngân hàng {nganHang}.</Typography.Text>
                <Input aria-label="Mã OTP" placeholder="Nhập mã OTP" inputMode="numeric" maxLength={6} value={otp} onChange={(e) => { datOtp(e.target.value); datLoiOtp(null) }} />
                {loiOtp && <Alert type="error" showIcon message={loiOtp} />}
                <Alert type="info" message={`Mã OTP thử nghiệm: ${OTP_THU_NGHIEM}`} />
                <Space>
                  <Button onClick={() => datBuoc('the')}>Quay lại</Button>
                  <Button type="primary" loading={dang} disabled={otp.length !== 6} onClick={xacNhanOtp}>Xác nhận</Button>
                </Space>
              </Space>
            )}
            <div style={{ marginTop: 16 }}>
              <Button danger type="link" disabled={dang} onClick={() => void hoanTat(false, 'Bạn đã hủy giao dịch.')}>Hủy giao dịch</Button>
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  )
}
