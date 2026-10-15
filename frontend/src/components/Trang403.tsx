import { Button, Result } from 'antd'
import { Link } from 'react-router-dom'

export function Trang403() {
  return (
    <Result
      status="403"
      title="Bạn không có quyền truy cập trang này"
      subTitle="Tài khoản của bạn chưa được cấp quyền cho chức năng này. Liên hệ quản trị viên nếu bạn cho rằng đây là nhầm lẫn."
      extra={
        <Link to="/">
          <Button type="primary">Về trang chủ</Button>
        </Link>
      }
    />
  )
}
