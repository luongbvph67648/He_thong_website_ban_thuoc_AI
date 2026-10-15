"""Mẫu tin nhắn OTP. SMS không dấu và gọn trong một tin (160 ký tự)."""


def sms_otp(ma: str, so_phut: int) -> str:
    return f"Nha thuoc AI: ma xac thuc cua ban la {ma}. Co hieu luc {so_phut} phut. Khong chia se ma nay cho ai."


def sms_da_co_tai_khoan() -> str:
    """Gửi khi ai đó xin OTP đăng ký bằng số đã có tài khoản: chỉ chủ số đọc được, phản hồi của API thì giống hệt."""
    return "Nha thuoc AI: so dien thoai nay da co tai khoan. Hay dang nhap hoac chon Quen mat khau neu can."


def email_otp(ma: str, so_phut: int) -> tuple[str, str]:
    """(tiêu đề, nội dung HTML). Mã không đưa vào tiêu đề vì tiêu đề hiện ở thông báo trên màn hình khóa."""
    tieu_de = "Mã xác thực Nhà thuốc AI"
    html = (
        "<p>Mã xác thực của bạn là:</p>"
        f'<p style="font-size:24px;letter-spacing:4px"><strong>{ma}</strong></p>'
        f"<p>Mã có hiệu lực trong {so_phut} phút. Vui lòng không chia sẻ mã này cho bất kỳ ai.</p>"
    )
    return tieu_de, html
