import { api } from '../../../api/client'
import { goi, type KetQuaGoi } from '../../../api/goi'
import { chuoiHoacNull, gonTen } from '../../../lib/duLieuChung'
import type { BanGhi, GiaTriForm, MaNhom, MaNhomXoa } from './nhom'

export interface ThamSoDanhSach {
  q?: string
  sap_xep?: string
  trang: number
  kich_thuoc: number
}

interface TrangBanGhi {
  du_lieu: BanGhi[]
  tong: number
}

/** Ép kết quả của từng nhóm về dạng chung (các schema khác nhau ở trường riêng của nhóm). */
const chung = <T>(kq: KetQuaGoi<unknown>) => kq as KetQuaGoi<T>

/** Gọi API của ba nhóm qua cùng một giao diện; mỗi nhánh giữ nguyên kiểu từ `schema.d.ts`. */
export function danhSach(ma: MaNhom, query: ThamSoDanhSach): Promise<KetQuaGoi<TrangBanGhi>> {
  const params = { params: { query } }
  switch (ma) {
    case 'thuong-hieu':
      return goi(() => api.GET('/api/v1/noi-bo/thuong-hieu', params)).then((k) => chung<TrangBanGhi>(k))
    case 'nha-san-xuat':
      return goi(() => api.GET('/api/v1/noi-bo/nha-san-xuat', params)).then((k) => chung<TrangBanGhi>(k))
    case 'hoat-chat':
      return goi(() => api.GET('/api/v1/noi-bo/hoat-chat', params)).then((k) => chung<TrangBanGhi>(k))
  }
}

/** Body gửi lên cho POST/PATCH: ô trống thành `null` (PATCH: xóa giá trị; POST: không có). */
function thanBody(ma: MaNhom, g: GiaTriForm) {
  const ten = gonTen(g.ten)
  switch (ma) {
    case 'thuong-hieu':
      return { ten, logo_url: chuoiHoacNull(g.logo_url) }
    case 'nha-san-xuat':
      return { ten, quoc_gia: chuoiHoacNull(g.quoc_gia) }
    case 'hoat-chat':
      return { ten, ten_khac: chuoiHoacNull(g.ten_khac), mo_ta: chuoiHoacNull(g.mo_ta, true) }
  }
}

export function tao(ma: MaNhom, g: GiaTriForm): Promise<KetQuaGoi<BanGhi>> {
  const body = thanBody(ma, g)
  switch (ma) {
    case 'thuong-hieu':
      return goi(() => api.POST('/api/v1/noi-bo/thuong-hieu', { body: body as { ten: string } })).then((k) => chung<BanGhi>(k))
    case 'nha-san-xuat':
      return goi(() => api.POST('/api/v1/noi-bo/nha-san-xuat', { body: body as { ten: string } })).then((k) => chung<BanGhi>(k))
    case 'hoat-chat':
      return goi(() => api.POST('/api/v1/noi-bo/hoat-chat', { body: body as { ten: string } })).then((k) => chung<BanGhi>(k))
  }
}

export function sua(ma: MaNhom, id: number, g: GiaTriForm): Promise<KetQuaGoi<BanGhi>> {
  const body = thanBody(ma, g)
  const params = { path: { ban_ghi_id: id } }
  switch (ma) {
    case 'thuong-hieu':
      return goi(() => api.PATCH('/api/v1/noi-bo/thuong-hieu/{ban_ghi_id}', { params, body })).then((k) => chung<BanGhi>(k))
    case 'nha-san-xuat':
      return goi(() => api.PATCH('/api/v1/noi-bo/nha-san-xuat/{ban_ghi_id}', { params, body })).then((k) => chung<BanGhi>(k))
    case 'hoat-chat':
      return goi(() => api.PATCH('/api/v1/noi-bo/hoat-chat/{ban_ghi_id}', { params, body })).then((k) => chung<BanGhi>(k))
  }
}

export function xoa(ma: MaNhomXoa, id: number): Promise<KetQuaGoi<undefined>> {
  const params = { path: { ban_ghi_id: id } }
  switch (ma) {
    case 'thuong-hieu':
      return goi(() => api.DELETE('/api/v1/noi-bo/thuong-hieu/{ban_ghi_id}', { params })).then((k) => chung<undefined>(k))
    case 'nha-san-xuat':
      return goi(() => api.DELETE('/api/v1/noi-bo/nha-san-xuat/{ban_ghi_id}', { params })).then((k) => chung<undefined>(k))
  }
}
