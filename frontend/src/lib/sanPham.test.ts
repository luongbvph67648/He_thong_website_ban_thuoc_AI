import { describe, expect, it } from 'vitest'
import { donViMoi, donViRaApi, donViTuApi, khoaTen, kiemTraDonVi, kiemTraThanhPhan, loiCheo, loiDonViTuApi, loiSku, loiThanhPhanTuApi, thanhPhanMoi, type DonViForm } from './sanPham'

const dv = (t: Partial<DonViForm>): DonViForm => donViMoi({ ten_don_vi: 'Viên', he_so: 1, gia_ban: 1000, ...t })

describe('khoaTen', () => {
  it('không phân biệt hoa thường, dấu và khoảng trắng thừa', () => {
    expect(khoaTen('  Hộp ')).toBe('hop')
    expect(khoaTen('ĐÓNG   gói')).toBe('dong goi')
    expect(khoaTen('Hộp')).toBe(khoaTen('hop'))
  })
})

describe('kiemTraDonVi (cùng quy tắc với backend schemas_san_pham.py)', () => {
  it('danh sách hợp lệ: một đơn vị cơ sở, một mặc định, tên và mã vạch khác nhau', () => {
    const r = kiemTraDonVi([dv({ ma_vach: '123' }), dv({ ten_don_vi: 'Hộp', he_so: 100, gia_ban: 90000, la_mac_dinh: true, ma_vach: '456' })])
    expect(r.coLoi).toBe(false)
    expect(r.chung).toEqual([])
  })

  it.each([
    ['rỗng', [], /ít nhất một đơn vị/],
    ['không có đơn vị cơ sở', [dv({ he_so: 10 })], /đúng một đơn vị cơ sở/],
    ['hai đơn vị cơ sở', [dv({}), dv({ ten_don_vi: 'B' })], /đúng một đơn vị cơ sở/],
    ['hai mặc định', [dv({ la_mac_dinh: true }), dv({ ten_don_vi: 'Hộp', he_so: 10, la_mac_dinh: true })], /một đơn vị mặc định/],
    ['tên trùng không dấu', [dv({ ten_don_vi: 'Hộp' }), dv({ ten_don_vi: 'hop', he_so: 10 })], /không được trùng/],
    ['mã vạch trùng không phân biệt hoa thường', [dv({ ma_vach: 'abc' }), dv({ ten_don_vi: 'B', he_so: 2, ma_vach: 'ABC' })], /Mã vạch không được trùng/],
  ])('%s là lỗi chung', (_ten, ds, mau) => {
    const r = kiemTraDonVi(ds as DonViForm[])
    expect(r.coLoi).toBe(true)
    expect(r.chung.join('|')).toMatch(mau)
  })

  it.each([
    ['tên rỗng', { ten_don_vi: '  ' }, 'ten_don_vi'],
    ['tên quá dài', { ten_don_vi: 'x'.repeat(31) }, 'ten_don_vi'],
    ['hệ số thiếu', { he_so: null }, 'he_so'],
    ['hệ số 0', { he_so: 0 }, 'he_so'],
    ['hệ số thực', { he_so: 1.5 }, 'he_so'],
    ['giá thiếu', { gia_ban: null }, 'gia_ban'],
    ['giá âm', { gia_ban: -1 }, 'gia_ban'],
    ['giá lẻ', { gia_ban: 10.5 }, 'gia_ban'],
    ['giá quá lớn', { gia_ban: 10 ** 12 }, 'gia_ban'],
    ['mã vạch có khoảng trắng', { ma_vach: '12 34' }, 'ma_vach'],
    ['mã vạch quá dài', { ma_vach: '1'.repeat(51) }, 'ma_vach'],
  ])('%s là lỗi ở đúng ô', (_ten, ghiDe, truong) => {
    const r = kiemTraDonVi([dv({}), dv({ ten_don_vi: 'Hộp', he_so: 10, gia_ban: 9000, ...ghiDe })])
    expect(r.coLoi).toBe(true)
    expect(Object.keys(r.theoDong[1] ?? {})).toContain(truong)
    expect(r.theoDong[0]).toBeUndefined()
  })

  it('giá 0 là hợp lệ (quà tặng, hàng mẫu)', () => {
    expect(kiemTraDonVi([dv({ gia_ban: 0 })]).coLoi).toBe(false)
  })
})

describe('donViRaApi và donViTuApi', () => {
  it('đi tới lui: tiền "90000.00" thành số rồi ra chuỗi số nguyên, ô trống thành null, giữ id', () => {
    const tuApi = donViTuApi({ id: 7, ten_don_vi: 'Hộp', he_so: 100, gia_ban: '90000.00', ban_online: true, la_mac_dinh: true, ma_vach: null })
    expect(tuApi).toMatchObject({ id: 7, gia_ban: 90000, ma_vach: '' })
    expect(donViRaApi(tuApi)).toEqual({ id: 7, ten_don_vi: 'Hộp', he_so: 100, gia_ban: '90000', ban_online: true, la_mac_dinh: true, ma_vach: null })
  })

  it('đơn vị mới không có id; tên được gọn khoảng trắng', () => {
    const ra = donViRaApi(dv({ ten_don_vi: '  Vỉ   nhỏ ', ma_vach: ' 8934 '.replace(' ', '') }))
    expect(ra).not.toHaveProperty('id')
    expect(ra.ten_don_vi).toBe('Vỉ nhỏ')
  })
})

describe('kiemTraThanhPhan', () => {
  it('bắt buộc chọn hoạt chất, không trùng, hàm lượng tối đa 50 ký tự', () => {
    const tp = (id: number | null, ham = '') => ({ ...thanhPhanMoi(), hoat_chat_id: id, ham_luong: ham })
    expect(kiemTraThanhPhan([tp(1, '500mg'), tp(2)]).coLoi).toBe(false)
    expect(kiemTraThanhPhan([tp(null)]).theoDong[0]).toMatch(/Chọn/)
    expect(kiemTraThanhPhan([tp(1), tp(1)]).chung.join()).toMatch(/một lần/)
    expect(kiemTraThanhPhan([tp(1, 'x'.repeat(51))]).theoDong[0]).toMatch(/50/)
    expect(kiemTraThanhPhan([]).coLoi).toBe(false) // thành phần không bắt buộc
  })
})

describe('loiSku và loiCheo', () => {
  it('SKU gồm chữ số và . _ - , được viết thường (sẽ chuyển thành chữ hoa)', () => {
    expect(loiSku('para-500')).toBeNull()
    expect(loiSku('  ')).toMatch(/nhập/)
    for (const sai of ['a b', 'a/b', '-ab', 'x'.repeat(51)]) expect(loiSku(sai), sai).not.toBeNull()
  })
  it('quy tắc chéo giống backend vi_pham_cheo', () => {
    const co = { dung_dinh_ky: false, so_ngay: null as number | null, loai: 'thuoc_khong_ke_don', la_noi_bat: false }
    expect(loiCheo(co)).toBeNull()
    expect(loiCheo({ ...co, dung_dinh_ky: true })?.truong).toBe('so_ngay_dung_moi_don_vi')
    expect(loiCheo({ ...co, so_ngay: 3 })?.truong).toBe('so_ngay_dung_moi_don_vi')
    expect(loiCheo({ ...co, dung_dinh_ky: true, so_ngay: 3 })).toBeNull()
    expect(loiCheo({ ...co, loai: 'thuoc_ke_don', la_noi_bat: true })?.truong).toBe('la_noi_bat')
    expect(loiCheo({ ...co, loai: 'thuoc_ke_don' })).toBeNull()
  })
})

describe('loiDonViTuApi / loiThanhPhanTuApi', () => {
  it('lỗi theo dòng đi vào đúng ô của đúng dòng, lỗi khác thành lỗi chung', () => {
    const r = loiDonViTuApi({ 'don_vi.2.ma_vach': 'Mã vạch trùng', 'don_vi.0.gia_ban': 'Sai giá', don_vi: 'Phải có đúng một đơn vị cơ sở', phien_ban: 'Sai định dạng' })
    expect(r.theoDong).toEqual({ 2: { ma_vach: 'Mã vạch trùng' }, 0: { gia_ban: 'Sai giá' } })
    expect(r.chung).toEqual(['Phải có đúng một đơn vị cơ sở', 'Sai định dạng'])
  })

  it('trường không có ô riêng của một dòng (ví dụ ban_online) hiện ở lỗi chung chứ không mất', () => {
    expect(loiDonViTuApi({ 'don_vi.1.ban_online': 'Phải là true/false' })).toEqual({ chung: ['Phải là true/false'], theoDong: {} })
  })

  it('thành phần: lỗi theo dòng và lỗi chung', () => {
    const r = loiThanhPhanTuApi({ 'thanh_phan.1.hoat_chat_id': 'Hoạt chất không tồn tại', 'thanh_phan.0.ham_luong': 'Tối đa 50 ký tự', thanh_phan: 'Mỗi hoạt chất chỉ được xuất hiện một lần' })
    expect(r.theoDong).toEqual({ 1: 'Hoạt chất không tồn tại', 0: 'Tối đa 50 ký tự' })
    expect(r.chung).toEqual(['Mỗi hoạt chất chỉ được xuất hiện một lần'])
  })
})
