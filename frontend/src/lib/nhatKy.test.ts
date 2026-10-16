import { describe, expect, it } from 'vitest'
import { BANG_SUC_KHOE, nhanHanhDong, soSanhGiaTri } from './nhatKy'

describe('nhanHanhDong', () => {
  it('đổi mã hành động đã biết sang tiếng Việt, mã lạ giữ nguyên', () => {
    expect(nhanHanhDong('sua')).toBe('Sửa')
    expect(nhanHanhDong('mo_khoa')).toBe('Mở khóa')
    expect(nhanHanhDong('doc_suc_khoe')).toBe('Đọc dữ liệu sức khỏe')
    expect(nhanHanhDong('hanh_dong_moi')).toBe('hanh_dong_moi')
  })
})

describe('soSanhGiaTri', () => {
  it('đối tượng: so từng trường, trường đổi được đánh dấu, thứ tự theo tên', () => {
    expect(soSanhGiaTri({ b: 1, a: 'x', c: 3 }, { a: 'y', b: 1, d: 4 })).toEqual([
      { truong: 'a', cu: 'x', moi: 'y', doi: true },
      { truong: 'b', cu: 1, moi: 1, doi: false },
      { truong: 'c', cu: 3, moi: undefined, doi: true },
      { truong: 'd', cu: undefined, moi: 4, doi: true },
    ])
  })
  it('giá trị không phải đối tượng: một dòng không tên trường', () => {
    expect(soSanhGiaTri(5, 3)).toEqual([{ truong: null, cu: 5, moi: 3, doi: true }])
    expect(soSanhGiaTri(null, 3)).toEqual([{ truong: null, cu: undefined, moi: 3, doi: true }])
    expect(soSanhGiaTri(null, null)).toEqual([])
  })
  it('đối tượng so với giá trị khác kiểu thì coi như một dòng', () => {
    expect(soSanhGiaTri({ a: 1 }, 5)).toEqual([{ truong: null, cu: { a: 1 }, moi: 5, doi: true }])
  })
  it('danh sách và đối tượng lồng nhau so sánh theo nội dung', () => {
    const [dong] = soSanhGiaTri({ ds: [1, 2] }, { ds: [1, 2] })
    expect(dong.doi).toBe(false)
  })
})

describe('BANG_SUC_KHOE', () => {
  it('khớp các bảng backend không bao giờ ghi giá trị', () => {
    expect([...BANG_SUC_KHOE].sort()).toEqual(['di_ung', 'ho_so_suc_khoe'])
  })
})
