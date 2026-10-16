import { DeleteOutlined, UploadOutlined } from '@ant-design/icons'
import { Alert, Button, Space } from 'antd'
import { useRef, useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { lienKetAnToan } from '../../../lib/lienKet'
import { loiTepAnh, KIEU_ANH } from '../../../lib/anhTep'

interface Props {
  /** Địa chỉ ảnh hiện tại (trống là chưa có). */
  value: string
  onChange: (url: string) => void
  /** Thư mục vùng công khai: banner hoặc ảnh bìa bài viết. */
  khu: 'banner' | 'bai-viet'
  id?: string
  disabled?: boolean
  loi?: string
}

/** Chọn ảnh từ máy, tải lên vùng công khai rồi trả URL. Ảnh có thể mồ côi nếu form không được lưu (job dọn ở T3.2). */
export function NutTaiAnh({ value, onChange, khu, id, disabled, loi }: Props) {
  const oChon = useRef<HTMLInputElement>(null)
  const [dangTai, setDangTai] = useState(false)
  const [thongDiep, setThongDiep] = useState<string | null>(null)
  const anh = lienKetAnToan(value)

  const chon = async (tep: File | undefined) => {
    if (oChon.current) oChon.current.value = '' // cho phép chọn lại đúng tệp vừa bị từ chối
    if (!tep) return
    const sai = loiTepAnh(tep)
    if (sai) return setThongDiep(`${tep.name}: ${sai}`)
    setThongDiep(null)
    setDangTai(true)
    const bodySerializer = () => {
      const form = new FormData()
      form.append('tep', tep)
      return form
    }
    const kq = await goi(() =>
      khu === 'banner'
        ? api.POST('/api/v1/noi-bo/banner/anh', { body: { tep: '' }, bodySerializer })
        : api.POST('/api/v1/noi-bo/bai-viet/anh', { body: { tep: '' }, bodySerializer }),
    )
    setDangTai(false)
    if (!kq.ok) return setThongDiep(thongDiepChung(kq.loi))
    onChange(kq.data.url)
  }

  return (
    <Space orientation="vertical" size={8} style={{ width: '100%' }}>
      {thongDiep && <Alert type="error" showIcon title={thongDiep} closable={{ onClose: () => setThongDiep(null) }} />}
      {anh && <img src={anh} alt="Ảnh đã chọn" style={{ maxWidth: '100%', maxHeight: 160, objectFit: 'contain', background: '#fafafa' }} />}
      <Space wrap>
        <input
          id={id}
          ref={oChon}
          type="file"
          accept={KIEU_ANH.join(',')}
          hidden
          aria-label="Chọn ảnh để tải lên"
          onChange={(e) => void chon(e.target.files?.[0])}
        />
        <Button icon={<UploadOutlined />} loading={dangTai} disabled={disabled} onClick={() => oChon.current?.click()}>
          {value ? 'Đổi ảnh' : 'Tải ảnh lên'}
        </Button>
        {value && (
          <Button icon={<DeleteOutlined />} disabled={disabled || dangTai} onClick={() => onChange('')}>
            Bỏ ảnh
          </Button>
        )}
        <span style={{ color: 'rgba(0,0,0,.45)' }}>JPEG, PNG hoặc WebP, tối đa 5 MB</span>
      </Space>
      {loi && <span style={{ color: '#ff4d4f' }}>{loi}</span>}
    </Space>
  )
}
