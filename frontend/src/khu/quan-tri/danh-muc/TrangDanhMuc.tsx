import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Empty, Popconfirm, Space, Tag, Tooltip, Tree, Typography } from 'antd'
import type { DataNode, TreeProps } from 'antd/es/tree'
import type { Key } from 'react'
import { useMemo, useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { LoiApi } from '../../../api/loi'
import type { components } from '../../../api/schema'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { coQuyen } from '../../../lib/quyen'
import { usePhien } from '../../../stores/phien'
import { giuNguyenViTri, idCoCon, lyDoKhongThaDuoc, SO_CAP_TOI_DA, tinhViTriTha, type HuongTha } from './cayDanhMuc'
import { KHOA_QUERY_DANH_MUC } from './danhMuc'
import { FormDanhMuc, type GiaTriFormDanhMuc } from './FormDanhMuc'

type Nut = components['schemas']['DanhMucNut']
type TrangThaiForm = { kieu: 'tao'; cha: Nut | null } | { kieu: 'sua'; nut: Nut } | null

const huongTuViTri = (tuongDoi: number): HuongTha => (tuongDoi < 0 ? 'truoc' : tuongDoi > 0 ? 'sau' : 'trong')

/** Quản lý cây danh mục (AD03): thêm, sửa, ẩn/hiện, xóa mềm, kéo thả để sắp xếp hoặc chuyển cha. Tối đa 3 cấp. */
export default function TrangDanhMuc() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const quyen = usePhien((s) => s.quyen)
  const coGhi = coQuyen(quyen, 'category.manage')
  const [form, setForm] = useState<TrangThaiForm>(null)
  const [moRong, setMoRong] = useState<Key[] | null>(null)

  const cay = useQuery({
    queryKey: KHOA_QUERY_DANH_MUC,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/danh-muc')
      if (error) throw error
      return data
    },
  })
  const nut = cay.data ?? []
  // Mở sẵn cả cây ở lần tải đầu; sau đó giữ nguyên lựa chọn của người dùng (kể cả khi dữ liệu được làm mới).
  const khoaMoRong = moRong ?? idCoCon(nut)

  const lamMoi = () => queryClient.invalidateQueries({ queryKey: KHOA_QUERY_DANH_MUC })

  const luu = useMutation({
    mutationFn: async ({ trangThai, giaTri }: { trangThai: NonNullable<TrangThaiForm>; giaTri: GiaTriFormDanhMuc }) =>
      trangThai.kieu === 'tao'
        ? goi(() => api.POST('/api/v1/noi-bo/danh-muc', { body: { ...giaTri, danh_muc_cha_id: trangThai.cha?.id ?? null } }))
        : goi(() => api.PATCH('/api/v1/noi-bo/danh-muc/{danh_muc_id}', { params: { path: { danh_muc_id: trangThai.nut.id } }, body: giaTri })),
  })

  const luuForm = async (giaTri: GiaTriFormDanhMuc): Promise<LoiApi | null> => {
    if (!form) return null
    const kq = await luu.mutateAsync({ trangThai: form, giaTri })
    if (!kq.ok) {
      if (!kq.loi || (kq.loi.ma_loi !== 'TRUNG_DU_LIEU' && kq.loi.ma_loi !== 'DU_LIEU_KHONG_HOP_LE')) void message.error(thongDiepChung(kq.loi))
      return kq.loi ?? { ma_loi: 'MANG', thong_diep: thongDiepChung(null), chi_tiet: null }
    }
    if (form.kieu === 'tao' && form.cha) setMoRong([...new Set([...khoaMoRong, form.cha.id])])
    setForm(null)
    void message.success(form.kieu === 'tao' ? 'Đã thêm danh mục' : 'Đã lưu danh mục')
    await lamMoi()
    return null
  }

  const doiHienThi = useMutation({
    mutationFn: (n: Nut) =>
      goi(() => api.PATCH('/api/v1/noi-bo/danh-muc/{danh_muc_id}', { params: { path: { danh_muc_id: n.id } }, body: { dang_hien_thi: !n.dang_hien_thi } })),
    onSuccess: async (kq, n) => {
      if (!kq.ok) return void message.error(thongDiepChung(kq.loi))
      void message.success(n.dang_hien_thi ? `Đã ẩn “${n.ten}”` : `Đã hiện “${n.ten}”`)
      await lamMoi()
    },
  })

  const xoa = useMutation({
    mutationFn: (n: Nut) => goi(() => api.DELETE('/api/v1/noi-bo/danh-muc/{danh_muc_id}', { params: { path: { danh_muc_id: n.id } } })),
    onSuccess: async (kq, n) => {
      if (!kq.ok) {
        void message.error(thongDiepChung(kq.loi))
        return void (await lamMoi()) // số liệu trên màn hình có thể đã cũ
      }
      void message.success(`Đã xóa “${n.ten}”`)
      await lamMoi()
    },
  })

  const datViTri = useMutation({
    mutationFn: ({ id, chaId, viTri }: { id: number; chaId: number | null; viTri: number }) =>
      goi(() => api.PUT('/api/v1/noi-bo/danh-muc/{danh_muc_id}/vi-tri', { params: { path: { danh_muc_id: id } }, body: { danh_muc_cha_id: chaId, vi_tri: viTri } })),
    onSuccess: async (kq, v) => {
      if (!kq.ok) {
        void message.error(thongDiepChung(kq.loi))
        return void (await lamMoi())
      }
      queryClient.setQueryData(KHOA_QUERY_DANH_MUC, kq.data)
      if (v.chaId !== null) setMoRong([...new Set([...khoaMoRong, v.chaId])])
    },
  })

  const dangBan = luu.isPending || doiHienThi.isPending || xoa.isPending || datViTri.isPending

  const duLieuCay = useMemo<DataNode[]>(() => {
    const doi = (ds: Nut[]): DataNode[] =>
      ds.map((n) => ({
        key: n.id,
        title: <DongDanhMuc nut={n} coGhi={coGhi} dangBan={dangBan} onThemCon={() => setForm({ kieu: 'tao', cha: n })} onSua={() => setForm({ kieu: 'sua', nut: n })} onDoiHienThi={() => doiHienThi.mutate(n)} onXoa={() => xoa.mutate(n)} />,
        children: doi(n.con),
      }))
    return doi(nut)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nut, coGhi, dangBan])

  const choPhepTha: TreeProps['allowDrop'] = ({ dragNode, dropNode, dropPosition }) =>
    lyDoKhongThaDuoc(nut, Number(dragNode.key), Number(dropNode.key), huongTuViTri(dropPosition)) === null

  const khiTha: TreeProps['onDrop'] = (info) => {
    const idKeo = Number(info.dragNode.key)
    const idDich = Number(info.node.key)
    const tuongDoi = info.dropPosition - Number(info.node.pos.split('-').pop())
    const huong: HuongTha = info.dropToGap ? huongTuViTri(tuongDoi) : 'trong'
    const lyDo = lyDoKhongThaDuoc(nut, idKeo, idDich, huong)
    if (lyDo) return void message.warning(lyDo)
    const vt = tinhViTriTha(nut, idKeo, idDich, huong)
    if (!vt || giuNguyenViTri(nut, idKeo, vt)) return
    datViTri.mutate({ id: idKeo, chaId: vt.chaId, viTri: vt.viTri })
  }

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }} align="start" wrap>
        <div>
          <Typography.Title level={3} style={{ marginBottom: 4 }}>
            Danh mục
          </Typography.Title>
          <Typography.Text type="secondary">
            Tối đa {SO_CAP_TOI_DA} cấp. {coGhi ? 'Kéo thả để sắp xếp hoặc chuyển sang danh mục khác.' : ''}
          </Typography.Text>
        </div>
        <YeuCauQuyen ma="category.manage" kieu="nut">
          <Button type="primary" onClick={() => setForm({ kieu: 'tao', cha: null })}>
            Thêm danh mục gốc
          </Button>
        </YeuCauQuyen>
      </Space>

      {cay.isError && <Alert type="error" showIcon title="Không tải được danh mục" style={{ marginBottom: 16 }} />}
      {cay.isSuccess && nut.length === 0 ? (
        <Empty description="Chưa có danh mục nào" />
      ) : (
        <Tree
          blockNode
          showLine
          selectable={false}
          draggable={coGhi && !dangBan ? { icon: false } : false}
          allowDrop={choPhepTha}
          onDrop={khiTha}
          treeData={duLieuCay}
          expandedKeys={khoaMoRong}
          onExpand={(k) => setMoRong(k)}
        />
      )}

      <FormDanhMuc
        mo={
          form === null
            ? null
            : form.kieu === 'tao'
              ? { kieu: 'tao', chaTen: form.cha?.ten ?? null }
              : { kieu: 'sua', ban: { id: form.nut.id, ten: form.nut.ten, anh_url: form.nut.anh_url, dang_hien_thi: form.nut.dang_hien_thi } }
        }
        dangLuu={luu.isPending}
        onLuu={luuForm}
        onDong={() => setForm(null)}
      />
    </div>
  )
}

interface DongProps {
  nut: Nut
  coGhi: boolean
  dangBan: boolean
  onThemCon: () => void
  onSua: () => void
  onDoiHienThi: () => void
  onXoa: () => void
}

function DongDanhMuc({ nut, coGhi, dangBan, onThemCon, onSua, onDoiHienThi, onXoa }: DongProps) {
  const lyDoKhongXoa =
    nut.so_san_pham > 0 ? `Danh mục còn ${nut.so_san_pham} sản phẩm` : nut.con.length > 0 ? `Danh mục còn ${nut.con.length} danh mục con` : null
  return (
    <Space size="small" wrap>
      <Typography.Text strong={nut.cap === 1} type={nut.dang_hien_thi ? undefined : 'secondary'}>
        {nut.ten}
      </Typography.Text>
      {!nut.dang_hien_thi && <Tag>Đang ẩn</Tag>}
      <Tag color="blue">{nut.so_san_pham} sản phẩm</Tag>
      {coGhi && (
        <Space size={0} onClick={(e) => e.stopPropagation()}>
          {nut.cap < SO_CAP_TOI_DA && (
            <Button type="link" size="small" disabled={dangBan} onClick={onThemCon}>
              Thêm con
            </Button>
          )}
          <Button type="link" size="small" disabled={dangBan} onClick={onSua}>
            Sửa
          </Button>
          <Tooltip title={nut.dang_hien_thi ? 'Ẩn danh mục này và các danh mục con khỏi cửa hàng' : 'Cho khách thấy lại danh mục này'}>
            <Button type="link" size="small" disabled={dangBan} onClick={onDoiHienThi}>
              {nut.dang_hien_thi ? 'Ẩn' : 'Hiện'}
            </Button>
          </Tooltip>
          <Tooltip title={lyDoKhongXoa}>
            <span>
              <Popconfirm
                title={`Xóa danh mục “${nut.ten}”?`}
                description="Danh mục bị xóa khỏi cây; đường dẫn (slug) vẫn được giữ chỗ."
                okText="Xóa"
                okButtonProps={{ danger: true }}
                cancelText="Hủy"
                onConfirm={onXoa}
                disabled={lyDoKhongXoa !== null}
              >
                <Button type="link" size="small" danger disabled={dangBan || lyDoKhongXoa !== null}>
                  Xóa
                </Button>
              </Popconfirm>
            </span>
          </Tooltip>
        </Space>
      )}
    </Space>
  )
}
