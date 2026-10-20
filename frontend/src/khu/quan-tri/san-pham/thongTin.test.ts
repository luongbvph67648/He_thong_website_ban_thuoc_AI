import { describe, expect, it } from 'vitest'
import { kiemTraThongTin, loiThongTinTuApi, THONG_TIN_MAC_DINH, thongTinRaApi, thongTinRaSua, thongTinTuApi, type GiaTriThongTin } from './thongTin'
import type { SanPhamChiTiet } from './sanPham'

const ban = (ghiDe: Partial<SanPhamChiTiet> = {}): SanPhamChiTiet => ({
  id: 5,
  sku: 'PARA500',
  ten: 'Paracetamol 500mg',
  slug: 'paracetamol-500mg',
  loai_san_pham: 'thuoc_khong_ke_don',
  danh_muc_id: 3,
  ten_danh_muc: 'Giảm đau',
  thuong_hieu_id: 7,
  ten_thuong_hieu: 'Hậu Giang',
  nha_san_xuat_id: null,
  ten_nha_san_xuat: null,
  so_dang_ky: null,
  dang_bao_che: 'Viên nén',
  quy_cach: null,
  doi_tuong_su_dung: null,
  don_vi_co_so: 'Viên',
  ton_toi_thieu: 20,
  dung_dinh_ky: true,
  so_ngay_dung_moi_don_vi: '30.00',
  so_luong_toi_da_moi_don: null,
  la_noi_bat: false,
  trang_thai: 'dang_kinh_doanh',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: null,
  don_vi: [],
  thanh_phan: [],
  anh: [],
  phien_ban: '0123456789abcdef',
  ...ghiDe,
})

const hopLe = (g: Partial<GiaTriThongTin> = {}): GiaTriThongTin => ({ ...THONG_TIN_MAC_DINH, sku: 'abc-1', ten: 'Thuốc A', loai_san_pham: 'thuoc_khong_ke_don', danh_muc_id: 1, ...g })

describe('thongTinTuApi / thongTinRaApi', () => {
  it('đi và về giữ nguyên giá trị; ô trống thành null, số ngày là chuỗi không qua float', () => {
    const g = thongTinTuApi(ban())
    expect(g.thuong_hieu).toEqual({ value: 7, label: 'Hậu Giang' })
    expect(g.nha_san_xuat).toBeNull()
    expect(g.so_ngay_dung_moi_don_vi).toBe(30)
    expect(thongTinRaApi(g)).toMatchObject({
      sku: 'PARA500',
      thuong_hieu_id: 7,
      nha_san_xuat_id: null,
      so_dang_ky: null,
      dang_bao_che: 'Viên nén',
      so_ngay_dung_moi_don_vi: '30',
      so_luong_toi_da_moi_don: null,
    })
  })

  it('SKU đổi sang chữ hoa, tên gộp khoảng trắng, chuỗi chỉ có khoảng trắng thành null', () => {
    const r = thongTinRaApi(hopLe({ sku: '  ab-1 ', ten: '  Thuốc   A ', so_dang_ky: '   ', quy_cach: ' Hộp  10 vỉ ' }))
    expect(r).toMatchObject({ sku: 'AB-1', ten: 'Thuốc A', so_dang_ky: null, quy_cach: 'Hộp 10 vỉ' })
  })
})

describe('thongTinRaSua', () => {
  it('chỉ gồm trường đã đổi so với bản gốc', () => {
    const goc = thongTinTuApi(ban())
    expect(thongTinRaSua(goc, goc)).toEqual({})
    expect(thongTinRaSua({ ...goc, ten: 'Tên mới', quy_cach: 'Hộp 10 vỉ' }, goc)).toEqual({ ten: 'Tên mới', quy_cach: 'Hộp 10 vỉ' })
  })

  it('xóa một ô tùy chọn gửi null; chọn lại cùng thương hiệu thì không phải thay đổi', () => {
    const goc = thongTinTuApi(ban())
    expect(thongTinRaSua({ ...goc, dang_bao_che: '', thuong_hieu: null }, goc)).toEqual({ dang_bao_che: null, thuong_hieu_id: null })
    expect(thongTinRaSua({ ...goc, thuong_hieu: { value: 7, label: 'Tên khác nhưng cùng id' } }, goc)).toEqual({})
  })

  it('tắt dùng định kỳ kèm bỏ số ngày: gửi cả hai trong cùng yêu cầu', () => {
    const goc = thongTinTuApi(ban())
    expect(thongTinRaSua({ ...goc, dung_dinh_ky: false, so_ngay_dung_moi_don_vi: null }, goc)).toEqual({ dung_dinh_ky: false, so_ngay_dung_moi_don_vi: null })
  })

  it('đổi sang thuốc kê đơn kèm bỏ nổi bật', () => {
    const goc = thongTinTuApi(ban({ la_noi_bat: true }))
    expect(thongTinRaSua({ ...goc, loai_san_pham: 'thuoc_ke_don', la_noi_bat: false }, goc)).toEqual({ loai_san_pham: 'thuoc_ke_don', la_noi_bat: false })
  })
})

describe('kiemTraThongTin (cùng quy tắc với backend schemas_san_pham.py)', () => {
  it('hợp lệ thì không có lỗi', () => {
    expect(kiemTraThongTin(hopLe())).toEqual({})
    expect(kiemTraThongTin(hopLe({ dung_dinh_ky: true, so_ngay_dung_moi_don_vi: 7.25, so_luong_toi_da_moi_don: 10, la_noi_bat: true }))).toEqual({})
  })

  it.each<[string, Partial<GiaTriThongTin>, keyof GiaTriThongTin]>([
    ['SKU trống', { sku: ' ' }, 'sku'],
    ['SKU có khoảng trắng', { sku: 'A B' }, 'sku'],
    ['SKU quá dài', { sku: 'A'.repeat(51) }, 'sku'],
    ['tên trống', { ten: '  ' }, 'ten'],
    ['tên quá dài', { ten: 'a'.repeat(256) }, 'ten'],
    ['tên chỉ có dấu câu', { ten: '--- !!!' }, 'ten'],
    ['chưa chọn loại', { loai_san_pham: undefined }, 'loai_san_pham'],
    ['chưa chọn danh mục', { danh_muc_id: undefined }, 'danh_muc_id'],
    ['số đăng ký quá dài', { so_dang_ky: 'x'.repeat(51) }, 'so_dang_ky'],
    ['dạng bào chế quá dài', { dang_bao_che: 'x'.repeat(101) }, 'dang_bao_che'],
    ['quy cách quá dài', { quy_cach: 'x'.repeat(151) }, 'quy_cach'],
    ['đối tượng quá dài', { doi_tuong_su_dung: 'x'.repeat(151) }, 'doi_tuong_su_dung'],
    ['ký tự điều khiển', { quy_cach: 'a\u0000b' }, 'quy_cach'],
    ['tồn tối thiểu trống', { ton_toi_thieu: null }, 'ton_toi_thieu'],
    ['tồn tối thiểu âm', { ton_toi_thieu: -1 }, 'ton_toi_thieu'],
    ['tồn tối thiểu lẻ', { ton_toi_thieu: 1.5 }, 'ton_toi_thieu'],
    ['tồn tối thiểu quá lớn', { ton_toi_thieu: 1_000_000_001 }, 'ton_toi_thieu'],
    ['tối đa mỗi đơn bằng 0', { so_luong_toi_da_moi_don: 0 }, 'so_luong_toi_da_moi_don'],
    ['tối đa mỗi đơn lẻ', { so_luong_toi_da_moi_don: 2.5 }, 'so_luong_toi_da_moi_don'],
    ['số ngày bằng 0', { dung_dinh_ky: true, so_ngay_dung_moi_don_vi: 0 }, 'so_ngay_dung_moi_don_vi'],
    ['số ngày 3 chữ số lẻ', { dung_dinh_ky: true, so_ngay_dung_moi_don_vi: 1.005 }, 'so_ngay_dung_moi_don_vi'],
    ['số ngày từ 10.000', { dung_dinh_ky: true, so_ngay_dung_moi_don_vi: 10_000 }, 'so_ngay_dung_moi_don_vi'],
    ['dùng định kỳ mà thiếu số ngày', { dung_dinh_ky: true, so_ngay_dung_moi_don_vi: null }, 'so_ngay_dung_moi_don_vi'],
    ['có số ngày mà không dùng định kỳ', { dung_dinh_ky: false, so_ngay_dung_moi_don_vi: 30 }, 'so_ngay_dung_moi_don_vi'],
    ['thuốc kê đơn nổi bật', { loai_san_pham: 'thuoc_ke_don', la_noi_bat: true }, 'la_noi_bat'],
  ])('%s là lỗi ở đúng ô', (_ten, ghiDe, o) => {
    const loi = kiemTraThongTin(hopLe(ghiDe))
    expect(Object.keys(loi)).toContain(o)
  })

  it('số ngày hợp lệ ở biên: 0,01 và 9999,99', () => {
    expect(kiemTraThongTin(hopLe({ dung_dinh_ky: true, so_ngay_dung_moi_don_vi: 0.01 }))).toEqual({})
    expect(kiemTraThongTin(hopLe({ dung_dinh_ky: true, so_ngay_dung_moi_don_vi: 9999.99 }))).toEqual({})
  })
})

describe('loiThongTinTuApi', () => {
  it('lỗi theo trường API vào đúng ô (thuong_hieu_id thành thuong_hieu), phần còn lại ra ngoài; đơn vị và thành phần để các tab khác', () => {
    const r = loiThongTinTuApi({
      sku: 'SKU đã tồn tại',
      thuong_hieu_id: 'Thương hiệu không tồn tại',
      phien_ban: 'Sai định dạng',
      'don_vi.0.gia_ban': 'Sai giá',
      thanh_phan: 'Trùng',
    })
    expect(r.theoO).toEqual({ sku: 'SKU đã tồn tại', thuong_hieu: 'Thương hiệu không tồn tại' })
    expect(r.khac).toEqual(['Sai định dạng'])
  })
})
