import { describe, expect, it } from 'vitest'
import dayjs from '../../../lib/dayjs'
import { chia, congTien, dsViec, khoangMau, kyTruoc, mauCuaKhoang, phanTram, soNgay, thamSoKy, thayDoi, tienNgan } from './tongQuan'

const ngay = (s: string) => dayjs(s)
const tien = (s: string) => `${s} ₫`

describe('kỳ báo cáo', () => {
  it('mẫu kỳ tính từ hôm nay, gồm cả hai đầu', () => {
    const hn = ngay('2026-10-19')
    expect(thamSoKy(khoangMau('hom_nay', hn))).toEqual({ tu_ngay: '2026-10-19', den_ngay: '2026-10-19' })
    expect(thamSoKy(khoangMau('7_ngay', hn))).toEqual({ tu_ngay: '2026-10-13', den_ngay: '2026-10-19' })
    expect(thamSoKy(khoangMau('30_ngay', hn))).toEqual({ tu_ngay: '2026-09-20', den_ngay: '2026-10-19' })
    expect(thamSoKy(khoangMau('thang_nay', hn))).toEqual({ tu_ngay: '2026-10-01', den_ngay: '2026-10-19' })
  })

  it('kỳ trước cùng số ngày, kết thúc ngay trước ngày đầu kỳ', () => {
    const k = khoangMau('7_ngay', ngay('2026-10-19'))
    expect(soNgay(k)).toBe(7)
    expect(thamSoKy(kyTruoc(k))).toEqual({ tu_ngay: '2026-10-06', den_ngay: '2026-10-12' })
    expect(thamSoKy(kyTruoc(khoangMau('hom_nay', ngay('2026-03-01'))))).toEqual({ tu_ngay: '2026-02-28', den_ngay: '2026-02-28' })
  })

  it('nhận ra mẫu kỳ đang chọn, khoảng tự chọn thì không', () => {
    const hn = ngay('2026-10-19')
    expect(mauCuaKhoang(khoangMau('7_ngay', hn), hn)).toBe('7_ngay')
    expect(mauCuaKhoang([ngay('2026-10-02'), ngay('2026-10-05')], hn)).toBeUndefined()
  })
})

describe('so sánh và định dạng', () => {
  it('thay đổi so với kỳ trước; kỳ trước bằng 0 hoặc thiếu thì không so', () => {
    expect(thayDoi('1250000.00', '1000000.00')).toBeCloseTo(0.25)
    expect(thayDoi(8, 10)).toBeCloseTo(-0.2)
    expect(thayDoi('100.00', '0.00')).toBeNull()
    expect(thayDoi(5, undefined)).toBeNull()
  })

  it('chia an toàn và phần trăm kiểu Việt Nam', () => {
    expect(chia('300', '1200')).toBe(0.25)
    expect(chia(1, 0)).toBeNull()
    expect(phanTram(0.1234)).toBe('12,3%')
    expect(phanTram(null)).toBe('—')
  })

  it('cộng tiền dạng chuỗi không qua float', () => {
    expect(congTien(['0.10', '0.20'])).toBe('0.30')
    expect(congTien(['125000.00', '9999999999999999.99', '1'])).toBe('10000000000125000.99')
    expect(congTien([])).toBe('0.00')
  })

  it('rút gọn tiền cho trục biểu đồ', () => {
    expect(tienNgan(1_250_000)).toBe('1,3 tr')
    expect(tienNgan(25_000)).toBe('25 N')
    expect(tienNgan(2_000_000_000)).toBe('2,0 tỷ')
    expect(tienNgan(0)).toBe('0')
  })
})

describe('việc cần xử lý', () => {
  it('việc gấp còn tồn lên trước, rồi việc cần chú ý, việc bằng 0 xuống cuối', () => {
    const ds = dsViec({ phieuChoDuyet: 0, hoanTien: { so: 2, tongTien: '300000.00', thieuTaiKhoan: 1 }, tonThap: 5, loCanHan: 9, loHetHan: 1, aiGanCo: 0 }, tien)
    expect(ds.map((v) => v.khoa)).toEqual(['hoan-tien', 'het-han', 'can-han', 'ton-thap', 'phieu', 'ai'])
    expect(ds[0]!.moTa).toBe('Tổng 300000.00 ₫ · 1 khoản khách chưa gửi tài khoản')
  })

  it('nguồn chưa tải hoặc không có quyền thì không hiện, để khỏi báo ổn sai', () => {
    expect(dsViec({}, tien)).toEqual([])
    expect(dsViec({ phieuChoDuyet: 3 }, tien).map((v) => [v.khoa, v.so, v.duong])).toEqual([['phieu', 3, '/duyet-phieu']])
  })

  it('đơn giao thất bại dẫn tới danh sách đơn đã lọc sẵn', () => {
    expect(dsViec({ donGiaoThatBai: 2 }, tien)[0]!.duong).toBe('/xem/don-hang?trang_thai=giao_that_bai')
  })
})
