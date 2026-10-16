import { Typography } from 'antd'
import { useParams } from 'react-router-dom'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import SuaSanPham, { KhongTimThay } from './SuaSanPham'
import TaoSanPham from './TaoSanPham'

const ID_TOI_DA = 2_147_483_647 // khớp `IdInt` của backend: ngoài khoảng là 400 chứ không phải 404, nên chặn từ đầu

function docId(gia: string | undefined): number | null {
  if (!gia || !/^[1-9]\d*$/.test(gia)) return null
  const so = Number(gia)
  return Number.isSafeInteger(so) && so <= ID_TOI_DA ? so : null
}

/** Trang `/san-pham/moi` (thêm) và `/san-pham/:id` (xem, sửa) của AD04. */
export default function TrangChiTietSanPham() {
  const { id } = useParams()
  if (id === undefined) {
    return (
      <YeuCauQuyen ma="product.commercial.manage">
        <Typography.Title level={3}>Thêm sản phẩm</Typography.Title>
        <TaoSanPham />
      </YeuCauQuyen>
    )
  }
  const sanPhamId = docId(id)
  return sanPhamId === null ? <KhongTimThay /> : <SuaSanPham key={sanPhamId} id={sanPhamId} />
}
