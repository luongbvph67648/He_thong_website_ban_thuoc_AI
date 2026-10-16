import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Carousel, Empty, Skeleton, Typography } from 'antd'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { lienKetAnToan, laLienKetNgoai } from '../../lib/lienKet'
import { KHOA_QUERY_CUA_HANG, type SanPhamThe } from './cuaHang'
import { useCayDanhMuc } from './useCayDanhMuc'
import { LuoiSanPham } from './TheSanPham'

type Banner = { id: number; tieu_de: string | null; anh_url: string; lien_ket: string | null }

function AnhBanner({ b, cao }: { b: Banner; cao: number }) {
  const anh = lienKetAnToan(b.anh_url)
  if (!anh) return null
  const hinh = <img src={anh} alt={b.tieu_de ?? 'Banner'} style={{ width: '100%', height: cao, objectFit: 'cover', display: 'block' }} />
  const dich = lienKetAnToan(b.lien_ket)
  if (!dich) return hinh
  return laLienKetNgoai(dich) ? (
    <a href={dich} target="_blank" rel="noopener noreferrer">
      {hinh}
    </a>
  ) : (
    <Link to={dich}>{hinh}</Link>
  )
}

function KhuSanPham({ tieuDe, danhSach }: { tieuDe: string; danhSach: readonly SanPhamThe[] }) {
  if (!danhSach.length) return null
  return (
    <section aria-label={tieuDe} style={{ marginTop: 24 }}>
      <Typography.Title level={3}>{tieuDe}</Typography.Title>
      <LuoiSanPham danhSach={danhSach} nguon="trang_chu" />
    </section>
  )
}

const AN_VISUAL = { position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)', whiteSpace: 'nowrap' } as const

/** Trang chủ cửa hàng (KVL01): banner, danh mục gốc, sản phẩm nổi bật và bán chạy. */
export default function TrangChu() {
  return (
    <>
      <h1 style={AN_VISUAL}>Nhà thuốc trực tuyến</h1>
      <NoiDungTrangChu />
    </>
  )
}

function NoiDungTrangChu() {
  const trangChu = useQuery({
    queryKey: [...KHOA_QUERY_CUA_HANG, 'trang-chu'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/trang-chu')
      if (error || !data) throw new Error('Không tải được trang chủ')
      return data
    },
  })
  const danhMuc = useCayDanhMuc()

  if (trangChu.isPending) return <Skeleton active paragraph={{ rows: 8 }} />
  if (trangChu.isError)
    return (
      <Alert
        type="error"
        showIcon
        title="Không tải được trang chủ"
        description="Vui lòng kiểm tra kết nối rồi thử lại."
        action={<Button onClick={() => void trangChu.refetch()}>Thử lại</Button>}
      />
    )
  const { banner_chinh, banner_phu, noi_bat, ban_chay } = trangChu.data
  const chuaCoGi = !banner_chinh.length && !banner_phu.length && !noi_bat.length && !ban_chay.length && !danhMuc.data?.length

  return (
    <>
      {banner_chinh.length > 0 && (
        <section aria-label="Banner chính">
          <Carousel autoplay autoplaySpeed={5000} dots>
            {banner_chinh.map((b) => (
              <AnhBanner key={b.id} b={b} cao={220} />
            ))}
          </Carousel>
        </section>
      )}
      {banner_phu.length > 0 && (
        <section
          aria-label="Banner phụ"
          style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12, marginTop: 12 }}
        >
          {banner_phu.map((b) => (
            <AnhBanner key={b.id} b={b} cao={120} />
          ))}
        </section>
      )}
      {!!danhMuc.data?.length && (
        <section aria-label="Danh mục" style={{ marginTop: 24 }}>
          <Typography.Title level={3}>Danh mục</Typography.Title>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {danhMuc.data.map((d) => (
              <Link key={d.id} to={`/danh-muc/${d.slug}`}>
                <Button>{d.ten}</Button>
              </Link>
            ))}
          </div>
        </section>
      )}
      <KhuSanPham tieuDe="Sản phẩm nổi bật" danhSach={noi_bat} />
      <KhuSanPham tieuDe="Bán chạy" danhSach={ban_chay} />
      {chuaCoGi && <Empty style={{ marginTop: 48 }} description="Cửa hàng chưa có sản phẩm" />}
    </>
  )
}
