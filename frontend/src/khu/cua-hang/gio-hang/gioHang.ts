import { useQueryClient, useQuery } from '@tanstack/react-query'
import { App } from 'antd'
import { useEffect, useRef } from 'react'
import { create } from 'zustand'
import { api } from '../../../api/client'
import { laLoiApi } from '../../../api/loi'
import type { components } from '../../../api/schema'
import { usePhien } from '../../../stores/phien'

export type GioHangRa = components['schemas']['GioHangRa']
export type DongGio = components['schemas']['DongGio']
export interface DongCucBo {
  san_pham_id: number
  don_vi_id: number
  so_luong: number
}

/** Giỏ của khách vãng lai ở localStorage (KVL07): chỉ id và số lượng, giá và tên luôn lấy mới từ máy chủ. */
const KHOA = 'gio_hang_khach'
export const SO_LUONG_TOI_DA = 9999

export function docGioCucBo(): DongCucBo[] {
  try {
    const goc: unknown = JSON.parse(globalThis.localStorage.getItem(KHOA) ?? '[]')
    if (!Array.isArray(goc)) return []
    return goc.filter(
      (d): d is DongCucBo =>
        typeof d === 'object' && d !== null && Number.isInteger(d.san_pham_id) && Number.isInteger(d.don_vi_id) && Number.isInteger(d.so_luong) && d.so_luong >= 1,
    ).slice(0, 100)
  } catch {
    return []
  }
}

function luuGioCucBo(dong: DongCucBo[]) {
  try {
    globalThis.localStorage.setItem(KHOA, JSON.stringify(dong))
  } catch {
    // trình duyệt chặn lưu trữ: giỏ chỉ sống trong phiên trang
  }
}

interface KhoGioCucBo {
  dong: DongCucBo[]
  them: (d: DongCucBo) => void
  datSoLuong: (spId: number, dvId: number, soLuong: number) => void
  doiDonVi: (spId: number, tu: number, den: number) => void
  xoa: (spId: number, dvId: number) => void
  lamRong: () => void
}

/** Cộng dồn dòng cùng (sản phẩm, đơn vị), cắt ở mức tối đa mỗi dòng. */
export function themVaoDanhSach(ds: DongCucBo[], d: DongCucBo): DongCucBo[] {
  const co = ds.find((x) => x.san_pham_id === d.san_pham_id && x.don_vi_id === d.don_vi_id)
  if (!co) return [...ds, { ...d, so_luong: Math.min(d.so_luong, SO_LUONG_TOI_DA) }]
  return ds.map((x) => (x === co ? { ...x, so_luong: Math.min(x.so_luong + d.so_luong, SO_LUONG_TOI_DA) } : x))
}

export const useGioCucBo = create<KhoGioCucBo>()((set, get) => {
  const dat = (dong: DongCucBo[]) => {
    luuGioCucBo(dong)
    set({ dong })
  }
  return {
    dong: docGioCucBo(),
    them: (d) => dat(themVaoDanhSach(get().dong, d)),
    datSoLuong: (sp, dv, sl) => dat(get().dong.map((x) => (x.san_pham_id === sp && x.don_vi_id === dv ? { ...x, so_luong: sl } : x))),
    doiDonVi: (sp, tu, den) => {
      const dong = get().dong
      const dong_tu = dong.find((x) => x.san_pham_id === sp && x.don_vi_id === tu)
      if (!dong_tu) return
      dat(themVaoDanhSach(dong.filter((x) => x !== dong_tu), { ...dong_tu, don_vi_id: den }))
    },
    xoa: (sp, dv) => dat(get().dong.filter((x) => !(x.san_pham_id === sp && x.don_vi_id === dv))),
    lamRong: () => dat([]),
  }
})

export const KHOA_GIO_HANG = ['gio-hang'] as const
const TRONG: GioHangRa = { dong: [], tam_tinh: '0.00', tong_so_luong: 0 }

/** Thông điệp lỗi của API (hoặc câu mặc định) để hiện cho người dùng. */
function thongDiep(loi: unknown, macDinh: string): string {
  return laLoiApi(loi) ? loi.thong_diep : macDinh
}

/**
 * Giỏ hàng hiện tại: khách thành viên đọc/ghi ở máy chủ, khách vãng lai giữ ở localStorage và nhờ máy chủ dựng lại
 * (tên, giá, cờ mua được). Các hàm hành động trả `null` khi thành công, hoặc thông điệp lỗi.
 */
export function useGioHang() {
  const qc = useQueryClient()
  const thanhVien = usePhien((s) => s.loai === 'khach')
  const cucBo = useGioCucBo((s) => s.dong)
  const khoa = thanhVien ? [...KHOA_GIO_HANG, 'thanh-vien'] : [...KHOA_GIO_HANG, 'vang-lai', cucBo]
  const q = useQuery({
    queryKey: khoa,
    queryFn: async (): Promise<GioHangRa> => {
      if (thanhVien) {
        const { data, error } = await api.GET('/api/v1/toi/gio-hang')
        if (error || !data) throw error ?? new Error('Không tải được giỏ hàng')
        return data
      }
      if (cucBo.length === 0) return TRONG
      const { data, error } = await api.POST('/api/v1/gio-hang/xem', { body: { dong: cucBo } })
      if (error || !data) throw error ?? new Error('Không tải được giỏ hàng')
      return data
    },
    placeholderData: (truoc) => truoc,
  })

  const capNhat = (gio: GioHangRa) => qc.setQueryData(['gio-hang', 'thanh-vien'], gio)

  async function goi(
    viec: () => Promise<{ data?: GioHangRa; error?: unknown }>,
    macDinh: string,
  ): Promise<string | null> {
    const { data, error } = await viec()
    if (error || !data) return thongDiep(error, macDinh)
    capNhat(data)
    return null
  }

  return {
    gio: q.data ?? TRONG,
    dangTai: q.isLoading,
    loi: q.isError,
    thanhVien,
    them: async (d: DongCucBo): Promise<string | null> => {
      if (!thanhVien) {
        useGioCucBo.getState().them(d)
        return null
      }
      return goi(() => api.POST('/api/v1/toi/gio-hang/dong', { body: d }), 'Không thêm được vào giỏ hàng')
    },
    datSoLuong: async (dong: DongGio, soLuong: number): Promise<string | null> => {
      if (!thanhVien || dong.dong_id === null || !dong.don_vi) {
        useGioCucBo.getState().datSoLuong(dong.san_pham.id, dong.don_vi?.id ?? 0, soLuong)
        return null
      }
      return goi(() => api.PUT('/api/v1/toi/gio-hang/dong/{dong_id}', { params: { path: { dong_id: dong.dong_id! } }, body: { so_luong: soLuong } }), 'Không đổi được số lượng')
    },
    doiDonVi: async (dong: DongGio, donViId: number): Promise<string | null> => {
      if (!thanhVien || dong.dong_id === null || !dong.don_vi) {
        useGioCucBo.getState().doiDonVi(dong.san_pham.id, dong.don_vi?.id ?? 0, donViId)
        return null
      }
      return goi(() => api.PUT('/api/v1/toi/gio-hang/dong/{dong_id}', { params: { path: { dong_id: dong.dong_id! } }, body: { don_vi_id: donViId } }), 'Không đổi được đơn vị')
    },
    xoa: async (dong: DongGio): Promise<string | null> => {
      if (!thanhVien || dong.dong_id === null || !dong.don_vi) {
        useGioCucBo.getState().xoa(dong.san_pham.id, dong.don_vi?.id ?? 0)
        return null
      }
      return goi(() => api.DELETE('/api/v1/toi/gio-hang/dong/{dong_id}', { params: { path: { dong_id: dong.dong_id! } } }), 'Không xóa được dòng')
    },
  }
}

/** Khi khách đăng nhập (kể cả lấy lại phiên lúc tải trang): gộp giỏ localStorage vào giỏ tài khoản một lần. */
export function useGopGioKhiDangNhap() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const thanhVien = usePhien((s) => s.loai === 'khach')
  const daKhoiPhuc = usePhien((s) => s.daKhoiPhuc)
  const dangGop = useRef(false)
  useEffect(() => {
    if (!thanhVien || !daKhoiPhuc || dangGop.current) return
    const dong = useGioCucBo.getState().dong
    if (dong.length === 0) return
    dangGop.current = true
    void (async () => {
      try {
        const { data } = await api.PUT('/api/v1/toi/gio-hang/gop', { body: { dong } })
        if (!data) return // giữ nguyên giỏ localStorage, lần sau thử lại
        useGioCucBo.getState().lamRong()
        qc.setQueryData(['gio-hang', 'thanh-vien'], data.gio_hang)
        if (data.bo_qua.length > 0) message.warning(`${data.bo_qua.length} sản phẩm trong giỏ cũ không thêm được (hết hiệu lực hoặc vượt giới hạn mua).`)
      } catch {
        // lỗi mạng: giữ giỏ localStorage, lần sau thử lại
      } finally {
        dangGop.current = false
      }
    })()
  }, [thanhVien, daKhoiPhuc, qc, message])
}
