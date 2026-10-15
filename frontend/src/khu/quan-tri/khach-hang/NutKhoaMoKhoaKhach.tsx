import { useMutation, useQueryClient } from '@tanstack/react-query'
import { App, Button, Input, Modal, Popconfirm, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { dangBiKhoa, KHOA_QUERY_KHACH, type TrangThaiTaiKhoanKhach } from './khach'

interface Props {
  khach: TrangThaiTaiKhoanKhach & { id: number; ho_ten: string }
  /** Kiểu nút: dạng liên kết trong bảng, hoặc nút thường ở trang chi tiết. */
  kieu?: 'link' | 'default'
}

/**
 * Khóa (kèm lý do không bắt buộc, chỉ ghi vào nhật ký) hoặc mở khóa một khách. Chỉ hiện với mức đầy đủ của
 * `customer.manage`; backend vẫn kiểm tra quyền và đòi người thực hiện là Admin.
 */
export function NutKhoaMoKhoaKhach({ khach, kieu = 'link' }: Props) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [moHop, setMoHop] = useState(false)
  const [lyDo, setLyDo] = useState('')
  const duongDan = { params: { path: { khach_id: khach.id } } }

  const hanhDong = useMutation({
    mutationFn: (loai: 'khoa' | 'mo-khoa') =>
      loai === 'khoa'
        ? goi(() => api.POST('/api/v1/noi-bo/khach-hang/{khach_id}/khoa', { ...duongDan, body: { ly_do: lyDo.trim() || null } }))
        : goi(() => api.POST('/api/v1/noi-bo/khach-hang/{khach_id}/mo-khoa', duongDan)),
    onSuccess: async (kq, loai) => {
      setMoHop(false)
      if (!kq.ok) return void message.error(thongDiepChung(kq.loi))
      setLyDo('')
      await queryClient.invalidateQueries({ queryKey: KHOA_QUERY_KHACH })
      void message.success(`${loai === 'khoa' ? 'Đã khóa' : 'Đã mở khóa'} ${khach.ho_ten}`)
    },
  })

  return (
    <YeuCauQuyen ma="customer.manage" kieu="nut">
      {dangBiKhoa(khach) ? (
        <Popconfirm
          title={`Mở khóa ${khach.ho_ten}?`}
          description="Khách đăng nhập lại được ngay."
          okText="Mở khóa"
          cancelText="Hủy"
          onConfirm={() => hanhDong.mutate('mo-khoa')}
        >
          <Button type={kieu} size={kieu === 'link' ? 'small' : 'middle'} loading={hanhDong.isPending}>
            Mở khóa
          </Button>
        </Popconfirm>
      ) : (
        <>
          <Button type={kieu} size={kieu === 'link' ? 'small' : 'middle'} danger onClick={() => setMoHop(true)}>
            Khóa
          </Button>
          <Modal
            title={`Khóa tài khoản của ${khach.ho_ten}?`}
            open={moHop}
            okText="Khóa tài khoản"
            okButtonProps={{ danger: true }}
            cancelText="Hủy"
            confirmLoading={hanhDong.isPending}
            onOk={() => hanhDong.mutate('khoa')}
            onCancel={() => setMoHop(false)}
            destroyOnHidden
          >
            <Typography.Paragraph>
              Khách bị đăng xuất khỏi mọi thiết bị và không đăng nhập được cho tới khi bạn mở khóa.
            </Typography.Paragraph>
            <label htmlFor={`ly-do-khoa-${khach.id}`}>Lý do (không bắt buộc, ghi vào nhật ký hệ thống)</label>
            <Input.TextArea
              id={`ly-do-khoa-${khach.id}`}
              value={lyDo}
              onChange={(e) => setLyDo(e.target.value)}
              maxLength={300}
              showCount
              rows={3}
              style={{ marginTop: 8 }}
            />
          </Modal>
        </>
      )}
    </YeuCauQuyen>
  )
}
