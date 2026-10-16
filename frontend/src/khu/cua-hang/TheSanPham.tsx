import { Card, Space, Tag, Typography } from 'antd'
import { Link } from 'react-router-dom'
import { dinhDangTien } from '../../lib/dinhDang'
import type { NguonXem, SanPhamThe } from './cuaHang'

/** Thẻ sản phẩm ở mọi danh sách. Thuốc kê đơn hiện nhãn đỏ và "Cần tư vấn", không có hành động mua. */
export function TheSanPham({ sp, nguon }: { sp: SanPhamThe; nguon?: NguonXem }) {
  return (
    <Link to={`/san-pham/${sp.slug}${nguon ? `?nguon=${nguon}` : ''}`} aria-label={sp.ten} style={{ display: 'block', height: '100%' }}>
      <Card
        hoverable
        size="small"
        style={{ height: '100%' }}
        cover={
          sp.anh_chinh_url ? (
            <img
              src={sp.anh_chinh_url}
              alt=""
              loading="lazy"
              style={{ height: 160, objectFit: 'contain', padding: 8, background: '#fafafa' }}
            />
          ) : (
            <div
              aria-hidden
              style={{ height: 160, background: '#fafafa', display: 'grid', placeItems: 'center', color: '#bfbfbf' }}
            >
              Chưa có ảnh
            </div>
          )
        }
      >
        <Space orientation="vertical" size={4} style={{ width: '100%' }}>
          {sp.can_tu_van && <Tag color="red">Thuốc kê đơn</Tag>}
          <Typography.Paragraph strong ellipsis={{ rows: 2 }} style={{ marginBottom: 0, minHeight: 44 }}>
            {sp.ten}
          </Typography.Paragraph>
          {sp.thuong_hieu && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {sp.thuong_hieu}
            </Typography.Text>
          )}
          {sp.gia ? (
            <Typography.Text strong style={{ color: '#cf1322' }}>
              {dinhDangTien(sp.gia)}
              {sp.ten_don_vi_gia && <span style={{ fontWeight: 400, color: '#8c8c8c' }}> / {sp.ten_don_vi_gia}</span>}
            </Typography.Text>
          ) : (
            <Typography.Text type="secondary">Chỉ bán tại nhà thuốc</Typography.Text>
          )}
          <Space size={4} wrap>
            {sp.can_tu_van && <Tag color="volcano">Cần tư vấn</Tag>}
            {!sp.con_hang && <Tag>Hết hàng</Tag>}
          </Space>
        </Space>
      </Card>
    </Link>
  )
}

export function LuoiSanPham({ danhSach, nguon }: { danhSach: readonly SanPhamThe[]; nguon?: NguonXem }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
        gap: 12,
      }}
    >
      {danhSach.map((sp) => (
        <TheSanPham key={sp.id} sp={sp} nguon={nguon} />
      ))}
    </div>
  )
}
