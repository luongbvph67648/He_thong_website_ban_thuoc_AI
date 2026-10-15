import { create } from 'zustand'
import { docGoiY, luuGoiY, xoaGoiY } from '../lib/goiYPhien'
import type { QuyenCuaToi } from '../lib/quyen'

export type LoaiPhien = 'khach' | 'noi_bo'

export interface HoSoPhien {
  id: number
  hoTen: string
  /** Mã vai trò (`PHARMACIST`, `WAREHOUSE`, `ADMIN`); chỉ có ở phiên nội bộ. */
  vaiTro?: string
}

interface TrangThaiPhien {
  accessToken: string | null
  loai: LoaiPhien | null
  hoSo: HoSoPhien | null
  quyen: QuyenCuaToi
  /** `false` khi đang thử lấy lại phiên lúc tải trang (`api/khoiPhuc.ts`); trang cần biết đã đăng nhập hay chưa phải chờ. */
  daKhoiPhuc: boolean
  dangNhap: (phien: { accessToken: string; loai: LoaiPhien; hoSo: HoSoPhien; quyen: QuyenCuaToi }) => void
  datToken: (accessToken: string) => void
  dangXuat: () => void
}

const TRONG = { accessToken: null, loai: null, hoSo: null, quyen: {} } as const

/**
 * Phiên đăng nhập, CHỈ giữ trong bộ nhớ (không persist): access token sống 15 phút và được lấy lại từ refresh token
 * (cookie httpOnly) khi tải lại trang; không để token hay hồ sơ trong localStorage. Ngoại lệ duy nhất là "gợi ý" loại
 * phiên (`lib/goiYPhien.ts`) để biết có cần thử lấy lại phiên hay không.
 */
export const usePhien = create<TrangThaiPhien>()((set) => ({
  ...TRONG,
  daKhoiPhuc: docGoiY() === null,
  dangNhap: ({ accessToken, loai, hoSo, quyen }) => {
    luuGoiY(loai)
    set({ accessToken, loai, hoSo, quyen })
  },
  datToken: (accessToken) => set({ accessToken }),
  dangXuat: () => {
    xoaGoiY()
    set({ ...TRONG })
  },
}))
