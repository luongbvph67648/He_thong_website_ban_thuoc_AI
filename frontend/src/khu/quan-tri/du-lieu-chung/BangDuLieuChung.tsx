import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Input, Popconfirm, Space, Table, Tooltip, Typography } from 'antd'
import type { ColumnsType, SorterResult } from 'antd/es/table/interface'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { thongDiepChung } from '../../../api/goi'
import type { LoiApi } from '../../../api/loi'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { danhSach, sua, tao, xoa } from './goiApi'
import { FormDuLieuChung } from './FormDuLieuChung'
import { docSapXep, KHOA_QUERY_DU_LIEU_CHUNG, lyDoKhongXoa, TRUONG_SAP_XEP, type BanGhi, type CauHinhNhom, type GiaTriForm } from './nhom'

const KICH_THUOC = 20

/** Bảng của một nhóm (AD05): tìm, sắp xếp, phân trang đồng bộ URL; thêm, sửa, xóa. Dược sĩ (chỉ xem) không thấy nút ghi. */
export function BangDuLieuChung({ nhom }: { nhom: CauHinhNhom }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [tham, datTham] = useSearchParams()
  const [mo, setMo] = useState<{ ban: BanGhi | null } | null>(null)

  const q = tham.get('q') ?? ''
  const sapXep = docSapXep(tham.get('sap_xep'))
  const trang = Math.max(1, Number(tham.get('trang')) || 1)
  const sapXepGui = sapXep ? `${sapXep.giam ? '-' : ''}${sapXep.truong}` : undefined

  const doiThamSo = (thayDoi: Record<string, string | undefined>) => {
    const moi = new URLSearchParams(tham)
    for (const [k, v] of Object.entries({ trang: undefined, ...thayDoi })) {
      if (v) moi.set(k, v)
      else moi.delete(k)
    }
    datTham(moi, { replace: true })
  }

  const ds = useQuery({
    queryKey: [...KHOA_QUERY_DU_LIEU_CHUNG, nhom.ma, { q, sapXepGui, trang }],
    queryFn: async () => {
      const kq = await danhSach(nhom.ma, { q: q || undefined, sap_xep: sapXepGui, trang, kich_thuoc: KICH_THUOC })
      if (!kq.ok) throw kq.loi ?? new Error('mang')
      return kq.data
    },
  })

  const lamMoi = () => queryClient.invalidateQueries({ queryKey: KHOA_QUERY_DU_LIEU_CHUNG })

  const luu = useMutation({
    mutationFn: ({ ban, giaTri }: { ban: BanGhi | null; giaTri: GiaTriForm }) => (ban ? sua(nhom.ma, ban.id, giaTri) : tao(nhom.ma, giaTri)),
  })

  const luuForm = async (giaTri: GiaTriForm): Promise<LoiApi | null> => {
    if (!mo) return null
    const kq = await luu.mutateAsync({ ban: mo.ban, giaTri })
    if (!kq.ok) {
      const gan = kq.loi && (kq.loi.ma_loi === 'TRUNG_DU_LIEU' || kq.loi.ma_loi === 'DU_LIEU_KHONG_HOP_LE')
      if (!gan) void message.error(thongDiepChung(kq.loi))
      return kq.loi ?? { ma_loi: 'MANG', thong_diep: thongDiepChung(null), chi_tiet: null }
    }
    setMo(null)
    void message.success(mo.ban ? `Đã lưu ${nhom.danhTu}` : `Đã thêm ${nhom.danhTu}`)
    await lamMoi()
    return null
  }

  const xoaBan = useMutation({
    mutationFn: (ban: BanGhi) => {
      if (nhom.ma === 'hoat-chat') throw new Error('Hoạt chất không có thao tác xóa') // nút Xóa không hiện ở nhóm này
      return xoa(nhom.ma, ban.id)
    },
    onSuccess: async (kq, ban) => {
      if (!kq.ok) void message.error(thongDiepChung(kq.loi))
      else void message.success(`Đã xóa “${ban.ten}”`)
      await lamMoi() // kể cả khi lỗi: số liệu trên màn hình có thể đã cũ
    },
  })

  const thuTuCot = (truong: (typeof TRUONG_SAP_XEP)[number]) => (sapXep?.truong === truong ? (sapXep.giam ? ('descend' as const) : ('ascend' as const)) : null)

  const cot: ColumnsType<BanGhi> = [
    { title: 'Tên', key: 'ten', dataIndex: 'ten', sorter: true, sortOrder: thuTuCot('ten') },
    ...(nhom.ma === 'thuong-hieu'
      ? [{ title: 'Logo', key: 'logo_url', render: (_: unknown, b: BanGhi) => (b.logo_url ? <img src={b.logo_url} alt={`Logo ${b.ten}`} referrerPolicy="no-referrer" style={{ maxHeight: 32, maxWidth: 96 }} /> : '—') }]
      : []),
    ...(nhom.ma === 'nha-san-xuat' ? [{ title: 'Quốc gia', key: 'quoc_gia', render: (_: unknown, b: BanGhi) => b.quoc_gia ?? '—' }] : []),
    ...(nhom.ma === 'hoat-chat'
      ? [
          { title: 'Tên khác', key: 'ten_khac', render: (_: unknown, b: BanGhi) => b.ten_khac ?? '—' },
          { title: 'Mô tả', key: 'mo_ta', render: (_: unknown, b: BanGhi) => (b.mo_ta ? <Typography.Paragraph ellipsis={{ rows: 2, tooltip: b.mo_ta }} style={{ marginBottom: 0, maxWidth: 360 }}>{b.mo_ta}</Typography.Paragraph> : '—') },
        ]
      : []),
    { title: 'Số sản phẩm', key: 'so_san_pham', dataIndex: 'so_san_pham', align: 'right', sorter: true, sortOrder: thuTuCot('so_san_pham') },
    { title: 'Ngày tạo', key: 'created_at', sorter: true, sortOrder: thuTuCot('created_at'), render: (_, b) => dinhDangNgay(b.created_at) },
    {
      title: 'Thao tác',
      key: 'thao_tac',
      render: (_, b) => {
        const lyDo = lyDoKhongXoa(nhom, b)
        return (
          <YeuCauQuyen ma="master_data.manage" kieu="nut">
            <Space size={0}>
              <Button type="link" size="small" onClick={() => setMo({ ban: b })}>
                Sửa
              </Button>
              {nhom.choPhepXoa && (
                <Tooltip title={lyDo}>
                  <span>
                    <Popconfirm
                      title={`Xóa ${nhom.danhTu} “${b.ten}”?`}
                      description="Chỉ xóa được khi chưa được dùng ở đâu."
                      okText="Xóa"
                      okButtonProps={{ danger: true }}
                      cancelText="Hủy"
                      disabled={lyDo !== null}
                      onConfirm={() => xoaBan.mutate(b)}
                    >
                      <Button type="link" size="small" danger disabled={lyDo !== null || xoaBan.isPending}>
                        Xóa
                      </Button>
                    </Popconfirm>
                  </span>
                </Tooltip>
              )}
            </Space>
          </YeuCauQuyen>
        )
      },
    },
  ]

  return (
    <div>
      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search
          key={`${nhom.ma}-${q}`}
          defaultValue={q}
          allowClear
          placeholder={nhom.ma === 'hoat-chat' ? 'Tìm theo tên hoặc tên khác' : 'Tìm theo tên'}
          style={{ width: 340 }}
          onSearch={(v) => doiThamSo({ q: v.trim() || undefined })}
        />
        <YeuCauQuyen ma="master_data.manage" kieu="nut">
          <Button type="primary" onClick={() => setMo({ ban: null })}>
            {`Thêm ${nhom.danhTu}`}
          </Button>
        </YeuCauQuyen>
      </Space>

      {ds.isError && <Alert type="error" showIcon title={`Không tải được danh sách ${nhom.danhTu}`} style={{ marginBottom: 16 }} />}
      <Table<BanGhi>
        rowKey="id"
        columns={cot}
        loading={ds.isPending}
        dataSource={ds.data?.du_lieu ?? []}
        pagination={{
          current: trang,
          pageSize: KICH_THUOC,
          total: ds.data?.tong ?? 0,
          showSizeChanger: false,
          onChange: (t) => doiThamSo({ trang: t > 1 ? String(t) : undefined }),
        }}
        onChange={(_, __, sorter, extra) => {
          // antd gọi `onChange` này cho cả lần bấm trang (sau `pagination.onChange`); xử lý ở đây sẽ xóa `trang` vừa đặt.
          if (extra.action !== 'sort') return
          const s = Array.isArray(sorter) ? sorter[0] : (sorter as SorterResult<BanGhi>)
          const truong = String(s?.columnKey ?? '')
          doiThamSo({ sap_xep: s?.order && TRUONG_SAP_XEP.some((t) => t === truong) ? `${s.order === 'descend' ? '-' : ''}${truong}` : undefined })
        }}
        locale={{ emptyText: `Không có ${nhom.danhTu} phù hợp`, triggerAsc: 'Bấm để sắp xếp tăng dần', triggerDesc: 'Bấm để sắp xếp giảm dần', cancelSort: 'Bấm để bỏ sắp xếp' }}
      />

      <FormDuLieuChung nhom={nhom} mo={mo} dangLuu={luu.isPending} onLuu={luuForm} onDong={() => setMo(null)} />
    </div>
  )
}
