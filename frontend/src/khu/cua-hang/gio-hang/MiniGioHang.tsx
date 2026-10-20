import { ShoppingCartOutlined } from '@ant-design/icons'
import { Badge, Button, Popover, Space, Typography } from 'antd'
import { Link } from 'react-router-dom'
import { dinhDangTien } from '../../../lib/dinhDang'
import { useGioHang } from './gioHang'

const SO_DONG_HIEN = 5

/** Mini-cart ở header: số lượng trên biểu tượng, rê chuột/bấm để xem vài dòng đầu và tạm tính. */
export function MiniGioHang() {
  const { gio } = useGioHang()
  const dong = gio.dong.filter((d) => d.mua_duoc)
  const noiDung =
    dong.length === 0 ? (
      <Typography.Text type="secondary">Giỏ hàng trống</Typography.Text>
    ) : (
      <Space orientation="vertical" style={{ width: 280 }}>
        {dong.slice(0, SO_DONG_HIEN).map((d) => (
          <div key={`${d.san_pham.id}-${d.don_vi?.id}`} style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
            <span>{d.so_luong} × {d.san_pham.ten}{d.don_vi ? ` (${d.don_vi.ten_don_vi})` : ''}</span>
            <span>{dinhDangTien(d.thanh_tien)}</span>
          </div>
        ))}
        {dong.length > SO_DONG_HIEN && <Typography.Text type="secondary">và {dong.length - SO_DONG_HIEN} sản phẩm khác</Typography.Text>}
        <Typography.Text strong>Tạm tính: {dinhDangTien(gio.tam_tinh)}</Typography.Text>
        <Link to="/gio-hang"><Button type="primary" block>Xem giỏ hàng</Button></Link>
      </Space>
    )
  return (
    <Popover content={noiDung} placement="bottomRight" title="Giỏ hàng">
      <Link className="nut-gio-hang" to="/gio-hang" aria-label={`Giỏ hàng, ${gio.tong_so_luong} sản phẩm`}>
        <Badge count={gio.tong_so_luong} size="small" overflowCount={99} showZero>
          <span className="bieu-tuong-gio-hang"><ShoppingCartOutlined /></span>
        </Badge>{' '}
        <span className="nhan-gio-hang">Giỏ hàng</span>
      </Link>
    </Popover>
  )
}
