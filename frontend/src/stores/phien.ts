import { create } from 'zustand'
import { docGoiY, luuGoiY, xoaGoiY } from '../lib/goiYPhien'
import type { QuyenCuaToi } from '../lib/quyen'

export type LoaiPhien = 'khach' | 'noi_bo'

export interface HoSoPhien {
  id: number
  hoTen: string
  /** Mã vai trò (`PHARMACIST`, `WAREHOUSE`, `ADMIN`); chỉ có ở phiên nội bộ. */
  vaiTro?: string
  /** Chỉ phiên nội bộ có các trường dưới đây. */
  maNhanVien?: string
  email?: string
  soDienThoai?: string | null
}

interface TrangThaiPhien {
  accessToken: string | null
  loai: LoaiPhien | null
  hoSo: HoSoPhien | null
  quyen: QuyenCuaToi
  /** Nhân viên còn bị bắt đổi mật khẩu: mọi trang nội bộ chuyển tới trang tài khoản cho tới khi đổi xong. */
  phaiDoiMatKhau: boolean
  /** `false` khi đang thử lấy lại phiên lúc tải trang (`api/khoiPhuc.ts`); trang cần biết đã đăng nhập hay chưa phải chờ. */
  daKhoiPhuc: boolean
  dangNhap: (phien: {
    accessToken: string
    loai: LoaiPhien
    hoSo: HoSoPhien
    quyen: QuyenCuaToi
    phaiDoiMatKhau?: boolean
  }) => void
  datToken: (accessToken: string) => void
  /** Cập nhật một phần hồ sơ (ví dụ sau khi sửa họ tên), giữ nguyên token và quyền. */
  capNhatHoSo: (hoSo: Partial<HoSoPhien>) => void
  dangXuat: () => void
}

const TRONG = { accessToken: null, loai: null, hoSo: null, quyen: {}, phaiDoiMatKhau: false } as const

/**
 * Phiên đăng nhập, CHỈ giữ trong bộ nhớ (không persist): access token sống 15 phút và được lấy lại từ refresh token
 * (cookie httpOnly) khi tải lại trang; không để token hay hồ sơ trong localStorage. Ngoại lệ duy nhất là "gợi ý" loại
 * phiên (`lib/goiYPhien.ts`) để biết có cần thử lấy lại phiên hay không.
 */
export const usePhien = create<TrangThaiPhien>()((set) => ({
  ...TRONG,
  daKhoiPhuc: docGoiY() === null,
  dangNhap: ({ accessToken, loai, hoSo, quyen, phaiDoiMatKhau = false }) => {
    luuGoiY(loai)
    set({ accessToken, loai, hoSo, quyen, phaiDoiMatKhau })
  },
  datToken: (accessToken) => set({ accessToken }),
  capNhatHoSo: (hoSo) => set((s) => (s.hoSo ? { hoSo: { ...s.hoSo, ...hoSo } } : {})),
  dangXuat: () => {
    xoaGoiY()
    set({ ...TRONG })
  },
}))
