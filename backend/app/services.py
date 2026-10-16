"""Fungsi bantu: id, kategori bawaan, stok, dan bentuk JSON yang dikirim ke aplikasi."""
import datetime as dt
import json
import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import api_error
from .config import HISTORY_DAYS
from .models import Category, Customer, StockHistory, StockItem, Transaction, User

DEFAULT_CATEGORIES = {
    "masuk": ["Penjualan", "Pesanan", "Pelunasan bon", "Lain-lain"],
    "keluar": ["Bahan baku", "Operasional", "Sewa", "Gaji", "Lain-lain"],
}
ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")


def new_id() -> str:
    return "id" + secrets.token_hex(10)


def client_id(value: str | None) -> str:
    """Pakai id dari aplikasi kalau formatnya benar (agar tampilan bisa langsung diperbarui), selain itu buat baru."""
    if value is None:
        return new_id()
    if not ID_RE.match(value):
        raise api_error(422, "bad_id", "Format id tidak valid.")
    return value


def today() -> dt.date:
    return dt.date.today()


def now_hm() -> str:
    return dt.datetime.now().strftime("%H:%M")


def history_start() -> dt.date:
    return today() - dt.timedelta(days=HISTORY_DAYS - 1)


def stock_keywords(name: str) -> list[str]:
    return [w for w in re.split(r"[^a-z]+", name.lower()) if len(w) >= 3]


# ---------- Kategori ----------

def create_default_categories(db: Session, user: User) -> None:
    for type_, names in DEFAULT_CATEGORIES.items():
        for pos, name in enumerate(names):
            db.add(Category(user_id=user.id, type=type_, name=name, position=pos))


def categories_out(db: Session, user: User) -> dict:
    rows = db.scalars(select(Category).where(Category.user_id == user.id).order_by(Category.type, Category.position)).all()
    out = {"masuk": [], "keluar": []}
    for row in rows:
        out[row.type].append(row.name)
    return out


def pick_category(cats: dict, type_: str, wanted: str | None, fallback: str) -> str:
    names = cats.get(type_) or DEFAULT_CATEGORIES[type_]
    if wanted and wanted in names:
        return wanted
    if fallback in names:
        return fallback
    return "Lain-lain" if "Lain-lain" in names else names[0]


# ---------- Stok ----------

def get_stock_item(db: Session, user: User, item_id: str) -> StockItem:
    item = db.get(StockItem, item_id)
    if not item or item.user_id != user.id:
        raise api_error(404, "not_found", "Bahan tidak ditemukan.")
    return item


def apply_stock(db: Session, item: StockItem, change: float, note: str, date: dt.date | None = None,
                scan_id: str | None = None, history_id: str | None = None) -> StockItem:
    item.qty = max(0.0, round(item.qty + change, 2))
    db.add(StockHistory(id=history_id or new_id(), stock_item_id=item.id, date=date or today(), time=now_hm(),
                        change=round(change, 2), note=note[:160], scan_id=scan_id))
    return item


# ---------- Bentuk JSON (sama dengan bentuk data di aplikasi) ----------

def user_out(user: User) -> dict:
    return {"name": user.name, "contact": user.contact_display}


def business_out(user: User) -> dict:
    return {"name": user.business_name, "type": user.business_type, "setupDone": user.setup_done}


def tx_out(t: Transaction) -> dict:
    return {"id": t.id, "type": t.type, "item": t.item, "amount": t.amount, "category": t.category,
            "date": t.date.isoformat(), "time": t.time, "source": t.source, "scanId": t.scan_id}


def customer_out(c: Customer) -> dict:
    return {"id": c.id, "name": c.name, "note": c.note, "items": [
        {"id": i.id, "desc": i.desc, "amount": i.amount, "date": i.date.isoformat(), "paid": i.paid,
         "paidDate": i.paid_date.isoformat() if i.paid_date else None}
        for i in c.items]}


def _num(v: float):
    return int(v) if float(v).is_integer() else round(v, 2)


def stock_out(s: StockItem) -> dict:
    return {"id": s.id, "name": s.name, "unit": s.unit, "qty": _num(s.qty), "min": _num(s.min),
            "keywords": json.loads(s.keywords or "[]"),
            "history": [{"id": h.id, "date": h.date.isoformat(), "time": h.time, "change": _num(h.change), "note": h.note}
                        for h in s.history[:20]]}


def transactions_query(user: User, start: dt.date, end: dt.date):
    return (select(Transaction)
            .where(Transaction.user_id == user.id, Transaction.date >= start, Transaction.date <= end)
            .order_by(Transaction.date.desc(), Transaction.time.desc()))


def bootstrap_out(db: Session, user: User) -> dict:
    txs = db.scalars(transactions_query(user, history_start(), today())).all()
    customers = db.scalars(select(Customer).where(Customer.user_id == user.id).order_by(Customer.name)).all()
    stock = db.scalars(select(StockItem).where(StockItem.user_id == user.id).order_by(StockItem.name)).all()
    return {
        "user": user_out(user),
        "business": business_out(user),
        "categories": categories_out(db, user),
        "transactions": [tx_out(t) for t in txs],
        "customers": [customer_out(c) for c in customers],
        "stock": [stock_out(s) for s in stock],
        "historyDays": HISTORY_DAYS,
    }
