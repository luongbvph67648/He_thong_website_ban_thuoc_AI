"""Sổ địa chỉ của khách (KTV01, spec 06 mục 3.20). Luôn đúng một địa chỉ mặc định khi khách có địa chỉ."""

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.models.khach_hang import DiaChi, KhachHang
from app.modules.dia_chi.schemas import DiaChiVao
from app.tich_hop.van_chuyen import lay_danh_muc_dia_gioi

TOI_DA_DIA_CHI = 10


def _khong_hop_le(truong: str, loi: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": truong, "loi": loi}])


def _ten_dia_gioi(ma_tinh: str, ma_xa: str) -> tuple[str, str]:
    """Tên tỉnh/xã từ danh mục (không tin tên do client gửi); mã lạ hoặc xã không thuộc tỉnh là 400."""
    danh_muc = lay_danh_muc_dia_gioi()
    tinh = next((t for t in danh_muc.danh_sach_tinh() if t.ma == ma_tinh), None)
    if tinh is None:
        raise _khong_hop_le("ma_tinh", "Mã tỉnh không có trong danh mục")
    xa = next((x for x in danh_muc.danh_sach_xa(ma_tinh) or [] if x.ma == ma_xa), None)
    if xa is None:
        raise _khong_hop_le("ma_phuong_xa", "Mã phường/xã không thuộc tỉnh đã chọn")
    return tinh.ten, xa.ten


async def _khoa_khach(db: AsyncSession, khach: KhachHang) -> None:
    """Tuần tự hóa mọi thay đổi sổ địa chỉ của một khách (tránh hai địa chỉ mặc định, vượt giới hạn 10)."""
    await db.execute(select(KhachHang.id).where(KhachHang.id == khach.id).with_for_update())


async def danh_sach(db: AsyncSession, khach: KhachHang) -> list[DiaChi]:
    return list(
        (
            await db.execute(
                select(DiaChi).where(DiaChi.khach_hang_id == khach.id).order_by(DiaChi.la_mac_dinh.desc(), DiaChi.id)
            )
        ).scalars()
    )


async def _lay(db: AsyncSession, khach: KhachHang, dia_chi_id: int) -> DiaChi:
    dc = (
        await db.execute(select(DiaChi).where(DiaChi.id == dia_chi_id, DiaChi.khach_hang_id == khach.id))
    ).scalar_one_or_none()
    if dc is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy địa chỉ")  # của khách khác cũng là 404
    return dc


async def _dat_mac_dinh(db: AsyncSession, khach: KhachHang, dc: DiaChi) -> None:
    await db.execute(
        update(DiaChi).where(DiaChi.khach_hang_id == khach.id, DiaChi.id != dc.id).values(la_mac_dinh=False)
    )
    dc.la_mac_dinh = True
    await db.flush()


async def tao(db: AsyncSession, khach: KhachHang, vao: DiaChiVao, la_mac_dinh: bool) -> DiaChi:
    await _khoa_khach(db, khach)
    hien_co = await danh_sach(db, khach)
    if len(hien_co) >= TOI_DA_DIA_CHI:
        raise _khong_hop_le("dia_chi", f"Mỗi tài khoản tối đa {TOI_DA_DIA_CHI} địa chỉ")
    ten_tinh, ten_xa = _ten_dia_gioi(vao.ma_tinh, vao.ma_phuong_xa)
    dc = DiaChi(
        khach_hang_id=khach.id,
        **vao.model_dump(),
        ten_tinh=ten_tinh,
        ten_phuong_xa=ten_xa,
        la_mac_dinh=False,
    )
    db.add(dc)
    await db.flush()
    if la_mac_dinh or not hien_co:
        await _dat_mac_dinh(db, khach, dc)
    return dc


async def sua(db: AsyncSession, khach: KhachHang, dia_chi_id: int, vao: DiaChiVao) -> DiaChi:
    await _khoa_khach(db, khach)
    dc = await _lay(db, khach, dia_chi_id)
    dc.ten_tinh, dc.ten_phuong_xa = _ten_dia_gioi(vao.ma_tinh, vao.ma_phuong_xa)
    for truong, gia_tri in vao.model_dump().items():
        setattr(dc, truong, gia_tri)
    await db.flush()
    return dc


async def dat_mac_dinh(db: AsyncSession, khach: KhachHang, dia_chi_id: int) -> DiaChi:
    await _khoa_khach(db, khach)
    dc = await _lay(db, khach, dia_chi_id)
    if not dc.la_mac_dinh:
        await _dat_mac_dinh(db, khach, dc)
    return dc


async def xoa(db: AsyncSession, khach: KhachHang, dia_chi_id: int) -> None:
    await _khoa_khach(db, khach)
    dc = await _lay(db, khach, dia_chi_id)
    la_mac_dinh = dc.la_mac_dinh
    await db.execute(delete(DiaChi).where(DiaChi.id == dc.id))
    if la_mac_dinh:  # địa chỉ cũ nhất còn lại thành mặc định
        con_lai = (
            await db.execute(select(DiaChi).where(DiaChi.khach_hang_id == khach.id).order_by(DiaChi.id).limit(1))
        ).scalar_one_or_none()
        if con_lai is not None:
            con_lai.la_mac_dinh = True
            await db.flush()
