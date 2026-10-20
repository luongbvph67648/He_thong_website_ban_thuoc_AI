"""Mẫu email cấp mật khẩu tạm cho nhân viên: mật khẩu chỉ tới hộp thư của chính nhân viên, Admin không nhìn thấy."""

from html import escape


def email_mat_khau_tam(ho_ten: str, mat_khau_tam: str, *, dat_lai: bool) -> tuple[str, str]:
    """(tiêu đề, nội dung HTML). Mật khẩu không đưa vào tiêu đề vì tiêu đề hiện ở thông báo trên màn hình khóa."""
    tieu_de = "Mật khẩu tạm mới của bạn" if dat_lai else "Tài khoản nhân viên Nhà thuốc AI"
    mo_dau = "Mật khẩu của bạn vừa được đặt lại" if dat_lai else "Tài khoản nhân viên của bạn đã được tạo"
    html = (
        f"<p>Xin chào {escape(ho_ten)},</p>"
        f"<p>{mo_dau}. Mật khẩu tạm:</p>"
        f'<p style="font-size:20px;letter-spacing:2px"><strong>{escape(mat_khau_tam)}</strong></p>'
        "<p>Bạn sẽ được yêu cầu đổi mật khẩu ngay ở lần đăng nhập đầu tiên. "
        "Không chia sẻ mật khẩu này cho bất kỳ ai, kể cả quản trị viên.</p>"
    )
    return tieu_de, html
