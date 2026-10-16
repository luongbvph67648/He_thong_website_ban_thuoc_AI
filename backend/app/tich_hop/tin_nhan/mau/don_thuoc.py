"""Mẫu SMS của luồng đơn thuốc (không dấu, gọn). Không chứa tên thuốc hay dữ liệu sức khỏe."""


def sms_link_xac_nhan(ma_don: str, link: str, han: str) -> str:
    return f"Nha thuoc AI: don {ma_don} tu don thuoc cua ban da san sang. Xac nhan va thanh toan truoc {han} tai {link}"


def sms_tu_choi(ma_yeu_cau: str, ly_do: str) -> str:
    return f"Nha thuoc AI: yeu cau don thuoc {ma_yeu_cau} chua duoc chap nhan. Ly do: {ly_do}"
