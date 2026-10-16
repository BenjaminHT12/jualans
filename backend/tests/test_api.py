import datetime as dt
import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["JUALANS_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
os.environ.pop("JUALANS_AI_ENABLED", None)

from fastapi.testclient import TestClient  # noqa: E402

from app import ai_scan  # noqa: E402
from app.main import app  # noqa: E402

TODAY = dt.date.today()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user(client):
    import secrets
    phone = "0857" + str(secrets.randbelow(10**8)).zfill(8)
    r = client.post("/api/auth/register", json={"name": "Budi", "contact": phone, "password": "rahasia123"})
    assert r.status_code == 201, r.text
    return {"token": r.json()["token"], "contact": phone}


# ---------- Login ----------

def test_register_login_and_bootstrap(client):
    r = client.post("/api/auth/register", json={"name": "Sari", "contact": "+62 813-1111-2222", "password": "abcdef"})
    assert r.status_code == 201
    data = r.json()
    assert data["user"]["name"] == "Sari"
    assert data["categories"]["masuk"][0] == "Penjualan"
    assert data["transactions"] == [] and data["stock"] == [] and data["customers"] == []
    assert data["business"]["setupDone"] is False

    # nomor yang sama dengan format lain dianggap sama
    dup = client.post("/api/auth/register", json={"name": "X", "contact": "081311112222", "password": "abcdef"})
    assert dup.status_code == 409 and dup.json()["detail"]["code"] == "contact_taken"

    bad = client.post("/api/auth/login", json={"contact": "081311112222", "password": "salah"})
    assert bad.status_code == 401 and bad.json()["detail"]["code"] == "bad_login"

    ok = client.post("/api/auth/login", json={"contact": "6281311112222", "password": "abcdef"})
    assert ok.status_code == 200
    token = ok.json()["token"]
    assert client.get("/api/bootstrap", headers=auth(token)).status_code == 200

    assert client.post("/api/auth/logout", headers=auth(token)).status_code == 200
    assert client.get("/api/bootstrap", headers=auth(token)).status_code == 401


def test_password_is_not_stored_in_plain_text(client):
    from app.db import SessionLocal
    from app.models import User
    client.post("/api/auth/register", json={"name": "Tono", "contact": "tono@contoh.id", "password": "kuncirahasia"})
    with SessionLocal() as db:
        u = db.query(User).filter_by(contact="tono@contoh.id").one()
        assert "kuncirahasia" not in u.password_hash and u.password_hash.startswith("pbkdf2_sha256$")


def test_validation_messages(client):
    r = client.post("/api/auth/register", json={"name": "A", "contact": "bukan-kontak", "password": "abcdef"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "bad_contact"
    r = client.post("/api/auth/register", json={"name": "A", "contact": "081299998888", "password": "123"})
    assert r.status_code == 422
    assert client.get("/api/bootstrap").status_code == 401


# ---------- Akun demo & riwayat 3 bulan ----------

def test_demo_has_three_months_of_history(client):
    r = client.post("/api/auth/demo")
    assert r.status_code == 200
    data = r.json()
    dates = sorted(t["date"] for t in data["transactions"])
    assert data["historyDays"] == 90
    assert dates[0] >= (TODAY - dt.timedelta(days=89)).isoformat()   # tidak lebih dari 3 bulan
    assert dates[0] <= (TODAY - dt.timedelta(days=85)).isoformat()   # tapi memang berisi ~3 bulan
    assert len(data["transactions"]) > 250
    assert len(data["customers"]) == 3 and len(data["stock"]) == 7

    # data yang lebih lama dari 90 hari ada di database tapi tidak dikirim
    from app.db import SessionLocal
    from app.models import Transaction
    with SessionLocal() as db:
        oldest = db.query(Transaction).order_by(Transaction.date).first().date
    assert oldest < TODAY - dt.timedelta(days=89)

    token = data["token"]
    week = client.get("/api/transactions?days=7", headers=auth(token)).json()
    assert all(t["date"] >= (TODAY - dt.timedelta(days=6)).isoformat() for t in week["transactions"])
    assert client.get("/api/transactions?days=120", headers=auth(token)).status_code == 422
    found = client.get("/api/transactions?q=tepung", headers=auth(token)).json()["transactions"]
    assert found and all("tepung" in t["item"].lower() for t in found)


# ---------- Transaksi, stok, bon ----------

def test_transaction_crud_and_stock(client, user):
    h = auth(user["token"])
    item = client.post("/api/stock", headers=h, json={"id": "stoktepung1", "name": "Tepung tapioka", "unit": "kg", "qty": 2, "min": 5}).json()["item"]
    assert item["qty"] == 2 and item["keywords"] == ["tepung", "tapioka"]

    r = client.post("/api/transactions", headers=h, json={
        "id": "txbelanja01", "type": "keluar", "item": "Tepung tapioka 5 kg", "amount": 65000,
        "category": "Bahan baku", "date": TODAY.isoformat(), "stock": {"itemId": "stoktepung1", "qty": 5}})
    assert r.status_code == 201, r.text
    assert r.json()["stock"]["qty"] == 7

    dup = client.post("/api/transactions", headers=h, json={
        "id": "txbelanja01", "type": "masuk", "item": "x", "amount": 1, "category": "Penjualan", "date": TODAY.isoformat()})
    assert dup.status_code == 409

    future = client.post("/api/transactions", headers=h, json={
        "type": "masuk", "item": "x", "amount": 1, "category": "Penjualan", "date": (TODAY + dt.timedelta(days=1)).isoformat()})
    assert future.status_code == 422

    upd = client.put("/api/transactions/txbelanja01", headers=h, json={
        "type": "keluar", "item": "Tepung 5kg", "amount": 60000, "category": "Bahan baku", "date": TODAY.isoformat()})
    assert upd.json()["transaction"]["amount"] == 60000

    adj = client.post("/api/stock/stoktepung1/adjust", headers=h, json={"change": -3, "note": "Dipakai"})
    assert adj.json()["item"]["qty"] == 4

    assert client.delete("/api/transactions/txbelanja01", headers=h).status_code == 200
    assert client.get("/api/bootstrap", headers=h).json()["transactions"] == []


def test_other_users_data_is_private(client, user):
    h = auth(user["token"])
    client.post("/api/transactions", headers=h, json={
        "id": "txprivat001", "type": "masuk", "item": "Cilok", "amount": 5000, "category": "Penjualan", "date": TODAY.isoformat()})
    other = client.post("/api/auth/register", json={"name": "Lain", "contact": "lain@contoh.id", "password": "abcdef"}).json()["token"]
    assert client.delete("/api/transactions/txprivat001", headers=auth(other)).status_code == 404
    assert client.get("/api/bootstrap", headers=auth(other)).json()["transactions"] == []


def test_debt_and_settle(client, user):
    h = auth(user["token"])
    c1 = client.post("/api/debts", headers=h, json={"name": "Bu Sri", "desc": "Cilok 3 porsi", "amount": 15000,
                                                     "date": TODAY.isoformat(), "customerId": "custsri001", "itemId": "debt000001"}).json()["customer"]
    c2 = client.post("/api/debts", headers=h, json={"name": "bu sri", "amount": 6000, "date": TODAY.isoformat()}).json()["customer"]
    assert c1["id"] == c2["id"] == "custsri001" and len(c2["items"]) == 2
    s = client.post("/api/customers/custsri001/settle", headers=h, json={"recordIncome": True, "txId": "txlunas0001"}).json()
    assert all(i["paid"] for i in s["customer"]["items"])
    assert s["transaction"]["amount"] == 21000 and s["transaction"]["category"] == "Pelunasan bon"
    again = client.post("/api/customers/custsri001/settle", headers=h, json={})
    assert again.status_code == 422


def test_categories_and_profile(client, user):
    h = auth(user["token"])
    r = client.put("/api/categories", headers=h, json={"masuk": ["Penjualan", "Jasa"], "keluar": ["Bahan baku"]})
    assert r.json() == {"masuk": ["Penjualan", "Jasa"], "keluar": ["Bahan baku"]}
    assert client.put("/api/categories", headers=h, json={"masuk": [], "keluar": ["A"]}).status_code == 422
    me = client.put("/api/me", headers=h, json={"business_name": "Laundry Wangi", "business_type": "Laundry kiloan", "setup_done": True}).json()
    assert me["business"] == {"name": "Laundry Wangi", "type": "Laundry kiloan", "setupDone": True}


# ---------- Scan struk pakai AI ----------

PNG_1PX = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                        "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")


def test_scan_without_ai_key_tells_app_to_fall_back(client, user):
    r = client.post("/api/scan", headers=auth(user["token"]), files={"file": ("nota.png", PNG_1PX, "image/png")})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "ai_unavailable"


def test_sales_receipt_goes_straight_into_income(client, user, monkeypatch):
    h = auth(user["token"])
    client.post("/api/stock", headers=h, json={"id": "stokminyak1", "name": "Minyak goreng", "unit": "liter", "qty": 1, "min": 2})
    monkeypatch.setenv("JUALANS_AI_ENABLED", "1")
    seen = {}

    def fake_read(image, media_type, business, categories, stock, today):
        seen.update(business=business, stock=stock)
        return ai_scan.ScanResult(
            jenis_dokumen="struk_penjualan", jenis="masuk", nama_toko="Cilok Jualans", tanggal=TODAY.isoformat(),
            total=62000, catatan="", items=[
                ai_scan.ScanItem(nama="Cilok goreng (10 porsi)", nominal=50000, kategori="Penjualan", stok_id="", stok_jumlah=0),
                ai_scan.ScanItem(nama="Es teh manis (4 gelas)", nominal=12000, kategori="Kategori ngawur", stok_id="", stok_jumlah=0),
            ])
    monkeypatch.setattr(ai_scan, "read_receipt", fake_read)

    r = client.post("/api/scan", headers=h, files={"file": ("struk.png", PNG_1PX, "image/png")})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["kind"] == "masuk" and len(data["transactions"]) == 2
    assert {t["type"] for t in data["transactions"]} == {"masuk"}
    assert data["transactions"][1]["category"] == "Penjualan"     # kategori tak dikenal diganti yang valid
    assert seen["stock"][0]["name"] == "Minyak goreng"
    boot = client.get("/api/bootstrap", headers=h).json()
    assert sum(t["amount"] for t in boot["transactions"] if t["type"] == "masuk") == 62000

    undo = client.delete(f"/api/scans/{data['scanId']}", headers=h).json()
    assert len(undo["deleted"]) == 2
    assert client.get("/api/bootstrap", headers=h).json()["transactions"] == []


def test_purchase_receipt_adds_stock_and_undo_reverts_it(client, user, monkeypatch):
    h = auth(user["token"])
    client.post("/api/stock", headers=h, json={"id": "stokgas0001", "name": "Gas elpiji 3 kg", "unit": "tabung", "qty": 1, "min": 1})
    monkeypatch.setenv("JUALANS_AI_ENABLED", "1")
    monkeypatch.setattr(ai_scan, "read_receipt", lambda *a, **k: ai_scan.ScanResult(
        jenis_dokumen="nota_belanja", jenis="keluar", nama_toko="Agen Gas", tanggal="2001-01-01", total=44000, catatan="",
        items=[ai_scan.ScanItem(nama="Gas elpiji 3 kg", nominal=44000, kategori="Operasional", stok_id="stokgas0001", stok_jumlah=2)]))
    data = client.post("/api/scan", headers=h, files={"file": ("n.png", PNG_1PX, "image/png")}).json()
    assert data["kind"] == "keluar" and data["stock"][0]["qty"] == 3
    assert data["date"] == TODAY.isoformat()      # tanggal yang tidak masuk akal diganti hari ini
    undo = client.delete(f"/api/scans/{data['scanId']}", headers=h).json()
    assert undo["stock"][0]["qty"] == 1


def test_not_a_receipt(client, user, monkeypatch):
    monkeypatch.setenv("JUALANS_AI_ENABLED", "1")
    monkeypatch.setattr(ai_scan, "read_receipt", lambda *a, **k: ai_scan.ScanResult(
        jenis_dokumen="bukan_nota", jenis="masuk", nama_toko="", tanggal="", total=0, catatan="Ini foto kucing.", items=[]))
    r = client.post("/api/scan", headers=auth(user["token"]), files={"file": ("n.png", PNG_1PX, "image/png")})
    assert r.status_code == 422 and r.json()["detail"]["message"] == "Ini foto kucing."


def test_scan_rejects_non_images(client, user, monkeypatch):
    monkeypatch.setenv("JUALANS_AI_ENABLED", "1")
    r = client.post("/api/scan", headers=auth(user["token"]), files={"file": ("a.txt", b"halo", "text/plain")})
    assert r.status_code == 415


def test_claude_request_is_well_formed(monkeypatch):
    """Panggilan SDK sungguhan ke alamat yang tidak ada: parameternya harus diterima SDK
    (tidak ada TypeError), lalu gagal koneksi dan diterjemahkan ke pesan yang ramah."""
    import anthropic
    monkeypatch.setattr(ai_scan, "_client", anthropic.Anthropic(api_key="sk-test", base_url="http://127.0.0.1:9", max_retries=0, timeout=2))
    with pytest.raises(ai_scan.ScanError) as e:
        ai_scan.read_receipt(PNG_1PX, "image/png", {"name": "Jualans", "type": "Cilok"}, {"masuk": ["Penjualan"], "keluar": ["Lain-lain"]}, [], TODAY.isoformat())
    assert e.value.code == "ai_offline"
