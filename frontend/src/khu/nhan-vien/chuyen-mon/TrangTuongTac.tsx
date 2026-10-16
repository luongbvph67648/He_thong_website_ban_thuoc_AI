import { PlusOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Input, Popconfirm, Select, Space, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { loiTheoTruong } from '../../../api/loi'
import { NhanTrangThai } from '../../../components/NhanTrangThai'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { nhanTrangThai } from '../../../lib/trangThai'
import { FormTuongTac } from './FormTuongTac'
import { KHOA_QUERY_TUONG_TAC, MUC_DO, noiDungRaApi, O_THEO_TRUONG_API, type GiaTriTuongTac, type LoiTuongTac, type MucDoTuongTac, type TuongTac } from './tuongTac'

const KICH_THUOC = 20

/** Tương tác giữa các hoạt chất (DS10): bảng, thêm, sửa, xóa. Dùng cho cảnh báo ở đơn thuốc, POS, tư vấn và AI. */
export default function TrangTuongTac() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [tham, datTham] = useSearchParams()
  const q = tham.get('q') ?? ''
  const mucDo = MUC_DO.find((m) => m === tham.get('muc_do'))
  const trang = Math.max(1, Number(tham.get('trang')) || 1)
  const [form, setForm] = useState<{ kieu: 'tao' } | { kieu: 'sua'; ban: TuongTac } | null>(null)

  const doiThamSo = (thayDoi: Record<string, string | undefined>) => {
    const moi = new URLSearchParams(tham)
    for (const [k, v] of Object.entries({ trang: undefined, ...thayDoi })) {
      if (v) moi.set(k, v)
      else moi.delete(k)
    }
    datTham(moi, { replace: true })
  }

  const danhSach = useQuery({
    queryKey: [...KHOA_QUERY_TUONG_TAC, 'danh-sach', { q, mucDo, trang }],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/tuong-tac', { params: { query: { q: q || undefined, muc_do: mucDo, trang, kich_thuoc: KICH_THUOC } } })
      if (error) throw error
      return data
    },
  })
  const lamMoi = () => queryClient.invalidateQueries({ queryKey: KHOA_QUERY_TUONG_TAC })

  const luu = useMutation({
    mutationFn: async ({ g, ban }: { g: GiaTriTuongTac; ban: TuongTac | null }) =>
      ban === null
        ? goi(() => api.POST('/api/v1/noi-bo/tuong-tac', { body: { hoat_chat_1_id: g.hoat_chat_1!.value, hoat_chat_2_id: g.hoat_chat_2!.value, ...noiDungRaApi(g) } }))
        : goi(() =>
            api.PUT('/api/v1/noi-bo/tuong-tac/{hoat_chat_1_id}/{hoat_chat_2_id}', {
              params: { path: { hoat_chat_1_id: ban.hoat_chat_a_id, hoat_chat_2_id: ban.hoat_chat_b_id } },
              body: { phien_ban: ban.phien_ban, ...noiDungRaApi(g) },
            }),
          ),
  })
  const xoa = useMutation({
    mutationFn: (t: TuongTac) =>
      goi(() =>
        api.DELETE('/api/v1/noi-bo/tuong-tac/{hoat_chat_1_id}/{hoat_chat_2_id}', {
          params: { path: { hoat_chat_1_id: t.hoat_chat_a_id, hoat_chat_2_id: t.hoat_chat_b_id }, query: { phien_ban: t.phien_ban } },
        }),
      ),
  })

  const luuForm = async (g: GiaTriTuongTac): Promise<{ theoO: LoiTuongTac; chung: string | null } | null> => {
    if (!form) return null
    const ban = form.kieu === 'sua' ? form.ban : null
    const kq = await luu.mutateAsync({ g, ban })
    if (!kq.ok) {
      if (kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI' && ban) {
        // Người khác vừa sửa bản ghi này: lấy bản mới để lần lưu sau dùng phien_ban mới, giữ chữ đang gõ (QĐ-13).
        await lamMoi()
        const moi = await goi(() =>
          api.GET('/api/v1/noi-bo/tuong-tac/{hoat_chat_1_id}/{hoat_chat_2_id}', { params: { path: { hoat_chat_1_id: ban.hoat_chat_a_id, hoat_chat_2_id: ban.hoat_chat_b_id } } }),
        )
        if (!moi.ok) {
          setForm(null)
          void message.error('Tương tác này không còn nữa (có người vừa xóa hoặc đổi).')
          return null
        }
        setForm({ kieu: 'sua', ban: moi.data })
        return { theoO: {}, chung: 'Tương tác này vừa được người khác thay đổi. Giá trị bạn đang gõ vẫn còn nguyên; bấm Lưu lần nữa để ghi đè bản của họ, hoặc Hủy để xem bản mới.' }
      }
      const theoTruong = kq.loi ? loiTheoTruong(kq.loi) : {}
      const theoO: LoiTuongTac = {}
      for (const [truong, thongDiep] of Object.entries(theoTruong)) {
        const o = O_THEO_TRUONG_API[truong]
        if (o) theoO[o] = thongDiep
      }
      return { theoO, chung: Object.keys(theoO).length > 0 ? null : thongDiepChung(kq.loi) }
    }
    setForm(null)
    void message.success(ban === null ? 'Đã thêm tương tác' : 'Đã lưu tương tác')
    await lamMoi()
    return null
  }

  const xoaMot = async (t: TuongTac) => {
    const kq = await xoa.mutateAsync(t)
    if (!kq.ok) {
      void message.error(thongDiepChung(kq.loi))
      return void (await lamMoi())
    }
    void message.success('Đã xóa tương tác')
    await lamMoi()
  }

  const cot: ColumnsType<TuongTac> = [
    { title: 'Hoạt chất thứ nhất', dataIndex: 'ten_hoat_chat_a', key: 'a' },
    { title: 'Hoạt chất thứ hai', dataIndex: 'ten_hoat_chat_b', key: 'b' },
    { title: 'Mức độ', key: 'muc_do', render: (_, t) => <NhanTrangThai loai="muc_do_tuong_tac" giaTri={t.muc_do} /> },
    { title: 'Khuyến cáo', dataIndex: 'khuyen_cao', key: 'khuyen_cao', ellipsis: true },
    {
      title: 'Cập nhật',
      key: 'cap_nhat',
      render: (_, t) => (
        <span>
          {t.nguoi_cap_nhat ?? '—'}
          {t.updated_at && <Typography.Text type="secondary"> · {dinhDangNgay(t.updated_at, 'ngayGio')}</Typography.Text>}
        </span>
      ),
    },
    {
      title: 'Thao tác',
      key: 'tt',
      render: (_, t) => (
        <YeuCauQuyen ma="content.professional.edit" kieu="nut">
          <Space>
            <Button size="small" onClick={() => setForm({ kieu: 'sua', ban: t })}>
              Sửa
            </Button>
            <Popconfirm title="Xóa tương tác này?" description="Cảnh báo cho cặp hoạt chất này sẽ không còn." okText="Xóa" cancelText="Hủy" okButtonProps={{ danger: true }} onConfirm={() => xoaMot(t)}>
              <Button size="small" danger disabled={xoa.isPending}>
                Xóa
              </Button>
            </Popconfirm>
          </Space>
        </YeuCauQuyen>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }} align="start" wrap>
        <Typography.Title level={3} style={{ margin: 0 }}>
          Tương tác thuốc
        </Typography.Title>
        <YeuCauQuyen ma="content.professional.edit" kieu="nut">
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setForm({ kieu: 'tao' })}>
            Thêm tương tác
          </Button>
        </YeuCauQuyen>
      </Space>
      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search key={q} defaultValue={q} allowClear placeholder="Tìm theo tên hoạt chất" style={{ width: 300 }} onSearch={(v) => doiThamSo({ q: v.trim() || undefined })} />
        <Select
          allowClear
          placeholder="Mức độ"
          style={{ width: 180 }}
          aria-label="Lọc theo mức độ"
          value={mucDo}
          options={MUC_DO.map((m) => ({ value: m, label: nhanTrangThai('muc_do_tuong_tac', m).nhan }))}
          onChange={(v: MucDoTuongTac | undefined) => doiThamSo({ muc_do: v })}
        />
      </Space>
      {danhSach.isError && <Alert type="error" showIcon title="Không tải được danh sách tương tác" style={{ marginBottom: 16 }} />}
      <Table<TuongTac>
        rowKey={(t) => `${t.hoat_chat_a_id}-${t.hoat_chat_b_id}`}
        columns={cot}
        loading={danhSach.isPending}
        dataSource={danhSach.data?.du_lieu ?? []}
        pagination={{ current: trang, pageSize: KICH_THUOC, total: danhSach.data?.tong ?? 0, showSizeChanger: false, onChange: (t) => doiThamSo({ trang: t > 1 ? String(t) : undefined }) }}
        locale={{ emptyText: 'Chưa có tương tác nào' }}
      />
      <FormTuongTac mo={form} dangLuu={luu.isPending} onLuu={luuForm} onDong={() => setForm(null)} />
    </div>
  )
}
