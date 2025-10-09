from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.crypto.keys import (
    generate_tron_wallet,
    encrypt_privkey_hex,
    decrypt_privkey_hex,
)
from app.config import get_settings


class WalletRecord(BaseModel):
    id: str = Field(alias="_id")
    address: str
    public_key: str
    # encrypted with KEY_ENC_SECRET
    enc_privkey: str
    label: str | None = None
    chain: Literal["tron"] = "tron"
    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        populate_by_name = True


class WalletsRepo:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.col = db["wallets"]
        self.settings = get_settings()

    async def create(self, label: str | None = None) -> WalletRecord:
        keys = generate_tron_wallet()
        enc = encrypt_privkey_hex(keys.private_key_hex, self.settings.KEY_ENC_SECRET)
        now = dt.datetime.utcnow()
        doc: dict[str, Any] = {
            "address": keys.address_base58,
            "public_key": keys.public_key_hex,
            "enc_privkey": enc,
            "label": label,
            "chain": "tron",
            "created_at": now,
            "updated_at": now,
        }
        res = await self.col.insert_one(doc)
        doc["_id"] = str(res.inserted_id)
        return WalletRecord.model_validate(doc)

    async def list(self, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        skip = (max(page, 1) - 1) * max(1, page_size)
        cur = (
            self.col.find({}, {"enc_privkey": 0})
            .skip(skip)
            .limit(page_size)
            .sort("created_at", 1)
        )
        items = [
            WalletRecord.model_validate({**d, "_id": str(d["_id"])}) async for d in cur
        ]
        total = await self.col.count_documents({})
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get(self, wallet_id: str) -> WalletRecord | None:
        from bson import ObjectId

        try:
            oid = ObjectId(wallet_id)
        except Exception:
            return None
        doc = await self.col.find_one({"_id": oid})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return WalletRecord.model_validate(doc)

    async def transfer_sun(
        self, wallet_id: str, to_addr: str, amount_sun: int
    ) -> dict[str, Any] | None:
        w = await self.get(wallet_id)
        if not w:
            return None
        priv = decrypt_privkey_hex(w.enc_privkey, self.settings.KEY_ENC_SECRET)
        # Use Tron service
        from app.services.tron_client import TronService

        tron = TronService()
        return tron.transfer_sun(priv, to_addr, amount_sun)
