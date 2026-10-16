import { Alert, App, Button, Card, Empty, Input, Radio, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { dinhDangTien } from '../../../lib/dinhDang'
import { nhanTrangThai } from '../../../lib/trangThai'
import type { DonQuay } from './donHo'

type CachThu = 'tien_mat' | 'chuyen_khoan'

/** DS15: khách đến quầy đọc mã đơn hoặc SĐT; dược sĩ đối chiếu, thu tiền nếu chưa trả rồi bàn giao hàng. */
export default function TrangGiaoTaiQuay() {
  const { message } = App.useApp()
  const [q, setQ] = useState('')
  const [ds, setDs] = useState<DonQuay[] | null>(null)
  const [dangTim, setDangTim] = useState(false)
  const [cachThu, setCachThu] = useState<Record<number, CachThu>>({})
  const [dangGiao, setDangGiao] = useState<number | null>(null)

  async function tim() {
    setDangTim(true)
    const r = await goi(() => api.GET('/api/v1/noi-bo/giao-tai-quay', { params: { query: { q: q.trim() } } }))
    setDangTim(false)
    if (r.ok) setDs(r.data)
    else void message.error(thongDiepChung(r.loi))
  }

  async function giao(d: DonQuay) {
    setDangGiao(d.id)
    const r = await goi(() => api.POST('/api/v1/noi-bo/giao-tai-quay/{don_id}', { params: { path: { don_id: d.id } }, body: { phuong_thuc_thu: d.trang_thai_tt === 'chua_thanh_toan' ? cachThu[d.id] : null } }))
    setDangGiao(null)
    if (!r.ok) return void message.error(thongDiepChung(r.loi))
    void message.success(`Đã giao đơn ${d.ma_don}`)
    setDs((cu) => (cu ?? []).filter((x) => x.id !== d.id))
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%', maxWidth: 880 }}>
      <Typography.Title level={3} style={{ margin: 0 }}>Giao đơn nhận tại nhà thuốc</Typography.Title>
      <Input.Search placeholder="Mã đơn hoặc SĐT của khách" enterButton="Tìm đơn" loading={dangTim} value={q} onChange={(e) => setQ(e.target.value)} onSearch={() => void tim()} style={{ maxWidth: 420 }} />
      {ds !== null && ds.length === 0 && <Empty description="Không có đơn nhận tại nhà thuốc đang chờ lấy hàng khớp tìm kiếm" />}
      {(ds ?? []).map((d) => {
        const chuaTra = d.trang_thai_tt === 'chua_thanh_toan'
        const tt = nhanTrangThai('thanh_toan', d.trang_thai_tt)
        return (
          <Card key={d.id} size="small" title={`Đơn ${d.ma_don}`} extra={<Tag color={tt.mau}>{tt.nhan}</Tag>}>
            <Typography.Paragraph>Người nhận: {[d.ten_nguoi_nhan, d.sdt_nguoi_nhan].filter(Boolean).join(' · ') || '—'}</Typography.Paragraph>
            <Table size="small" pagination={false} rowKey={(x) => `${x.ten_san_pham}-${x.ten_don_vi}`} dataSource={d.dong} columns={[{ title: 'Sản phẩm', key: 'ten', render: (_, x) => `${x.ten_san_pham} (${x.ten_don_vi})` }, { title: 'SL', dataIndex: 'so_luong', key: 'sl', align: 'right' }]} />
            <Typography.Paragraph style={{ marginTop: 8 }}>Tổng tiền: <b>{dinhDangTien(d.tong_tien)}</b></Typography.Paragraph>
            {chuaTra && (
              <>
                <Alert type="warning" showIcon message={`Thu ${dinhDangTien(d.tong_tien)} của khách trước khi bàn giao hàng`} style={{ marginBottom: 8 }} />
                <Radio.Group value={cachThu[d.id]} onChange={(e) => setCachThu((c) => ({ ...c, [d.id]: e.target.value as CachThu }))} options={[{ value: 'tien_mat', label: 'Tiền mặt' }, { value: 'chuyen_khoan', label: 'Chuyển khoản' }]} />
              </>
            )}
            <div style={{ marginTop: 12 }}>
              <Button type="primary" loading={dangGiao === d.id} disabled={chuaTra && !cachThu[d.id]} onClick={() => void giao(d)}>
                {chuaTra ? 'Đã thu tiền, giao hàng' : 'Giao hàng'}
              </Button>
            </div>
          </Card>
        )
      })}
    </Space>
  )
}
