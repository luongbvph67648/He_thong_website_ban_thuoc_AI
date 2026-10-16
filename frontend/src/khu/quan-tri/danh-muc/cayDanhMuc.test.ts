import { describe, expect, it } from 'vitest'
import { chieuCao, giuNguyenViTri, idCoCon, lyDoKhongThaDuoc, namTrongCayCon, timNut, tinhViTriTha, type NutCay } from './cayDanhMuc'

const nut = (id: number, con: NutCay[] = []): NutCay => ({ id, ten: `D${id}`, con })

/**
 * 1 Thuốc
 *   2 Giảm đau
 *     3 Paracetamol
 *   4 Ho
 * 5 Thực phẩm chức năng
 *   6 Vitamin
 * 7 Dụng cụ
 */
const cay = (): NutCay[] => [nut(1, [nut(2, [nut(3)]), nut(4)]), nut(5, [nut(6)]), nut(7)]

describe('timNut, chieuCao, namTrongCayCon, idCoCon', () => {
  it('tìm nút kèm cha và cấp', () => {
    expect(timNut(cay(), 3)).toMatchObject({ cap: 3, cha: { id: 2 }, nut: { id: 3 } })
    expect(timNut(cay(), 7)).toMatchObject({ cap: 1, cha: null })
    expect(timNut(cay(), 99)).toBeNull()
  })
  it('chiều cao cây con tính cả chính nó', () => {
    expect(chieuCao(nut(7))).toBe(1)
    expect(chieuCao(cay()[0])).toBe(3)
    expect(chieuCao(cay()[1])).toBe(2)
  })
  it('một nút nằm trong cây con của chính nó và của tổ tiên, không nằm trong nhánh khác', () => {
    const [thuoc, tpcn] = cay()
    expect(namTrongCayCon(thuoc, 1)).toBe(true)
    expect(namTrongCayCon(thuoc, 3)).toBe(true)
    expect(namTrongCayCon(thuoc, 6)).toBe(false)
    expect(namTrongCayCon(tpcn, 3)).toBe(false)
  })
  it('liệt kê id có con để mở sẵn', () => {
    expect(idCoCon(cay())).toEqual([1, 2, 5])
  })
})

describe('tinhViTriTha', () => {
  it('thả trước/sau một nút gốc: cùng cha (gốc), chỉ số trong các anh em đã bỏ nút kéo', () => {
    expect(tinhViTriTha(cay(), 7, 1, 'truoc')).toEqual({ chaId: null, viTri: 0 })
    expect(tinhViTriTha(cay(), 7, 1, 'sau')).toEqual({ chaId: null, viTri: 1 })
    expect(tinhViTriTha(cay(), 7, 5, 'sau')).toEqual({ chaId: null, viTri: 2 })
  })
  it('kéo trong cùng một cấp không đếm chính nút kéo: kéo 1 xuống sau 5 -> chỉ số 1 trong [5, 7]', () => {
    expect(tinhViTriTha(cay(), 1, 5, 'sau')).toEqual({ chaId: null, viTri: 1 })
    expect(tinhViTriTha(cay(), 1, 7, 'sau')).toEqual({ chaId: null, viTri: 2 })
    expect(tinhViTriTha(cay(), 7, 5, 'truoc')).toEqual({ chaId: null, viTri: 1 })
  })
  it('thả vào trong: thành con cuối của đích', () => {
    expect(tinhViTriTha(cay(), 7, 5, 'trong')).toEqual({ chaId: 5, viTri: 1 })
    expect(tinhViTriTha(cay(), 7, 1, 'trong')).toEqual({ chaId: 1, viTri: 2 })
    expect(tinhViTriTha(cay(), 4, 1, 'trong')).toEqual({ chaId: 1, viTri: 1 }) // 4 đã là con của 1: bỏ nó ra thì còn 1 anh em
  })
  it('thả cạnh nút ở cấp sâu: cha là cha của nút đích', () => {
    expect(tinhViTriTha(cay(), 7, 2, 'sau')).toEqual({ chaId: 1, viTri: 1 })
    expect(tinhViTriTha(cay(), 7, 3, 'truoc')).toEqual({ chaId: 2, viTri: 0 })
  })
  it('kéo vào chính nó hoặc id không có trong cây là null', () => {
    expect(tinhViTriTha(cay(), 1, 1, 'trong')).toBeNull()
    expect(tinhViTriTha(cay(), 99, 1, 'sau')).toBeNull()
    expect(tinhViTriTha(cay(), 1, 99, 'sau')).toBeNull()
  })
})

describe('lyDoKhongThaDuoc', () => {
  it('cho phép chuyển hợp lệ', () => {
    expect(lyDoKhongThaDuoc(cay(), 7, 5, 'trong')).toBeNull() // lá vào cấp 1 -> cấp 2
    expect(lyDoKhongThaDuoc(cay(), 7, 2, 'trong')).toBeNull() // lá vào cấp 2 -> cấp 3
    expect(lyDoKhongThaDuoc(cay(), 3, 5, 'sau')).toBeNull() // lá cấp 3 ra gốc
    expect(lyDoKhongThaDuoc(cay(), 2, 5, 'trong')).toBeNull() // nhánh cao 2 vào cấp 1: cao nhất cấp 3
  })
  it('chặn thả vào chính nó và vào cây con của nó (vòng)', () => {
    expect(lyDoKhongThaDuoc(cay(), 1, 1, 'trong')).toMatch(/chính nó/)
    expect(lyDoKhongThaDuoc(cay(), 1, 2, 'trong')).toMatch(/danh mục con/)
    expect(lyDoKhongThaDuoc(cay(), 1, 3, 'trong')).toMatch(/danh mục con/)
    expect(lyDoKhongThaDuoc(cay(), 1, 3, 'sau')).toMatch(/danh mục con/) // cạnh cháu = vào con của chính nó
    expect(lyDoKhongThaDuoc(cay(), 2, 3, 'truoc')).toMatch(/danh mục con/)
  })
  it('chặn vượt 3 cấp, tính cả cây con mang theo', () => {
    expect(lyDoKhongThaDuoc(cay(), 7, 3, 'trong')).toMatch(/tối đa 3 cấp/) // vào cấp 3 -> cấp 4
    expect(lyDoKhongThaDuoc(cay(), 5, 2, 'trong')).toMatch(/tối đa 3 cấp/) // nhánh cao 2 vào cấp 2 -> cấp 4
    expect(lyDoKhongThaDuoc(cay(), 1, 6, 'trong')).toMatch(/tối đa 3 cấp/) // nhánh cao 3 vào đâu cũng tràn
    expect(lyDoKhongThaDuoc(cay(), 1, 7, 'trong')).toMatch(/tối đa 3 cấp/)
    expect(lyDoKhongThaDuoc(cay(), 1, 5, 'sau')).toBeNull() // cạnh một nút gốc vẫn là gốc
  })
  it('id không có trong cây', () => {
    expect(lyDoKhongThaDuoc(cay(), 99, 1, 'trong')).toMatch(/Không tìm thấy/)
  })
})

describe('giuNguyenViTri', () => {
  it('nhận ra thả đúng chỗ cũ (kể cả thả cạnh anh em liền kề theo hướng không đổi thứ tự)', () => {
    const c = cay()
    expect(giuNguyenViTri(c, 5, { chaId: null, viTri: 1 })).toBe(true)
    expect(giuNguyenViTri(c, 5, { chaId: null, viTri: 0 })).toBe(false)
    expect(giuNguyenViTri(c, 4, { chaId: 1, viTri: 1 })).toBe(true)
    expect(giuNguyenViTri(c, 4, { chaId: null, viTri: 1 })).toBe(false) // khác cha
    expect(giuNguyenViTri(c, 7, { chaId: null, viTri: 99 })).toBe(true) // chỉ số lớn hơn số anh em bị kẹp về cuối
    expect(giuNguyenViTri(c, 99, { chaId: null, viTri: 0 })).toBe(false)
  })
})
