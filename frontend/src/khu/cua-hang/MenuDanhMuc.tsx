import { Menu } from 'antd'
import type { MenuProps } from 'antd'
import { Link } from 'react-router-dom'
import type { DanhMucNut } from './cuaHang'
import { useCayDanhMuc } from './useCayDanhMuc'

type Muc = Required<MenuProps>['items'][number]

function doiThanhMuc(d: DanhMucNut): Muc {
  const con = d.con.map(doiThanhMuc)
  return {
    key: d.slug,
    label: <Link to={`/danh-muc/${d.slug}`}>{d.ten}</Link>,
    ...(con.length ? { children: con } : {}),
  }
}

/** Thanh danh mục 3 cấp ở đầu cửa hàng. Lỗi tải thì ẩn (không chặn việc dùng trang). */
export function MenuDanhMuc() {
  const { data } = useCayDanhMuc()
  if (!data?.length) return null
  return (
    <nav aria-label="Danh mục sản phẩm" style={{ background: '#fff', borderBottom: '1px solid #f0f0f0' }}>
      <Menu mode="horizontal" selectable={false} items={data.map(doiThanhMuc)} style={{ maxWidth: 1200, margin: '0 auto' }} />
    </nav>
  )
}
