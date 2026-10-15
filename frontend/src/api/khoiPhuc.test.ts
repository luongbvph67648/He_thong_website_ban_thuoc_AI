import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../stores/phien'

const GET = vi.fn()
vi.mock('./client', () => ({ api: { GET: (...tham_so: unknown[]) => GET(...tham_so) } }))
const lamMoiPhien = vi.fn()
vi.mock('./xacThuc', () => ({ lamMoiPhien: (...tham_so: unknown[]) => lamMoiPhien(...tham_so) }))

const HO_SO = { id: 7, ho_ten: 'Nguyễn Thị Mai', so_dien_thoai: '0912345678', email: null }

/** Mỗi test nạp lại module để có một "lần tải trang" mới (khoiPhucPhien chỉ chạy một lần mỗi lần tải). */
async function taiLaiModule() {
  vi.resetModules()
  const { usePhien: store } = await import('../stores/phien')
  const { khoiPhucPhien } = await import('./khoiPhuc')
  return { khoiPhucPhien, store }
}

describe('khoiPhucPhien', () => {
  beforeEach(() => {
    GET.mockReset()
    lamMoiPhien.mockReset()
    localStorage.clear()
    usePhien.getState().dangXuat()
  })

  it('không có gợi ý đăng nhập thì khách vãng lai không gọi API nào và coi như đã khôi phục xong', async () => {
    const { khoiPhucPhien, store } = await taiLaiModule()
    expect(store.getState().daKhoiPhuc).toBe(true)
    await khoiPhucPhien()
    expect(lamMoiPhien).not.toHaveBeenCalled()
    expect(GET).not.toHaveBeenCalled()
    expect(store.getState().loai).toBeNull()
  })

  it('có gợi ý khách: làm mới, lấy hồ sơ bằng token mới rồi đăng nhập vào store', async () => {
    localStorage.setItem('phien_goi_y', 'khach')
    lamMoiPhien.mockResolvedValue({ token: 'tok-moi', hetPhien: false })
    GET.mockResolvedValue({ data: HO_SO })
    const { khoiPhucPhien, store } = await taiLaiModule()
    expect(store.getState().daKhoiPhuc).toBe(false) // giao diện phải chờ, không nhấp nháy "Đăng nhập"

    await khoiPhucPhien()
    expect(lamMoiPhien).toHaveBeenCalledWith('khach')
    expect(GET).toHaveBeenCalledWith('/api/v1/toi', { headers: { Authorization: 'Bearer tok-moi' } })
    const p = store.getState()
    expect([p.daKhoiPhuc, p.loai, p.accessToken, p.hoSo]).toEqual([true, 'khach', 'tok-moi', { id: 7, hoTen: 'Nguyễn Thị Mai' }])
  })

  it('gọi nhiều lần (React StrictMode) chỉ làm mới đúng một lần: làm mới hai lần bằng một cookie sẽ bị đăng xuất khắp nơi', async () => {
    localStorage.setItem('phien_goi_y', 'khach')
    lamMoiPhien.mockResolvedValue({ token: 'tok', hetPhien: false })
    GET.mockResolvedValue({ data: HO_SO })
    const { khoiPhucPhien } = await taiLaiModule()
    await Promise.all([khoiPhucPhien(), khoiPhucPhien(), khoiPhucPhien()])
    expect(lamMoiPhien).toHaveBeenCalledTimes(1)
  })

  it('máy chủ nói phiên đã hết thì xóa gợi ý và vẫn là khách vãng lai', async () => {
    localStorage.setItem('phien_goi_y', 'khach')
    lamMoiPhien.mockResolvedValue({ token: null, hetPhien: true })
    const { khoiPhucPhien, store } = await taiLaiModule()
    await khoiPhucPhien()
    expect(localStorage.getItem('phien_goi_y')).toBeNull()
    expect(GET).not.toHaveBeenCalled()
    expect([store.getState().loai, store.getState().daKhoiPhuc]).toEqual([null, true])
  })

  it('lỗi mạng khi làm mới thì giữ gợi ý để lần tải sau thử lại', async () => {
    localStorage.setItem('phien_goi_y', 'khach')
    lamMoiPhien.mockResolvedValue({ token: null, hetPhien: false })
    const { khoiPhucPhien, store } = await taiLaiModule()
    await khoiPhucPhien()
    expect(localStorage.getItem('phien_goi_y')).toBe('khach')
    expect(store.getState().loai).toBeNull()
  })

  it('lấy hồ sơ thất bại (lỗi mạng hoặc lỗi API) thì không đăng nhập nửa vời', async () => {
    localStorage.setItem('phien_goi_y', 'khach')
    lamMoiPhien.mockResolvedValue({ token: 'tok', hetPhien: false })
    const { khoiPhucPhien, store } = await taiLaiModule()
    GET.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    await khoiPhucPhien()
    expect([store.getState().loai, store.getState().accessToken, store.getState().daKhoiPhuc]).toEqual([null, null, true])

    const lanSau = await taiLaiModule()
    GET.mockResolvedValueOnce({ error: { ma_loi: 'TAI_KHOAN_BI_KHOA', thong_diep: 'khóa', chi_tiet: null } })
    await lanSau.khoiPhucPhien()
    expect(lanSau.store.getState().loai).toBeNull()
  })

  it('gợi ý phiên nội bộ chưa được khôi phục ở T1.2: xóa gợi ý, không gọi API', async () => {
    localStorage.setItem('phien_goi_y', 'noi_bo')
    const { khoiPhucPhien, store } = await taiLaiModule()
    await khoiPhucPhien()
    expect(lamMoiPhien).not.toHaveBeenCalled()
    expect(localStorage.getItem('phien_goi_y')).toBeNull()
    expect(store.getState().daKhoiPhuc).toBe(true)
  })

  it('giá trị lạ trong gợi ý bị bỏ qua', async () => {
    localStorage.setItem('phien_goi_y', 'admin')
    const { khoiPhucPhien } = await taiLaiModule()
    await khoiPhucPhien()
    expect(lamMoiPhien).not.toHaveBeenCalled()
  })
})
