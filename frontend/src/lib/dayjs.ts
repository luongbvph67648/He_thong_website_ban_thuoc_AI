import dayjs from 'dayjs'
import 'dayjs/locale/vi'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'

// Ant Design (DatePicker...) dùng dayjs: đặt tiếng Việt và múi giờ Việt Nam làm mặc định.
dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.locale('vi')
dayjs.tz.setDefault('Asia/Ho_Chi_Minh')

export default dayjs
