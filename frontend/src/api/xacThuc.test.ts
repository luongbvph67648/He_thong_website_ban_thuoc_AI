import createClient from 'openapi-fetch'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { paths } from './schema'
import { lamMoiAccessToken, lamMoiPhien, taoMiddlewareXacThuc } from './xacThuc'

/** Server giả: mỗi lần gọi lấy phản hồi kế tiếp theo hàm quyết định, ghi lại mọi request đã nhận. */
function dungServerGia(quyetDinh: (req: Request, lanThu: number) => Response | Promise<Response>) {
  const daNhan: Request[] = []
  const fetchGia = vi.fn(async (input: Request | string | URL, init?: RequestInit) => {
    const req = input instanceof Request ? input : new Request(input, init)
    daNhan.push(req.clone())
    return quyetDinh(req, daNhan.length)
  })
  return { fetchGia: fetchGia as unknown as typeof fetch, daNhan }
}

const json = (status: number, body: unknown = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

function taoClient(opts: {
  fetchGia: typeof fetch
  token?: string | null
  lamMoi?: () => Promise<string | null>
  khiHetPhien?: () => void
}) {
  let token = opts.token ?? null
  const khiHetPhien = opts.khiHetPhien ?? vi.fn()
  const lamMoi = opts.lamMoi ?? vi.fn(async () => 'token-moi')
  const client = createClient<paths>({ baseUrl: 'http://api.test', fetch: opts.fetchGia })
  client.use(
    taoMiddlewareXacThuc({
      layToken: () => token,
      datToken: (t) => (token = t),
      lamMoi,
      khiHetPhien,
      fetchLai: opts.fetchGia,
    }),
  )
  return { client, khiHetPhien, lamMoi, layToken: () => token }
}

// Đường dẫn ngoài schema (chưa có endpoint ở T0.7): ép kiểu để thử hành vi của middleware.
const goi = (client: ReturnType<typeof taoClient>['client'], duong: string, init?: Record<string, unknown>) =>
  (client as unknown as { GET: (p: string, i?: unknown) => Promise<{ response: Response }> }).GET(duong, init)
const goiPost = (client: ReturnType<typeof taoClient>['client'], duong: string, body: unknown) =>
  (client as unknown as { POST: (p: string, i?: unknown) => Promise<{ response: Response }> }).POST(duong, { body })

describe('middleware xác thực', () => {
  beforeEach(() => vi.clearAllMocks())

  it('gắn Bearer token khi đã đăng nhập, không gắn khi chưa', async () => {
    const { fetchGia, daNhan } = dungServerGia(() => json(200))
    await goi(taoClient({ fetchGia, token: 'abc' }).client, '/api/v1/toi')
    await goi(taoClient({ fetchGia, token: null }).client, '/api/v1/toi')
    expect(daNhan[0].headers.get('Authorization')).toBe('Bearer abc')
    expect(daNhan[1].headers.has('Authorization')).toBe(false)
  })

  it('gặp 401 thì làm mới token đúng một lần rồi gọi lại với token mới', async () => {
    const { fetchGia, daNhan } = dungServerGia((req) =>
      req.headers.get('Authorization') === 'Bearer token-moi' ? json(200, { ok: true }) : json(401),
    )
    const { client, lamMoi, layToken } = taoClient({ fetchGia, token: 'het-han' })
    const { response } = await goi(client, '/api/v1/toi')
    expect(response.status).toBe(200)
    expect(lamMoi).toHaveBeenCalledTimes(1)
    expect(daNhan.map((r) => r.headers.get('Authorization'))).toEqual(['Bearer het-han', 'Bearer token-moi'])
    expect(layToken()).toBe('token-moi')
  })

  it('nhiều request cùng gặp 401 chỉ làm mới một lần (dùng chung một lời hứa)', async () => {
    const { fetchGia } = dungServerGia((req) =>
      req.headers.get('Authorization') === 'Bearer token-moi' ? json(200) : json(401),
    )
    let xong!: (t: string) => void
    const lamMoi = vi.fn(() => new Promise<string>((giai) => (xong = giai)))
    const { client } = taoClient({ fetchGia, token: 'het-han', lamMoi })
    const ba = Promise.all([goi(client, '/api/v1/a'), goi(client, '/api/v1/b'), goi(client, '/api/v1/c')])
    await vi.waitFor(() => expect(lamMoi).toHaveBeenCalled())
    xong('token-moi')
    const ketQua = await ba
    expect(ketQua.map((k) => k.response.status)).toEqual([200, 200, 200])
    expect(lamMoi).toHaveBeenCalledTimes(1)
  })

  it('làm mới thất bại thì kết thúc phiên và trả nguyên 401', async () => {
    const { fetchGia } = dungServerGia(() => json(401))
    const { client, khiHetPhien } = taoClient({ fetchGia, token: 'het-han', lamMoi: async () => null })
    const { response } = await goi(client, '/api/v1/toi')
    expect(response.status).toBe(401)
    expect(khiHetPhien).toHaveBeenCalledTimes(1)
  })

  it('gọi lại vẫn 401 thì kết thúc phiên, không lặp vô hạn', async () => {
    const { fetchGia, daNhan } = dungServerGia(() => json(401))
    const { client, khiHetPhien, lamMoi } = taoClient({ fetchGia, token: 'het-han' })
    const { response } = await goi(client, '/api/v1/toi')
    expect(response.status).toBe(401)
    expect(lamMoi).toHaveBeenCalledTimes(1)
    expect(daNhan).toHaveLength(2) // 1 lần gốc + đúng 1 lần gọi lại
    expect(khiHetPhien).toHaveBeenCalledTimes(1)
  })

  it('gửi lại nguyên vẹn thân JSON của request POST', async () => {
    const { fetchGia, daNhan } = dungServerGia((req) =>
      req.headers.get('Authorization') === 'Bearer token-moi' ? json(200) : json(401),
    )
    const { client } = taoClient({ fetchGia, token: 'het-han' })
    const { response } = await goiPost(client, '/api/v1/toi/don-hang', { san_pham_id: 5, so_luong: 2 })
    expect(response.status).toBe(200)
    expect(await daNhan[1].json()).toEqual({ san_pham_id: 5, so_luong: 2 })
    expect(daNhan[1].method).toBe('POST')
  })

  it.each([
    '/api/v1/auth/dang-nhap',
    '/api/v1/auth/lam-moi',
    '/api/v1/noi-bo/auth/dang-nhap',
    '/api/v1/auth/dang-ky',
    '/api/v1/auth/dat-lai-mat-khau',
    '/api/v1/auth/otp',
  ])(
    '401 ở %s không kích hoạt làm mới (sai mật khẩu không phải hết phiên)',
    async (duong) => {
      const { fetchGia, daNhan } = dungServerGia(() => json(401))
      const { client, lamMoi, khiHetPhien } = taoClient({ fetchGia, token: 'abc' })
      const { response } = await goi(client, duong)
      expect(response.status).toBe(401)
      expect(lamMoi).not.toHaveBeenCalled()
      expect(khiHetPhien).not.toHaveBeenCalled()
      expect(daNhan).toHaveLength(1)
    },
  )

  it('khách chưa đăng nhập gặp 401 thì không làm mới và không đụng tới phiên', async () => {
    const { fetchGia } = dungServerGia(() => json(401))
    const { client, lamMoi, khiHetPhien } = taoClient({ fetchGia, token: null })
    expect((await goi(client, '/api/v1/toi')).response.status).toBe(401)
    expect(lamMoi).not.toHaveBeenCalled()
    expect(khiHetPhien).not.toHaveBeenCalled()
  })

  it.each([400, 403, 404, 409, 500])('mã %i không phải hết phiên nên không làm mới', async (ma) => {
    const { fetchGia } = dungServerGia(() => json(ma))
    const { client, lamMoi } = taoClient({ fetchGia, token: 'abc' })
    expect((await goi(client, '/api/v1/toi')).response.status).toBe(ma)
    expect(lamMoi).not.toHaveBeenCalled()
  })

  it('401 đến muộn sau khi token đã được làm mới thì dùng token hiện tại, không làm mới lần nữa', async () => {
    let giaiPhongA!: () => void
    const { fetchGia, daNhan } = dungServerGia(async (req, lanThu) => {
      if (req.headers.get('Authorization') === 'Bearer token-moi') return json(200)
      if (lanThu === 1) await new Promise<void>((giai) => (giaiPhongA = giai)) // request A bị giữ lại rồi mới trả 401
      return json(401)
    })
    const { client, lamMoi } = taoClient({ fetchGia, token: 'het-han' })
    const a = goi(client, '/api/v1/a')
    await vi.waitFor(() => expect(daNhan).toHaveLength(1))
    expect((await goi(client, '/api/v1/b')).response.status).toBe(200) // B: 401 -> làm mới -> thành công
    giaiPhongA()
    expect((await a).response.status).toBe(200) // A: 401 muộn -> dùng token mới có sẵn
    expect(lamMoi).toHaveBeenCalledTimes(1)
  })

  it('làm mới xong thì request sau dùng token mới ngay từ đầu', async () => {
    const { fetchGia, daNhan } = dungServerGia((req) =>
      req.headers.get('Authorization') === 'Bearer token-moi' ? json(200) : json(401),
    )
    const { client, lamMoi } = taoClient({ fetchGia, token: 'het-han' })
    await goi(client, '/api/v1/a')
    await goi(client, '/api/v1/b')
    expect(lamMoi).toHaveBeenCalledTimes(1)
    expect(daNhan.at(-1)?.headers.get('Authorization')).toBe('Bearer token-moi')
  })
})

describe('lamMoiAccessToken', () => {
  it('khách gọi /api/v1/auth/lam-moi, nhân viên gọi /api/v1/noi-bo/auth/lam-moi, kèm cookie', async () => {
    const url: string[] = []
    const cheDo: (RequestCredentials | undefined)[] = []
    const fetchGia = vi.fn(async (u: string | URL | Request, init?: RequestInit) => {
      url.push(String(u))
      cheDo.push(init?.credentials)
      return json(200, { access_token: 'tok' })
    }) as unknown as typeof fetch
    expect(await lamMoiAccessToken('khach', fetchGia)).toBe('tok')
    expect(await lamMoiAccessToken('noi_bo', fetchGia)).toBe('tok')
    expect(url).toEqual(['/api/v1/auth/lam-moi', '/api/v1/noi-bo/auth/lam-moi'])
    expect(cheDo).toEqual(['include', 'include'])
  })

  it.each([
    ['401', () => json(401)],
    ['500', () => json(500)],
    ['thân không có access_token', () => json(200, {})],
    ['thân không phải JSON', () => new Response('<html>', { status: 200 })],
  ])('trả null khi phản hồi %s', async (_ten, tao) => {
    const fetchGia = (async () => tao()) as unknown as typeof fetch
    expect(await lamMoiAccessToken('khach', fetchGia)).toBeNull()
  })

  it('trả null khi mất mạng thay vì ném lỗi', async () => {
    const fetchGia = (async () => {
      throw new TypeError('Failed to fetch')
    }) as unknown as typeof fetch
    expect(await lamMoiAccessToken('noi_bo', fetchGia)).toBeNull()
  })

  it('phân biệt hết phiên (401/403) với lỗi tạm thời (mạng, 500) để biết có xóa gợi ý đăng nhập không', async () => {
    const lam = (tao: () => Response | Promise<Response>) => lamMoiPhien('khach', (async () => tao()) as unknown as typeof fetch)
    expect(await lam(() => json(401))).toEqual({ token: null, hetPhien: true })
    expect(await lam(() => json(403))).toEqual({ token: null, hetPhien: true })
    expect(await lam(() => json(500))).toEqual({ token: null, hetPhien: false })
    // Khóa tạm do đoán sai mật khẩu: token vẫn còn giá trị nên giữ gợi ý đăng nhập, khác với Admin khóa.
    const khoaTam = json(403, { ma_loi: 'TAI_KHOAN_BI_KHOA', thong_diep: 'x', chi_tiet: { thu_lai_sau_giay: 600 } })
    expect(await lam(() => khoaTam)).toEqual({ token: null, hetPhien: false })
    const adminKhoa = json(403, { ma_loi: 'TAI_KHOAN_BI_KHOA', thong_diep: 'x', chi_tiet: null })
    expect(await lam(() => adminKhoa)).toEqual({ token: null, hetPhien: true })
    expect(await lam(() => json(200, { access_token: 'tok' }))).toEqual({ token: 'tok', hetPhien: false })
    expect(
      await lam(() => {
        throw new TypeError('Failed to fetch')
      }),
    ).toEqual({ token: null, hetPhien: false })
  })

  describe('khi trình duyệt có Web Locks', () => {
    const goc = Object.getOwnPropertyDescriptor(globalThis.navigator, 'locks')
    afterEach(() => {
      if (goc) Object.defineProperty(globalThis.navigator, 'locks', goc)
      else delete (globalThis.navigator as { locks?: unknown }).locks
    })

    it('hai lần làm mới đồng thời (hai tab) chạy lần lượt, không chồng nhau', async () => {
      // Khóa giả giống thật: yêu cầu sau chờ yêu cầu trước xong.
      let hangDoi: Promise<unknown> = Promise.resolve()
      const request = vi.fn((_ten: string, viec: () => Promise<unknown>) => {
        const chay = hangDoi.then(viec)
        hangDoi = chay.catch(() => undefined)
        return chay
      })
      Object.defineProperty(globalThis.navigator, 'locks', { value: { request }, configurable: true })

      const nhatKy: string[] = []
      let dangChay = 0
      const fetchGia = (async () => {
        dangChay += 1
        nhatKy.push(`vao${dangChay}`)
        await new Promise((r) => setTimeout(r, 10))
        nhatKy.push(`ra${dangChay}`)
        dangChay -= 1
        return json(200, { access_token: 'tok' })
      }) as unknown as typeof fetch

      await Promise.all([lamMoiAccessToken('khach', fetchGia), lamMoiAccessToken('khach', fetchGia)])
      expect(request).toHaveBeenCalledTimes(2)
      expect(request.mock.calls[0][0]).toBe('nha-thuoc-lam-moi-phien')
      expect(nhatKy).toEqual(['vao1', 'ra1', 'vao1', 'ra1']) // không bao giờ có hai lần chạy cùng lúc
    })
  })

  it('chưa biết loại phiên thì không gọi gì', async () => {
    const fetchGia = vi.fn() as unknown as typeof fetch
    expect(await lamMoiAccessToken(null, fetchGia)).toBeNull()
    expect(fetchGia).not.toHaveBeenCalled()
  })
})
