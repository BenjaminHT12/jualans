"""Membaca foto struk/nota dengan Claude lalu mengubahnya menjadi data transaksi.

Struk penjualan dari usaha sendiri  -> uang masuk (pemasukan)
Nota belanja dari pemasok/toko lain -> uang keluar (pengeluaran), sekalian menambah stok bahan
"""
import base64
import json
import os
from typing import Literal

import anthropic
from pydantic import BaseModel, ValidationError

from .config import AI_MODEL

SUPPORTED_MEDIA = {"image/jpeg", "image/png", "image/webp", "image/gif"}

SYSTEM_PROMPT = """\
You read photos of receipts for Jualans, a bookkeeping app for small Indonesian businesses \
(food stalls, laundries, photocopy shops). You turn one photo into bookkeeping entries for the \
business described in the user message. The owner relies on these entries without retyping them, \
so read every line carefully.

Decide jenis_dokumen:
- "struk_penjualan": a receipt or bill this business gave to ITS customer. The business name appears \
as the seller, or the items are the products this business sells. These are income: jenis = "masuk".
- "nota_belanja": a receipt from a supplier, shop or market where this business bought goods or paid \
for a service. These are expenses: jenis = "keluar".
- "bukan_nota": the photo is not a receipt, or it is too blurry to read any line. Return no items.
If it is unclear whether a receipt is a sale or a purchase, choose "struk_penjualan" when the items \
match what this business sells, otherwise "nota_belanja".

Items: one entry per product or service line.
- nominal is the final rupiah amount of that line as an integer, after any discount shown for that \
line. It is the line total, not the unit price. Indonesian formatting: "65.000" and "65.000,00" both mean 65000.
- Skip payment lines such as TUNAI, CASH, KEMBALI, DEBIT, QRIS and SUBTOTAL. If the receipt has tax \
or a service charge, add it as its own item.
- When the total is readable, the item amounts should add up to it. If they do not, re-read the digits \
and explain any remaining difference in catatan.
- nama: natural Indonesian sentence case that keeps size and quantity, for example \
"Tepung tapioka 5 kg" or "Cilok goreng (10 porsi)".
- kategori: exactly one name from the category list for the chosen jenis.
- stok_id and stok_jumlah: only for nota_belanja. When the item is one of the listed stock ingredients, \
give that ingredient's id and the amount bought in the ingredient's unit (2 x minyak 2 L = 4 liter; one \
3 kg gas cylinder counted in "tabung" = 1). Otherwise use "" and 0.

tanggal: the receipt date as YYYY-MM-DD, or "" when no date is visible. Indonesian receipts usually \
write DD/MM/YYYY.
total: the TOTAL printed on the receipt as an integer, or 0 when none is visible.
catatan: a short note in everyday Indonesian for the owner when something was hard to read or does not \
add up, otherwise "".
"""

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "jenis_dokumen": {"type": "string", "enum": ["struk_penjualan", "nota_belanja", "bukan_nota"]},
        "jenis": {"type": "string", "enum": ["masuk", "keluar"]},
        "nama_toko": {"type": "string"},
        "tanggal": {"type": "string"},
        "total": {"type": "integer"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nama": {"type": "string"},
                    "nominal": {"type": "integer"},
                    "kategori": {"type": "string"},
                    "stok_id": {"type": "string"},
                    "stok_jumlah": {"type": "number"},
                },
                "required": ["nama", "nominal", "kategori", "stok_id", "stok_jumlah"],
                "additionalProperties": False,
            },
        },
        "catatan": {"type": "string"},
    },
    "required": ["jenis_dokumen", "jenis", "nama_toko", "tanggal", "total", "items", "catatan"],
    "additionalProperties": False,
}


class ScanItem(BaseModel):
    nama: str
    nominal: int
    kategori: str
    stok_id: str
    stok_jumlah: float


class ScanResult(BaseModel):
    jenis_dokumen: Literal["struk_penjualan", "nota_belanja", "bukan_nota"]
    jenis: Literal["masuk", "keluar"]
    nama_toko: str
    tanggal: str
    total: int
    items: list[ScanItem]
    catatan: str


class ScanError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def available() -> bool:
    """AI aktif kalau server punya kredensial Claude (atau dipaksa aktif lewat JUALANS_AI_ENABLED=1)."""
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
                or os.getenv("JUALANS_AI_ENABLED") == "1")


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=90.0, max_retries=2)
    return _client


def read_receipt(image: bytes, media_type: str, business: dict, categories: dict, stock: list[dict],
                 today: str) -> ScanResult:
    context = {
        "usaha": {"nama": business.get("name") or "", "jenis": business.get("type") or ""},
        "tanggal_hari_ini": today,
        "kategori": categories,
        "bahan_stok": [{"id": s["id"], "nama": s["name"], "satuan": s["unit"]} for s in stock],
    }
    try:
        response = _get_client().beta.messages.create(
            model=AI_MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": RESULT_SCHEMA}},
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                                 "data": base64.standard_b64encode(image).decode()}},
                    {"type": "text", "text": "Data usaha:\n" + json.dumps(context, ensure_ascii=False, indent=2)
                     + "\n\nBaca struk pada foto di atas."},
                ],
            }],
        )
    except anthropic.AuthenticationError:
        raise ScanError(503, "ai_auth", "Kunci API AI di server tidak valid.")
    except anthropic.PermissionDeniedError:
        raise ScanError(503, "ai_auth", "Kunci API AI tidak punya izin untuk model ini.")
    except anthropic.RateLimitError:
        raise ScanError(503, "ai_busy", "AI sedang sibuk. Coba lagi sebentar lagi.")
    except anthropic.BadRequestError as e:
        raise ScanError(502, "ai_error", f"Permintaan ke AI ditolak: {e.message}")
    except anthropic.APIStatusError as e:
        raise ScanError(503, "ai_busy", f"Layanan AI sedang bermasalah ({e.status_code}). Coba lagi nanti.")
    except anthropic.APIConnectionError:
        raise ScanError(503, "ai_offline", "Server tidak bisa menghubungi layanan AI.")

    if response.stop_reason == "refusal":
        raise ScanError(422, "ai_refused", "AI tidak bisa memproses foto ini.")
    if response.stop_reason == "max_tokens":
        raise ScanError(502, "ai_error", "Struk terlalu panjang untuk dibaca sekaligus.")
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return ScanResult.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError):
        raise ScanError(502, "ai_error", "Jawaban AI tidak bisa dibaca. Coba foto ulang.")
