import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Carousel, Empty, Skeleton, Typography } from 'antd'
import {
  AppstoreOutlined,
  ArrowRightOutlined,
  CameraOutlined,
  FileTextOutlined,
  HeartOutlined,
  MedicineBoxOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  SmileOutlined,
} from '@ant-design/icons'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { lienKetAnToan, laLienKetNgoai } from '../../lib/lienKet'
import { layMaPhien } from '../../lib/maPhien'
import { usePhien } from '../../stores/phien'
import { KHOA_QUERY_CUA_HANG, type NguonXem, type SanPhamThe } from './cuaHang'
import { useCayDanhMuc } from './useCayDanhMuc'
import { LuoiSanPham } from './TheSanPham'

type Banner = { id: number; tieu_de: string | null; anh_url: string; lien_ket: string | null }

function AnhBanner({ b, cao, viTri = 'phu' }: { b: Banner; cao: number; viTri?: 'chinh' | 'phu' }) {
  const anh = lienKetAnToan(b.anh_url)
  if (!anh) return null
  const hinh = (
    <span className={`banner-slide banner-slide-${viTri}`}>
      <img src={anh} alt="" aria-hidden="true" style={{ width: '100%', height: cao, objectFit: 'cover', display: 'block' }} />
      <span className="banner-slide-noi-dung">
        {viTri === 'chinh' && <span className="banner-slide-nhan">NHÀ THUỐC AI <span aria-hidden="true">·</span> KHỎE AN TÂM</span>}
        <span className="banner-slide-tieu-de">{b.tieu_de ?? 'Chăm sóc sức khỏe mỗi ngày'}</span>
        {viTri === 'chinh' && (
          <>
            <span className="banner-slide-mo-ta">Chọn sản phẩm phù hợp, an tâm chăm sóc sức khỏe mỗi ngày.</span>
            <span className="banner-slide-nut">Khám phá ngay <ArrowRightOutlined /></span>
          </>
        )}
        {viTri === 'phu' && <span className="banner-slide-kham-pha">Xem ưu đãi <ArrowRightOutlined /></span>}
      </span>
    </span>
  )
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

function KhuSanPham({ tieuDe, danhSach, nguon = 'trang_chu' }: { tieuDe: string; danhSach: readonly SanPhamThe[]; nguon?: NguonXem }) {
  if (!danhSach.length) return null
  return (
    <section aria-label={tieuDe} className="khu-san-pham">
      <div className="tieu-de-khu-san-pham">
        <span className="dau-trang-tri" aria-hidden="true" />
        <Typography.Title level={3}>{tieuDe}</Typography.Title>
      </div>
      <LuoiSanPham danhSach={danhSach} nguon={nguon} />
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

function GioiThieuVaTacVu() {
  return (
    <>
      <section className="loi-chao-cua-hang" aria-label="Giới thiệu nhà thuốc">
        <div className="loi-chao-noi-dung">
          <span className="loi-chao-nhan">CHĂM SÓC SỨC KHỎE MỖI NGÀY</span>
          <Typography.Title>Sức khỏe gia đình,<br /><span>chăm sóc dễ dàng</span></Typography.Title>
          <Typography.Paragraph>Tìm sản phẩm phù hợp, xem thông tin rõ ràng và nhận hỗ trợ từ dược sĩ khi bạn cần.</Typography.Paragraph>
          <div className="loi-chao-nut">
            <Link to="/danh-muc/thuoc"><Button type="primary" size="large" icon={<SearchOutlined />}>
              Khám phá sản phẩm <ArrowRightOutlined />
            </Button></Link>
            <Link className="loi-chao-lien-ket" to="/hoi-dap">Tư vấn sức khỏe <ArrowRightOutlined /></Link>
          </div>
          <div className="loi-chao-cam-ket">
            <span><SafetyCertificateOutlined /> Thông tin rõ ràng</span>
            <span><SmileOutlined /> Tư vấn tận tâm</span>
          </div>
        </div>
        <div className="loi-chao-minh-hoa" aria-hidden="true">
          <div className="vong-tron vong-tron-lon" />
          <div className="vien-thuoc vien-thuoc-xanh"><span>+</span></div>
          <div className="vien-thuoc vien-thuoc-vang"><span>✦</span></div>
          <div className="the-cham-soc"><span className="the-cham-soc-icon">✚</span><span>Khỏe mạnh<br />từ hôm nay</span></div>
          <span className="hat-trang-tri hat-1">✦</span><span className="hat-trang-tri hat-2">✦</span>
        </div>
      </section>
      <nav className="tac-vu-nhanh" aria-label="Dịch vụ nhanh">
        <Link to="/tra-cuu-anh" className="tac-vu-nhanh-the">
          <span className="tac-vu-nhanh-icon tac-vu-xanh"><CameraOutlined /></span>
          <span><strong>Tra cứu thuốc bằng ảnh</strong><small>Nhận diện sản phẩm nhanh chóng</small></span>
          <ArrowRightOutlined className="tac-vu-mui-ten" />
        </Link>
        <Link to="/gui-don-thuoc" className="tac-vu-nhanh-the">
          <span className="tac-vu-nhanh-icon tac-vu-cam"><FileTextOutlined /></span>
          <span><strong>Gửi đơn thuốc</strong><small>Dược sĩ hỗ trợ kiểm tra đơn</small></span>
          <ArrowRightOutlined className="tac-vu-mui-ten" />
        </Link>
        <Link to="/hoi-dap" className="tac-vu-nhanh-the">
          <span className="tac-vu-nhanh-icon tac-vu-lam"><HeartOutlined /></span>
          <span><strong>Góc hỏi đáp sức khỏe</strong><small>Tìm thông tin hữu ích</small></span>
          <ArrowRightOutlined className="tac-vu-mui-ten" />
        </Link>
      </nav>
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
  // AI07 "Dành cho bạn": theo lịch sử xem 30 ngày của thành viên hoặc của phiên trình duyệt; rỗng thì khu này tự ẩn.
  const daKhoiPhuc = usePhien((st) => st.daKhoiPhuc)
  const loaiPhien = usePhien((st) => st.loai)
  const danhChoBan = useQuery({
    queryKey: [...KHOA_QUERY_CUA_HANG, 'danh-cho-ban', loaiPhien],
    enabled: daKhoiPhuc,
    staleTime: 5 * 60_000,
    retry: false,
    queryFn: async () => {
      const maPhien = layMaPhien()
      const { data } = await api.GET('/api/v1/goi-y/danh-cho-ban', { params: { header: { 'x-ma-phien': maPhien } } })
      return data ?? []
    },
  })

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
      {(banner_chinh.length > 0 || banner_phu.length > 0) && (
        <section className={`khuyen-mai-trang-chu${banner_phu.length ? ' co-banner-phu' : ''}`} aria-label="Khuyến mãi">
          {banner_chinh.length > 0 && (
            <section className="banner-chinh" aria-label="Banner khuyến mãi nổi bật">
              <Carousel className="banner-trinh-chieu" effect="fade" autoplay autoplaySpeed={5200} speed={750} pauseOnHover arrows dots>
                {banner_chinh.map((b) => (
                <AnhBanner key={b.id} b={b} cao={340} viTri="chinh" />
                ))}
              </Carousel>
            </section>
          )}
          {banner_phu.length > 0 && (
            <section className="banner-phu-grid" aria-label="Banner phụ">
              {banner_phu.map((b) => (
                <AnhBanner key={b.id} b={b} cao={142} viTri="phu" />
              ))}
            </section>
          )}
        </section>
      )}
      <GioiThieuVaTacVu />
      {!!danhMuc.data?.length && (
        <section aria-label="Danh mục" className="khu-danh-muc-noi-bat">
          <div className="tieu-de-khu-san-pham">
            <span className="dau-trang-tri" aria-hidden="true" />
            <Typography.Title level={3}>Mua sắm theo nhu cầu</Typography.Title>
            <Link className="xem-them-khu" to={`/danh-muc/${danhMuc.data[0].slug}`}>Xem danh mục <ArrowRightOutlined /></Link>
          </div>
          <div className="luoi-danh-muc-noi-bat">
            {danhMuc.data.slice(0, 6).map((d, i) => {
              const BieuTuong = [MedicineBoxOutlined, HeartOutlined, SafetyCertificateOutlined, SmileOutlined, AppstoreOutlined][i % 5]
              return (
                <Link key={d.id} className="the-danh-muc-noi-bat" to={`/danh-muc/${d.slug}`}>
                  <span className={`danh-muc-bieu-tuong danh-muc-mau-${i % 5}`}><BieuTuong /></span>
                  <strong>{d.ten}</strong>
                  <span className="danh-muc-kham-pha">Khám phá <ArrowRightOutlined /></span>
                </Link>
              )
            })}
          </div>
        </section>
      )}
      <KhuSanPham tieuDe="Sản phẩm nổi bật" danhSach={noi_bat} />
      <KhuSanPham tieuDe="Dành cho bạn" danhSach={danhChoBan.data ?? []} nguon="danh_cho_ban" />
      <KhuSanPham tieuDe="Bán chạy" danhSach={ban_chay} />
      {chuaCoGi && <Empty style={{ marginTop: 48 }} description="Cửa hàng chưa có sản phẩm" />}
    </>
  )
}
