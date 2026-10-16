"""KHO01: /api/v1/noi-bo/nha-cung-cap."""

GOC = "/api/v1/noi-bo/nha-cung-cap"


async def tao(c, **ghi_de):
    r = await c.post(GOC, json={"ten": "Công ty Dược A", "ma_so_thue": "0312345678", **ghi_de})
    assert r.status_code == 201, r.text
    return r.json()


async def test_tao_chuan_hoa_va_tra_phien_ban(dang_nhap_kho):
    n = await tao(
        dang_nhap_kho, ten="  Dược   A ", ma_so_thue="0312345678001", so_dien_thoai="0912345678", email=" A@B.vn "
    )
    assert n["ten"] == "Dược A" and n["ma_so_thue"] == "0312345678-001" and n["email"] == "a@b.vn"
    assert n["dang_hop_tac"] is True and len(n["phien_ban"]) == 16


async def test_trung_ma_so_thue_ke_ca_da_ngung(dang_nhap_kho):
    n = await tao(dang_nhap_kho)
    r = await dang_nhap_kho.post(GOC, json={"ten": "B", "ma_so_thue": "0312345678"})
    assert r.status_code == 409 and r.json()["ma_loi"] == "TRUNG_DU_LIEU"
    assert (await dang_nhap_kho.delete(f"{GOC}/{n['id']}", params={"phien_ban": n["phien_ban"]})).status_code == 204
    r = await dang_nhap_kho.post(GOC, json={"ten": "B", "ma_so_thue": "0312345678"})
    assert r.status_code == 409


async def test_ma_so_thue_sai_la_400(dang_nhap_kho):
    for mst in ("123", "abcdefghij", "0312345678-12"):
        r = await dang_nhap_kho.post(GOC, json={"ten": "A", "ma_so_thue": mst})
        assert r.status_code == 400, mst


async def test_sua_chi_doi_truong_gui_va_xoa_bang_null(dang_nhap_kho):
    n = await tao(dang_nhap_kho, dia_chi="HN")
    r = await dang_nhap_kho.patch(f"{GOC}/{n['id']}", json={"phien_ban": n["phien_ban"], "dia_chi": None, "ten": "Mới"})
    assert r.status_code == 200 and r.json()["dia_chi"] is None and r.json()["ma_so_thue"] == "0312345678"
    r2 = await dang_nhap_kho.patch(f"{GOC}/{n['id']}", json={"phien_ban": r.json()["phien_ban"], "ten": None})
    assert r2.status_code == 400


async def test_phien_ban_cu_la_409(dang_nhap_kho):
    n = await tao(dang_nhap_kho)
    await dang_nhap_kho.patch(f"{GOC}/{n['id']}", json={"phien_ban": n["phien_ban"], "ten": "Đổi"})
    r = await dang_nhap_kho.patch(f"{GOC}/{n['id']}", json={"phien_ban": n["phien_ban"], "ten": "Đổi nữa"})
    assert r.status_code == 409 and r.json()["ma_loi"] == "DU_LIEU_DA_THAY_DOI"
    assert "phien_ban_hien_tai" in r.json()["chi_tiet"]


async def test_ngung_hop_tac_xoa_mem_loc_va_hop_tac_lai(dang_nhap_kho):
    n = await tao(dang_nhap_kho)
    assert (await dang_nhap_kho.delete(f"{GOC}/{n['id']}", params={"phien_ban": n["phien_ban"]})).status_code == 204
    assert (await dang_nhap_kho.get(GOC)).json()["tong"] == 0
    ngung = (await dang_nhap_kho.get(GOC, params={"trang_thai": "ngung"})).json()
    assert ngung["tong"] == 1 and ngung["du_lieu"][0]["dang_hop_tac"] is False
    # ngừng lần hai bằng phiên bản cũ: 409
    assert (await dang_nhap_kho.delete(f"{GOC}/{n['id']}", params={"phien_ban": n["phien_ban"]})).status_code == 409
    r = await dang_nhap_kho.post(f"{GOC}/{n['id']}/hop-tac-lai")
    assert r.status_code == 200 and r.json()["dang_hop_tac"] is True
    assert (await dang_nhap_kho.post(f"{GOC}/{n['id']}/hop-tac-lai")).status_code == 200  # idempotent


async def test_tim_kiem_khong_dau(dang_nhap_kho):
    await tao(dang_nhap_kho, ten="Công ty Dược Hậu Giang", ma_so_thue="1111111111")
    await tao(dang_nhap_kho, ten="Khác", ma_so_thue="2222222222")
    r = await dang_nhap_kho.get(GOC, params={"q": "duoc hau"})
    assert [x["ten"] for x in r.json()["du_lieu"]] == ["Công ty Dược Hậu Giang"]


async def test_admin_chi_xem_duoc_si_bi_chan(clients_theo_vai_tro):
    n = await tao(clients_theo_vai_tro["WAREHOUSE"])
    admin, ds = clients_theo_vai_tro["ADMIN"], clients_theo_vai_tro["PHARMACIST"]
    assert (await admin.get(f"{GOC}/{n['id']}")).status_code == 200
    assert (await admin.post(GOC, json={"ten": "X"})).status_code == 403
    assert (await ds.get(GOC)).status_code == 403
