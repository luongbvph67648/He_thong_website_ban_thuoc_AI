import createClient from 'openapi-fetch'
import { usePhien } from '../stores/phien'
import type { paths } from './schema'
import { lamMoiAccessToken, taoMiddlewareXacThuc } from './xacThuc'

/**
 * Client API duy nhất của ứng dụng, có kiểu từ `schema.d.ts` (sinh bằng `npm run gen:api`).
 * Dev: trình duyệt gọi cùng origin, Vite chuyển `/api` sang backend (xem vite.config.ts).
 */
export const api = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_URL ?? globalThis.location?.origin ?? '',
  // Gửi/nhận cookie refresh token cả khi API khác origin (VITE_API_URL); CORS phía backend đã bật allow_credentials.
  credentials: 'include',
})

api.use(
  taoMiddlewareXacThuc({
    layToken: () => usePhien.getState().accessToken,
    datToken: (token) => usePhien.getState().datToken(token),
    lamMoi: () => lamMoiAccessToken(usePhien.getState().loai),
    khiHetPhien: () => usePhien.getState().dangXuat(),
  }),
)
