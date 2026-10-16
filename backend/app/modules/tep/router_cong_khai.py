"""Phục vụ file vùng CÔNG KHAI (ảnh sản phẩm, banner, bài viết): `GET /api/v1/tep/{khoa}`, không cần đăng nhập.

Chỉ khóa do hệ thống tự sinh mới đọc được (`san-pham/<uuid>.<jpg|png|webp>`); khóa chứa `..`, đường dẫn tuyệt đối hay ký
tự lạ là 404. `Content-Type` lấy theo đuôi đã được kiểm khi upload, kèm `nosniff` để trình duyệt không tự đoán lại.
Tên file là UUID nên nội dung không bao giờ đổi: cho bộ nhớ đệm giữ một năm.
"""

from fastapi import APIRouter, Query, Response

from app.core import luu_tru
from app.core.loi import LoiNghiepVu

router = APIRouter(prefix="/tep", tags=["Tệp công khai"])


@router.get("/{thu_muc}/{ten_tep}", summary="Tải file công khai", response_class=Response)
async def tai_tep(thu_muc: str, ten_tep: str) -> Response:
    khoa = f"{thu_muc}/{ten_tep}"
    if not luu_tru.khoa_hop_le(khoa):
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy tệp")
    try:
        noi_dung = await luu_tru.luu_tru().doc(khoa)
    except ValueError:  # symlink dẫn ra ngoài vùng công khai: coi như không có
        noi_dung = None
    if noi_dung is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy tệp")
    kieu = luu_tru.KIEU_THEO_DUOI["." + khoa.rsplit(".", 1)[1]]
    return Response(
        noi_dung,
        media_type=kieu,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("-rieng/{thu_muc}/{ten_tep}", summary="Tải file riêng tư bằng URL ký có hạn", response_class=Response)
async def tai_tep_rieng(
    thu_muc: str, ten_tep: str, het_han: int = Query(ge=0, le=4_000_000_000), ky: str = Query(max_length=64)
) -> Response:
    """Không cần token: quyền đã được kiểm khi cấp URL (chủ yêu cầu hoặc dược sĩ đang xử lý). Chữ ký sai, hết hạn hoặc
    khóa lạ đều là 404 để không lộ file có tồn tại hay không."""
    khoa = f"{thu_muc}/{ten_tep}"
    if not luu_tru.khoa_hop_le(khoa) or not luu_tru.kiem_tra_ky(khoa, het_han, ky):
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy tệp")
    try:
        noi_dung = await luu_tru.luu_tru().doc(khoa, "rieng_tu")
    except ValueError:
        noi_dung = None
    if noi_dung is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy tệp")
    kieu = luu_tru.KIEU_THEO_DUOI["." + khoa.rsplit(".", 1)[1]]
    return Response(
        noi_dung,
        media_type=kieu,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )
