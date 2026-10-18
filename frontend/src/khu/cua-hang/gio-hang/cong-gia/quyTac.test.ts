import { describe, expect, it } from 'vitest'
import { dongHoDemNguoc, kiemTraThe } from './quyTac'

const THE = { soThe: '9704198526191432198', ten: 'NGUYEN VAN A', ngay: '07/15' }

describe('kiemTraThe', () => {
  it('đủ ba thông tin đúng thì hợp lệ, bỏ qua dấu cách trong số thẻ', () => {
    expect(kiemTraThe(THE)).toBe('hop_le')
    expect(kiemTraThe({ ...THE, soThe: '9704 1985 2619 1432 198' })).toBe('hop_le')
  })

  it('tên chủ thẻ không phân biệt dấu, hoa thường, khoảng trắng thừa', () => {
    expect(kiemTraThe({ ...THE, ten: '  nguyễn  văn a ' })).toBe('hop_le')
  })

  it('sai tên hoặc ngày phát hành là sai thông tin', () => {
    expect(kiemTraThe({ ...THE, ten: 'TRAN VAN B' })).toBe('sai_thong_tin')
    expect(kiemTraThe({ ...THE, ngay: '08/15' })).toBe('sai_thong_tin')
    expect(kiemTraThe({ ...THE, soThe: '1234' })).toBe('sai_thong_tin')
  })

  it('thẻ thử nghiệm không đủ số dư và chưa kích hoạt', () => {
    expect(kiemTraThe({ ...THE, soThe: '9704195798459170488' })).toBe('khong_du_so_du')
    expect(kiemTraThe({ ...THE, soThe: '9704192181368742' })).toBe('chua_kich_hoat')
  })
})

describe('dongHoDemNguoc', () => {
  it('định dạng mm:ss và không âm', () => {
    expect(dongHoDemNguoc(905)).toBe('15:05')
    expect(dongHoDemNguoc(59.9)).toBe('00:59')
    expect(dongHoDemNguoc(-3)).toBe('00:00')
  })
})
