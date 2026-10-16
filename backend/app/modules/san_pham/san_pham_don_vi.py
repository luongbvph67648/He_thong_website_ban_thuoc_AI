"""Đơn vị quy đổi và thành phần của sản phẩm (AD04, spec 06 mục 3.11): thay cả danh sách trong một giao dịch.

Đơn vị quy đổi được giỏ hàng, đơn hàng và phiếu nhập tham chiếu (cả khóa ngoại kép với `san_pham_id`), nên thay danh
sách là SỬA tại chỗ theo `id` chứ không xóa rồi tạo lại. Ràng buộc duy nhất của DB (một đơn vị cơ sở, một đơn vị mặc
định, tên đơn vị) kiểm từng dòng ngay lúc ghi, nên các thay đổi áp theo pha để không lúc nào hai dòng cùng vi phạm.
"""

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import CtDonHang, CtGioHang
from app.models.he_thong import NhanVien
from app.models.kho import CtPhieuNhap, LoThuoc
from app.models.san_pham import DonViQuyDoi, ThanhPhan
from app.modules.san_pham import san_pham as dich_vu
from app.modules.san_pham.schemas_san_pham import (
    SanPhamChiTiet,
    ThanhPhanVao,
    ThayDonVi,
    ThayThanhPhan,
)

MA_VI_PHAM_KHOA_NGOAI = "23503"


async def _duoc_tham_chieu(db: AsyncSession, don_vi_id: int) -> bool:
    for mo_hinh in (CtGioHang, CtDonHang, CtPhieuNhap):
        if (await db.execute(select(mo_hinh.don_vi_id).where(mo_hinh.don_vi_id == don_vi_id).limit(1))).first():
            return True
    return False


async def _co_lo(db: AsyncSession, san_pham_id: int) -> bool:
    return (await db.execute(select(LoThuoc.id).where(LoThuoc.san_pham_id == san_pham_id).limit(1))).first() is not None


def _khong_doi_duoc_he_so() -> LoiNghiepVu:
    return LoiNghiepVu(
        "DU_LIEU_DANG_DUOC_SU_DUNG",
        "Không đổi được hệ số của đơn vị đang được dùng (giỏ hàng, đơn hàng, phiếu nhập) hoặc của sản phẩm đã có lô: "
        "số lượng tồn tính theo đơn vị cơ sở",
    )


async def thay_don_vi(
    db: AsyncSession, actor: NhanVien, san_pham_id: int, du_lieu: ThayDonVi, *, ip: str
) -> SanPhamChiTiet:
    await dam_bao_la_admin(db, actor)
    sp, hien_tai = await dich_vu.khoa_va_kiem_tra(db, san_pham_id, du_lieu.phien_ban)
    moi = du_lieu.don_vi
    hien_co = {
        d.id: d
        for d in (
            await db.execute(
                select(DonViQuyDoi).where(DonViQuyDoi.san_pham_id == sp.id).execution_options(populate_existing=True)
            )
        ).scalars()
    }
    for i, d in enumerate(moi):
        if d.id is not None and d.id not in hien_co:
            raise dich_vu.loi_truong(f"don_vi.{i}.id", "Đơn vị không thuộc sản phẩm này")
    await dich_vu.kiem_tra_ma_vach(db, moi, sp.id)

    cu = dich_vu._tom_tat_don_vi(sorted(hien_co.values(), key=lambda d: (d.he_so, d.id)))
    sap_xoa = [d for id_, d in hien_co.items() if id_ not in {m.id for m in moi if m.id is not None}]
    co_lo = await _co_lo(db, sp.id)
    # Hệ số của đơn vị đã có chỉ đổi được khi chưa ai dùng nó và sản phẩm chưa có lô.
    for m in moi:
        if m.id is not None and hien_co[m.id].he_so != m.he_so and (co_lo or await _duoc_tham_chieu(db, m.id)):
            raise _khong_doi_duoc_he_so()
    co_so_cu = next(d for d in hien_co.values() if d.he_so == 1)
    co_so_moi = next(m for m in moi if m.he_so == 1)
    if (co_so_moi.id is None or co_so_moi.id != co_so_cu.id) and (co_lo or await _duoc_tham_chieu(db, co_so_cu.id)):
        raise _khong_doi_duoc_he_so()  # đổi đơn vị cơ sở làm mọi số lượng đã ghi đổi nghĩa

    # Pha 1: xóa đơn vị bỏ đi (đang được tham chiếu thì khóa ngoại từ chối trong savepoint).
    for d in sap_xoa:
        try:
            async with db.begin_nested():
                await db.execute(delete(DonViQuyDoi).where(DonViQuyDoi.id == d.id))
        except IntegrityError as loi:
            if getattr(loi.orig, "sqlstate", None) != MA_VI_PHAM_KHOA_NGOAI:
                raise
            raise LoiNghiepVu(
                "DU_LIEU_DANG_DUOC_SU_DUNG",
                f"Không xóa được đơn vị “{d.ten_don_vi}” vì đang được dùng (giỏ hàng, đơn hàng hoặc phiếu nhập)",
            ) from loi
        db.expunge(d)
    sua = [(hien_co[m.id], m) for m in moi if m.id is not None]
    # Pha 2: gỡ cờ mặc định và đưa tên về tên tạm để pha 3 áp từng dòng mà không va unique tên / mặc định.
    for d, _ in sua:
        d.la_mac_dinh = False
        d.ten_don_vi = f"~{d.id}"
    await db.flush()
    # Pha 3: áp giá trị cuối; các dòng rời hệ số 1 trước, dòng vào hệ số 1 sau (unique một đơn vị cơ sở).
    for d, m in sorted(sua, key=lambda cap: cap[1].he_so == 1):
        d.ten_don_vi = m.ten_don_vi
        d.he_so = m.he_so
        d.gia_ban = m.gia_ban
        d.ban_online = m.ban_online
        d.ma_vach = m.ma_vach
        await db.flush()
    for d, m in sua:
        d.la_mac_dinh = m.la_mac_dinh
    for m in moi:
        if m.id is None:
            db.add(
                DonViQuyDoi(
                    san_pham_id=sp.id,
                    ten_don_vi=m.ten_don_vi,
                    he_so=m.he_so,
                    gia_ban=m.gia_ban,
                    ban_online=m.ban_online,
                    la_mac_dinh=m.la_mac_dinh,
                    ma_vach=m.ma_vach,
                )
            )
    sp.don_vi_co_so = co_so_moi.ten_don_vi
    sp.updated_at = bay_gio_utc()
    await db.flush()
    sau = await dich_vu.chi_tiet(db, sp)
    if sau.don_vi == hien_tai.don_vi and sp.don_vi_co_so == hien_tai.don_vi_co_so:
        sp.updated_at = hien_tai.updated_at  # không có gì đổi thật: giữ nguyên dấu vết, không ghi nhật ký
        await db.flush()
        return await dich_vu.chi_tiet(db, sp)
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="sua",
        bang="don_vi_quy_doi",
        ban_ghi_id=sp.id,
        gia_tri_cu={"san_pham_id": sp.id, "don_vi": cu},
        gia_tri_moi={"san_pham_id": sp.id, "don_vi": dich_vu._tom_tat_don_vi(sau.don_vi)},
        ip=ip,
    )
    return sau


async def thay_thanh_phan(
    db: AsyncSession, actor: NhanVien, san_pham_id: int, du_lieu: ThayThanhPhan, *, ip: str
) -> SanPhamChiTiet:
    await dam_bao_la_admin(db, actor)
    sp, hien_tai = await dich_vu.khoa_va_kiem_tra(db, san_pham_id, du_lieu.phien_ban)
    await dich_vu.kiem_tra_hoat_chat(db, du_lieu.thanh_phan)
    cu = [{"hoat_chat_id": t.hoat_chat_id, "ham_luong": t.ham_luong} for t in hien_tai.thanh_phan]
    moi: list[ThanhPhanVao] = du_lieu.thanh_phan
    moi_dang_dict = sorted(
        ({"hoat_chat_id": t.hoat_chat_id, "ham_luong": t.ham_luong} for t in moi), key=lambda x: x["hoat_chat_id"]
    )
    if sorted(cu, key=lambda x: x["hoat_chat_id"]) == moi_dang_dict:
        return hien_tai
    await db.execute(delete(ThanhPhan).where(ThanhPhan.san_pham_id == sp.id))
    for t in moi:
        db.add(ThanhPhan(san_pham_id=sp.id, hoat_chat_id=t.hoat_chat_id, ham_luong=t.ham_luong))
    sp.updated_at = bay_gio_utc()
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="sua",
        bang="thanh_phan",
        ban_ghi_id=sp.id,
        gia_tri_cu={"san_pham_id": sp.id, "thanh_phan": cu},
        gia_tri_moi={"san_pham_id": sp.id, "thanh_phan": moi_dang_dict},
        ip=ip,
    )
    return await dich_vu.chi_tiet(db, sp)
