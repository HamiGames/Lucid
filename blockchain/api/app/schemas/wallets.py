from __future__ import annotations

import datetime as dt
from pydantic import BaseModel, Field


class Wallet(BaseModel):
    id: str = Field(alias="_id")
    address: str
    public_key: str
    label: str | None = None
    chain: str = "tron"
    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        populate_by_name = True


class WalletCreateRequest(BaseModel):
    label: str | None = None


class WalletsPage(BaseModel):
    items: list[Wallet]
    total: int
    page: int
    page_size: int


class TransferRequest(BaseModel):
    to_address: str
    amount_sun: int = Field(ge=1)
