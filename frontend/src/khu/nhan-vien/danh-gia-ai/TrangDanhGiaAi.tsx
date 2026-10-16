import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Checkbox, Drawer, Input, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { HoiThoaiAnDanh } from '../../../components/HoiThoaiAnDanh'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { dinhDangNgay } from '../../../lib/dinhDang'

type Tom = components['schemas']['HoiThoaiAnDanhTom']
type ChiTiet = components['schemas']['HoiThoaiAnDanhChiTiet']
type Tin = components['schemas']['TinNhanAnDanh']

const KICH_THUOC = 20
const KHOA = ['noi-bo', 'danh-gia-ai'] as const

function DanhGiaTin({ hoiThoaiId, tin, onXong }: { hoiThoaiId: number; tin: Tin; onXong: (c: ChiTiet) => void }) {
  const { message } = App.useApp()
  const cuaToi = tin.danh_gia.find((d) => d.cua_toi)
  const [ghiChu, setGhiChu] = useState(cuaToi?.ghi_chu ?? '')
  const [dangSai, setDangSai] = useState(cuaToi?.ket_qua === 'sai')
  const [loi, setLoi] = useState<string | null>(null)
  const gui = useMutation({
    mutationFn: async (ketQua: 'dung' | 'sai') => {
      const r = await goi(() =>
        api.PUT('/api/v1/noi-bo/danh-gia-ai/{hoi_thoai_id}/tin-nhan/{tin_nhan_id}', {
          params: { path: { hoi_thoai_id: hoiThoaiId, tin_nhan_id: tin.id } },
          body: { ket_qua: ketQua, ghi_chu: ketQua === 'sai' ? ghiChu.trim() : null },
        }),
      )
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
      return r.data as ChiTiet
    },
    onSuccess: (c) => {
      setLoi(null)
      void message.success('Đã lưu đánh giá')
      onXong(c)
    },
    onError: (e: Error) => setLoi(e.message),
  })
  if (tin.vai_tro !== 'ai') return null
  return (
    <YeuCauQuyen ma="ai_answer.review" kieu="nut">
      <Space orientation="vertical" size={4} style={{ width: '100%', marginTop: 4 }}>
        <Space>
          <Button size="small" loading={gui.isPending && gui.variables === 'dung'} onClick={() => { setDangSai(false); gui.mutate('dung') }}>Đúng</Button>
          <Button size="small" danger loading={gui.isPending && gui.variables === 'sai'} onClick={() => (dangSai ? gui.mutate('sai') : setDangSai(true))}>Sai</Button>
        </Space>
        {dangSai && <Input.TextArea aria-label="Nội dung đúng" rows={2} maxLength={1000} placeholder="Ghi nội dung đúng (bắt buộc khi đánh dấu sai), sau đó bấm Sai lần nữa để lưu" value={ghiChu} onChange={(e) => setGhiChu(e.target.value)} />}
        {loi && <Alert type="error" showIcon title={loi} />}
      </Space>
    </YeuCauQuyen>
  )
}

/** DS12: hội thoại AI bị gắn cờ (hệ thống phát hiện nguy hiểm hoặc khách báo "không hữu ích"); dược sĩ đánh dấu đúng/sai. */
export default function TrangDanhGiaAi() {
  const qc = useQueryClient()
  const [trang, setTrang] = useState(1)
  const [chuaDanhGia, setChuaDanhGia] = useState(true)
  const [mo, setMo] = useState<number | null>(null)
  const ds = useQuery({
    queryKey: [...KHOA, 'ds', trang, chuaDanhGia],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/danh-gia-ai', { params: { query: { trang, kich_thuoc: KICH_THUOC, chua_danh_gia: chuaDanhGia } } })
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
  })
  const ct = useQuery({
    queryKey: [...KHOA, 'ct', mo],
    enabled: mo !== null,
    staleTime: Infinity,
    gcTime: 0,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/danh-gia-ai/{hoi_thoai_id}', { params: { path: { hoi_thoai_id: mo! } } })
      if (error || !data) throw error ?? new Error('Không mở được hội thoại')
      return data
    },
  })
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Đánh giá câu trả lời AI</Typography.Title>
      <Checkbox checked={chuaDanhGia} onChange={(e) => { setChuaDanhGia(e.target.checked); setTrang(1) }}>Chỉ hiện hội thoại chưa được dược sĩ đánh giá</Checkbox>
      {ds.isError && <Alert type="error" showIcon title="Không tải được danh sách" />}
      <Table<Tom>
        rowKey="id"
        size="small"
        loading={ds.isLoading}
        dataSource={ds.data?.du_lieu ?? []}
        locale={{ emptyText: 'Không có hội thoại nào bị gắn cờ' }}
        pagination={{ current: trang, pageSize: KICH_THUOC, total: ds.data?.tong ?? 0, showSizeChanger: false, onChange: setTrang }}
        columns={[
          { title: 'Thời điểm', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
          { title: 'Câu hỏi đầu', dataIndex: 'cau_hoi_dau', ellipsis: true },
          { title: 'Lý do', render: (_, r) => <Space size={4} wrap>{r.bi_gan_co && <Tag color="red">Dấu hiệu nguy hiểm</Tag>}{r.so_khach_bao_sai > 0 && <Tag color="orange">Khách báo sai: {r.so_khach_bao_sai}</Tag>}</Space> },
          { title: 'Đã đánh giá', dataIndex: 'so_duoc_si_danh_gia', align: 'right' },
          { title: '', render: (_, r) => <Button size="small" onClick={() => setMo(r.id)}>Xem</Button> },
        ]}
      />
      <Drawer title="Hội thoại bị gắn cờ" size={640} open={mo !== null} onClose={() => setMo(null)} destroyOnHidden>
        {ct.isError && <Alert type="error" showIcon title="Không mở được hội thoại" />}
        {ct.data && (
          <HoiThoaiAnDanh
            tin={ct.data.tin_nhan}
            hanhDong={(t) => (
              <DanhGiaTin
                key={`${t.id}-${t.danh_gia.length}`}
                hoiThoaiId={ct.data.id}
                tin={t}
                onXong={(c) => {
                  qc.setQueryData([...KHOA, 'ct', mo], c)
                  void qc.invalidateQueries({ queryKey: [...KHOA, 'ds'] })
                }}
              />
            )}
          />
        )}
      </Drawer>
    </Space>
  )
}
