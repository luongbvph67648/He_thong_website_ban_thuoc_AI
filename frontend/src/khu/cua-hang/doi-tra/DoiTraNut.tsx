import { InboxOutlined } from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Form, Input, InputNumber, Modal, Select, Table, Upload } from 'antd'
import type { UploadFile } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangTien } from '../../../lib/dinhDang'
import { loiTepBangChung, NHAN_LY_DO_DOI_TRA, TEP_BANG_CHUNG, type LyDoDoiTra } from '../../../lib/doiTra'

type DongDon = components['schemas']['DongDonRa']

interface FormDoiTra {
  ly_do: LyDoDoiTra
  mo_ta?: string
  tep: UploadFile[]
}

/** KTV09: nút và form yêu cầu đổi trả trong chi tiết đơn đã giao (chọn dòng và số lượng trả, lý do, ảnh/video). */
export default function DoiTraNut({ maDon, dong }: { maDon: string; dong: DongDon[] }) {
  const { message } = App.useApp()
  const dieuHuong = useNavigate()
  const qc = useQueryClient()
  const [mo, setMo] = useState(false)
  const [form] = Form.useForm<FormDoiTra>()
  const [soTra, setSoTra] = useState<Record<number, number>>({})
  const [loi, setLoi] = useState<string | null>(null)
  const [dang, setDang] = useState(false)

  async function gui(v: FormDoiTra) {
    const chon = Object.entries(soTra).filter(([, n]) => n > 0).map(([id, n]) => ({ ct_don_hang_id: Number(id), so_luong: n }))
    if (chon.length === 0) return setLoi('Chọn ít nhất một sản phẩm cần trả')
    const files = v.tep.map((f) => f.originFileObj).filter((f): f is NonNullable<typeof f> => !!f)
    setDang(true)
    setLoi(null)
    const r = await goi(() =>
      api.POST('/api/v1/toi/don-hang/{ma_don}/doi-tra', {
        params: { path: { ma_don: maDon } },
        body: { dong: '', ly_do: v.ly_do, tep: [] },
        bodySerializer: () => {
          const fd = new FormData()
          fd.append('dong', JSON.stringify(chon))
          fd.append('ly_do', v.ly_do)
          if (v.mo_ta?.trim()) fd.append('mo_ta', v.mo_ta.trim())
          files.forEach((f) => fd.append('tep', f))
          return fd
        },
      }),
    )
    setDang(false)
    if (!r.ok) return setLoi(thongDiepChung(r.loi))
    void message.success('Đã gửi yêu cầu đổi trả')
    void qc.invalidateQueries({ queryKey: ['doi-tra'] })
    setMo(false)
    dieuHuong('/tai-khoan/doi-tra')
  }

  return (
    <>
      <Button onClick={() => setMo(true)}>Yêu cầu đổi trả</Button>
      <Modal title={`Đổi trả đơn ${maDon}`} open={mo} onCancel={() => setMo(false)} okText="Gửi yêu cầu" cancelText="Đóng" confirmLoading={dang} onOk={() => form.submit()} width={680} destroyOnHidden>
        {loi && <Alert type="error" showIcon title={loi} style={{ marginBottom: 12 }} />}
        <Alert type="info" showIcon style={{ marginBottom: 12 }} title="Chỉ nhận đổi trả khi lỗi thuộc về nhà thuốc (giao sai, sai số lượng, hư hỏng, hết hạn hoặc cận hạn)." />
        <Table<DongDon>
          size="small"
          pagination={false}
          rowKey={(d) => String(d.id)}
          dataSource={dong}
          columns={[
            { title: 'Sản phẩm', render: (_, d) => `${d.ten_san_pham} (${d.ten_don_vi})` },
            { title: 'Đã mua', dataIndex: 'so_luong', align: 'right' },
            { title: 'Thành tiền', align: 'right', render: (_, d) => dinhDangTien(d.thanh_tien) },
            {
              title: 'Số lượng trả',
              render: (_, d) => (
                <InputNumber aria-label={`Số lượng trả ${d.ten_san_pham}`} min={0} max={d.so_luong} value={soTra[d.id ?? 0] ?? 0} onChange={(v) => setSoTra((s) => ({ ...s, [d.id ?? 0]: v ?? 0 }))} />
              ),
            },
          ]}
        />
        <Form form={form} layout="vertical" style={{ marginTop: 16 }} onFinish={(v) => void gui(v)} initialValues={{ tep: [] }}>
          <Form.Item name="ly_do" label="Lý do" rules={[{ required: true, message: 'Chọn lý do' }]}>
            <Select placeholder="Chọn lý do" options={Object.entries(NHAN_LY_DO_DOI_TRA).map(([value, label]) => ({ value, label }))} />
          </Form.Item>
          <Form.Item name="mo_ta" label="Mô tả"><Input.TextArea rows={3} maxLength={1000} showCount /></Form.Item>
          <Form.Item
            name="tep"
            label="Ảnh hoặc video mở hàng"
            valuePropName="fileList"
            getValueFromEvent={(e: { fileList: UploadFile[] }) => e.fileList}
            rules={[{ validator: (_, v: UploadFile[]) => (v?.length ? Promise.resolve() : Promise.reject(new Error('Cần ít nhất một ảnh hoặc video'))) }]}
            extra="Ảnh JPEG/PNG/WebP tối đa 5 MB, video MP4 tối đa 30 MB; tối đa 8 tệp."
          >
            <Upload.Dragger
              multiple
              listType="picture"
              maxCount={8}
              accept={TEP_BANG_CHUNG.join(',')}
              beforeUpload={(f) => {
                const l = loiTepBangChung(f)
                if (l) {
                  setLoi(l)
                  return Upload.LIST_IGNORE
                }
                return false
              }}
            >
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p>Bấm hoặc kéo ảnh/video vào đây</p>
            </Upload.Dragger>
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
