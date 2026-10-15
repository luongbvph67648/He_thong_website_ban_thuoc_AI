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

  describe('phiên nhân viên', () => {
    const NHAN_VIEN = {
      id: 3,
      ma_nhan_vien: 'NV0003',
      ho_ten: 'Trần Văn Kho',
      email: 'kho@example.com',
      so_dien_thoai: null,
      vai_tro: { ma: 'WAREHOUSE', ten: 'Nhân viên kho' },
      phai_doi_mat_khau: false,
      quyen: { 'profile.self': 'day_du', 'order.view': 'chi_xem' },
    }

    it('làm mới bằng endpoint nội bộ, lấy /noi-bo/toi rồi đăng nhập kèm quyền và vai trò', async () => {
      localStorage.setItem('phien_goi_y', 'noi_bo')
      lamMoiPhien.mockResolvedValue({ token: 'tok-nv', hetPhien: false })
      GET.mockResolvedValue({ data: NHAN_VIEN })
      const { khoiPhucPhien, store } = await taiLaiModule()
      await khoiPhucPhien()
      expect(lamMoiPhien).toHaveBeenCalledWith('noi_bo')
      expect(GET).toHaveBeenCalledWith('/api/v1/noi-bo/toi', { headers: { Authorization: 'Bearer tok-nv' } })
      const p = store.getState()
      expect([p.loai, p.accessToken, p.phaiDoiMatKhau]).toEqual(['noi_bo', 'tok-nv', false])
      expect(p.hoSo).toMatchObject({ id: 3, hoTen: 'Trần Văn Kho', vaiTro: 'WAREHOUSE', email: 'kho@example.com' })
      expect(p.quyen).toEqual({ 'profile.self': 'day_du', 'order.view': 'chi_xem' })
    })

    it('khôi phục cả cờ bắt đổi mật khẩu để tải lại trang không thoát được việc đổi mật khẩu', async () => {
      localStorage.setItem('phien_goi_y', 'noi_bo')
      lamMoiPhien.mockResolvedValue({ token: 'tok-nv', hetPhien: false })
      GET.mockResolvedValue({ data: { ...NHAN_VIEN, phai_doi_mat_khau: true } })
      const { khoiPhucPhien, store } = await taiLaiModule()
      await khoiPhucPhien()
      expect(store.getState().phaiDoiMatKhau).toBe(true)
    })

    it('phiên đã hết thì xóa gợi ý; lỗi mạng thì giữ gợi ý', async () => {
      localStorage.setItem('phien_goi_y', 'noi_bo')
      lamMoiPhien.mockResolvedValue({ token: null, hetPhien: true })
      await (await taiLaiModule()).khoiPhucPhien()
      expect(localStorage.getItem('phien_goi_y')).toBeNull()

      localStorage.setItem('phien_goi_y', 'noi_bo')
      lamMoiPhien.mockResolvedValue({ token: null, hetPhien: false })
      await (await taiLaiModule()).khoiPhucPhien()
      expect(localStorage.getItem('phien_goi_y')).toBe('noi_bo')
    })

    it('tài khoản bị khóa khi lấy hồ sơ thì không đăng nhập nửa vời', async () => {
      localStorage.setItem('phien_goi_y', 'noi_bo')
      lamMoiPhien.mockResolvedValue({ token: 'tok-nv', hetPhien: false })
      GET.mockResolvedValue({ error: { ma_loi: 'TAI_KHOAN_BI_KHOA', thong_diep: 'khóa', chi_tiet: null } })
      const { khoiPhucPhien, store } = await taiLaiModule()
      await khoiPhucPhien()
      expect([store.getState().loai, store.getState().daKhoiPhuc]).toEqual([null, true])
    })
  })

  it('giá trị lạ trong gợi ý bị bỏ qua', async () => {
    localStorage.setItem('phien_goi_y', 'admin')
    const { khoiPhucPhien } = await taiLaiModule()
    await khoiPhucPhien()
    expect(lamMoiPhien).not.toHaveBeenCalled()
  })
})
