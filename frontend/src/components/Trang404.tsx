import { Button, Result } from 'antd'
import { Link } from 'react-router-dom'

export function Trang404({ veTrang = '/', nhanVe = 'Về trang chủ' }: { veTrang?: string; nhanVe?: string }) {
  return (
    <Result
      status="404"
      title="Không tìm thấy trang"
      subTitle="Đường dẫn không tồn tại hoặc đã được chuyển đi."
      extra={
        <Link to={veTrang}>
          <Button type="primary">{nhanVe}</Button>
        </Link>
      }
    />
  )
}
