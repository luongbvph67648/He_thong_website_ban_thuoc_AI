import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { nhanTrangThai, TRANG_THAI } from './trangThai'

/** Các giá trị của một enum trong `schema.d.ts` (sinh từ OpenAPI): `TenEnum: "a" | "b";`. */
function giaTriEnum(ten: string): string[] {
  const van_ban = readFileSync(resolve(__dirname, '../api/schema.d.ts'), 'utf8')
  const khop = new RegExp(`\\n\\s+${ten}: ([^;]+);`).exec(van_ban)
  if (!khop) throw new Error(`Không thấy enum ${ten} trong schema.d.ts`)
  return [...khop[1].matchAll(/"([^"]+)"/g)].map((m) => m[1])
}

describe('trangThai', () => {
  it.each([
    ['don_hang', 'TrangThaiDon'],
    ['thanh_toan', 'TrangThaiThanhToan'],
    ['kenh_ban', 'KenhBan'],
    ['loai_san_pham', 'LoaiSanPham'],
    ['kinh_doanh', 'TrangThaiKinhDoanh'],
    ['noi_dung', 'TrangThaiNoiDung'],
    ['muc_do_tuong_tac', 'MucDoTuongTac'],
  ] as const)('bảng nhãn %s khớp từng giá trị enum %s của API (thêm giá trị mới mà quên nhãn thì test báo)', (loai, ten) => {
    expect(Object.keys(TRANG_THAI[loai]).sort()).toEqual(giaTriEnum(ten).sort())
  })

  it('mọi nhãn là tiếng Việt có chữ và có màu', () => {
    for (const bang of Object.values(TRANG_THAI)) {
      for (const [giaTri, { nhan, mau }] of Object.entries(bang)) {
        expect(nhan.trim(), giaTri).not.toBe('')
        expect(nhan, giaTri).not.toMatch(/_/) // không để lộ mã kỹ thuật
        expect(mau, giaTri).not.toBe('')
      }
    }
  })

  it('giá trị lạ (backend thêm trạng thái mới) hiện nguyên giá trị với màu mặc định, không ném lỗi', () => {
    expect(nhanTrangThai('don_hang', 'trang_thai_moi')).toEqual({ nhan: 'trang_thai_moi', mau: 'default' })
    expect(nhanTrangThai('don_hang', null)).toEqual({ nhan: '—', mau: 'default' })
  })

  it('nhãn đúng với spec 04', () => {
    expect(nhanTrangThai('don_hang', 'cho_khach_xac_nhan').nhan).toBe('Chờ khách xác nhận')
    expect(nhanTrangThai('don_hang', 'hoan_ve_kho').nhan).toBe('Hoàn về kho')
    expect(nhanTrangThai('don_hang', 'da_huy').nhan).toBe('Đã hủy')
    expect(nhanTrangThai('thanh_toan', 'cho_hoan_tien').nhan).toBe('Chờ hoàn tiền')
    expect(nhanTrangThai('kenh_ban', 'tai_quay').nhan).toBe('Tại quầy')
  })
})
