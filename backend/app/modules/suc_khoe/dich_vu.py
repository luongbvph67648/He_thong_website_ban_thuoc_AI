"""Hồ sơ sức khỏe và dị ứng (KTV11, spec 03 mục 5.1).

Khách có toàn quyền với hồ sơ của mình; dược sĩ chỉ đọc qua `duoc_doc_ho_so_suc_khoe`. Chỉ lưu khi khách đồng ý sử
dụng dữ liệu; thu hồi đồng ý = xóa hồ sơ (QĐ-32). `benh_nen` được mã hóa Fernet trong DB. Không hàm nào ghi giá trị
hồ sơ ra log hay nhật ký. Hàm không commit.
"""

from sqlalchemy import delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.ma_hoa import giai_ma, ma_hoa
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import MA_VAI_TRO_DUOC_SI
from app.core.thoi_gian import bay_gio_utc
from app.core.tim_kiem import mau_tim_like
from app.models.ai import HoiThoai
from app.models.ban_hang import YeuCauDonThuoc
from app.models.enums import TrangThaiHoiThoai, TrangThaiYeuCauDonThuoc
from app.models.he_thong import NhanVien, VaiTro
from app.models.khach_hang import DiUng, HoSoSucKhoe, KhachHang
from app.models.san_pham import HoatChat
from app.modules.suc_khoe.schemas import DiUngRa, HoatChatChon, HoSoRa, HoSoVao


async def _dung_ho_so(db: AsyncSession, khach_hang_id: int) -> HoSoRa:
    ho_so = await db.get(HoSoSucKhoe, khach_hang_id)
    if ho_so is None:
        return HoSoRa()
    ds = (
        await db.execute(
            select(DiUng.hoat_chat_id, HoatChat.ten, DiUng.ghi_chu)
            .join(HoatChat, HoatChat.id == DiUng.hoat_chat_id)
            .where(DiUng.khach_hang_id == khach_hang_id)
            .order_by(HoatChat.ten)
        )
    ).all()
    return HoSoRa(
        dong_y_su_dung=ho_so.dong_y_su_dung,
        dong_y_luc=None if ho_so.dong_y_luc is None else ho_so.dong_y_luc.isoformat(),
        nam_sinh=ho_so.nam_sinh,
        benh_nen=None if ho_so.benh_nen is None else giai_ma(ho_so.benh_nen),
        dang_mang_thai=ho_so.dang_mang_thai,
        dang_cho_con_bu=ho_so.dang_cho_con_bu,
        di_ung=[DiUngRa(hoat_chat_id=h, ten_hoat_chat=t, ghi_chu=g) for h, t, g in ds],
    )


async def xem(db: AsyncSession, khach: KhachHang) -> HoSoRa:
    return await _dung_ho_so(db, khach.id)


async def luu(db: AsyncSession, khach: KhachHang, vao: HoSoVao) -> HoSoRa:
    """Tạo hoặc thay toàn bộ hồ sơ. Không đồng ý thì không lưu gì (422)."""
    if not vao.dong_y_su_dung:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Cần đồng ý sử dụng dữ liệu sức khỏe mới lưu được hồ sơ. Muốn thu hồi đồng ý, hãy xóa hồ sơ",
        )
    ids = sorted({d.hoat_chat_id for d in vao.di_ung})
    if ids:
        co = set((await db.execute(select(HoatChat.id).where(HoatChat.id.in_(ids)))).scalars())
        if set(ids) - co:
            raise LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Có hoạt chất không tồn tại trong danh mục")
    bay_gio = bay_gio_utc()
    ho_so = await db.get(HoSoSucKhoe, khach.id, with_for_update=True)
    if ho_so is None:
        ho_so = HoSoSucKhoe(khach_hang_id=khach.id, dong_y_su_dung=True, dong_y_luc=bay_gio)
        db.add(ho_so)
    elif not ho_so.dong_y_su_dung or ho_so.dong_y_luc is None:
        ho_so.dong_y_su_dung = True
        ho_so.dong_y_luc = bay_gio
    ho_so.nam_sinh = vao.nam_sinh
    ho_so.benh_nen = ma_hoa(vao.benh_nen) if vao.benh_nen else None
    ho_so.dang_mang_thai = vao.dang_mang_thai
    ho_so.dang_cho_con_bu = vao.dang_cho_con_bu
    ho_so.updated_at = bay_gio
    await db.execute(delete(DiUng).where(DiUng.khach_hang_id == khach.id))
    ghi_chu = {d.hoat_chat_id: d.ghi_chu or None for d in vao.di_ung}
    db.add_all(DiUng(khach_hang_id=khach.id, hoat_chat_id=i, ghi_chu=ghi_chu[i]) for i in ids)
    await db.flush()
    return await _dung_ho_so(db, khach.id)


async def xoa(db: AsyncSession, khach: KhachHang) -> None:
    """Xóa cứng cả hai bảng (cũng là cách thu hồi đồng ý). Idempotent."""
    await db.execute(delete(DiUng).where(DiUng.khach_hang_id == khach.id))
    await db.execute(delete(HoSoSucKhoe).where(HoSoSucKhoe.khach_hang_id == khach.id))


async def duoc_doc_ho_so_suc_khoe(db: AsyncSession, nhan_vien: NhanVien, khach_hang_id: int) -> bool:
    """Hàm cổng (spec 03 mục 5.1). True khi: là PHARMACIST, khách đã đồng ý, và dược sĩ đang xử lý yêu cầu đơn thuốc
    (`dang_tu_van`) hoặc phiên chat (`duoc_si_dang_xu_ly`) của chính khách đó. Mỗi lần trả True ghi `nhat_ky_he_thong`
    (`doc_suc_khoe`, không ghi nội dung)."""
    ma_vai_tro = await db.scalar(select(VaiTro.ma).where(VaiTro.id == nhan_vien.vai_tro_id))
    if ma_vai_tro != MA_VAI_TRO_DUOC_SI:
        return False
    dong_y = await db.scalar(select(HoSoSucKhoe.dong_y_su_dung).where(HoSoSucKhoe.khach_hang_id == khach_hang_id))
    if not dong_y:
        return False
    dang_xu_ly = await db.scalar(
        select(
            exists().where(
                YeuCauDonThuoc.khach_hang_id == khach_hang_id,
                YeuCauDonThuoc.duoc_si_id == nhan_vien.id,
                YeuCauDonThuoc.trang_thai == TrangThaiYeuCauDonThuoc.dang_tu_van,
            )
            | exists().where(
                HoiThoai.khach_hang_id == khach_hang_id,
                HoiThoai.duoc_si_id == nhan_vien.id,
                HoiThoai.trang_thai == TrangThaiHoiThoai.duoc_si_dang_xu_ly,
            )
        )
    )
    if not dang_xu_ly:
        return False
    await ghi_nhat_ky(
        db, nhan_vien_id=nhan_vien.id, hanh_dong="doc_suc_khoe", bang="ho_so_suc_khoe", ban_ghi_id=khach_hang_id
    )
    return True


async def doc_ho_so_cho_duoc_si(db: AsyncSession, nhan_vien: NhanVien, khach_hang_id: int) -> HoSoRa:
    """Dược sĩ đọc hồ sơ qua hàm cổng; không qua cổng thì 403 (không tiết lộ khách có hồ sơ hay không)."""
    if not await duoc_doc_ho_so_suc_khoe(db, nhan_vien, khach_hang_id):
        raise LoiNghiepVu("KHONG_CO_QUYEN", "Bạn không được xem hồ sơ sức khỏe của khách này")
    return await _dung_ho_so(db, khach_hang_id)


async def tim_hoat_chat(db: AsyncSession, q: str | None, toi_da: int = 20) -> list[HoatChatChon]:
    """Gợi ý hoạt chất theo tên hoặc tên khác (không phân biệt hoa thường và dấu), tối đa `toi_da` kết quả."""
    cau = select(HoatChat.id, HoatChat.ten).order_by(HoatChat.ten).limit(toi_da)
    if q and q.strip():
        mau = func.unaccent(mau_tim_like(q))
        cau = cau.where(
            func.unaccent(HoatChat.ten).ilike(mau, escape="\\")
            | func.unaccent(func.coalesce(HoatChat.ten_khac, "")).ilike(mau, escape="\\")
        )
    return [HoatChatChon(id=i, ten=t) for i, t in (await db.execute(cau)).all()]
