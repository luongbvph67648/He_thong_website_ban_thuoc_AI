"""Đọc cấu hình động từ bảng cau_hinh."""

from sqlalchemy import text

from app.core.cau_hinh import doc_cau_hinh


async def test_doc_gia_tri_da_seed(db):
    assert await doc_cau_hinh(db, "gioi_han_otp", {}) == {"moi_sdt_moi_gio": 5, "moi_ip_moi_gio": 20}
    assert await doc_cau_hinh(db, "nguong_can_han_ngay", 0) == 90


async def test_khoa_khong_co_thi_dung_mac_dinh(db):
    assert await doc_cau_hinh(db, "khoa_khong_ton_tai", {"a": 1}) == {"a": 1}


async def test_doc_duoc_gia_tri_vua_sua(db):
    await db.execute(
        text(
            "UPDATE cau_hinh SET gia_tri = '{\"moi_sdt_moi_gio\": 2, \"moi_ip_moi_gio\": 3}' WHERE khoa = 'gioi_han_otp'"
        )
    )
    assert (await doc_cau_hinh(db, "gioi_han_otp", {}))["moi_sdt_moi_gio"] == 2


async def test_khong_tra_ve_none_khi_gia_tri_json_null(db):
    """JSON null là giá trị hợp lệ của cột JSONB; coi như chưa cấu hình để mặc định luôn dùng được."""
    await db.execute(text("UPDATE cau_hinh SET gia_tri = 'null'::jsonb WHERE khoa = 'nguong_can_han_ngay'"))
    assert await doc_cau_hinh(db, "nguong_can_han_ngay", 90) == 90
