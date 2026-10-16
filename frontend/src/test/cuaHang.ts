/** Dữ liệu giả cho test khu cửa hàng (hình dạng đúng với `schema.d.ts`; tsc bắt lệch khi API đổi). */
import type { SanPhamChiTiet, SanPhamThe } from '../khu/cua-hang/cuaHang'

export const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
export const loi = (status: number, ma_loi: string, thong_diep: string) => ({
  error: { ma_loi, thong_diep, chi_tiet: null, request_id: 'r' },
  response: { ok: false, status },
})

export function the(ghiDe: Partial<SanPhamThe> = {}): SanPhamThe {
  return {
    id: 1,
    ten: 'Paracetamol 500mg',
    slug: 'paracetamol-500mg',
    loai_san_pham: 'thuoc_khong_ke_don',
    can_tu_van: false,
    thuong_hieu: 'Hà Thành Pharma',
    quy_cach: 'Hộp 10 vỉ',
    anh_chinh_url: null,
    gia: '9000.00',
    ten_don_vi_gia: 'vỉ',
    con_hang: true,
    ...ghiDe,
  }
}

export function chiTiet(ghiDe: Partial<SanPhamChiTiet> = {}): SanPhamChiTiet {
  return {
    id: 1,
    sku: 'PARA500',
    ten: 'Paracetamol 500mg',
    slug: 'paracetamol-500mg',
    loai_san_pham: 'thuoc_khong_ke_don',
    can_tu_van: false,
    luu_y_khong_phai_thuoc: false,
    chi_ban_tai_quay: false,
    thuong_hieu: { id: 2, ten: 'Hà Thành Pharma' },
    nha_san_xuat: 'Hậu Giang',
    so_dang_ky: 'VD-1234-20',
    dang_bao_che: 'Viên nén',
    quy_cach: 'Hộp 10 vỉ x 10 viên',
    doi_tuong_su_dung: 'Người lớn',
    duong_dan_danh_muc: [
      { ten: 'Thuốc', slug: 'thuoc' },
      { ten: 'Giảm đau', slug: 'giam-dau' },
    ],
    don_vi: [
      { id: 10, ten_don_vi: 'viên', he_so: 1, gia_ban: '1000.00', la_mac_dinh: false, con_hang: true },
      { id: 11, ten_don_vi: 'vỉ', he_so: 10, gia_ban: '9000.00', la_mac_dinh: true, con_hang: true },
      { id: 12, ten_don_vi: 'hộp', he_so: 100, gia_ban: '80000.00', la_mac_dinh: false, con_hang: false },
    ],
    anh: [
      { url: '/api/v1/tep/san-pham/a.jpg', la_anh_chinh: true },
      { url: '/api/v1/tep/san-pham/b.jpg', la_anh_chinh: false },
    ],
    thanh_phan: [{ hoat_chat_id: 5, ten: 'Paracetamol', ham_luong: '500mg' }],
    noi_dung_chuyen_mon: {
      phien_ban: 2,
      ngay_duyet: '2026-10-10T03:00:00Z',
      chi_dinh: 'Giảm đau, hạ sốt',
      chong_chi_dinh: 'Quá mẫn với paracetamol',
      lieu_dung_tham_khao: null,
      tac_dung_phu: null,
      than_trong: null,
      tuong_tac_thuoc: null,
      phu_nu_co_thai_cho_con_bu: null,
      tre_em: null,
      qua_lieu_xu_tri: null,
      bao_quan: 'Nơi khô ráo',
      file_hdsd_url: null,
    },
    con_hang: true,
    danh_gia: { so_luong: 0, tong_sao: 0, phan_bo: [0, 0, 0, 0, 0], moi_nhat: [] },
    tuong_tu: [],
    ...ghiDe,
  }
}
