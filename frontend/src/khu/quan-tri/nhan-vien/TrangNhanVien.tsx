import { PlusOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Alert, Button, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag, Tooltip, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { loiTheoTruong, type LoiApi } from '../../../api/loi'
import type { components } from '../../../api/schema'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { chuanHoaSdt } from '../../../lib/dienThoai'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { usePhien } from '../../../stores/phien'

type NhanVien = components['schemas']['NhanVienQuanTriDoc']
type TrangThai = 'hoat_dong' | 'bi_khoa'

const KICH_THUOC = 20
const KHOA_QUERY = ['noi-bo', 'nhan-vien'] as const
const TEN_VAI_TRO: Record<string, string> = { ADMIN: 'Quản trị', PHARMACIST: 'Dược sĩ bán hàng', WAREHOUSE: 'Nhân viên kho' }

/** Email nhận mật khẩu tạm (đã che) trong phản hồi tạo/đặt lại; Admin không bao giờ nhận chính mật khẩu. */
function guiDenCua(data: unknown): string | null {
  if (typeof data !== 'object' || data === null || !('gui_den' in data)) return null
  return typeof data.gui_den === 'string' ? data.gui_den : null
}

interface FormNhanVien {
  ho_ten: string
  email: string
  so_dien_thoai?: string
  vai_tro: string
}

/** Quản lý tài khoản nhân viên (AD01): danh sách có tìm/lọc, tạo, sửa, gán vai trò, khóa/mở, đặt lại mật khẩu, xóa mềm. */
export default function TrangNhanVien() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [tham, datTham] = useSearchParams()
  const [formMo, setFormMo] = useState<{ sua?: NhanVien } | null>(null)
  const [form] = Form.useForm<FormNhanVien>()
  const toi = usePhien((s) => s.hoSo?.id)

  const q = tham.get('q') ?? ''
  const vaiTro = tham.get('vai_tro') ?? undefined
  const trangThai = (tham.get('trang_thai') as TrangThai | null) ?? undefined
  const trang = Math.max(1, Number(tham.get('trang')) || 1)
  const doiThamSo = (thayDoi: Record<string, string | undefined>) => {
    const moi = new URLSearchParams(tham)
    for (const [k, v] of Object.entries({ trang: undefined, ...thayDoi })) {
      if (v) moi.set(k, v)
      else moi.delete(k)
    }
    datTham(moi, { replace: true })
  }

  const vaiTroQuery = useQuery({
    queryKey: ['noi-bo', 'vai-tro', 'danh-sach'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/vai-tro')
      if (error) throw error
      return data
    },
  })
  const danhSach = useQuery({
    queryKey: [...KHOA_QUERY, { q, vaiTro, trangThai, trang }],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/nhan-vien', {
        params: { query: { q: q || undefined, vai_tro: vaiTro, trang_thai: trangThai, trang, kich_thuoc: KICH_THUOC } },
      })
      if (error) throw error
      return data
    },
  })

  const lamMoi = () => queryClient.invalidateQueries({ queryKey: KHOA_QUERY })
  const baoLoi = (loi: LoiApi | null) => void message.error(thongDiepChung(loi))

  const luu = useMutation({
    mutationFn: async (gia_tri: FormNhanVien) => {
      const sua = formMo?.sua
      const than = { ho_ten: gia_tri.ho_ten.trim(), email: gia_tri.email.trim(), so_dien_thoai: gia_tri.so_dien_thoai?.trim() || null, vai_tro: gia_tri.vai_tro }
      return sua
        ? goi(() => api.PATCH('/api/v1/noi-bo/nhan-vien/{nhan_vien_id}', { params: { path: { nhan_vien_id: sua.id } }, body: than }))
        : goi(() => api.POST('/api/v1/noi-bo/nhan-vien', { body: than }))
    },
    onSuccess: async (kq, gia_tri) => {
      if (!kq.ok) {
        const theoTruong = kq.loi ? loiTheoTruong(kq.loi) : {}
        if (Object.keys(theoTruong).length > 0) {
          form.setFields(Object.entries(theoTruong).map(([name, loi]) => ({ name: name as keyof FormNhanVien, errors: [loi] })))
        } else baoLoi(kq.loi)
        return
      }
      const dangSua = formMo?.sua
      setFormMo(null)
      await lamMoi()
      const guiDen = guiDenCua(kq.data)
      if (!dangSua && guiDen) {
        void message.success(`Đã tạo ${gia_tri.ho_ten.trim()}. Mật khẩu tạm đã gửi tới email ${guiDen}`, 6)
      } else void message.success(`Đã lưu ${gia_tri.ho_ten.trim()}`)
    },
  })

  const hanhDong = useMutation({
    mutationFn: async ({ loai, nv }: { loai: 'khoa' | 'mo-khoa' | 'dat-lai' | 'xoa'; nv: NhanVien }) => {
      const path = { params: { path: { nhan_vien_id: nv.id } } }
      switch (loai) {
        case 'khoa':
          return goi(() => api.POST('/api/v1/noi-bo/nhan-vien/{nhan_vien_id}/khoa', path))
        case 'mo-khoa':
          return goi(() => api.POST('/api/v1/noi-bo/nhan-vien/{nhan_vien_id}/mo-khoa', path))
        case 'dat-lai':
          return goi(() => api.POST('/api/v1/noi-bo/nhan-vien/{nhan_vien_id}/dat-lai-mat-khau', path))
        case 'xoa':
          return goi(() => api.DELETE('/api/v1/noi-bo/nhan-vien/{nhan_vien_id}', path))
      }
    },
    onSuccess: async (kq, { loai, nv }) => {
      if (!kq.ok) return baoLoi(kq.loi)
      await lamMoi()
      const guiDen = guiDenCua(kq.data)
      if (loai === 'dat-lai' && guiDen) {
        void message.success(`Đã đặt lại mật khẩu ${nv.ho_ten}. Mật khẩu tạm đã gửi tới email ${guiDen}`, 6)
      } else {
        const viec = { khoa: 'Đã khóa', 'mo-khoa': 'Đã mở khóa', xoa: 'Đã xóa', 'dat-lai': 'Đã đặt lại mật khẩu' }[loai]
        void message.success(`${viec} ${nv.ho_ten}`)
      }
    },
  })

  const moForm = (sua?: NhanVien) => {
    form.resetFields()
    if (sua) form.setFieldsValue({ ho_ten: sua.ho_ten, email: sua.email, so_dien_thoai: sua.so_dien_thoai ?? '', vai_tro: sua.vai_tro.ma })
    setFormMo({ sua })
  }

  const luaChonVaiTro = (vaiTroQuery.data ?? []).map((v) => ({ value: v.ma, label: TEN_VAI_TRO[v.ma] ?? v.ten }))

  const cot: ColumnsType<NhanVien> = [
    { title: 'Mã', dataIndex: 'ma_nhan_vien', width: 90 },
    { title: 'Họ và tên', dataIndex: 'ho_ten' },
    { title: 'Email', dataIndex: 'email' },
    { title: 'Số điện thoại', dataIndex: 'so_dien_thoai', render: (v: string | null) => v ?? '—' },
    { title: 'Vai trò', render: (_, nv) => TEN_VAI_TRO[nv.vai_tro.ma] ?? nv.vai_tro.ten },
    {
      title: 'Trạng thái',
      render: (_, nv) => (
        <Space size={4} wrap>
          {nv.trang_thai === 'bi_khoa' ? <Tag color="red">Bị khóa</Tag> : <Tag color="green">Hoạt động</Tag>}
          {nv.khoa_den && new Date(nv.khoa_den) > new Date() && <Tag color="orange">Khóa tạm đến {dinhDangNgay(nv.khoa_den, 'ngayGio')}</Tag>}
          {nv.phai_doi_mat_khau && <Tag>Chờ đổi mật khẩu</Tag>}
        </Space>
      ),
    },
    {
      title: 'Thao tác',
      render: (_, nv) => {
        const laToi = nv.id === toi
        const khongTu = (nut: React.ReactNode) => (laToi ? <Tooltip title="Bạn không thể tự thao tác trên chính mình">{nut}</Tooltip> : nut)
        return (
          <YeuCauQuyen ma="staff.manage" kieu="nut">
            <Space size={0} wrap>
              <Button type="link" size="small" onClick={() => moForm(nv)}>
                Sửa
              </Button>
              {nv.trang_thai === 'bi_khoa' ? (
                <Button type="link" size="small" onClick={() => hanhDong.mutate({ loai: 'mo-khoa', nv })}>
                  Mở khóa
                </Button>
              ) : (
                khongTu(
                  <Popconfirm
                    title={`Khóa tài khoản ${nv.ho_ten}?`}
                    description="Nhân viên bị đăng xuất khỏi mọi thiết bị và không đăng nhập được nữa."
                    okText="Khóa"
                    cancelText="Hủy"
                    disabled={laToi}
                    onConfirm={() => hanhDong.mutate({ loai: 'khoa', nv })}
                  >
                    <Button type="link" size="small" danger disabled={laToi}>
                      Khóa
                    </Button>
                  </Popconfirm>,
                )
              )}
              {khongTu(
                <Popconfirm
                  title={`Đặt lại mật khẩu của ${nv.ho_ten}?`}
                  description="Mật khẩu cũ mất hiệu lực, nhân viên bị đăng xuất khỏi mọi thiết bị và phải đổi mật khẩu tạm khi đăng nhập."
                  okText="Đặt lại"
                  cancelText="Hủy"
                  disabled={laToi}
                  onConfirm={() => hanhDong.mutate({ loai: 'dat-lai', nv })}
                >
                  <Button type="link" size="small" disabled={laToi}>
                    Đặt lại mật khẩu
                  </Button>
                </Popconfirm>,
              )}
              {khongTu(
                <Popconfirm
                  title={`Xóa ${nv.ho_ten}?`}
                  description="Tài khoản bị ẩn và không đăng nhập được; dữ liệu cũ do nhân viên này lập vẫn được giữ."
                  okText="Xóa"
                  okButtonProps={{ danger: true }}
                  cancelText="Hủy"
                  disabled={laToi}
                  onConfirm={() => hanhDong.mutate({ loai: 'xoa', nv })}
                >
                  <Button type="link" size="small" danger disabled={laToi}>
                    Xóa
                  </Button>
                </Popconfirm>,
              )}
            </Space>
          </YeuCauQuyen>
        )
      },
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, gap: 12, flexWrap: 'wrap' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          Nhân viên
        </Typography.Title>
        <YeuCauQuyen ma="staff.manage" kieu="nut">
          <Button type="primary" icon={<PlusOutlined />} onClick={() => moForm()}>
            Thêm nhân viên
          </Button>
        </YeuCauQuyen>
      </div>

      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search
          key={q}
          defaultValue={q}
          allowClear
          placeholder="Tìm theo tên, email, mã nhân viên"
          style={{ width: 320 }}
          onSearch={(v) => doiThamSo({ q: v.trim() || undefined })}
        />
        <Select
          allowClear
          placeholder="Vai trò"
          style={{ width: 200 }}
          value={vaiTro}
          options={luaChonVaiTro}
          onChange={(v: string | undefined) => doiThamSo({ vai_tro: v })}
          aria-label="Lọc theo vai trò"
        />
        <Select
          allowClear
          placeholder="Trạng thái"
          style={{ width: 160 }}
          value={trangThai}
          options={[
            { value: 'hoat_dong', label: 'Hoạt động' },
            { value: 'bi_khoa', label: 'Bị khóa' },
          ]}
          onChange={(v: string | undefined) => doiThamSo({ trang_thai: v })}
          aria-label="Lọc theo trạng thái"
        />
      </Space>

      {danhSach.isError && <Alert type="error" showIcon title="Không tải được danh sách nhân viên" style={{ marginBottom: 16 }} />}
      <Table<NhanVien>
        rowKey="id"
        columns={cot}
        loading={danhSach.isPending}
        dataSource={danhSach.data?.du_lieu ?? []}
        pagination={{
          current: trang,
          pageSize: KICH_THUOC,
          total: danhSach.data?.tong ?? 0,
          showSizeChanger: false,
          onChange: (t) => doiThamSo({ trang: t > 1 ? String(t) : undefined }),
        }}
        locale={{ emptyText: 'Không có nhân viên phù hợp' }}
      />

      <Modal
        title={formMo?.sua ? `Sửa ${formMo.sua.ho_ten}` : 'Thêm nhân viên'}
        open={formMo !== null}
        onCancel={() => setFormMo(null)}
        okText="Lưu"
        cancelText="Hủy"
        confirmLoading={luu.isPending}
        onOk={() => form.submit()}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" requiredMark={false} onFinish={(v) => luu.mutate(v)}>
          <Form.Item name="ho_ten" label="Họ và tên" rules={[{ required: true, whitespace: true, message: 'Vui lòng nhập họ và tên' }, { max: 150, message: 'Tối đa 150 ký tự' }]}>
            <Input autoComplete="off" />
          </Form.Item>
          <Form.Item name="email" label="Email đăng nhập" normalize={(v: string) => v?.trim()} rules={[{ required: true, message: 'Vui lòng nhập email' }, { type: 'email', message: 'Email không hợp lệ' }]}>
            <Input autoComplete="off" />
          </Form.Item>
          <Form.Item
            name="so_dien_thoai"
            label="Số điện thoại (không bắt buộc)"
            rules={[{ validator: (_, v: string) => (!v?.trim() || chuanHoaSdt(v) ? Promise.resolve() : Promise.reject(new Error('Số điện thoại không hợp lệ (cần số di động Việt Nam 10 chữ số)'))) }]}
          >
            <Input inputMode="tel" autoComplete="off" />
          </Form.Item>
          <Form.Item
            name="vai_tro"
            label="Vai trò"
            rules={[{ required: true, message: 'Vui lòng chọn vai trò' }]}
            extra={
              formMo?.sua
                ? formMo.sua.id === toi
                  ? 'Bạn không thể tự đổi vai trò của mình.'
                  : 'Đổi vai trò sẽ đăng xuất nhân viên khỏi mọi thiết bị để nạp lại quyền.'
                : 'Mật khẩu tạm được sinh tự động và hiện một lần sau khi tạo.'
            }
          >
            <Select options={luaChonVaiTro} disabled={formMo?.sua?.id === toi} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
