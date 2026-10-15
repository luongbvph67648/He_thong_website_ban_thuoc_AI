import { create } from 'zustand'
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
  dangNhap: (phien: { accessToken: string; loai: LoaiPhien; hoSo: HoSoPhien; quyen: QuyenCuaToi }) => void
  datToken: (accessToken: string) => void
  dangXuat: () => void
}

const TRONG = { accessToken: null, loai: null, hoSo: null, quyen: {} } as const

/**
 * Phiên đăng nhập, CHỈ giữ trong bộ nhớ (không persist): access token sống 15 phút và được lấy lại từ refresh token
 * (cookie httpOnly) khi tải lại trang; không để token hay hồ sơ trong localStorage.
 */
export const usePhien = create<TrangThaiPhien>()((set) => ({
  ...TRONG,
  dangNhap: ({ accessToken, loai, hoSo, quyen }) => set({ accessToken, loai, hoSo, quyen }),
  datToken: (accessToken) => set({ accessToken }),
  dangXuat: () => set({ ...TRONG }),
}))
