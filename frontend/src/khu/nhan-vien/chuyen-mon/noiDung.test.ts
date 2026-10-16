import { describe, expect, it } from 'vitest'
import {
  banDienSan,
  coThayDoi,
  giaTriTuPhienBan,
  kiemTraNoiDung,
  noiDungRaApi,
  NOI_DUNG_TRONG,
  phienBanCoSo,
  soSanh,
  TOI_DA_KY_TU,
  type PhienBanNoiDung,
} from './noiDung'

const ban = (phien_ban: number, trang_thai: PhienBanNoiDung['trang_thai'], ghiDe: Partial<PhienBanNoiDung> = {}): PhienBanNoiDung => ({
  id: phien_ban * 10,
  san_pham_id: 1,
  phien_ban,
  trang_thai,
  chi_dinh: 'Giảm đau',
  chong_chi_dinh: null,
  lieu_dung_tham_khao: null,
  tac_dung_phu: null,
  than_trong: null,
  tuong_tac_thuoc: null,
  phu_nu_co_thai_cho_con_bu: null,
  tre_em: null,
  qua_lieu_xu_tri: null,
  bao_quan: null,
  file_hdsd_url: null,
  nguoi_soan: null,
  duoc_si_duyet: null,
  ngay_duyet: null,
  created_at: '2026-10-16T00:00:00Z',
  ...ghiDe,
})

describe('phienBanCoSo / banDienSan', () => {
  it('cơ sở là số lớn nhất mọi trạng thái; chưa có bản nào là null', () => {
    expect(phienBanCoSo([])).toBeNull()
    expect(phienBanCoSo([ban(1, 'da_duyet'), ban(3, 'luu_tru'), ban(2, 'nhap')])).toBe(3)
  })

  it('điền sẵn từ bản còn hiệu lực mới nhất; bản nháp cũ hơn bản đang hiển thị không được chọn', () => {
    expect(banDienSan([ban(1, 'da_duyet'), ban(2, 'nhap'), ban(3, 'nhap')])?.phien_ban).toBe(3)
    expect(banDienSan([ban(1, 'nhap'), ban(2, 'da_duyet')])?.phien_ban).toBe(2)
    expect(banDienSan([ban(1, 'luu_tru'), ban(2, 'da_duyet')])?.phien_ban).toBe(2)
    expect(banDienSan([ban(1, 'luu_tru')])).toBeUndefined()
    expect(banDienSan([])).toBeUndefined()
    expect(giaTriTuPhienBan(undefined)).toEqual(NOI_DUNG_TRONG)
  })
})

describe('noiDungRaApi / kiemTraNoiDung', () => {
  it('ô trống thành null, giữ xuống dòng, cắt đầu cuối, kèm phien_ban_co_so', () => {
    const g = { ...NOI_DUNG_TRONG, chi_dinh: '  Giảm đau\n\nhạ sốt  ', tac_dung_phu: '   ', file_hdsd_url: ' /tep/hdsd.pdf ' }
    const api = noiDungRaApi(g, 4)
    expect(api).toMatchObject({ phien_ban_co_so: 4, chi_dinh: 'Giảm đau\n\nhạ sốt', tac_dung_phu: null, file_hdsd_url: '/tep/hdsd.pdf', bao_quan: null })
    expect(noiDungRaApi(NOI_DUNG_TRONG, null).phien_ban_co_so).toBeNull()
  })

  it.each([
    ['ký tự điều khiển', { chi_dinh: 'a\u0000b' }, 'chi_dinh'],
    ['quá dài', { tre_em: 'x'.repeat(TOI_DA_KY_TU + 1) }, 'tre_em'],
    ['URL nguy hiểm', { file_hdsd_url: 'javascript:alert(1)' }, 'file_hdsd_url'],
    ['URL //host', { file_hdsd_url: '//evil.example/x' }, 'file_hdsd_url'],
  ])('%s là lỗi ở đúng ô', (_ten, ghiDe, truong) => {
    expect(Object.keys(kiemTraNoiDung({ ...NOI_DUNG_TRONG, ...ghiDe }))).toEqual([truong])
  })

  it('hợp lệ: ô dài đúng giới hạn, xuống dòng và tab được phép', () => {
    expect(kiemTraNoiDung({ ...NOI_DUNG_TRONG, chi_dinh: 'x'.repeat(TOI_DA_KY_TU), than_trong: 'a\n\tb', file_hdsd_url: 'https://example.com/a.pdf' })).toEqual({})
  })
})

describe('soSanh / coThayDoi', () => {
  it('chỉ đánh dấu trường khác nhau; null và chuỗi rỗng là một', () => {
    const dong = soSanh(ban(1, 'luu_tru', { tre_em: 'Trên 6 tuổi', bao_quan: '' }), ban(2, 'nhap', { tre_em: 'Trên 12 tuổi', tac_dung_phu: 'Buồn nôn' }))
    expect(dong.filter((d) => d.khac).map((d) => d.ten)).toEqual(['tac_dung_phu', 'tre_em'])
    const tre = dong.find((d) => d.ten === 'tre_em')!
    expect([tre.nhan, tre.truoc, tre.sau]).toEqual(['Trẻ em', 'Trên 6 tuổi', 'Trên 12 tuổi'])
    expect(dong.find((d) => d.ten === 'bao_quan')!.khac).toBe(false)
  })

  it('coThayDoi bỏ qua khoảng trắng đầu cuối', () => {
    const goc = giaTriTuPhienBan(ban(1, 'nhap'))
    expect(coThayDoi({ ...goc, chi_dinh: '  Giảm đau  ' }, goc)).toBe(false)
    expect(coThayDoi({ ...goc, chi_dinh: 'Giảm đau mạnh' }, goc)).toBe(true)
    expect(coThayDoi({ ...goc, tre_em: 'Không dùng' }, goc)).toBe(true)
  })
})
