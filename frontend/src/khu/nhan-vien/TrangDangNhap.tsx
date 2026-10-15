import { Alert, Card, Typography } from 'antd'

/** Đăng nhập nội bộ dùng chung cho dược sĩ, kho và Admin (spec 09 mục 1). Form thật làm ở T1.3 (NV01). */
export default function TrangDangNhapNoiBo() {
  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', padding: 16 }}>
      <Card style={{ width: 420, maxWidth: '100%' }}>
        <Typography.Title level={3}>Đăng nhập nội bộ</Typography.Title>
        <Alert type="info" showIcon title="Chức năng đăng nhập (NV01) đang được xây dựng." />
      </Card>
    </div>
  )
}
