import { Result } from 'antd'

/** Trang giữ chỗ cho chức năng chưa làm; ghi rõ mã chức năng (spec 05) để biết task nào sẽ thay thế. */
export function TrangDangXayDung({ ten, chucNang }: { ten: string; chucNang: readonly string[] }) {
  return <Result status="info" title={ten} subTitle={`Chức năng ${chucNang.join(', ')} đang được xây dựng.`} />
}
