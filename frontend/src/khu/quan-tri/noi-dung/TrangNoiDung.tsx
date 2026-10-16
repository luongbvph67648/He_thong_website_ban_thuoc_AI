import { Tabs, Typography } from 'antd'
import { coQuyen } from '../../../lib/quyen'
import { usePhien } from '../../../stores/phien'
import { TabBaiViet } from './TabBaiViet'
import { TabBanner } from './TabBanner'
import { LOAI_BAI } from './noiDungWeb'

/** Nội dung website (AD07): banner, bài viết sức khỏe, chính sách, hỏi đáp thường gặp. Ghi chỉ Admin (`cms.manage` đầy đủ). */
export default function TrangNoiDung() {
  const quyen = usePhien((s) => s.quyen)
  const coGhi = coQuyen(quyen, 'cms.manage')
  return (
    <>
      <Typography.Title level={3}>Nội dung website</Typography.Title>
      <Tabs
        destroyOnHidden
        items={[
          { key: 'banner', label: 'Banner', children: <TabBanner coGhi={coGhi} /> },
          ...LOAI_BAI.map((l) => ({ key: l.value, label: l.label, children: <TabBaiViet loai={l.value} coGhi={coGhi} /> })),
        ]}
      />
    </>
  )
}
