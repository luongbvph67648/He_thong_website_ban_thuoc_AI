"""Phiếu nhập kho (KHO02, spec 06 mục 3.15). Phiếu đã lưu không sửa, không xóa."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cau_hinh import doc_cau_hinh
from app.core.loi import LoiNghiepVu
from app.core.ma_chung_tu import ma_phieu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_trang import ThamSoPhanTrang, Trang, lay_trang, tao_trang
from app.core.thoi_gian import dau_ngay_vn, hom_nay_vn
from app.core.tien import cong, lam_tron_vnd
from app.core.tim_kiem import mau_tim_like
from app.models.enums import TrangThaiLo
from app.models.he_thong import NhanVien
from app.models.kho import CtPhieuNhap, LoThuoc, NhaCungCap, PhieuNhap
from app.models.san_pham import DonViQuyDoi, SanPham
from app.modules.kho import ton_kho
from app.modules.kho.lo import trang_thai_theo_han
from app.modules.kho.schemas_phieu_nhap import (
    CanhBao,
    DongNhapRa,
    DonViRut,
    DonViTraCuu,
    NhaCungCapRut,
    NhanVienRut,
    PhieuNhapChiTiet,
    PhieuNhapTao,
    PhieuNhapTomTat,
    SanPhamRut,
    SanPhamTraCuu,
)
from app.modules.kho.ton_kho import ChungTu

BANG = "phieu_nhap"
NAM_TOI_DA = 15
TON_TOI_DA = 2_000_000_000
TONG_TIEN_TOI_DA = 10**14


def _loi_truong(truong: str, loi: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": truong, "loi": loi}])


def _khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy phiếu nhập")


async def tao(db: AsyncSession, actor: NhanVien, du_lieu: PhieuNhapTao, *, ip: str) -> PhieuNhapChiTiet:
    hom_nay = hom_nay_vn()
    # --- Kiểm tra đầu vào (chưa ghi gì) ---
    if (
        await db.scalar(
            select(NhaCungCap.id).where(NhaCungCap.id == du_lieu.nha_cung_cap_id, NhaCungCap.deleted_at.is_(None))
        )
        is None
    ):
        raise _loi_truong("nha_cung_cap_id", "Nhà cung cấp không tồn tại hoặc đã ngừng hợp tác")
    sp_ids = {d.san_pham_id for d in du_lieu.dong}
    san_pham = {
        s.id: s
        for s in (
            await db.execute(select(SanPham).where(SanPham.id.in_(sp_ids), SanPham.deleted_at.is_(None)))
        ).scalars()
    }
    don_vi = {
        d.id: d
        for d in (
            await db.execute(select(DonViQuyDoi).where(DonViQuyDoi.id.in_({d.don_vi_id for d in du_lieu.dong})))
        ).scalars()
    }
    gioi_han_hsd = hom_nay + timedelta(days=366 * NAM_TOI_DA)
    nguong_toi_thieu = int(await doc_cau_hinh(db, "han_su_dung_toi_thieu_nhap_ngay", 180))
    nguong_can_han = int(await doc_cau_hinh(db, "nguong_can_han_ngay", 90))
    hsd_theo_lo: dict[tuple[int, str], date] = {}
    canh_bao: list[CanhBao] = []
    for i, d in enumerate(du_lieu.dong):
        if d.san_pham_id not in san_pham:
            raise _loi_truong(f"dong.{i}.san_pham_id", "Sản phẩm không tồn tại")
        if d.don_vi_id not in don_vi or don_vi[d.don_vi_id].san_pham_id != d.san_pham_id:
            raise _loi_truong(f"dong.{i}.don_vi_id", "Đơn vị không thuộc sản phẩm này")
        if d.han_su_dung <= hom_nay:
            raise _loi_truong(f"dong.{i}.han_su_dung", "Hạn sử dụng phải sau hôm nay")
        if d.han_su_dung > gioi_han_hsd:
            raise _loi_truong(f"dong.{i}.han_su_dung", f"Hạn sử dụng không quá {NAM_TOI_DA} năm tới")
        if d.ngay_san_xuat and (d.ngay_san_xuat > hom_nay or d.ngay_san_xuat >= d.han_su_dung):
            raise _loi_truong(f"dong.{i}.ngay_san_xuat", "Ngày sản xuất không sau hôm nay và phải trước hạn sử dụng")
        khoa = (d.san_pham_id, d.so_lo)
        if hsd_theo_lo.setdefault(khoa, d.han_su_dung) != d.han_su_dung:
            raise _trung_so_lo(i)
        so_ngay = (d.han_su_dung - hom_nay).days
        if so_ngay < nguong_toi_thieu:
            canh_bao.append(
                CanhBao(
                    dong=i,
                    loai="han_su_dung_ngan",
                    han_su_dung=d.han_su_dung,
                    so_ngay_con_lai=so_ngay,
                    toi_thieu=nguong_toi_thieu,
                )
            )
    tong_tien = cong(*[d.so_luong * d.gia_nhap for d in du_lieu.dong])
    if tong_tien >= TONG_TIEN_TOI_DA:
        raise _loi_truong("dong", "Tổng tiền phiếu vượt giới hạn cho phép")
    if canh_bao and not du_lieu.xac_nhan_canh_bao:
        raise LoiNghiepVu(
            "CAN_XAC_NHAN_CANH_BAO",
            "Có dòng hạn sử dụng ngắn, cần xác nhận để tiếp tục",
            chi_tiet={"canh_bao": [c.model_dump(mode="json") for c in canh_bao]},
        )

    # --- Lô: tuần tự hóa theo sản phẩm (id tăng dần) để kiểm tra "cùng số lô khác hạn" không bị đua ---
    for sp_id in sorted(sp_ids):
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"nha_thuoc.lo.{sp_id}"})
    for i, d in enumerate(du_lieu.dong):
        khac = await db.scalar(
            select(LoThuoc.id)
            .where(LoThuoc.san_pham_id == d.san_pham_id, LoThuoc.so_lo == d.so_lo, LoThuoc.han_su_dung != d.han_su_dung)
            .limit(1)
        )
        if khac is not None:
            raise _trung_so_lo(i)
    for (sp_id, so_lo), hsd in hsd_theo_lo.items():
        dong_dau = next(d for d in du_lieu.dong if (d.san_pham_id, d.so_lo) == (sp_id, so_lo))
        await db.execute(
            pg_insert(LoThuoc)
            .values(
                san_pham_id=sp_id,
                so_lo=so_lo,
                ngay_san_xuat=dong_dau.ngay_san_xuat,
                han_su_dung=hsd,
                gia_nhap=0,
                trang_thai=trang_thai_theo_han(hsd, hom_nay, nguong_can_han),
            )
            .on_conflict_do_nothing(index_elements=["san_pham_id", "so_lo", "han_su_dung"])
        )
    lo_theo_khoa = {
        (lo.san_pham_id, lo.so_lo): lo
        for lo in (
            await db.execute(
                select(LoThuoc)
                .where(or_(*[(LoThuoc.san_pham_id == sp) & (LoThuoc.so_lo == sl) for sp, sl in hsd_theo_lo]))
                .execution_options(populate_existing=True)
            )
        ).scalars()
    }
    lo_khoa = {lo.id: lo for lo in await ton_kho.khoa_cac_lo(db, [lo.id for lo in lo_theo_khoa.values()])}
    for i, d in enumerate(du_lieu.dong):
        lo = lo_khoa[lo_theo_khoa[(d.san_pham_id, d.so_lo)].id]
        if lo.trang_thai not in (TrangThaiLo.dang_ban, TrangThaiLo.can_han):
            raise LoiNghiepVu(
                "LO_KHONG_NHAP_DUOC",
                f"Lô {lo.so_lo} đang ở trạng thái {lo.trang_thai.value}, không nhập thêm được",
                chi_tiet={"dong": i, "lo_id": lo.id},
            )

    # --- Ghi phiếu, cộng tồn ---
    phieu = PhieuNhap(
        ma_phieu=await ma_phieu(db, "phieu_nhap"),
        nha_cung_cap_id=du_lieu.nha_cung_cap_id,
        so_hoa_don_ncc=du_lieu.so_hoa_don_ncc,
        nhan_vien_id=actor.id,
        tong_tien=tong_tien,
        ghi_chu=du_lieu.ghi_chu,
    )
    db.add(phieu)
    await db.flush()
    chung_tu = ChungTu("phieu_nhap", phieu.id, actor.id)
    for i, d in enumerate(du_lieu.dong):
        lo = lo_khoa[lo_theo_khoa[(d.san_pham_id, d.so_lo)].id]
        he_so = don_vi[d.don_vi_id].he_so
        co_so = d.so_luong * he_so
        if lo.so_luong_ton + co_so > TON_TOI_DA:
            raise _loi_truong(f"dong.{i}.so_luong", "Tồn của lô sau khi nhập vượt giới hạn cho phép")
        gia_dong = lam_tron_vnd(Decimal(d.gia_nhap) / he_so)
        lo.gia_nhap = (
            gia_dong
            if lo.so_luong_ton == 0
            else lam_tron_vnd((lo.so_luong_ton * lo.gia_nhap + co_so * gia_dong) / (lo.so_luong_ton + co_so))
        )
        if lo.ngay_san_xuat is None and d.ngay_san_xuat:
            lo.ngay_san_xuat = d.ngay_san_xuat
        await db.flush()  # nhap_kho nạp lại lô từ CSDL: phải ghi giá mới trước
        db.add(
            CtPhieuNhap(
                phieu_nhap_id=phieu.id,
                lo_id=lo.id,
                don_vi_id=d.don_vi_id,
                so_luong=d.so_luong,
                so_luong_co_so=co_so,
                gia_nhap=d.gia_nhap,
            )
        )
        await ton_kho.nhap_kho(db, lo, co_so, chung_tu)
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao",
        bang=BANG,
        ban_ghi_id=phieu.id,
        gia_tri_moi={
            "ma_phieu": phieu.ma_phieu,
            "nha_cung_cap_id": phieu.nha_cung_cap_id,
            "tong_tien": str(tong_tien),
            "so_dong": len(du_lieu.dong),
        },
        ip=ip,
    )
    ket_qua = await chi_tiet(db, phieu.id)
    ket_qua.canh_bao = canh_bao
    return ket_qua


def _trung_so_lo(i: int) -> LoiNghiepVu:
    return LoiNghiepVu(
        "TRUNG_DU_LIEU",
        "Số lô này đã có với hạn sử dụng khác: số lô của nhà sản xuất chỉ có một hạn, hãy kiểm tra lại",
        chi_tiet={"truong": f"dong.{i}.so_lo"},
    )


def _tom_tat(p: PhieuNhap, ncc: NhaCungCap, nv: NhanVien, so_dong: int) -> PhieuNhapTomTat:
    return PhieuNhapTomTat(
        id=p.id,
        ma_phieu=p.ma_phieu,
        nha_cung_cap=NhaCungCapRut(id=ncc.id, ten=ncc.ten),
        so_hoa_don_ncc=p.so_hoa_don_ncc,
        nhan_vien=NhanVienRut(id=nv.id, ma_nhan_vien=nv.ma_nhan_vien, ho_ten=nv.ho_ten),
        ngay_nhap=p.ngay_nhap,
        tong_tien=p.tong_tien,
        so_dong=so_dong,
    )


async def danh_sach(
    db: AsyncSession,
    q: str | None,
    nha_cung_cap_id: int | None,
    tu_ngay: date | None,
    den_ngay: date | None,
    tp: ThamSoPhanTrang,
) -> Trang[PhieuNhapTomTat]:
    so_dong = (
        select(func.count()).where(CtPhieuNhap.phieu_nhap_id == PhieuNhap.id).correlate(PhieuNhap).scalar_subquery()
    )
    stmt = (
        select(PhieuNhap, NhaCungCap, NhanVien, so_dong)
        .join(NhaCungCap, NhaCungCap.id == PhieuNhap.nha_cung_cap_id)
        .join(NhanVien, NhanVien.id == PhieuNhap.nhan_vien_id)
    )
    if q and q.strip():
        mau = mau_tim_like(q.lower())
        stmt = stmt.where(
            or_(
                func.lower(PhieuNhap.ma_phieu).like(mau, escape="\\"),
                func.lower(func.coalesce(PhieuNhap.so_hoa_don_ncc, "")).like(mau, escape="\\"),
            )
        )
    if nha_cung_cap_id is not None:
        stmt = stmt.where(PhieuNhap.nha_cung_cap_id == nha_cung_cap_id)
    if tu_ngay is not None:
        stmt = stmt.where(PhieuNhap.ngay_nhap >= dau_ngay_vn(tu_ngay))
    if den_ngay is not None:
        stmt = stmt.where(PhieuNhap.ngay_nhap < dau_ngay_vn(den_ngay + timedelta(days=1)))
    dong, tong = await lay_trang(db, stmt.order_by(PhieuNhap.ngay_nhap.desc(), PhieuNhap.id.desc()), tp, nhieu_cot=True)
    return tao_trang([_tom_tat(p, n, v, c) for p, n, v, c in dong], tong, tp)


async def chi_tiet(db: AsyncSession, phieu_id: int) -> PhieuNhapChiTiet:
    hang = (
        await db.execute(
            select(PhieuNhap, NhaCungCap, NhanVien)
            .join(NhaCungCap, NhaCungCap.id == PhieuNhap.nha_cung_cap_id)
            .join(NhanVien, NhanVien.id == PhieuNhap.nhan_vien_id)
            .where(PhieuNhap.id == phieu_id)
            .execution_options(populate_existing=True)
        )
    ).first()
    if hang is None:
        raise _khong_tim_thay()
    p, ncc, nv = hang
    dong = (
        await db.execute(
            select(CtPhieuNhap, LoThuoc, SanPham, DonViQuyDoi)
            .join(LoThuoc, LoThuoc.id == CtPhieuNhap.lo_id)
            .join(SanPham, SanPham.id == LoThuoc.san_pham_id)
            .join(DonViQuyDoi, DonViQuyDoi.id == CtPhieuNhap.don_vi_id)
            .where(CtPhieuNhap.phieu_nhap_id == phieu_id)
            .order_by(CtPhieuNhap.id)
        )
    ).all()
    return PhieuNhapChiTiet(
        **_tom_tat(p, ncc, nv, len(dong)).model_dump(),
        ghi_chu=p.ghi_chu,
        dong=[
            DongNhapRa(
                lo_id=lo.id,
                san_pham=SanPhamRut(id=sp.id, sku=sp.sku, ten=sp.ten),
                so_lo=lo.so_lo,
                ngay_san_xuat=lo.ngay_san_xuat,
                han_su_dung=lo.han_su_dung,
                don_vi=DonViRut(id=dv.id, ten_don_vi=dv.ten_don_vi, he_so=dv.he_so),
                so_luong=ct.so_luong,
                so_luong_co_so=ct.so_luong_co_so,
                gia_nhap=ct.gia_nhap,
                thanh_tien=ct.so_luong * ct.gia_nhap,
            )
            for ct, lo, sp, dv in dong
        ],
    )


async def tra_cuu_san_pham(db: AsyncSession, q: str) -> list[SanPhamTraCuu]:
    """Tìm sản phẩm chưa xóa để chọn vào dòng phiếu: tên (không dấu), SKU hoặc ĐÚNG mã vạch đơn vị (máy quét)."""
    q = q.strip()
    if not q:
        return []
    mau = mau_tim_like(q)
    khop_vach = select(DonViQuyDoi.san_pham_id).where(DonViQuyDoi.ma_vach == q)
    sp_list = (
        (
            await db.execute(
                select(SanPham)
                .where(
                    SanPham.deleted_at.is_(None),
                    or_(
                        func.f_unaccent(func.lower(SanPham.ten)).like(func.f_unaccent(func.lower(mau)), escape="\\"),
                        func.upper(SanPham.sku).like(func.upper(mau), escape="\\"),
                        SanPham.id.in_(khop_vach),
                    ),
                )
                .order_by(SanPham.ten, SanPham.id)
                .limit(20)
            )
        )
        .scalars()
        .all()
    )
    don_vi = (
        (
            await db.execute(
                select(DonViQuyDoi)
                .where(DonViQuyDoi.san_pham_id.in_([s.id for s in sp_list]))
                .order_by(DonViQuyDoi.he_so, DonViQuyDoi.id)
            )
        )
        .scalars()
        .all()
    )
    return [
        SanPhamTraCuu(
            id=sp.id,
            sku=sp.sku,
            ten=sp.ten,
            don_vi=[
                DonViTraCuu(id=d.id, ten_don_vi=d.ten_don_vi, he_so=d.he_so, ma_vach=d.ma_vach)
                for d in don_vi
                if d.san_pham_id == sp.id
            ],
            don_vi_mac_dinh_id=next((d.id for d in don_vi if d.san_pham_id == sp.id and d.la_mac_dinh), None),
        )
        for sp in sp_list
    ]
