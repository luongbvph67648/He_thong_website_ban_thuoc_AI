"""Mẫu SMS của luồng đơn thuốc (không dấu, gọn). Không chứa tên thuốc hay dữ liệu sức khỏe."""


def sms_link_xac_nhan(ma_don: str, link: str, han: str) -> str:
    return f"Nha thuoc AI: don {ma_don} tu don thuoc cua ban da san sang. Xac nhan va thanh toan truoc {han} tai {link}"


def sms_tu_choi(ma_yeu_cau: str) -> str:
    """Không nêu lý do: lý do là văn bản tự do của dược sĩ, có thể chứa thông tin sức khỏe."""
    return (
        f"Nha thuoc AI: yeu cau don thuoc {ma_yeu_cau} chua duoc chap nhan. Vui long lien he nha thuoc de duoc ho tro."
    )
