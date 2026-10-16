"""Tải ảnh lên vùng công khai cho banner và ảnh bìa bài viết (AD07). Cùng khuôn với ảnh sản phẩm (QĐ-17).

Ảnh nhận dạng bằng magic bytes, tối đa 5 MB, đổi tên UUID. Khác ảnh sản phẩm: ảnh được tải LÊN TRƯỚC khi có bản ghi để
gắn vào (người dùng chọn ảnh rồi mới lưu form), nên một ảnh có thể mồ côi nếu form không được lưu; việc dọn tệp mồ côi
thuộc job nền (T3.2, ghi ở "Việc phát sinh").
"""

from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import luu_tru
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin
from app.models.he_thong import NhanVien

ThuMuc = Literal["banner", "bai-viet"]


async def tai_anh(db: AsyncSession, actor: NhanVien, thu_muc: ThuMuc, noi_dung: bytes, *, ip: str) -> str:
    await dam_bao_la_admin(db, actor)
    if len(noi_dung) > luu_tru.TOI_DA_ANH_BYTE:
        raise LoiNghiepVu("TEP_QUA_LON", "Ảnh tối đa 5 MB", chi_tiet={"toi_da_byte": luu_tru.TOI_DA_ANH_BYTE})
    kieu = luu_tru.nhan_dang_anh(noi_dung)
    if kieu is None:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "tep", "loi": "Chỉ nhận ảnh jpeg, png hoặc webp (theo nội dung file)"}],
        )
    khoa = await luu_tru.luu_tru().luu(thu_muc, noi_dung, kieu)
    luu_tru.xoa_neu_hoan_tac(db, khoa)
    url = luu_tru.url_cong_khai(khoa)
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao",
        bang="tep_cong_khai",
        ban_ghi_id=khoa,
        gia_tri_moi={"url": url},
        ip=ip,
    )
    return url
