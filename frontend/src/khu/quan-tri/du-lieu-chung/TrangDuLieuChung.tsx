import { Tabs, Typography } from 'antd'
import { useSearchParams } from 'react-router-dom'
import { BangDuLieuChung } from './BangDuLieuChung'
import { CAC_NHOM, layNhom } from './nhom'

/** Dữ liệu dùng chung (AD05): thương hiệu, nhà sản xuất, hoạt chất. Tab hiện tại nằm trên URL (`?nhom=`). */
export default function TrangDuLieuChung() {
  const [tham, datTham] = useSearchParams()
  const nhom = layNhom(tham.get('nhom'))

  return (
    <div>
      <Typography.Title level={3}>Dữ liệu chung</Typography.Title>
      <Tabs
        activeKey={nhom.ma}
        // Đổi tab thì bỏ tìm kiếm, sắp xếp và trang của tab cũ.
        onChange={(ma) => datTham(ma === CAC_NHOM[0].ma ? {} : { nhom: ma }, { replace: true })}
        items={CAC_NHOM.map((n) => ({ key: n.ma, label: n.nhan, children: n.ma === nhom.ma ? <BangDuLieuChung nhom={n} /> : null }))}
      />
    </div>
  )
}
