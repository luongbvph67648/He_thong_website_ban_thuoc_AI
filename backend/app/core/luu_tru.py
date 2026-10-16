"""Lưu file (spec 08 mục 6): vùng CÔNG KHAI cho ảnh sản phẩm, banner, bài viết.

Bản dev ghi vào thư mục `LUU_TRU_THU_MUC`; thay bằng S3/MinIO sau này qua cùng giao diện (`luu`, `doc`, `xoa`).
Vùng riêng tư (ảnh đơn thuốc, chứng từ hoàn tiền, URL ký) làm ở các task dùng đến nó.

- Kiểu file được nhận dạng theo NỘI DUNG (magic bytes), không tin tên file hay `Content-Type` của client.
- Tên file lưu là UUID + đuôi theo kiểu đã nhận dạng; khóa (`san-pham/<uuid>.jpg`) chỉ gồm ký tự an toàn, nên không thể
  trỏ ra ngoài thư mục lưu trữ (`..`, đường dẫn tuyệt đối).
- File được ghi TRƯỚC khi giao dịch cơ sở dữ liệu kết thúc; `xoa_neu_hoan_tac` dọn file mồ côi nếu giao dịch bị hủy, và
  `xoa_sau_commit` chỉ xóa file thật sau khi giao dịch xóa bản ghi đã commit.
"""

import asyncio
import logging
import re
import uuid
from pathlib import Path

from sqlalchemy import event

from app.core.config import BACKEND_DIR, settings

logger = logging.getLogger(__name__)

TOI_DA_ANH_BYTE = 5 * 1024 * 1024
"""Ảnh tối đa 5 MB (spec 06 mục 7)."""

KIEU_ANH = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
KIEU_THEO_DUOI = {duoi: kieu for kieu, duoi in KIEU_ANH.items()}

TIEN_TO_URL_CONG_KHAI = "/api/v1/tep/"

_KHOA_HOP_LE = re.compile(r"^[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)*\.(jpg|png|webp)$")


def nhan_dang_anh(noi_dung: bytes) -> str | None:
    """Kiểu MIME thật của ảnh (jpeg, png, webp) theo byte đầu file, hoặc `None` nếu không phải ba kiểu đó."""
    if noi_dung[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if noi_dung[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if noi_dung[:4] == b"RIFF" and noi_dung[8:12] == b"WEBP":
        return "image/webp"
    return None


def khoa_hop_le(khoa: str) -> bool:
    return len(khoa) <= 200 and _KHOA_HOP_LE.fullmatch(khoa) is not None


def url_cong_khai(khoa: str) -> str:
    return f"{TIEN_TO_URL_CONG_KHAI}{khoa}"


def khoa_tu_url_cong_khai(url: str) -> str | None:
    """Khóa file của một URL công khai do hệ thống tạo ra, hoặc `None` nếu URL không có dạng đó."""
    if not url.startswith(TIEN_TO_URL_CONG_KHAI):
        return None
    khoa = url.removeprefix(TIEN_TO_URL_CONG_KHAI)
    return khoa if khoa_hop_le(khoa) else None


class LuuTruCucBo:
    """Vùng công khai trên đĩa cục bộ."""

    def __init__(self, goc: Path) -> None:
        self.goc = goc.resolve()

    def _duong_dan(self, khoa: str) -> Path:
        if not khoa_hop_le(khoa):
            raise ValueError(f"Khóa file không hợp lệ: {khoa!r}")
        vung = (self.goc / "cong_khai").resolve()
        duong_dan = (vung / khoa).resolve()
        # Phải nằm trong VÙNG CÔNG KHAI chứ không chỉ trong thư mục lưu trữ: symlink từ `cong_khai/` sang `rieng_tu/`
        # (ảnh đơn thuốc) vẫn ở trong thư mục lưu trữ. Khóa đã qua regex nên chỉ symlink mới có thể làm ra ngoài.
        if not duong_dan.is_relative_to(vung):
            raise ValueError(f"Khóa file trỏ ra ngoài vùng công khai: {khoa!r}")
        return duong_dan

    async def luu(self, thu_muc: str, noi_dung: bytes, kieu_mime: str) -> str:
        """Ghi file mới, trả khóa (`<thu_muc>/<uuid><đuôi>`). `kieu_mime` phải là kiểu đã nhận dạng từ nội dung."""
        khoa = f"{thu_muc}/{uuid.uuid4().hex}{KIEU_ANH[kieu_mime]}"
        duong_dan = self._duong_dan(khoa)

        def ghi() -> None:
            duong_dan.parent.mkdir(parents=True, exist_ok=True)
            duong_dan.write_bytes(noi_dung)

        await asyncio.to_thread(ghi)
        return khoa

    async def doc(self, khoa: str) -> bytes | None:
        duong_dan = self._duong_dan(khoa)

        def doc_file() -> bytes | None:
            try:
                return duong_dan.read_bytes()
            except (FileNotFoundError, IsADirectoryError):  # vừa bị xóa (`xoa_sau_commit`) giữa lúc request tới
                return None

        return await asyncio.to_thread(doc_file)

    async def xoa(self, khoa: str) -> None:
        duong_dan = self._duong_dan(khoa)
        await asyncio.to_thread(lambda: duong_dan.unlink(missing_ok=True))


def luu_tru() -> LuuTruCucBo:
    """Kho lưu trữ theo cấu hình hiện tại (đọc mỗi lần gọi để test đổi được thư mục)."""
    goc = Path(settings.LUU_TRU_THU_MUC)
    return LuuTruCucBo(goc if goc.is_absolute() else BACKEND_DIR / goc)


def _xoa_dong_bo(khoa: str) -> None:
    try:
        luu_tru()._duong_dan(khoa).unlink(missing_ok=True)
    except (OSError, ValueError):  # dọn dẹp tốt nhất có thể, không phá việc đã xong; để lại dấu vết cho ai dọn tay
        logger.warning("Không xóa được tệp công khai %s", khoa, exc_info=True)


def xoa_sau_commit(db, khoa: str) -> None:
    """Xóa file CHỈ KHI giao dịch của `db` commit (xóa bản ghi xong mới xóa file thật)."""
    event.listen(db.sync_session, "after_commit", lambda _phien: _xoa_dong_bo(khoa), once=True)


def xoa_neu_hoan_tac(db, khoa: str) -> None:
    """Xóa file nếu giao dịch của `db` bị hủy (file vừa ghi mà bản ghi trỏ tới nó không được lưu).

    Chỉ tính hủy giao dịch ngoài cùng: rollback một savepoint (ví dụ bắt lỗi trùng rồi đi tiếp) không được xóa file.
    """

    def khi_rollback(_phien, giao_dich) -> None:
        if giao_dich.parent is None:
            _xoa_dong_bo(khoa)

    event.listen(db.sync_session, "after_soft_rollback", khi_rollback)
