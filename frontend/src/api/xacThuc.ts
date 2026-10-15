import type { Middleware } from 'openapi-fetch'
import type { LoaiPhien } from '../stores/phien'

/** Các endpoint không cần đăng nhập: 401 ở đây là sai thông tin hoặc OTP, không phải hết phiên nên không làm mới. */
const DUONG_KHONG_LAM_MOI = /\/auth\/(dang-nhap|dang-ky|lam-moi|dang-xuat|quen-mat-khau|otp)(\/|$)/

export interface ThamSoXacThuc {
  layToken: () => string | null
  datToken: (token: string) => void
  /** Xin access token mới bằng refresh token (cookie). Trả null nếu không làm mới được. */
  lamMoi: () => Promise<string | null>
  /** Gọi khi phiên không cứu được nữa (làm mới thất bại, hoặc gọi lại vẫn 401). */
  khiHetPhien: () => void
  fetchLai?: typeof fetch
}

/**
 * Middleware cho openapi-fetch:
 * - Gắn `Authorization: Bearer <token>` khi đã đăng nhập.
 * - Gặp 401 thì làm mới token ĐÚNG MỘT LẦN (nhiều request cùng lỗi dùng chung một lần làm mới), rồi gọi lại request
 *   gốc đúng một lần với token mới. Gọi lại vẫn 401 hoặc làm mới thất bại thì kết thúc phiên.
 * - Chỉ làm mới khi request gốc có kèm token (khách vãng lai gặp 401 không đụng tới phiên).
 */
export function taoMiddlewareXacThuc(ts: ThamSoXacThuc): Middleware {
  // Bản sao request (thân chỉ đọc được một lần) và token đã dùng, theo id request, để gọi lại khi cần.
  const daGui = new Map<string, { banSao: Request; tokenDaDung: string }>()
  let dangLamMoi: Promise<string | null> | null = null

  const lamMoiMotLan = (): Promise<string | null> => {
    dangLamMoi ??= ts
      .lamMoi()
      .then((token) => {
        if (token) ts.datToken(token)
        return token
      })
      .finally(() => {
        dangLamMoi = null
      })
    return dangLamMoi
  }

  return {
    onRequest({ request, id }) {
      const token = ts.layToken()
      if (token && !request.headers.has('Authorization')) {
        daGui.set(id, { banSao: request.clone(), tokenDaDung: token })
        request.headers.set('Authorization', `Bearer ${token}`)
      }
      return request
    },
    async onResponse({ request, response, id }) {
      const ban = daGui.get(id)
      daGui.delete(id)
      if (response.status !== 401 || !ban) return response
      if (DUONG_KHONG_LAM_MOI.test(new URL(request.url).pathname)) return response

      // Token đã được request khác làm mới trong lúc request này đang bay: dùng token hiện tại, khỏi làm mới nữa.
      const tokenHienTai = ts.layToken()
      const token = tokenHienTai && tokenHienTai !== ban.tokenDaDung ? tokenHienTai : await lamMoiMotLan()
      if (!token) {
        ts.khiHetPhien()
        return response
      }
      const lai = new Request(ban.banSao)
      lai.headers.set('Authorization', `Bearer ${token}`)
      const ketQua = await (ts.fetchLai ?? fetch)(lai)
      if (ketQua.status === 401) ts.khiHetPhien()
      return ketQua
    },
    onError({ id }) {
      daGui.delete(id)
    },
  }
}

/** Làm mới access token bằng refresh token trong cookie httpOnly. Khách và nhân viên dùng hai endpoint khác nhau. */
export async function lamMoiAccessToken(
  loai: LoaiPhien | null,
  fetchFn: typeof fetch = (...tham_so) => fetch(...tham_so),
): Promise<string | null> {
  if (!loai) return null
  const duong = loai === 'noi_bo' ? '/api/v1/noi-bo/auth/lam-moi' : '/api/v1/auth/lam-moi'
  try {
    const phanHoi = await fetchFn(duong, { method: 'POST', credentials: 'include' })
    if (!phanHoi.ok) return null
    const than: unknown = await phanHoi.json()
    const token = (than as { access_token?: unknown } | null)?.access_token
    return typeof token === 'string' && token !== '' ? token : null
  } catch {
    return null
  }
}
