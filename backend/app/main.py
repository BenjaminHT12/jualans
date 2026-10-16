"""Jualans API: FastAPI + SQL (SQLite bawaan).

Menjalankan (dari folder backend):
    uv run --python 3.12 --with-requirements requirements.txt uvicorn app.main:app --reload
lalu buka http://localhost:8000
"""
import datetime as dt
import json
import re
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, File, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from . import ai_scan
from .auth import (api_error, bearer_token, create_session, current_user, delete_session, hash_password,
                   normalize_contact, verify_password)
from .config import DEMO_ENABLED, FRONTEND_FILE, HISTORY_DAYS, MAX_UPLOAD_BYTES
from .db import Base, engine, get_db, SessionLocal
from .models import Category, Customer, DebtItem, StockHistory, StockItem, Transaction, User
from .seed import DEMO_CONTACT, clear_user_data, ensure_demo_user, seed_sample
from .services import (apply_stock, bootstrap_out, business_out, categories_out, client_id,
                       create_default_categories, customer_out, get_stock_item, new_id, now_hm,
                       pick_category, stock_keywords, stock_out, today, transactions_query, tx_out, user_out)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    if DEMO_ENABLED:
        with SessionLocal() as db:
            ensure_demo_user(db)
    yield


app = FastAPI(title="Jualans API", lifespan=lifespan)

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


# ====================================================================
# Skema permintaan
# ====================================================================

class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    contact: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    contact: str
    password: str


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    business_name: str | None = Field(default=None, max_length=80)
    business_type: str | None = Field(default=None, max_length=80)
    setup_done: bool | None = None


class CategoriesIn(BaseModel):
    masuk: list[str]
    keluar: list[str]


class StockLink(BaseModel):
    itemId: str
    qty: float = Field(gt=0, le=100000)


class TxIn(BaseModel):
    id: str | None = None
    type: Literal["masuk", "keluar"]
    item: str = Field(min_length=1, max_length=200)
    amount: int = Field(gt=0, le=10_000_000_000)
    category: str = Field(min_length=1, max_length=40)
    date: dt.date
    time: str | None = None
    source: str | None = Field(default=None, max_length=20)
    stock: StockLink | None = None

    @field_validator("time")
    @classmethod
    def _time(cls, v):
        if v is not None and not TIME_RE.match(v):
            raise ValueError("format jam harus HH:MM")
        return v


class TxUpdate(BaseModel):
    type: Literal["masuk", "keluar"]
    item: str = Field(min_length=1, max_length=200)
    amount: int = Field(gt=0, le=10_000_000_000)
    category: str = Field(min_length=1, max_length=40)
    date: dt.date


class DebtIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    desc: str = Field(default="Utang", max_length=200)
    amount: int = Field(gt=0, le=1_000_000_000)
    date: dt.date
    itemId: str | None = None
    customerId: str | None = None


class SettleIn(BaseModel):
    recordIncome: bool = True
    txId: str | None = None


class StockIn(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=80)
    unit: str = Field(min_length=1, max_length=20)
    qty: float = Field(default=0, ge=0, le=100000)
    min: float = Field(default=0, ge=0, le=100000)


class StockUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    unit: str = Field(min_length=1, max_length=20)
    min: float = Field(ge=0, le=100000)


class StockAdjustIn(BaseModel):
    change: float = Field(ge=-100000, le=100000)
    note: str = Field(default="", max_length=160)
    date: dt.date | None = None


class ResetIn(BaseModel):
    mode: Literal["empty", "sample"]


def _check_date(d: dt.date) -> dt.date:
    if d > today():
        raise api_error(422, "future_date", "Tanggal tidak boleh lebih dari hari ini.")
    return d


def _ensure_new_id(db: Session, model, value: str | None) -> str:
    id_ = client_id(value)
    if db.get(model, id_) is not None:
        raise api_error(409, "duplicate_id", "Data dengan id ini sudah ada.")
    return id_


# ====================================================================
# Umum & login
# ====================================================================

@app.get("/api/health")
def health():
    return {"ok": True, "ai": ai_scan.available(), "demo": DEMO_ENABLED, "historyDays": HISTORY_DAYS}


@app.post("/api/auth/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    contact = normalize_contact(body.contact)
    if not contact:
        raise api_error(422, "bad_contact", "Isi nomor HP (contoh 0812xxxx) atau email yang benar.")
    if db.scalar(select(User).where(User.contact == contact)):
        raise api_error(409, "contact_taken", "Nomor HP atau email ini sudah terdaftar. Silakan login.")
    user = User(id=new_id(), name=body.name.strip(), contact=contact, contact_display=body.contact.strip(),
                password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    create_default_categories(db, user)
    token = create_session(db, user)
    db.commit()
    return {"token": token, **bootstrap_out(db, user)}


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    contact = normalize_contact(body.contact)
    user = db.scalar(select(User).where(User.contact == contact)) if contact else None
    if not user or not verify_password(body.password, user.password_hash):
        raise api_error(401, "bad_login", "Nomor HP/email atau kata sandi salah.")
    token = create_session(db, user)
    db.commit()
    return {"token": token, **bootstrap_out(db, user)}


@app.post("/api/auth/demo")
def login_demo(db: Session = Depends(get_db)):
    if not DEMO_ENABLED:
        raise api_error(404, "demo_disabled", "Akun demo tidak tersedia.")
    user = db.scalar(select(User).where(User.contact == DEMO_CONTACT)) or ensure_demo_user(db)
    token = create_session(db, user)
    db.commit()
    return {"token": token, **bootstrap_out(db, user)}


@app.post("/api/auth/logout")
def logout(token: str = Depends(bearer_token), db: Session = Depends(get_db)):
    delete_session(db, token)
    db.commit()
    return {"ok": True}


@app.get("/api/bootstrap")
def bootstrap(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return bootstrap_out(db, user)


@app.put("/api/me")
def update_me(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.name is not None:
        user.name = body.name.strip()
    if body.business_name is not None:
        user.business_name = body.business_name.strip()
    if body.business_type is not None:
        user.business_type = body.business_type.strip()
    if body.setup_done is not None:
        user.setup_done = body.setup_done
    db.commit()
    return {"user": user_out(user), "business": business_out(user)}


@app.put("/api/categories")
def update_categories(body: CategoriesIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lists = {"masuk": body.masuk, "keluar": body.keluar}
    for type_, names in lists.items():
        cleaned = [n.strip() for n in names]
        if not cleaned or len(cleaned) > 30 or any(not n or len(n) > 40 for n in cleaned) \
                or len({n.lower() for n in cleaned}) != len(cleaned):
            raise api_error(422, "bad_categories", "Daftar kategori tidak valid (minimal satu, tanpa nama ganda).")
        lists[type_] = cleaned
    db.execute(delete(Category).where(Category.user_id == user.id))
    for type_, names in lists.items():
        for pos, name in enumerate(names):
            db.add(Category(user_id=user.id, type=type_, name=name, position=pos))
    db.commit()
    return categories_out(db, user)


# ====================================================================
# Transaksi (riwayat 3 bulan terakhir)
# ====================================================================

@app.get("/api/transactions")
def list_transactions(
    days: int = Query(HISTORY_DAYS, ge=1, le=HISTORY_DAYS),
    q: str | None = Query(None, max_length=80),
    category: str | None = None,
    type: Literal["masuk", "keluar"] | None = None,
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    stmt = transactions_query(user, today() - dt.timedelta(days=days - 1), today())
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Transaction.item).like(like) | func.lower(Transaction.category).like(like))
    if category:
        stmt = stmt.where(Transaction.category == category)
    if type:
        stmt = stmt.where(Transaction.type == type)
    rows = db.scalars(stmt).all()
    return {"since": (today() - dt.timedelta(days=days - 1)).isoformat(), "transactions": [tx_out(t) for t in rows]}


@app.post("/api/transactions", status_code=201)
def create_transaction(body: TxIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    tx = Transaction(id=_ensure_new_id(db, Transaction, body.id), user_id=user.id, type=body.type,
                     item=body.item.strip(), amount=body.amount, category=body.category.strip(),
                     date=_check_date(body.date), time=body.time or now_hm(), source=body.source or "manual")
    db.add(tx)
    stock = None
    if body.stock and body.type == "keluar":
        stock = apply_stock(db, get_stock_item(db, user, body.stock.itemId), body.stock.qty,
                            f"Belanja: {tx.item}", tx.date)
    db.commit()
    return {"transaction": tx_out(tx), "stock": stock_out(stock) if stock else None}


def _own_tx(db: Session, user: User, tx_id: str) -> Transaction:
    tx = db.get(Transaction, tx_id)
    if not tx or tx.user_id != user.id:
        raise api_error(404, "not_found", "Transaksi tidak ditemukan.")
    return tx


@app.put("/api/transactions/{tx_id}")
def update_transaction(tx_id: str, body: TxUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    tx = _own_tx(db, user, tx_id)
    tx.type, tx.item, tx.amount, tx.category = body.type, body.item.strip(), body.amount, body.category.strip()
    tx.date = _check_date(body.date)
    db.commit()
    return {"transaction": tx_out(tx)}


@app.delete("/api/transactions/{tx_id}")
def delete_transaction(tx_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(_own_tx(db, user, tx_id))
    db.commit()
    return {"ok": True}


# ====================================================================
# Bon pelanggan
# ====================================================================

def _own_customer(db: Session, user: User, customer_id: str) -> Customer:
    c = db.get(Customer, customer_id)
    if not c or c.user_id != user.id:
        raise api_error(404, "not_found", "Pelanggan tidak ditemukan.")
    return c


@app.post("/api/debts", status_code=201)
def add_debt(body: DebtIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = body.name.strip()
    customer = db.scalar(select(Customer).where(Customer.user_id == user.id, func.lower(Customer.name) == name.lower()))
    if not customer:
        customer = Customer(id=_ensure_new_id(db, Customer, body.customerId), user_id=user.id, name=name, note="Pelanggan")
        db.add(customer)
    customer.items.append(DebtItem(id=_ensure_new_id(db, DebtItem, body.itemId), desc=body.desc.strip() or "Utang",
                                   amount=body.amount, date=_check_date(body.date)))
    db.commit()
    return {"customer": customer_out(customer)}


@app.post("/api/customers/{customer_id}/settle")
def settle_debt(customer_id: str, body: SettleIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    customer = _own_customer(db, user, customer_id)
    unpaid = [i for i in customer.items if not i.paid]
    total = sum(i.amount for i in unpaid)
    if not total:
        raise api_error(422, "nothing_to_settle", "Tidak ada utang yang belum dibayar.")
    for i in unpaid:
        i.paid, i.paid_date = True, today()
    tx = None
    if body.recordIncome:
        cats = categories_out(db, user)
        tx = Transaction(id=_ensure_new_id(db, Transaction, body.txId), user_id=user.id, type="masuk",
                         item=f"Pelunasan bon {customer.name}", amount=total,
                         category=pick_category(cats, "masuk", "Pelunasan bon", "Penjualan"),
                         date=today(), time=now_hm(), source="bon")
        db.add(tx)
    db.commit()
    return {"customer": customer_out(customer), "transaction": tx_out(tx) if tx else None}


# ====================================================================
# Stok bahan
# ====================================================================

@app.post("/api/stock", status_code=201)
def create_stock(body: StockIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = StockItem(id=_ensure_new_id(db, StockItem, body.id), user_id=user.id, name=body.name.strip(),
                     unit=body.unit.strip().lower(), qty=0, min=body.min,
                     keywords=json.dumps(stock_keywords(body.name)))
    db.add(item)
    if body.qty:
        apply_stock(db, item, body.qty, "Stok awal")
    db.commit()
    return {"item": stock_out(item)}


@app.put("/api/stock/{item_id}")
def update_stock(item_id: str, body: StockUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = get_stock_item(db, user, item_id)
    if body.name.strip() != item.name:
        item.keywords = json.dumps(stock_keywords(body.name))
    item.name, item.unit, item.min = body.name.strip(), body.unit.strip().lower(), body.min
    db.commit()
    return {"item": stock_out(item)}


@app.delete("/api/stock/{item_id}")
def delete_stock(item_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(get_stock_item(db, user, item_id))
    db.commit()
    return {"ok": True}


@app.post("/api/stock/{item_id}/adjust")
def adjust_stock(item_id: str, body: StockAdjustIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.change == 0:
        raise api_error(422, "zero_change", "Jumlah perubahan stok tidak boleh 0.")
    item = apply_stock(db, get_stock_item(db, user, item_id), body.change,
                       body.note.strip() or ("Tambah stok" if body.change > 0 else "Dipakai"),
                       _check_date(body.date or today()))
    db.commit()
    return {"item": stock_out(item)}


# ====================================================================
# Scan struk pakai AI: hasilnya langsung disimpan sebagai transaksi
# ====================================================================

def _receipt_date(value: str) -> dt.date:
    try:
        d = dt.date.fromisoformat(value)
    except ValueError:
        return today()
    return d if today() - dt.timedelta(days=365) <= d <= today() else today()


@app.post("/api/scan", status_code=201)
def scan_receipt(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not ai_scan.available():
        raise api_error(503, "ai_unavailable", "AI pembaca struk belum diaktifkan di server.")
    media_type = (file.content_type or "").lower()
    if media_type not in ai_scan.SUPPORTED_MEDIA:
        raise api_error(415, "bad_image", "Format foto harus JPG, PNG, WEBP, atau GIF.")
    image = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(image) > MAX_UPLOAD_BYTES:
        raise api_error(413, "image_too_large", "Ukuran foto terlalu besar (maksimal 8 MB).")

    cats = categories_out(db, user)
    stock_items = {s.id: s for s in db.scalars(select(StockItem).where(StockItem.user_id == user.id)).all()}
    try:
        result = ai_scan.read_receipt(image, media_type, {"name": user.business_name, "type": user.business_type},
                                      cats, [stock_out(s) for s in stock_items.values()], today().isoformat())
    except ai_scan.ScanError as e:
        raise api_error(e.status, e.code, e.message)

    items = [i for i in result.items if i.nominal > 0 and i.nama.strip()]
    if result.jenis_dokumen == "bukan_nota" or not items:
        raise api_error(422, "not_receipt", result.catatan or "Foto ini sepertinya bukan struk, atau tulisannya belum terbaca.")

    type_ = "masuk" if result.jenis_dokumen == "struk_penjualan" else "keluar"
    scan_id, date, time = new_id(), _receipt_date(result.tanggal), now_hm()
    fallback = "Penjualan" if type_ == "masuk" else "Lain-lain"
    created, touched = [], {}
    for i in items:
        tx = Transaction(id=new_id(), user_id=user.id, type=type_, item=i.nama.strip()[:200], amount=i.nominal,
                         category=pick_category(cats, type_, i.kategori, fallback), date=date, time=time,
                         source="scan", scan_id=scan_id)
        db.add(tx)
        created.append(tx)
        item = stock_items.get(i.stok_id)
        if type_ == "keluar" and item and i.stok_jumlah > 0:
            touched[item.id] = apply_stock(db, item, i.stok_jumlah, f"Belanja: {tx.item}", date, scan_id=scan_id)
    db.commit()
    return {
        "scanId": scan_id, "kind": type_, "store": result.nama_toko.strip() or "Struk",
        "date": date.isoformat(), "total": result.total, "note": result.catatan,
        "transactions": [tx_out(t) for t in created],
        "stock": [stock_out(s) for s in touched.values()],
    }


@app.delete("/api/scans/{scan_id}")
def undo_scan(scan_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Batalkan hasil scan: hapus transaksinya dan kembalikan stok yang sempat ditambah."""
    txs = db.scalars(select(Transaction).where(Transaction.user_id == user.id, Transaction.scan_id == scan_id)).all()
    if not txs:
        raise api_error(404, "not_found", "Hasil scan tidak ditemukan.")
    deleted = [t.id for t in txs]
    for t in txs:
        db.delete(t)
    touched = {}
    rows = db.scalars(select(StockHistory).join(StockItem)
                      .where(StockHistory.scan_id == scan_id, StockItem.user_id == user.id)).all()
    for h in rows:
        item = h.stock_item
        item.qty = max(0.0, round(item.qty - h.change, 2))
        touched[item.id] = item
        db.delete(h)
    db.commit()
    for item in touched.values():
        db.refresh(item)
    return {"deleted": deleted, "stock": [stock_out(s) for s in touched.values()]}


# ====================================================================
# Data contoh (khusus prototipe)
# ====================================================================

@app.post("/api/demo/reset")
def reset_data(body: ResetIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    clear_user_data(db, user)
    if body.mode == "sample":
        seed_sample(db, user)
    db.commit()
    return bootstrap_out(db, user)


# ====================================================================
# Tampilan aplikasi
# ====================================================================

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND_FILE)
