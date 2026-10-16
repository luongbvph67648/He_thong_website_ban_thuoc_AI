"""Kho nhận hàng khách trả về (spec 04 mục 3 dòng 4) và hàng hoàn do giao thất bại (mục 1.1 dòng 27), KHO10 (T6.2).

Không commit. Tồn kho chỉ đổi qua `modules/kho/ton_kho.py`: hàng khách trả vào khu biệt trữ (`nhan_tra_ve`), hàng hoàn
nguyên niêm phong hoàn nhập đúng lô, hàng hoàn hư hỏng vào biệt trữ.
"""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import luu_tru
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import CtDonHang, CtYeuCauDoiTra, DonHang, PhanBoLo, ThanhToan, VanDon, YeuCauDoiTra
from app.models.enums import (
    LoaiGiaoDich,
    LoaiVanDon,
    TrangThaiDoiTra,
    TrangThaiDon,
    TrangThaiGiaoDich,
    TrangThaiPhanBo,
    TrangThaiThanhToan,
)
from app.models.he_thong import NhanVien, VaiTro
from app.models.kho import LoThuoc
from app.modules.ban_hang import dat_hang
from app.modules.ban_hang.trang_thai import NGUON_NGUOI_DUNG, TacNhan, chuyen_trang_thai
from app.modules.doi_tra.schemas_kho import (
    DoiTraKhoRa,
    DongKhoRa,
    HoanVeKhoRa,
    KetQuaKiemHoan,
    KiemHoanVeVao,
    LoGoiY,
    NhanDoiTraVao,
    TinhTrangHang,
)
from app.modules.kho import ton_kho
from app.modules.thong_bao import service as thong_bao

MA_VAI_TRO_KHO = "WAREHOUSE"


async def _dam_bao_la_kho(db: AsyncSession, nv: NhanVien) -> None:
    """Chỉ nhân viên kho nhận hàng: `return.receive` gán cho vai trò khác (AD18) cũng không đổi được tồn."""
    if await db.scalar(select(VaiTro.ma).where(VaiTro.id == nv.vai_tro_id)) != MA_VAI_TRO_KHO:
        raise LoiNghiepVu("KHONG_CO_QUYEN", "Chỉ nhân viên kho mới được nhận hàng trả về")


async def _lo_theo_dong(db: AsyncSession, ct_ids: list[int]) -> dict[int, list[LoGoiY]]:
    ds = (
        await db.execute(
            select(PhanBoLo, LoThuoc)
            .join(LoThuoc, LoThuoc.id == PhanBoLo.lo_id)
            .where(PhanBoLo.ct_don_hang_id.in_(ct_ids), PhanBoLo.trang_thai == TrangThaiPhanBo.da_xuat)
            .order_by(PhanBoLo.id)
        )
    ).all()
    gop: dict[int, dict[int, LoGoiY]] = defaultdict(dict)
    for p, lo in ds:
        cu = gop[p.ct_don_hang_id].get(lo.id)
        if cu:
            cu.so_luong_da_xuat += p.so_luong_co_so
        else:
            gop[p.ct_don_hang_id][lo.id] = LoGoiY(
                lo_id=lo.id, so_lo=lo.so_lo, han_su_dung=lo.han_su_dung, so_luong_da_xuat=p.so_luong_co_so
            )
    return {k: list(v.values()) for k, v in gop.items()}


async def danh_sach_doi_tra(db: AsyncSession, nv: NhanVien) -> list[DoiTraKhoRa]:
    """Yêu cầu đã duyệt, kho chưa nhận. Không trả thông tin khách (kho không cần)."""
    await _dam_bao_la_kho(db, nv)
    ds = (
        await db.execute(
            select(YeuCauDoiTra, DonHang.ma_don)
            .join(DonHang, DonHang.id == YeuCauDoiTra.don_hang_id)
            .where(YeuCauDoiTra.trang_thai == TrangThaiDoiTra.da_duyet)
            .order_by(YeuCauDoiTra.created_at, YeuCauDoiTra.id)
            .limit(200)
        )
    ).all()
    return [await _doi_tra_ra(db, yc, ma) for yc, ma in ds]


async def _doi_tra_ra(db: AsyncSession, yc: YeuCauDoiTra, ma_don: str) -> DoiTraKhoRa:
    dong = (
        await db.execute(
            select(CtYeuCauDoiTra, CtDonHang)
            .join(CtDonHang, CtDonHang.id == CtYeuCauDoiTra.ct_don_hang_id)
            .where(CtYeuCauDoiTra.yeu_cau_id == yc.id)
            .order_by(CtYeuCauDoiTra.id)
        )
    ).all()
    lo = await _lo_theo_dong(db, [ct.id for _, ct in dong])
    van_don = await db.scalar(
        select(VanDon.ma_van_don)
        .where(VanDon.yeu_cau_doi_tra_id == yc.id, VanDon.loai == LoaiVanDon.tra_hang)
        .order_by(VanDon.id.desc())
        .limit(1)
    )
    return DoiTraKhoRa(
        id=yc.id,
        ma_yeu_cau=yc.ma_yeu_cau,
        ma_don=ma_don,
        ly_do=yc.ly_do,
        mo_ta=yc.mo_ta,
        ma_van_don=van_don,
        anh=[luu_tru.url_ky(k) for k in yc.anh or []],
        dong=[
            DongKhoRa(
                ct_don_hang_id=ct.id,
                ten_san_pham=ct.ten_san_pham,
                ten_don_vi=ct.ten_don_vi,
                he_so=ct.he_so,
                so_luong=r.so_luong,
                lo=lo.get(ct.id, []),
            )
            for r, ct in dong
        ],
    )


async def chi_tiet_doi_tra(db: AsyncSession, nv: NhanVien, yc_id: int) -> DoiTraKhoRa:
    """Kho chỉ thấy yêu cầu đã duyệt hoặc đã nhận (yêu cầu chờ duyệt/từ chối chứa mô tả tự do của khách)."""
    await _dam_bao_la_kho(db, nv)
    dong = (
        await db.execute(
            select(YeuCauDoiTra, DonHang.ma_don)
            .join(DonHang, DonHang.id == YeuCauDoiTra.don_hang_id)
            .where(YeuCauDoiTra.id == yc_id)
        )
    ).first()
    if dong is None or dong[0].trang_thai not in (TrangThaiDoiTra.da_duyet, TrangThaiDoiTra.kho_da_nhan):
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy yêu cầu đổi trả")
    return await _doi_tra_ra(db, dong[0], dong[1])


async def nhan_doi_tra(db: AsyncSession, nv: NhanVien, yc_id: int, vao: NhanDoiTraVao) -> DoiTraKhoRa:
    """Dòng 4: ghi lô và số lượng nhận từng dòng, hàng vào khu biệt trữ; yêu cầu sang `kho_da_nhan`."""
    await _dam_bao_la_kho(db, nv)
    yc = (
        await db.execute(
            select(YeuCauDoiTra)
            .where(YeuCauDoiTra.id == yc_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if yc is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy yêu cầu đổi trả")
    if yc.trang_thai != TrangThaiDoiTra.da_duyet:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Chỉ nhận hàng cho yêu cầu đã duyệt và chưa nhận")
    ds = (
        await db.execute(
            select(CtYeuCauDoiTra, CtDonHang)
            .join(CtDonHang, CtDonHang.id == CtYeuCauDoiTra.ct_don_hang_id)
            .where(CtYeuCauDoiTra.yeu_cau_id == yc.id)
            .order_by(CtYeuCauDoiTra.id)
        )
    ).all()
    theo_ct = {ct.id: (r, ct) for r, ct in ds}
    gui = {d.ct_don_hang_id: d for d in vao.dong}
    if len(gui) != len(vao.dong) or set(gui) != set(theo_ct):
        raise dat_hang.khong_hop_le("dong", "Phải kiểm đủ từng dòng của yêu cầu, mỗi dòng một lần")
    lo_theo_ct = await _lo_theo_dong(db, list(theo_ct))
    cong: list[tuple[int, int]] = []
    for ct_id, d in gui.items():
        r, ct = theo_ct[ct_id]
        if d.so_luong_nhan > r.so_luong:
            raise dat_hang.khong_hop_le("dong", f"{ct.ten_san_pham}: nhận nhiều hơn số lượng khách trả ({r.so_luong})")
        if d.so_luong_nhan == 0:
            continue
        if d.lo_id is None or d.lo_id not in {x.lo_id for x in lo_theo_ct.get(ct_id, [])}:
            raise dat_hang.khong_hop_le("dong", f"{ct.ten_san_pham}: chọn lô đã xuất cho dòng đơn này")
        cong.append((d.lo_id, d.so_luong_nhan * ct.he_so))
    tong_theo_lo: dict[int, int] = defaultdict(int)
    for lo_id, sl in cong:
        tong_theo_lo[lo_id] += sl
    for ct_id, d in gui.items():
        if d.so_luong_nhan > 0 and d.lo_id is not None:
            da_xuat = next(x.so_luong_da_xuat for x in lo_theo_ct[ct_id] if x.lo_id == d.lo_id)
            if d.so_luong_nhan * theo_ct[ct_id][1].he_so > da_xuat:
                raise dat_hang.khong_hop_le("dong", f"{theo_ct[ct_id][1].ten_san_pham}: lô này chỉ đã xuất {da_xuat}")
    chung_tu = ton_kho.ChungTu("yeu_cau_doi_tra", yc.id, nv.id)
    lo_khoa = {lo.id: lo for lo in await ton_kho.khoa_cac_lo(db, sorted(tong_theo_lo))}
    for lo_id in sorted(tong_theo_lo):
        await ton_kho.vao_biet_tru(db, lo_khoa[lo_id], tong_theo_lo[lo_id], chung_tu)
    for ct_id, d in gui.items():
        r, _ = theo_ct[ct_id]
        r.so_luong_nhan = d.so_luong_nhan
        r.lo_id = d.lo_id if d.so_luong_nhan else None
    yc.trang_thai, yc.nhan_vien_kho_id = TrangThaiDoiTra.kho_da_nhan, nv.id
    yc.ket_qua_kiem_hang, yc.updated_at = vao.ket_qua_kiem_hang.strip(), bay_gio_utc()
    await db.flush()
    await thong_bao.gui_cho_khach(
        db,
        yc.khach_hang_id,
        loai="doi_tra",
        tieu_de=f"Nhà thuốc đã nhận hàng trả của yêu cầu {yc.ma_yeu_cau}",
        noi_dung="Dược sĩ sẽ xử lý hoàn tiền hoặc gửi hàng thay thế.",
        lien_ket="/tai-khoan/doi-tra",
    )
    return await chi_tiet_doi_tra(db, nv, yc_id)


async def danh_sach_hoan_ve(db: AsyncSession, nv: NhanVien) -> list[HoanVeKhoRa]:
    await _dam_bao_la_kho(db, nv)
    don_ds = (
        (
            await db.execute(
                select(DonHang)
                .where(DonHang.trang_thai == TrangThaiDon.hoan_ve_kho)
                .order_by(DonHang.updated_at, DonHang.id)
                .limit(200)
            )
        )
        .scalars()
        .all()
    )
    return [await _hoan_ve_ra(db, d) for d in don_ds]


async def _hoan_ve_ra(db: AsyncSession, don: DonHang) -> HoanVeKhoRa:
    cts = (
        (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id).order_by(CtDonHang.id)))
        .scalars()
        .all()
    )
    lo = await _lo_theo_dong(db, [c.id for c in cts])
    return HoanVeKhoRa(
        id=don.id,
        ma_don=don.ma_don,
        trang_thai=don.trang_thai,
        da_thanh_toan=don.trang_thai_tt == TrangThaiThanhToan.da_thanh_toan,
        dong=[
            DongKhoRa(
                ct_don_hang_id=c.id,
                ten_san_pham=c.ten_san_pham,
                ten_don_vi=c.ten_don_vi,
                he_so=c.he_so,
                so_luong=c.so_luong,
                lo=lo.get(c.id, []),
            )
            for c in cts
        ],
    )


async def kiem_hoan_ve(db: AsyncSession, nv: NhanVien, don_id: int, vao: KiemHoanVeVao) -> KetQuaKiemHoan:
    """Dòng 27 của đơn hàng: nguyên niêm phong hoàn nhập đúng lô, hư hỏng vào biệt trữ, rồi chuyển `da_huy` qua HT06
    (hook tạo giao dịch hoàn tiền nếu đã thanh toán)."""
    await _dam_bao_la_kho(db, nv)
    don = (
        await db.execute(
            select(DonHang).where(DonHang.id == don_id).with_for_update().execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if don is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy đơn hàng")
    if don.trang_thai != TrangThaiDon.hoan_ve_kho:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Chỉ kiểm hàng của đơn đã hoàn về kho")
    cts = (await db.execute(select(CtDonHang.id).where(CtDonHang.don_hang_id == don.id))).scalars().all()
    gui = {d.ct_don_hang_id: d.tinh_trang for d in vao.dong}
    if len(gui) != len(vao.dong) or set(gui) != set(cts):
        raise dat_hang.khong_hop_le("dong", "Phải kiểm đủ từng dòng của đơn, mỗi dòng một lần")
    phan_bo = (
        (
            await db.execute(
                select(PhanBoLo)
                .where(PhanBoLo.ct_don_hang_id.in_(cts), PhanBoLo.trang_thai == TrangThaiPhanBo.da_xuat)
                .order_by(PhanBoLo.id)
            )
        )
        .scalars()
        .all()
    )
    nguyen = [p for p in phan_bo if gui[p.ct_don_hang_id] == TinhTrangHang.nguyen_niem_phong]
    hong = [p for p in phan_bo if gui[p.ct_don_hang_id] == TinhTrangHang.hu_hong]
    chung_tu = ton_kho.ChungTu("don_hang", don.id, nv.id)
    if nguyen:
        await ton_kho.hoan_nhap(db, nguyen, chung_tu)
    sl_hong: dict[int, int] = defaultdict(int)
    for p in hong:
        sl_hong[p.lo_id] += p.so_luong_co_so
    if sl_hong:
        lo_khoa = {lo.id: lo for lo in await ton_kho.khoa_cac_lo(db, sorted(sl_hong))}
        for lo_id in sorted(sl_hong):
            await ton_kho.vao_biet_tru(db, lo_khoa[lo_id], sl_hong[lo_id], chung_tu)
    ghi_chu = "Kho kiểm hàng hoàn: " + ", ".join(
        f"{'nguyên niêm phong' if t == TinhTrangHang.nguyen_niem_phong else 'hư hỏng'}"
        for t in sorted(set(gui.values()))
    )
    if vao.ghi_chu:
        ghi_chu += f". {vao.ghi_chu.strip()}"
    tac_nhan = TacNhan.kho(nv.id)
    await chuyen_trang_thai(db, don, TrangThaiDon.da_huy, tac_nhan, NGUON_NGUOI_DUNG, ghi_chu)
    cho_hoan = (
        await db.scalar(
            select(ThanhToan.id).where(
                ThanhToan.don_hang_id == don.id,
                ThanhToan.loai == LoaiGiaoDich.hoan_tien,
                ThanhToan.trang_thai == TrangThaiGiaoDich.khoi_tao,
            )
        )
    ) is not None
    return KetQuaKiemHoan(
        ma_don=don.ma_don,
        trang_thai=don.trang_thai,
        cho_hoan_tien=cho_hoan,
        so_luong_hoan_nhap=sum(p.so_luong_co_so for p in nguyen),
        so_luong_biet_tru=sum(p.so_luong_co_so for p in hong),
    )
