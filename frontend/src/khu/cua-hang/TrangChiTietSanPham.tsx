import { useQuery } from '@tanstack/react-query'
import { Alert, App, Breadcrumb, Button, Col, Descriptions, Empty, Image, InputNumber, Progress, Rate, Result, Row, Segmented, Skeleton, Space, Table, Tabs, Tag, Typography } from 'antd'
import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../../api/client'
import { laLoiApi } from '../../api/loi'
import { dinhDangNgay, dinhDangTien } from '../../lib/dinhDang'
import { lienKetAnToan } from '../../lib/lienKet'
import { layMaPhien } from '../../lib/maPhien'
import {
  diemTrungBinh,
  docNguonXem,
  DONG_KHONG_PHAI_THUOC,
  KHOA_QUERY_CUA_HANG,
  LOI_KHONG_CO,
  MUC_NOI_DUNG_CHUYEN_MON,
  type SanPhamChiTiet,
} from './cuaHang'
import { NhanTrangThai } from '../../components/NhanTrangThai'
import { usePhien } from '../../stores/phien'
import HoiDapSanPham from './danh-gia/HoiDapSanPham'
import { LuoiSanPham } from './TheSanPham'
import { useGioHang } from './gio-hang/gioHang'

function ThuVien({ anh, ten }: { anh: SanPhamChiTiet['anh']; ten: string }) {
  const [chon, datChon] = useState(() => Math.max(0, anh.findIndex((a) => a.la_anh_chinh)))
  if (!anh.length)
    return (
      <div aria-label="Chưa có ảnh" style={{ height: 320, background: '#fafafa', display: 'grid', placeItems: 'center', color: '#bfbfbf' }}>
        Chưa có ảnh
      </div>
    )
  return (
    <Space orientation="vertical" size={8} style={{ width: '100%' }}>
      <img src={anh[chon].url} alt={ten} style={{ width: '100%', height: 320, objectFit: 'contain', background: '#fafafa' }} />
      {anh.length > 1 && (
        <Space size={8} wrap>
          {anh.map((a, i) => (
            <button
              key={a.url}
              type="button"
              aria-label={`Xem ảnh ${i + 1}`}
              aria-pressed={i === chon}
              onClick={() => datChon(i)}
              style={{ border: i === chon ? '2px solid #1677ff' : '1px solid #d9d9d9', padding: 2, background: '#fff', cursor: 'pointer' }}
            >
              <img src={a.url} alt="" style={{ width: 56, height: 56, objectFit: 'contain', display: 'block' }} />
            </button>
          ))}
        </Space>
      )}
    </Space>
  )
}

/** Giá, chọn đơn vị và hành động mua. Thuốc kê đơn KHÔNG có nút thêm vào giỏ (CLAUDE.md quy tắc 6). */
function KhuMuaHang({ sp }: { sp: SanPhamChiTiet }) {
  const { message } = App.useApp()
  const gio = useGioHang()
  const [soLuong, datSoLuong] = useState(1)
  const [dangThem, datDangThem] = useState(false)
  const [donViId, datDonViId] = useState<number | null>(null)
  const donVi = sp.don_vi.find((d) => d.id === donViId) ?? sp.don_vi.find((d) => d.la_mac_dinh) ?? sp.don_vi[0]

  if (sp.can_tu_van)
    return (
      <Space orientation="vertical" size={12} style={{ width: '100%' }}>
        <Alert
          type="warning"
          showIcon
          title="Thuốc kê đơn"
          description="Sản phẩm chỉ được bán khi có đơn của bác sĩ và sau khi dược sĩ xem đơn. Thông tin dưới đây chỉ để tham khảo."
        />
        {donVi && <Typography.Text type="secondary">Giá tham khảo: {dinhDangTien(donVi.gia_ban)} / {donVi.ten_don_vi}</Typography.Text>}
        <Link to="/gui-don-thuoc">
          <Button type="primary" danger block size="large">
            Cần tư vấn từ dược sĩ
          </Button>
        </Link>
      </Space>
    )
  if (!donVi)
    return <Alert type="info" showIcon title="Sản phẩm này chỉ bán tại nhà thuốc" description="Vui lòng đến trực tiếp nhà thuốc để mua." />
  return (
    <Space orientation="vertical" size={12} style={{ width: '100%' }}>
      {sp.don_vi.length > 1 && (
        <Segmented
          aria-label="Đơn vị tính"
          value={donVi.id}
          options={sp.don_vi.map((d) => ({ value: d.id, label: d.ten_don_vi }))}
          onChange={(x) => datDonViId(x)}
        />
      )}
      <Typography.Title level={3} style={{ color: '#cf1322', margin: 0 }} aria-label="Giá">
        {dinhDangTien(donVi.gia_ban)} <span style={{ fontSize: 14, fontWeight: 400, color: '#8c8c8c' }}>/ {donVi.ten_don_vi}</span>
      </Typography.Title>
      {donVi.he_so > 1 && <Typography.Text type="secondary">1 {donVi.ten_don_vi} = {donVi.he_so} {sp.don_vi.find((d) => d.he_so === 1)?.ten_don_vi ?? 'đơn vị nhỏ nhất'}</Typography.Text>}
      {donVi.con_hang ? <Tag color="green">Còn hàng</Tag> : <Tag>Hết hàng</Tag>}
      <Space>
        <InputNumber aria-label="Số lượng" min={1} max={9999} precision={0} value={soLuong} onChange={(v) => datSoLuong(typeof v === 'number' ? v : 1)} />
        <Button
          type="primary"
          size="large"
          loading={dangThem}
          disabled={!donVi.con_hang}
          onClick={async () => {
            datDangThem(true)
            const loi = await gio.them({ san_pham_id: sp.id, don_vi_id: donVi.id, so_luong: soLuong })
            datDangThem(false)
            if (loi) void message.error(loi)
            else void message.success('Đã thêm vào giỏ hàng')
          }}
        >
          Thêm vào giỏ
        </Button>
      </Space>
    </Space>
  )
}

function NoiDungChuyenMon({ nd }: { nd: SanPhamChiTiet['noi_dung_chuyen_mon'] }) {
  if (!nd) return <Empty description="Nội dung chuyên môn đang được dược sĩ biên soạn" />
  const huongDan = lienKetAnToan(nd.file_hdsd_url)
  return (
    <>
      {MUC_NOI_DUNG_CHUYEN_MON.map(([truong, nhan]) =>
        nd[truong] ? (
          <section key={truong} aria-label={nhan}>
            <Typography.Title level={5}>{nhan}</Typography.Title>
            <Typography.Paragraph style={{ whiteSpace: 'pre-wrap' }}>{nd[truong]}</Typography.Paragraph>
          </section>
        ) : null,
      )}
      {huongDan && (
        <Typography.Paragraph>
          <a href={huongDan} target="_blank" rel="noopener noreferrer">
            Tải hướng dẫn sử dụng
          </a>
        </Typography.Paragraph>
      )}
      <Typography.Text type="secondary">
        Nội dung do dược sĩ nhà thuốc biên soạn (bản {nd.phien_ban}, duyệt {dinhDangNgay(nd.ngay_duyet, 'ngay')}), chỉ mang tính tham
        khảo và không thay thế tư vấn của bác sĩ hoặc dược sĩ.
      </Typography.Text>
    </>
  )
}

function DanhGia({ dg }: { dg: SanPhamChiTiet['danh_gia'] }) {
  if (dg.so_luong === 0) return <Empty description="Chưa có đánh giá" />
  const diem = diemTrungBinh(dg.tong_sao, dg.so_luong)
  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <Space size={24} align="start" wrap>
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>{diem}</Typography.Title>
          <Rate disabled allowHalf value={dg.tong_sao / dg.so_luong} aria-label={`Điểm ${diem} trên 5`} />
          <div><Typography.Text type="secondary">{dg.so_luong} đánh giá</Typography.Text></div>
        </div>
        <div style={{ minWidth: 200 }}>
          {[5, 4, 3, 2, 1].map((sao) => (
            <Space key={sao} style={{ display: 'flex' }}>
              <span style={{ width: 40 }}>{sao} sao</span>
              <Progress percent={Math.round((dg.phan_bo[sao - 1] / dg.so_luong) * 100)} size="small" style={{ width: 140 }} format={() => dg.phan_bo[sao - 1]} />
            </Space>
          ))}
        </div>
      </Space>
      {dg.moi_nhat.map((d) => (
        <article key={`${d.created_at}-${d.ten_hien_thi}`} style={{ borderTop: '1px solid #f0f0f0', paddingTop: 12 }}>
          <Space size={8} wrap>
            <Typography.Text strong>{d.ten_hien_thi}</Typography.Text>
            <Rate disabled value={d.so_sao} style={{ fontSize: 14 }} aria-label={`${d.so_sao} sao`} />
            <Typography.Text type="secondary">{dinhDangNgay(d.created_at, 'ngay')}</Typography.Text>
          </Space>
          {d.noi_dung && <Typography.Paragraph style={{ marginTop: 4, marginBottom: 4, whiteSpace: 'pre-wrap' }}>{d.noi_dung}</Typography.Paragraph>}
          {d.anh && d.anh.length > 0 && (
            <Space wrap style={{ marginBottom: 4 }}>
              {d.anh.map((u) => <Image key={u} src={u} width={80} alt="Ảnh khách đánh giá" />)}
            </Space>
          )}
          {d.phan_hoi && (
            <Alert type="info" title="Phản hồi từ nhà thuốc" description={d.phan_hoi} />
          )}
        </article>
      ))}
    </Space>
  )
}

/** Chi tiết sản phẩm công khai (KVL03). Ghi lịch sử xem ở máy chủ: khách đăng nhập theo token, vãng lai theo mã phiên. */
export default function TrangChiTietSanPhamCuaHang() {
  const { slug = '' } = useParams()
  const nguon = docNguonXem(useSearchParams()[0].get('nguon'))
  const daKhoiPhuc = usePhien((s) => s.daKhoiPhuc)
  const chiTiet = useQuery({
    queryKey: [...KHOA_QUERY_CUA_HANG, 'san-pham', 'chi-tiet', slug],
    queryFn: async () => {
      const maPhien = layMaPhien()
      const { data, error } = await api.GET('/api/v1/san-pham/{slug}', {
        params: { path: { slug }, query: { nguon }, header: { 'x-ma-phien': maPhien } },
      })
      if (error || !data) throw error ?? new Error('Không tải được sản phẩm')
      return data
    },
    // Chờ lấy lại phiên khi tải trang: gọi sớm sẽ ghi lịch sử xem của khách đã đăng nhập thành của khách vãng lai.
    enabled: daKhoiPhuc,
    refetchOnWindowFocus: false,
  })

  if (chiTiet.isPending) return <Skeleton active paragraph={{ rows: 10 }} />
  if (chiTiet.isError) {
    // Slug sai mẫu (chữ hoa...) cũng là không có trang, không phải lỗi tạm để thử lại.
    if (laLoiApi(chiTiet.error) && LOI_KHONG_CO.has(chiTiet.error.ma_loi))
      return <Result status="404" title="Không tìm thấy sản phẩm" subTitle="Sản phẩm không tồn tại hoặc đã ngừng bán." extra={<Link to="/">Về trang chủ</Link>} />
    return <Alert type="error" showIcon title="Không tải được sản phẩm" action={<Button onClick={() => void chiTiet.refetch()}>Thử lại</Button>} />
  }
  const sp = chiTiet.data

  const thongTin = [
    ['Số đăng ký', sp.so_dang_ky],
    ['Dạng bào chế', sp.dang_bao_che],
    ['Quy cách', sp.quy_cach],
    ['Đối tượng sử dụng', sp.doi_tuong_su_dung],
    ['Nhà sản xuất', sp.nha_san_xuat],
    ['Thương hiệu', sp.thuong_hieu?.ten],
    ['Mã sản phẩm', sp.sku],
  ].filter((d): d is [string, string] => !!d[1])

  return (
    <>
      <Breadcrumb
        items={[
          { title: <Link to="/">Trang chủ</Link> },
          ...sp.duong_dan_danh_muc.map((m) => ({ title: <Link to={`/danh-muc/${m.slug}`}>{m.ten}</Link> })),
          { title: sp.ten },
        ]}
      />
      <Row gutter={[24, 24]} style={{ marginTop: 16 }}>
        <Col xs={24} md={10}>
          <ThuVien anh={sp.anh} ten={sp.ten} />
        </Col>
        <Col xs={24} md={14}>
          <Space orientation="vertical" size={12} style={{ width: '100%' }}>
            <Space size={8} wrap>
              <NhanTrangThai loai="loai_san_pham" giaTri={sp.loai_san_pham} />
              {sp.thuong_hieu && <Typography.Text type="secondary">{sp.thuong_hieu.ten}</Typography.Text>}
            </Space>
            <Typography.Title level={1} style={{ margin: 0, fontSize: 26 }}>{sp.ten}</Typography.Title>
            {sp.quy_cach && <Typography.Text type="secondary">{sp.quy_cach}</Typography.Text>}
            {sp.luu_y_khong_phai_thuoc && <Alert type="info" showIcon title={DONG_KHONG_PHAI_THUOC} />}
            <KhuMuaHang key={sp.id} sp={sp} />
          </Space>
        </Col>
      </Row>
      <Tabs
        style={{ marginTop: 24 }}
        items={[
          {
            key: 'thong-tin',
            label: 'Thông tin sản phẩm',
            children: thongTin.length ? (
              <Descriptions column={{ xs: 1, md: 2 }} bordered size="small" items={thongTin.map(([nhan, gia]) => ({ key: nhan, label: nhan, children: gia }))} />
            ) : (
              <Empty description="Chưa có thông tin" />
            ),
          },
          {
            key: 'thanh-phan',
            label: 'Thành phần',
            children: sp.thanh_phan.length ? (
              <Table
                size="small"
                pagination={false}
                rowKey="hoat_chat_id"
                dataSource={sp.thanh_phan}
                columns={[
                  { title: 'Hoạt chất', dataIndex: 'ten', key: 'ten' },
                  { title: 'Hàm lượng', dataIndex: 'ham_luong', key: 'ham_luong', render: (v: string | null) => v ?? '—' },
                ]}
              />
            ) : (
              <Empty description="Chưa có thông tin thành phần" />
            ),
          },
          { key: 'chuyen-mon', label: 'Chỉ định, liều dùng', children: <NoiDungChuyenMon nd={sp.noi_dung_chuyen_mon} /> },
          { key: 'danh-gia', label: `Đánh giá (${sp.danh_gia.so_luong})`, children: <DanhGia dg={sp.danh_gia} /> },
          { key: 'hoi-dap', label: 'Hỏi đáp', children: <HoiDapSanPham slug={sp.slug} /> },
        ]}
      />
      {sp.tuong_tu.length > 0 && (
        <section aria-label="Sản phẩm tương tự" style={{ marginTop: 24 }}>
          <Typography.Title level={3}>Sản phẩm tương tự</Typography.Title>
          <LuoiSanPham danhSach={sp.tuong_tu} nguon="goi_y_tuong_tu" />
        </section>
      )}
    </>
  )
}
