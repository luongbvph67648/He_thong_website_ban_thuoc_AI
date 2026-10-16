import { DeleteOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Empty, InputNumber, Select, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import { dinhDangTien } from '../../../lib/dinhDang'
import { lienKetAnToan } from '../../../lib/lienKet'
import { type DongGio, useGioHang } from './gioHang'
import { OMaGiamGia, type KetQuaMa } from './OMaGiamGia'

const NHAN_LY_DO: Record<string, string> = {
  thuoc_ke_don: 'Thuốc kê đơn: không mua online',
  khong_hien_thi: 'Sản phẩm ngừng bán',
  don_vi_khong_hop_le: 'Đơn vị tính không còn bán online',
  vuot_toi_da: 'Vượt số lượng tối đa mỗi đơn',
}

/** "Thường được mua cùng" (luật mua kèm AI08); không có luật thì ẩn cả mục. Không bao giờ có thuốc kê đơn. */
function MuaCung({ ids, them }: { ids: number[]; them: (spId: number, dvId: number) => Promise<void> }) {
  const q = useQuery({
    queryKey: ['gio-hang', 'mua-kem', ids],
    enabled: ids.length > 0,
    queryFn: async () => (await api.GET('/api/v1/gio-hang/mua-kem', { params: { query: { san_pham_id: ids } } })).data ?? [],
  })
  if (!q.data || q.data.length === 0) return null
  return (
    <section aria-label="Thường được mua cùng">
      <Typography.Title level={4}>Thường được mua cùng</Typography.Title>
      <Space wrap size="middle" align="start">
        {q.data.map((s) => (
          <div key={s.id} style={{ width: 180, border: '1px solid #f0f0f0', borderRadius: 8, padding: 12 }}>
            {lienKetAnToan(s.anh_chinh_url) && <img src={lienKetAnToan(s.anh_chinh_url)!} alt={s.ten} style={{ width: '100%', height: 100, objectFit: 'contain' }} />}
            <Link to={`/san-pham/${s.slug}`}><div style={{ minHeight: 44 }}>{s.ten}</div></Link>
            <Typography.Text strong>{dinhDangTien(s.gia_ban)}</Typography.Text> / {s.ten_don_vi}
            <Button size="small" block style={{ marginTop: 8 }} onClick={() => void them(s.id, s.don_vi_id)}>Thêm vào giỏ</Button>
          </div>
        ))}
      </Space>
    </section>
  )
}

/** KVL07: trang giỏ hàng (thành viên: máy chủ; vãng lai: localStorage). */
export default function TrangGioHang() {
  const { message } = App.useApp()
  const g = useGioHang()
  const [maDangDung, datMaDangDung] = useState<KetQuaMa | null>(null)
  const bao = async (viec: Promise<string | null>) => {
    const loi = await viec
    if (loi) void message.error(loi)
  }
  const co_dong_hong = g.gio.dong.some((d) => !d.mua_duoc)

  const cot: ColumnsType<DongGio> = [
    {
      title: 'Sản phẩm',
      key: 'sp',
      render: (_, d) => (
        <Space orientation="vertical" size={2}>
          <Link to={`/san-pham/${d.san_pham.slug}`}>{d.san_pham.ten}</Link>
          {!d.mua_duoc && d.ly_do && <Tag color="red">{NHAN_LY_DO[d.ly_do]}</Tag>}
        </Space>
      ),
    },
    {
      title: 'Đơn vị',
      key: 'dv',
      width: 130,
      render: (_, d) => (
        <Select
          aria-label={`Đơn vị ${d.san_pham.ten}`}
          style={{ width: 110 }}
          value={d.don_vi?.id}
          disabled={d.don_vi_co_the_chon.length < 2 || d.ly_do === 'thuoc_ke_don'}
          options={d.don_vi_co_the_chon.map((x) => ({ value: x.id, label: x.ten_don_vi }))}
          onChange={(v) => void bao(g.doiDonVi(d, v))}
        />
      ),
    },
    { title: 'Đơn giá', key: 'gia', align: 'right', render: (_, d) => (d.don_vi ? dinhDangTien(d.don_vi.gia_ban) : '—') },
    {
      title: 'Số lượng',
      key: 'sl',
      width: 120,
      render: (_, d) => (
        <InputNumber
          aria-label={`Số lượng ${d.san_pham.ten}`}
          min={1}
          max={Math.min(d.toi_da_don_vi ?? 9999, 9999)}
          precision={0}
          value={d.so_luong}
          disabled={d.ly_do === 'thuoc_ke_don' || d.ly_do === 'khong_hien_thi'}
          onChange={(v) => { if (typeof v === 'number' && v !== d.so_luong) void bao(g.datSoLuong(d, v)) }}
        />
      ),
    },
    { title: 'Thành tiền', key: 'tt', align: 'right', render: (_, d) => (d.mua_duoc ? dinhDangTien(d.thanh_tien) : '—') },
    {
      title: '',
      key: 'xoa',
      width: 56,
      render: (_, d) => <Button type="text" danger icon={<DeleteOutlined />} aria-label={`Xóa ${d.san_pham.ten}`} onClick={() => void bao(g.xoa(d))} />,
    },
  ]
  return (
    <Space orientation="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Giỏ hàng</Typography.Title>
      {g.loi && <Alert type="error" showIcon message="Không tải được giỏ hàng" />}
      {co_dong_hong && <Alert type="warning" showIcon message="Có sản phẩm không còn mua được. Hãy xóa chúng trước khi thanh toán." />}
      <Table<DongGio>
        rowKey={(d) => `${d.san_pham.id}-${d.don_vi?.id ?? 0}`}
        columns={cot}
        dataSource={g.gio.dong}
        loading={g.dangTai}
        pagination={false}
        locale={{ emptyText: <Empty description="Giỏ hàng trống"><Link to="/">Tiếp tục mua sắm</Link></Empty> }}
        scroll={{ x: 'max-content' }}
      />
      {g.gio.dong.length > 0 && (
        <Space orientation="vertical" align="end" style={{ width: '100%' }}>
          {g.thanhVien && <OMaGiamGia khiDoi={datMaDangDung} />}
          <Typography.Title level={4} style={{ margin: 0 }}>Tạm tính: {dinhDangTien(g.gio.tam_tinh)}</Typography.Title>
          {maDangDung && <Typography.Text type="success">Mã {maDangDung.ma}: giảm {dinhDangTien(maDangDung.giam)}</Typography.Text>}
          <Typography.Text type="secondary">Phí vận chuyển và giảm giá được tính ở bước thanh toán.</Typography.Text>
          {g.thanhVien ? (
            <Link to="/thanh-toan"><Button type="primary" size="large" disabled={co_dong_hong || g.gio.tong_so_luong === 0}>Tiến hành thanh toán</Button></Link>
          ) : (
            <Link to="/dang-nhap?tiep=/gio-hang"><Button type="primary" size="large">Đăng nhập để thanh toán</Button></Link>
          )}
        </Space>
      )}
      <MuaCung
        ids={g.gio.dong.filter((d) => d.mua_duoc).map((d) => d.san_pham.id)}
        them={async (spId, dvId) => { await bao(g.them({ san_pham_id: spId, don_vi_id: dvId, so_luong: 1 })) }}
      />
    </Space>
  )
}
