import { describe, expect, it } from 'vitest'
import {
  BAI_TRONG,
  BANNER_TRONG,
  baiRaSua,
  baiRaTao,
  bannerRaSua,
  bannerRaTao,
  cungThoiDiem,
  daDoiNoiDungBai,
  gopThayDoi,
  giaTriTuBai,
  giaTriTuBanner,
  kiemTraBai,
  kiemTraBanner,
  nhanBai,
  suaSeVeChoDuyet,
  type BaiVietAdmin,
  type BannerRa,
} from './noiDungWeb'

const BAI: BaiVietAdmin = {
  id: 1,
  tieu_de: 'Phòng cảm cúm',
  slug: 'phong-cam-cum',
  loai: 'bai_viet',
  trang_thai: 'da_duyet',
  dua_vao_ai: false,
  tac_gia: 'Admin',
  created_at: '2026-10-10T00:00:00Z',
  updated_at: null,
  ngay_duyet: '2026-10-11T00:00:00Z',
  noi_dung: 'Rửa tay',
  anh_bia_url: null,
  duoc_si_duyet: 'DS',
  phien_ban: '0123456789abcdef',
}
const BANNER: BannerRa = {
  id: 1,
  tieu_de: 'Khuyến mãi',
  anh_url: '/banner/a.jpg',
  lien_ket: '/danh-muc/thuoc',
  vi_tri: 'trang_chu_chinh',
  thu_tu: 2,
  bat_dau: '2026-01-01T00:00:00Z',
  ket_thuc: null,
  dang_hien: true,
  tinh_trang: 'dang_hien',
  phien_ban: '0123456789abcdef',
}

describe('nhanBai', () => {
  it('bài sức khỏe nhap là chờ dược sĩ duyệt, chính sách nhap là bản nháp', () => {
    expect(nhanBai('bai_viet', 'nhap').nhan).toBe('Chờ dược sĩ duyệt')
    expect(nhanBai('faq', 'nhap').nhan).toBe('Bản nháp')
    expect(nhanBai('chinh_sach', 'da_duyet').nhan).toBe('Đang đăng')
    expect(nhanBai('bai_viet', 'luu_tru').nhan).toBe('Đã gỡ')
  })
})

describe('suaSeVeChoDuyet', () => {
  it.each([
    ['bai_viet', 'da_duyet', true, true],
    ['bai_viet', 'da_duyet', false, false],
    ['bai_viet', 'nhap', true, false],
    ['bai_viet', 'luu_tru', true, false],
    ['chinh_sach', 'da_duyet', true, false],
    ['faq', 'da_duyet', true, false],
  ] as const)('%s %s đổi=%s -> %s', (loai, tt, doi, mong) => expect(suaSeVeChoDuyet(loai, tt, doi)).toBe(mong))
})

describe('kiemTraBai', () => {
  const tot = { ...BAI_TRONG, tieu_de: 'Tiêu đề', noi_dung: 'Nội dung' }
  it('hợp lệ', () => expect(kiemTraBai(tot)).toEqual({}))
  it.each([
    ['tiêu đề rỗng', { tieu_de: '   ' }, 'tieu_de'],
    ['tiêu đề chỉ ký hiệu', { tieu_de: '!!! ???' }, 'tieu_de'],
    ['tiêu đề quá dài', { tieu_de: 'x'.repeat(256) }, 'tieu_de'],
    ['tiêu đề có NUL', { tieu_de: 'a\u0000b' }, 'tieu_de'],
    ['nội dung rỗng', { noi_dung: ' \n ' }, 'noi_dung'],
    ['nội dung quá dài', { noi_dung: 'x'.repeat(100_001) }, 'noi_dung'],
    ['ảnh bìa nguy hiểm', { anh_bia_url: 'javascript:alert(1)' }, 'anh_bia_url'],
    ['ảnh bìa giao thức tương đối', { anh_bia_url: '//evil.example/a.jpg' }, 'anh_bia_url'],
  ])('%s', (_ten, ghiDe, truong) => {
    expect(Object.keys(kiemTraBai({ ...tot, ...ghiDe }))).toEqual([truong])
  })
  it('nội dung nhiều dòng có xuống dòng và tab hợp lệ; chấp nhận đúng 255 ký tự tiêu đề', () => {
    expect(kiemTraBai({ ...tot, noi_dung: 'a\n\tb\r\nc', tieu_de: 'x'.repeat(255) })).toEqual({})
  })
})

describe('baiRaTao / baiRaSua', () => {
  it('tạo: gọn tiêu đề, bỏ ảnh bìa trống thành null', () => {
    expect(baiRaTao('faq', { tieu_de: '  Giao   hàng? ', noi_dung: '  Có \n', anh_bia_url: '  ', dua_vao_ai: true })).toEqual({
      loai: 'faq',
      tieu_de: 'Giao hàng?',
      noi_dung: 'Có',
      anh_bia_url: null,
      dua_vao_ai: true,
    })
  })
  it('sửa: không đổi gì thì rỗng; chỉ gửi trường đã đổi; ảnh bìa xóa là null', () => {
    const g = giaTriTuBai(BAI)
    expect(baiRaSua(BAI, g)).toEqual({})
    expect(baiRaSua(BAI, { ...g, noi_dung: 'Mới' })).toEqual({ noi_dung: 'Mới' })
    expect(baiRaSua({ ...BAI, anh_bia_url: '/a.jpg' }, { ...g, anh_bia_url: '' })).toEqual({ anh_bia_url: null })
    expect(baiRaSua(BAI, { ...g, tieu_de: '  Phòng   cảm cúm ' })).toEqual({}) // chỉ khác khoảng trắng
  })
  it('daDoiNoiDungBai: dua_vao_ai không tính', () => {
    expect(daDoiNoiDungBai({ dua_vao_ai: true })).toBe(false)
    expect(daDoiNoiDungBai({ tieu_de: 'x' })).toBe(true)
    expect(daDoiNoiDungBai({ anh_bia_url: null })).toBe(true)
    expect(daDoiNoiDungBai({})).toBe(false)
  })
})

describe('kiemTraBanner', () => {
  const tot = { ...BANNER_TRONG, anh_url: '/banner/a.jpg' }
  it('hợp lệ (tiêu đề, liên kết, thời gian đều tùy chọn)', () => expect(kiemTraBanner(tot)).toEqual({}))
  it.each([
    ['thiếu ảnh', { anh_url: ' ' }, 'anh_url'],
    ['ảnh nguy hiểm', { anh_url: 'javascript:alert(1)' }, 'anh_url'],
    ['liên kết nguy hiểm', { lien_ket: 'javascript:x' }, 'lien_ket'],
    ['vị trí lạ', { vi_tri: 'footer' }, 'vi_tri'],
    ['thứ tự âm', { thu_tu: -1 }, 'thu_tu'],
    ['thứ tự quá lớn', { thu_tu: 10_000 }, 'thu_tu'],
    ['thứ tự lẻ', { thu_tu: 1.5 }, 'thu_tu'],
    ['thứ tự trống', { thu_tu: null }, 'thu_tu'],
    ['tiêu đề quá dài', { tieu_de: 'x'.repeat(201) }, 'tieu_de'],
    ['kết thúc trước bắt đầu', { bat_dau: '2026-02-01T00:00:00Z', ket_thuc: '2026-01-01T00:00:00Z' }, 'ket_thuc'],
    ['kết thúc bằng bắt đầu', { bat_dau: '2026-02-01T00:00:00Z', ket_thuc: '2026-02-01T00:00:00Z' }, 'ket_thuc'],
  ])('%s', (_ten, ghiDe, truong) => {
    expect(Object.keys(kiemTraBanner({ ...tot, ...ghiDe }))).toEqual([truong])
  })
  it('thứ tự 0 và 9999 hợp lệ', () => {
    expect(kiemTraBanner({ ...tot, thu_tu: 0 })).toEqual({})
    expect(kiemTraBanner({ ...tot, thu_tu: 9999 })).toEqual({})
  })
})

describe('bannerRaTao / bannerRaSua', () => {
  it('tạo: trống thành null', () => {
    expect(bannerRaTao({ ...BANNER_TRONG, anh_url: ' /a.jpg ', tieu_de: '  ', lien_ket: '' })).toMatchObject({
      anh_url: '/a.jpg',
      tieu_de: null,
      lien_ket: null,
    })
  })
  it('sửa: không đổi thì rỗng, giờ cùng thời điểm khác cách viết không tính là đổi', () => {
    const g = giaTriTuBanner(BANNER)
    expect(bannerRaSua(BANNER, g)).toEqual({})
    expect(bannerRaSua(BANNER, { ...g, bat_dau: '2026-01-01T07:00:00+07:00' })).toEqual({})
    expect(bannerRaSua(BANNER, { ...g, bat_dau: null, lien_ket: '', thu_tu: 5 })).toEqual({ bat_dau: null, lien_ket: null, thu_tu: 5 })
  })
  it('cungThoiDiem', () => {
    expect(cungThoiDiem(null, null)).toBe(true)
    expect(cungThoiDiem(null, '2026-01-01T00:00:00Z')).toBe(false)
    expect(cungThoiDiem('2026-01-01T00:00:00Z', '2026-01-01T07:00:00+07:00')).toBe(true)
  })
})

describe('gopThayDoi', () => {
  it('giữ ô người dùng đã sửa, lấy bản mới cho ô họ không đụng tới', () => {
    const goc = { a: 'a0', b: 'b0', c: 'c0' }
    const dangGo = { a: 'a1', b: 'b0', c: 'c0' } // người dùng chỉ sửa a
    const moi = { a: 'a0', b: 'b9', c: 'c0' } // người kia sửa b
    expect(gopThayDoi(dangGo, goc, moi)).toEqual({ a: 'a1', b: 'b9', c: 'c0' })
  })
  it('hai bên cùng sửa một ô thì thắng bản người dùng đang gõ; không sửa gì thì bằng bản mới', () => {
    expect(gopThayDoi({ a: 'x' }, { a: '0' }, { a: 'y' })).toEqual({ a: 'x' })
    expect(gopThayDoi({ a: '0', n: null }, { a: '0', n: null }, { a: '9', n: 1 })).toEqual({ a: '9', n: 1 })
  })
})
