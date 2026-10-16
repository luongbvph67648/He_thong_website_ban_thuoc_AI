"""Ảnh sản phẩm (AD04, spec 06 mục 3.11): upload, đặt ảnh chính, sắp xếp, xóa.

- File nhận dạng theo NỘI DUNG (magic bytes), ≤ 5 MB, đổi tên UUID, lưu ở vùng công khai (`core/luu_tru.py`).
- Ảnh được ghi ra đĩa TRƯỚC khi giao dịch xong: nếu giao dịch bị hủy thì file bị dọn (`xoa_neu_hoan_tac`); xóa ảnh chỉ
  xóa file thật sau khi giao dịch commit (`xoa_sau_commit`).
- Đúng một ảnh chính (partial unique `anh_mot_anh_chinh`): đổi ảnh chính gỡ cờ ở ảnh cũ TRƯỚC khi đặt ở ảnh mới.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import luu_tru
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin
from app.core.thoi_gian import bay_gio_utc
from app.models.he_thong import NhanVien
from app.models.san_pham import AnhSanPham
from app.modules.san_pham import san_pham as dich_vu
from app.modules.san_pham.schemas_san_pham import SO_ANH_TOI_DA, SanPhamChiTiet

BANG = "anh_san_pham"


async def _anh_cua(db: AsyncSession, san_pham_id: int) -> list[AnhSanPham]:
    return list(
        (
            await db.execute(
                select(AnhSanPham)
                .where(AnhSanPham.san_pham_id == san_pham_id)
                .order_by(AnhSanPham.thu_tu, AnhSanPham.id)
                .execution_options(populate_existing=True)
            )
        ).scalars()
    )


def _khong_co_anh() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy ảnh của sản phẩm này")


async def them_anh(
    db: AsyncSession, actor: NhanVien, san_pham_id: int, phien_ban: str, noi_dung: bytes, *, ip: str
) -> SanPhamChiTiet:
    await dam_bao_la_admin(db, actor)
    sp, _ = await dich_vu.khoa_va_kiem_tra(db, san_pham_id, phien_ban)
    if len(noi_dung) > luu_tru.TOI_DA_ANH_BYTE:
        raise LoiNghiepVu("TEP_QUA_LON", "Ảnh tối đa 5 MB", chi_tiet={"toi_da_byte": luu_tru.TOI_DA_ANH_BYTE})
    kieu = luu_tru.nhan_dang_anh(noi_dung)
    if kieu is None:
        raise dich_vu.loi_truong("tep", "Chỉ nhận ảnh jpeg, png hoặc webp (theo nội dung file)")
    anh = await _anh_cua(db, sp.id)
    if len(anh) >= SO_ANH_TOI_DA:
        raise dich_vu.loi_truong("tep", f"Mỗi sản phẩm tối đa {SO_ANH_TOI_DA} ảnh")
    khoa = await luu_tru.luu_tru().luu("san-pham", noi_dung, kieu)
    luu_tru.xoa_neu_hoan_tac(db, khoa)
    moi = AnhSanPham(
        san_pham_id=sp.id,
        url=luu_tru.url_cong_khai(khoa),
        thu_tu=max((a.thu_tu for a in anh), default=-1) + 1,
        la_anh_chinh=not anh,  # ảnh đầu tiên tự là ảnh chính
    )
    db.add(moi)
    sp.updated_at = bay_gio_utc()
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao",
        bang=BANG,
        ban_ghi_id=moi.id,
        gia_tri_moi={"san_pham_id": sp.id, "url": moi.url, "thu_tu": moi.thu_tu, "la_anh_chinh": moi.la_anh_chinh},
        ip=ip,
    )
    return await dich_vu.chi_tiet(db, sp)


async def dat_thu_tu(
    db: AsyncSession, actor: NhanVien, san_pham_id: int, phien_ban: str, ids: list[int], *, ip: str
) -> SanPhamChiTiet:
    await dam_bao_la_admin(db, actor)
    sp, hien_tai = await dich_vu.khoa_va_kiem_tra(db, san_pham_id, phien_ban)
    anh = await _anh_cua(db, sp.id)
    if sorted(ids) != sorted(a.id for a in anh):
        raise dich_vu.loi_truong("ids", "Phải liệt kê đúng và đủ các ảnh hiện có của sản phẩm, mỗi ảnh một lần")
    theo_id = {a.id: a for a in anh}
    cu = [a.id for a in anh]
    if ids == cu:
        return hien_tai
    for i, id_ in enumerate(ids):
        theo_id[id_].thu_tu = i
    sp.updated_at = bay_gio_utc()
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="sua",
        bang=BANG,
        ban_ghi_id=sp.id,
        gia_tri_cu={"san_pham_id": sp.id, "thu_tu_anh": cu},
        gia_tri_moi={"san_pham_id": sp.id, "thu_tu_anh": ids},
        ip=ip,
    )
    return await dich_vu.chi_tiet(db, sp)


async def dat_anh_chinh(
    db: AsyncSession, actor: NhanVien, san_pham_id: int, anh_id: int, phien_ban: str, *, ip: str
) -> SanPhamChiTiet:
    await dam_bao_la_admin(db, actor)
    sp, hien_tai = await dich_vu.khoa_va_kiem_tra(db, san_pham_id, phien_ban)
    anh = await _anh_cua(db, sp.id)
    dich = next((a for a in anh if a.id == anh_id), None)
    if dich is None:
        raise _khong_co_anh()
    if dich.la_anh_chinh:
        return hien_tai
    cu = next((a.id for a in anh if a.la_anh_chinh), None)
    for a in anh:
        a.la_anh_chinh = False
    await db.flush()  # gỡ cờ ở ảnh cũ trước khi đặt ở ảnh mới (partial unique)
    dich.la_anh_chinh = True
    sp.updated_at = bay_gio_utc()
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="sua",
        bang=BANG,
        ban_ghi_id=sp.id,
        gia_tri_cu={"san_pham_id": sp.id, "anh_chinh_id": cu},
        gia_tri_moi={"san_pham_id": sp.id, "anh_chinh_id": dich.id},
        ip=ip,
    )
    return await dich_vu.chi_tiet(db, sp)


async def xoa_anh(
    db: AsyncSession, actor: NhanVien, san_pham_id: int, anh_id: int, phien_ban: str, *, ip: str
) -> SanPhamChiTiet:
    await dam_bao_la_admin(db, actor)
    sp, _ = await dich_vu.khoa_va_kiem_tra(db, san_pham_id, phien_ban)
    anh = await _anh_cua(db, sp.id)
    bo = next((a for a in anh if a.id == anh_id), None)
    if bo is None:
        raise _khong_co_anh()
    con_lai = [a for a in anh if a.id != anh_id]
    khoa = luu_tru.khoa_tu_url_cong_khai(bo.url)
    await db.delete(bo)
    await db.flush()
    if bo.la_anh_chinh and con_lai:
        con_lai[0].la_anh_chinh = True  # ảnh đầu danh sách thành ảnh chính
    for i, a in enumerate(con_lai):
        a.thu_tu = i
    sp.updated_at = bay_gio_utc()
    await db.flush()
    if khoa is not None:
        luu_tru.xoa_sau_commit(db, khoa)
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="xoa",
        bang=BANG,
        ban_ghi_id=anh_id,
        gia_tri_cu={"san_pham_id": sp.id, "url": bo.url, "la_anh_chinh": bo.la_anh_chinh},
        ip=ip,
    )
    return await dich_vu.chi_tiet(db, sp)


async def dem_anh(db: AsyncSession, san_pham_id: int) -> int:
    return (
        await db.scalar(select(func.count()).select_from(AnhSanPham).where(AnhSanPham.san_pham_id == san_pham_id)) or 0
    )
