import type { components } from '../../../api/schema'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'

type HoaDon = components['schemas']['HoaDonRa']

const HINH_THUC: Record<string, string> = { tien_mat: 'Tiền mặt', chuyen_khoan: 'Chuyển khoản' }

/** Hóa đơn POS dạng HTML in được (khổ 80 mm). In bằng `window.print()`; CSS `@media print` chỉ giữ vùng này. */
export default function HoaDonIn({ hd }: { hd: HoaDon }) {
  return (
    <div className="hoa-don-in" style={{ fontFamily: 'monospace', fontSize: 13, maxWidth: 320, margin: '0 auto' }}>
      <div style={{ textAlign: 'center', fontWeight: 700, fontSize: 16 }}>{hd.ten_nha_thuoc}</div>
      <div style={{ textAlign: 'center' }}>HÓA ĐƠN BÁN HÀNG</div>
      <div>Số: {hd.ma_don}</div>
      <div>Ngày: {dinhDangNgay(hd.thoi_diem, 'ngayGio')}</div>
      <div>Dược sĩ: {hd.nhan_vien}</div>
      {hd.khach && <div>Khách: {hd.khach}</div>}
      <hr />
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <tbody>
          {hd.dong.map((d, i) => (
            <tr key={i}>
              <td colSpan={2}>{d.ten_san_pham} ({d.ten_don_vi})</td>
              <td style={{ textAlign: 'right' }}>{d.so_luong} x {dinhDangTien(d.don_gia)}</td>
              <td style={{ textAlign: 'right' }}>{dinhDangTien(d.thanh_tien)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <hr />
      <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Tạm tính</span><span>{dinhDangTien(hd.tam_tinh)}</span></div>
      {Number(hd.giam_gia) > 0 && <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Giảm giá</span><span>-{dinhDangTien(hd.giam_gia)}</span></div>}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}><span>TỔNG CỘNG</span><span>{dinhDangTien(hd.tong_tien)}</span></div>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Thanh toán ({HINH_THUC[hd.phuong_thuc_thu] ?? hd.phuong_thuc_thu})</span><span>{dinhDangTien(hd.tong_tien)}</span></div>
      {hd.tien_khach_dua != null && <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Khách đưa</span><span>{dinhDangTien(hd.tien_khach_dua)}</span></div>}
      {hd.tien_thua != null && <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Tiền thối</span><span>{dinhDangTien(hd.tien_thua)}</span></div>}
      {hd.co_thuoc_ke_don && <div style={{ marginTop: 8 }}>* Có thuốc kê đơn, bán theo đơn của bác sĩ.</div>}
      <div style={{ textAlign: 'center', marginTop: 8 }}>Cảm ơn quý khách!</div>
    </div>
  )
}
