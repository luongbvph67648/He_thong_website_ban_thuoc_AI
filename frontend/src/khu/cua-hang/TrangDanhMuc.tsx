import { useQuery } from '@tanstack/react-query'
import { Alert, Breadcrumb, Button, Col, Empty, Pagination, Result, Row, Select, Skeleton, Space, Typography } from 'antd'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../../api/client'
import { laLoiApi } from '../../api/loi'
import { BoLocSanPham } from './BoLocSanPham'
import {
  capNhatThamSo,
  docBoLoc,
  KHOA_QUERY_CUA_HANG,
  KICH_THUOC_TRANG,
  LOI_KHONG_CO,
  SAP_XEP,
  taoQuerySanPham,
  type SapXep,
  type ThayDoiLoc,
} from './cuaHang'
import { LuoiSanPham } from './TheSanPham'

/** Danh sách sản phẩm của một danh mục (gồm danh mục con) kèm bộ lọc và sắp xếp (KVL02). */
export default function TrangDanhMucCuaHang() {
  const { slug = '' } = useParams()
  const [tham, datTham] = useSearchParams()
  const boLoc = docBoLoc(tham)
  const doiLoc = (thayDoi: ThayDoiLoc) => datTham(capNhatThamSo(tham, thayDoi), { replace: true })

  const danhMuc = useQuery({
    queryKey: [...KHOA_QUERY_CUA_HANG, 'danh-muc', slug],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/danh-muc/{slug}', { params: { path: { slug } } })
      if (error || !data) throw error ?? new Error('Không tải được danh mục')
      return data
    },
  })
  const tuyChon = useQuery({
    queryKey: [...KHOA_QUERY_CUA_HANG, 'bo-loc', slug],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/bo-loc-san-pham', { params: { query: { danh_muc: slug } } })
      if (error || !data) throw new Error('Không tải được bộ lọc')
      return data
    },
    enabled: danhMuc.isSuccess,
  })
  const query = taoQuerySanPham(boLoc, slug)
  const danhSach = useQuery({
    queryKey: [...KHOA_QUERY_CUA_HANG, 'san-pham', query],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/san-pham', { params: { query } })
      if (error || !data) throw new Error('Không tải được danh sách sản phẩm')
      return data
    },
    enabled: danhMuc.isSuccess,
    placeholderData: (truoc) => truoc, // đổi trang/bộ lọc không nháy trắng
  })

  if (danhMuc.isPending) return <Skeleton active paragraph={{ rows: 8 }} />
  if (danhMuc.isError) {
    const khongCo = laLoiApi(danhMuc.error) && LOI_KHONG_CO.has(danhMuc.error.ma_loi)
    return khongCo ? (
      <Result
        status="404"
        title="Không tìm thấy danh mục"
        subTitle="Danh mục không tồn tại hoặc đang tạm ẩn."
        extra={<Link to="/">Về trang chủ</Link>}
      />
    ) : (
      <Alert
        type="error"
        showIcon
        title="Không tải được danh mục"
        action={<Button onClick={() => void danhMuc.refetch()}>Thử lại</Button>}
      />
    )
  }
  const d = danhMuc.data

  return (
    <>
      <Breadcrumb
        items={[
          { title: <Link to="/">Trang chủ</Link> },
          ...d.duong_dan.map((m, i) => ({
            title: i === d.duong_dan.length - 1 ? m.ten : <Link to={`/danh-muc/${m.slug}`}>{m.ten}</Link>,
          })),
        ]}
      />
      <Typography.Title level={2} style={{ marginTop: 8 }}>
        {d.ten}
      </Typography.Title>
      {d.con.length > 0 && (
        <Space size={[8, 8]} wrap style={{ marginBottom: 16 }} aria-label="Danh mục con">
          {d.con.map((c) => (
            <Link key={c.id} to={`/danh-muc/${c.slug}`}>
              <Button size="small">{c.ten}</Button>
            </Link>
          ))}
        </Space>
      )}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={6}>
          <BoLocSanPham boLoc={boLoc} tuyChon={tuyChon.data} onDoi={doiLoc} onXoa={() => datTham(new URLSearchParams(), { replace: true })} />
        </Col>
        <Col xs={24} lg={18}>
          <Space style={{ justifyContent: 'space-between', width: '100%', marginBottom: 12 }} wrap>
            <Typography.Text type="secondary" role="status">
              {danhSach.data ? `${danhSach.data.tong} sản phẩm` : 'Đang tải…'}
            </Typography.Text>
            <Select<SapXep>
              aria-label="Sắp xếp"
              value={boLoc.sapXep}
              options={[...SAP_XEP]}
              style={{ minWidth: 160 }}
              onChange={(x) => doiLoc({ sapXep: x })}
            />
          </Space>
          {danhSach.isError ? (
            <Alert
              type="error"
              showIcon
              title="Không tải được danh sách sản phẩm"
              action={<Button onClick={() => void danhSach.refetch()}>Thử lại</Button>}
            />
          ) : danhSach.isPending ? (
            <Skeleton active paragraph={{ rows: 6 }} />
          ) : danhSach.data.du_lieu.length === 0 && danhSach.data.tong > 0 ? (
            <Empty description="Trang này không có sản phẩm">
              <Button onClick={() => doiLoc({ trang: 1 })}>Về trang 1</Button>
            </Empty>
          ) : danhSach.data.du_lieu.length === 0 ? (
            <Empty description={boLoc.conHang || boLoc.loai || boLoc.thuongHieu.length ? 'Không có sản phẩm phù hợp bộ lọc' : 'Danh mục chưa có sản phẩm'} />
          ) : (
            <>
              <LuoiSanPham danhSach={danhSach.data.du_lieu} nguon="danh_muc" />
              {danhSach.data.tong > KICH_THUOC_TRANG && (
                <Pagination
                  style={{ marginTop: 16, textAlign: 'center' }}
                  current={boLoc.trang}
                  pageSize={KICH_THUOC_TRANG}
                  total={danhSach.data.tong}
                  showSizeChanger={false}
                  onChange={(trang) => {
                    doiLoc({ trang })
                    window.scrollTo?.({ top: 0 })
                  }}
                />
              )}
            </>
          )}
        </Col>
      </Row>
    </>
  )
}
