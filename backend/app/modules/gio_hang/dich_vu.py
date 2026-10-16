"""Giỏ hàng (KVL07, spec 06 mục 3.20). Giỏ không giữ hàng; tồn chỉ bị giữ khi đặt hàng (T4.4).

Mọi đường vào giỏ (thêm, sửa, gộp) đi qua `_ly_do_khong_hop_le`: thuốc kê đơn bị chặn ở đây, không chỉ ở giao diện.
"""

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.loi import LoiNghiepVu
from app.core.tien import cong, lam_tron_vnd
from app.models.ai import LuatMuaKem
from app.models.ban_hang import CtGioHang, GioHang
from app.models.enums import LoaiSanPham, TrangThaiKinhDoanh
from app.models.khach_hang import KhachHang
from app.models.san_pham import AnhSanPham, DonViQuyDoi, SanPham
from app.modules.cua_hang.hien_thi import chon_don_vi_gia, nap_cay_hien_thi, ton_kha_dung
from app.modules.gio_hang.schemas import (
    DongBoQua,
    DongGio,
    DongVao,
    DonViTrongGio,
    GioHangRa,
    KetQuaGop,
    LyDo,
    MuaKem,
    SanPhamTrongGio,
)

SO_LUONG_DONG_TOI_DA = 9999
SO_MUA_KEM_TOI_DA = 6
TOI_DA_ID_MUA_KEM = 20


def _khong_hop_le(truong: str, loi: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": truong, "loi": loi}])


@dataclass
class SanPhamNap:
    sp: SanPham
    hien_thi: bool


async def _nap_san_pham(db: AsyncSession, ids: set[int]) -> dict[int, SanPhamNap]:
    if not ids:
        return {}
    cay = await nap_cay_hien_thi(db)
    ds = (
        await db.execute(select(SanPham).where(SanPham.id.in_(ids)).options(selectinload(SanPham.don_vi_quy_doi)))
    ).scalars()
    return {
        sp.id: SanPhamNap(
            sp,
            sp.deleted_at is None and sp.trang_thai == TrangThaiKinhDoanh.dang_kinh_doanh and sp.danh_muc_id in cay.ids,
        )
        for sp in ds
    }


def _ly_do_khong_hop_le(nap: SanPhamNap | None, don_vi_id: int, cho_phep_ke_don: bool = False) -> LyDo | None:
    if nap is None:
        return "khong_hien_thi"
    if nap.sp.loai_san_pham == LoaiSanPham.thuoc_ke_don and not cho_phep_ke_don:
        return "thuoc_ke_don"
    if not nap.hien_thi:
        return "khong_hien_thi"
    dv = next((d for d in nap.sp.don_vi_quy_doi if d.id == don_vi_id), None)
    if dv is None or not (dv.ban_online or cho_phep_ke_don):
        return "don_vi_khong_hop_le"
    return None


def _nem_loi(ly_do: LyDo, nap: SanPhamNap | None) -> LoiNghiepVu:
    if ly_do == "thuoc_ke_don":
        return LoiNghiepVu(
            "THUOC_KE_DON_KHONG_VAO_GIO",
            "Thuốc kê đơn không thêm vào giỏ hàng. Vui lòng gửi đơn thuốc để dược sĩ tư vấn.",
        )
    if ly_do == "khong_hien_thi":
        return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy sản phẩm")
    return _khong_hop_le("don_vi_id", "Đơn vị tính không hợp lệ hoặc không bán online")


def _he_so(nap: SanPhamNap, don_vi_id: int) -> int:
    return next(d.he_so for d in nap.sp.don_vi_quy_doi if d.id == don_vi_id)


def _loi_vuot(sp: SanPham) -> LoiNghiepVu:
    return LoiNghiepVu(
        "VUOT_SO_LUONG_TOI_DA",
        f"Mỗi đơn chỉ mua tối đa {sp.so_luong_toi_da_moi_don} {sp.don_vi_co_so} {sp.ten}",
        chi_tiet={"san_pham_id": sp.id, "toi_da": sp.so_luong_toi_da_moi_don},
    )


async def _gio_cua(db: AsyncSession, khach: KhachHang) -> GioHang:
    """Giỏ của khách (tạo nếu chưa có), khóa dòng giỏ để tuần tự hóa các thay đổi đồng thời."""
    await db.execute(
        insert(GioHang).values(khach_hang_id=khach.id).on_conflict_do_nothing(index_elements=["khach_hang_id"])
    )
    return (await db.execute(select(GioHang).where(GioHang.khach_hang_id == khach.id).with_for_update())).scalar_one()


async def _dong_cua_gio(db: AsyncSession, gio: GioHang) -> list[CtGioHang]:
    return list(
        (await db.execute(select(CtGioHang).where(CtGioHang.gio_hang_id == gio.id).order_by(CtGioHang.id))).scalars()
    )


def _co_so_khac(dong: list[CtGioHang], nap: SanPhamNap, bo_qua_ids: set[int]) -> int:
    """Tổng đơn vị cơ sở của sản phẩm trong giỏ, không tính các dòng `bo_qua_ids`."""
    he_so = {d.id: d.he_so for d in nap.sp.don_vi_quy_doi}
    return sum(c.so_luong * he_so[c.don_vi_id] for c in dong if c.san_pham_id == nap.sp.id and c.id not in bo_qua_ids)


async def them_dong(db: AsyncSession, khach: KhachHang, vao: DongVao) -> GioHangRa:
    gio = await _gio_cua(db, khach)
    nap = (await _nap_san_pham(db, {vao.san_pham_id})).get(vao.san_pham_id)
    ly_do = _ly_do_khong_hop_le(nap, vao.don_vi_id)
    if ly_do:
        raise _nem_loi(ly_do, nap)
    assert nap is not None
    dong = await _dong_cua_gio(db, gio)
    co = next((c for c in dong if c.san_pham_id == vao.san_pham_id and c.don_vi_id == vao.don_vi_id), None)
    moi = (co.so_luong if co else 0) + vao.so_luong
    if moi > SO_LUONG_DONG_TOI_DA:
        raise _khong_hop_le("so_luong", f"Tối đa {SO_LUONG_DONG_TOI_DA} mỗi dòng")
    toi_da = nap.sp.so_luong_toi_da_moi_don
    if (
        toi_da is not None
        and _co_so_khac(dong, nap, {co.id} if co else set()) + moi * _he_so(nap, vao.don_vi_id) > toi_da
    ):
        raise _loi_vuot(nap.sp)
    if co:
        co.so_luong = moi
    else:
        db.add(CtGioHang(gio_hang_id=gio.id, san_pham_id=vao.san_pham_id, don_vi_id=vao.don_vi_id, so_luong=moi))
    await db.flush()
    return await xem_gio(db, khach)


async def sua_dong(
    db: AsyncSession, khach: KhachHang, dong_id: int, so_luong: int | None, don_vi_id: int | None
) -> GioHangRa:
    gio = await _gio_cua(db, khach)
    dong = await _dong_cua_gio(db, gio)
    dong_sua = next((c for c in dong if c.id == dong_id), None)
    if dong_sua is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy dòng trong giỏ hàng")  # dòng của giỏ khác cũng là 404
    if so_luong is None and don_vi_id is None:
        return await xem_gio(db, khach)
    nap = (await _nap_san_pham(db, {dong_sua.san_pham_id})).get(dong_sua.san_pham_id)
    dv_dich = don_vi_id or dong_sua.don_vi_id
    ly_do = _ly_do_khong_hop_le(nap, dv_dich)
    if ly_do:
        raise _nem_loi(ly_do, nap)
    assert nap is not None
    dich = next(
        (c for c in dong if c.id != dong_sua.id and c.san_pham_id == dong_sua.san_pham_id and c.don_vi_id == dv_dich),
        None,
    )
    moi = (so_luong if so_luong is not None else dong_sua.so_luong) + (dich.so_luong if dich else 0)
    if moi > SO_LUONG_DONG_TOI_DA:
        raise _khong_hop_le("so_luong", f"Tối đa {SO_LUONG_DONG_TOI_DA} mỗi dòng")
    toi_da = nap.sp.so_luong_toi_da_moi_don
    bo = {dong_sua.id} | ({dich.id} if dich else set())
    if toi_da is not None and _co_so_khac(dong, nap, bo) + moi * _he_so(nap, dv_dich) > toi_da:
        raise _loi_vuot(nap.sp)
    if dich:  # đổi sang đơn vị đã có dòng: gộp vào dòng đó
        dich.so_luong = moi
        await db.execute(delete(CtGioHang).where(CtGioHang.id == dong_sua.id))
    else:
        dong_sua.don_vi_id = dv_dich
        dong_sua.so_luong = moi
    await db.flush()
    return await xem_gio(db, khach)


async def xoa_dong(db: AsyncSession, khach: KhachHang, dong_id: int) -> GioHangRa:
    gio = await _gio_cua(db, khach)
    da_xoa = await db.execute(
        delete(CtGioHang).where(CtGioHang.id == dong_id, CtGioHang.gio_hang_id == gio.id).returning(CtGioHang.id)
    )
    if da_xoa.first() is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy dòng trong giỏ hàng")
    return await xem_gio(db, khach)


async def xoa_het(db: AsyncSession, khach: KhachHang) -> None:
    gio = await _gio_cua(db, khach)
    await db.execute(delete(CtGioHang).where(CtGioHang.gio_hang_id == gio.id))


async def gop_gio(db: AsyncSession, khach: KhachHang, dong_vao: list[DongVao]) -> KetQuaGop:
    """Gộp giỏ localStorage: cộng dồn, cắt theo giới hạn, bỏ qua dòng không hợp lệ (không làm hỏng cả lần gộp)."""
    gio = await _gio_cua(db, khach)
    naps = await _nap_san_pham(db, {d.san_pham_id for d in dong_vao})
    dong = await _dong_cua_gio(db, gio)
    bo_qua: list[DongBoQua] = []

    def ghi_bo_qua(d: DongVao, ly_do: LyDo) -> None:
        bo_qua.append(DongBoQua(san_pham_id=d.san_pham_id, don_vi_id=d.don_vi_id, ly_do=ly_do))

    for d in dong_vao:
        nap = naps.get(d.san_pham_id)
        ly_do = _ly_do_khong_hop_le(nap, d.don_vi_id)
        if ly_do:
            ghi_bo_qua(d, ly_do)
            continue
        assert nap is not None
        co = next((c for c in dong if c.san_pham_id == d.san_pham_id and c.don_vi_id == d.don_vi_id), None)
        da_co = co.so_luong if co else 0
        muon = min(da_co + d.so_luong, SO_LUONG_DONG_TOI_DA)
        toi_da = nap.sp.so_luong_toi_da_moi_don
        if toi_da is not None:
            con_cho = toi_da - _co_so_khac(dong, nap, {co.id} if co else set())
            muon = min(muon, max(con_cho, 0) // _he_so(nap, d.don_vi_id))
        if muon <= da_co:
            ghi_bo_qua(d, "vuot_toi_da")
            continue
        if co:
            co.so_luong = muon
        else:
            co = CtGioHang(gio_hang_id=gio.id, san_pham_id=d.san_pham_id, don_vi_id=d.don_vi_id, so_luong=muon)
            db.add(co)
            await db.flush()
            dong.append(co)
    await db.flush()
    return KetQuaGop(gio_hang=await xem_gio(db, khach), bo_qua=bo_qua)


async def khoa_gio(db: AsyncSession, khach: KhachHang) -> GioHang:
    """Khóa dòng giỏ của khách (tạo nếu chưa có) để tuần tự hóa các lần đặt hàng đồng thời."""
    return await _gio_cua(db, khach)


@dataclass
class DongDat:
    """Một dòng giỏ đã kiểm tra mua được, kèm sản phẩm và đơn vị để dựng dòng đơn hàng (T4.4)."""

    dong_id: int
    sp: SanPham
    dv: DonViQuyDoi
    so_luong: int


async def lay_dong_de_dat(db: AsyncSession, khach: KhachHang) -> list[DongDat]:
    """Khóa giỏ của khách rồi trả các dòng để đặt hàng. Mọi dòng phải mua được (cùng quy tắc giỏ): có dòng không hợp
    lệ thì ném đúng lỗi của dòng đó (kê đơn, không còn bán, vượt giới hạn) thay vì lặng lẽ bỏ dòng."""
    gio = await khoa_gio(db, khach)
    dong = await _dong_cua_gio(db, gio)
    return await kiem_tra_dong_de_dat(db, [(c.id, c.san_pham_id, c.don_vi_id, c.so_luong) for c in dong])


async def kiem_tra_dong_de_dat(
    db: AsyncSession, dong: list[tuple[int, int, int, int]], *, cho_phep_ke_don: bool = False
) -> list[DongDat]:
    """Kiểm tra các dòng `(dong_id, san_pham_id, don_vi_id, so_luong)` có mua được không, cùng quy tắc với giỏ hàng
    (kê đơn bị chặn ở đây, đơn vị bán online, giới hạn mỗi đơn). Dùng chung cho đặt hàng online và tạo đơn hộ (DS07).

    `cho_phep_ke_don` CHỈ dành cho tạo đơn từ yêu cầu đơn thuốc đã duyệt (DS05): dược sĩ được chọn thuốc kê đơn và đơn
    vị bất kỳ của sản phẩm; mọi đường khác giữ mặc định chặn (CLAUDE.md quy tắc 6)."""
    naps = await _nap_san_pham(db, {sp_id for _, sp_id, _, _ in dong})
    tong_co_so: dict[int, int] = defaultdict(int)
    ra: list[DongDat] = []
    for dong_id, sp_id, don_vi_id, so_luong in dong:
        nap = naps.get(sp_id)
        ly_do = _ly_do_khong_hop_le(nap, don_vi_id, cho_phep_ke_don)
        if ly_do is not None:
            raise _nem_loi(ly_do, nap)
        assert nap is not None
        dv = next(d for d in nap.sp.don_vi_quy_doi if d.id == don_vi_id)
        tong_co_so[nap.sp.id] += so_luong * dv.he_so
        ra.append(DongDat(dong_id, nap.sp, dv, so_luong))
    for d in ra:
        toi_da = d.sp.so_luong_toi_da_moi_don
        if toi_da is not None and tong_co_so[d.sp.id] > toi_da:
            raise _loi_vuot(d.sp)
    return ra


async def xoa_dong_da_dat(db: AsyncSession, dong_ids: list[int]) -> None:
    """Bỏ các dòng giỏ vừa chuyển thành đơn (cùng transaction với việc tạo đơn)."""
    if dong_ids:
        await db.execute(delete(CtGioHang).where(CtGioHang.id.in_(dong_ids)))


async def xem_gio(db: AsyncSession, khach: KhachHang) -> GioHangRa:
    gio = await _gio_cua(db, khach)
    dong = await _dong_cua_gio(db, gio)
    return await dung_gio(db, [(c.id, c.san_pham_id, c.don_vi_id, c.so_luong) for c in dong])


async def dung_gio(db: AsyncSession, dong_vao: list[tuple[int | None, int, int, int]]) -> GioHangRa:
    """Dựng `GioHangRa` từ các dòng `(dong_id, san_pham_id, don_vi_id, so_luong)`: giỏ đã lưu hoặc giỏ localStorage."""
    ids = {d[1] for d in dong_vao}
    naps = await _nap_san_pham(db, ids)
    ton: dict[int, int] = {}
    anh: dict[int, str] = {}
    if ids:
        ton = dict((await db.execute(select(SanPham.id, ton_kha_dung()).where(SanPham.id.in_(ids)))).all())
        for a in (
            await db.execute(
                select(AnhSanPham)
                .where(AnhSanPham.san_pham_id.in_(ids))
                .order_by(AnhSanPham.la_anh_chinh.desc(), AnhSanPham.thu_tu, AnhSanPham.id)
            )
        ).scalars():
            anh.setdefault(a.san_pham_id, a.url)
    tong_co_so: dict[int, int] = defaultdict(int)
    for _, sp_id, dv_id, sl in dong_vao:
        nap = naps.get(sp_id)
        if nap and any(x.id == dv_id for x in nap.sp.don_vi_quy_doi):
            tong_co_so[sp_id] += sl * _he_so(nap, dv_id)
    ra: list[DongGio] = []
    for dong_id, sp_id, dv_id, sl in dong_vao:
        nap = naps.get(sp_id)
        ly_do = _ly_do_khong_hop_le(nap, dv_id)
        if nap is None:
            continue  # sản phẩm không còn tồn tại: không có gì để hiển thị
        sp = nap.sp
        if ly_do is None and sp.so_luong_toi_da_moi_don is not None and tong_co_so[sp_id] > sp.so_luong_toi_da_moi_don:
            ly_do = "vuot_toi_da"
        dv = next((d for d in sp.don_vi_quy_doi if d.id == dv_id), None)
        chon = sorted((d for d in sp.don_vi_quy_doi if d.ban_online), key=lambda d: (d.he_so, d.id))
        he_so = dv.he_so if dv else 1
        toi_da = sp.so_luong_toi_da_moi_don
        ra.append(
            DongGio(
                dong_id=dong_id,
                san_pham=SanPhamTrongGio(
                    id=sp.id,
                    ten=sp.ten,
                    slug=sp.slug,
                    anh_chinh_url=anh.get(sp.id),
                    can_tu_van=sp.loai_san_pham == LoaiSanPham.thuoc_ke_don,
                ),
                don_vi=_don_vi(dv) if dv else None,
                don_vi_co_the_chon=[_don_vi(d) for d in chon],
                so_luong=sl,
                thanh_tien=lam_tron_vnd(dv.gia_ban * sl) if dv else lam_tron_vnd(0),
                toi_da_don_vi=None if toi_da is None else toi_da // he_so,
                ton_kha_dung_don_vi=max(ton.get(sp.id, 0), 0) // he_so,
                mua_duoc=ly_do is None,
                ly_do=ly_do,
            )
        )
    mua_duoc = [d for d in ra if d.mua_duoc]
    return GioHangRa(
        dong=ra,
        tam_tinh=cong(*[d.thanh_tien for d in mua_duoc]) if mua_duoc else lam_tron_vnd(0),
        tong_so_luong=sum(d.so_luong for d in mua_duoc),
    )


def _don_vi(d: DonViQuyDoi) -> DonViTrongGio:
    return DonViTrongGio(id=d.id, ten_don_vi=d.ten_don_vi, he_so=d.he_so, gia_ban=d.gia_ban)


async def mua_kem(db: AsyncSession, san_pham_ids: set[int]) -> list[MuaKem]:
    """ "Thường được mua cùng": luật `luat_mua_kem` có `san_pham_a` trong giỏ; chỉ sản phẩm hiển thị, KHÔNG phải thuốc
    kê đơn (AI/gợi ý không được đưa thuốc kê đơn vào đường mua), có đơn vị bán online. Chưa có luật thì trả rỗng."""
    if not san_pham_ids:
        return []
    cay = await nap_cay_hien_thi(db)
    luat = (
        (
            await db.execute(
                select(LuatMuaKem.san_pham_b_id)
                .join(SanPham, SanPham.id == LuatMuaKem.san_pham_b_id)
                .where(
                    LuatMuaKem.san_pham_a_id.in_(san_pham_ids),
                    LuatMuaKem.san_pham_b_id.not_in(san_pham_ids),
                    SanPham.deleted_at.is_(None),
                    SanPham.trang_thai == TrangThaiKinhDoanh.dang_kinh_doanh,
                    SanPham.danh_muc_id.in_(cay.ids),
                    SanPham.loai_san_pham != LoaiSanPham.thuoc_ke_don,
                )
                .group_by(LuatMuaKem.san_pham_b_id)
                .order_by(
                    func.max(LuatMuaKem.lift).desc(), func.max(LuatMuaKem.confidence).desc(), LuatMuaKem.san_pham_b_id
                )
                .limit(SO_MUA_KEM_TOI_DA * 2)
            )
        )
        .scalars()
        .all()
    )
    if not luat:
        return []
    sps = {
        sp.id: sp
        for sp in (
            await db.execute(select(SanPham).where(SanPham.id.in_(luat)).options(selectinload(SanPham.don_vi_quy_doi)))
        ).scalars()
    }
    anh: dict[int, str] = {}
    for a in (
        await db.execute(
            select(AnhSanPham)
            .where(AnhSanPham.san_pham_id.in_(luat))
            .order_by(AnhSanPham.la_anh_chinh.desc(), AnhSanPham.thu_tu, AnhSanPham.id)
        )
    ).scalars():
        anh.setdefault(a.san_pham_id, a.url)
    ra = []
    for id_ in luat:  # giữ thứ tự xếp hạng của truy vấn
        sp = sps[id_]
        dv = chon_don_vi_gia(sp.don_vi_quy_doi)
        if dv is None:
            continue
        ra.append(
            MuaKem(
                id=sp.id,
                ten=sp.ten,
                slug=sp.slug,
                anh_chinh_url=anh.get(sp.id),
                don_vi_id=dv.id,
                ten_don_vi=dv.ten_don_vi,
                gia_ban=dv.gia_ban,
            )
        )
        if len(ra) == SO_MUA_KEM_TOI_DA:
            break
    return ra
