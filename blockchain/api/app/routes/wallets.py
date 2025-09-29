from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.connection import get_db
from app.repo.wallets_repo import WalletsRepo
from app.schemas.wallets import (
    Wallet,
    WalletCreateRequest,
    WalletsPage,
    TransferRequest,
)

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.post("", response_model=Wallet, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    payload: WalletCreateRequest, db: AsyncIOMotorDatabase = Depends(get_db)
):
    repo = WalletsRepo(db)
    rec = await repo.create(label=payload.label)
    # strip enc_privkey in API
    return Wallet.model_validate(rec.model_dump(by_alias=True, exclude={"enc_privkey"}))


@router.get("", response_model=WalletsPage)
async def list_wallets(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    repo = WalletsRepo(db)
    data = await repo.list(page=page, page_size=page_size)
    # objects already shaped; pydantic will coerce
    return data


@router.get("/{wallet_id}", response_model=Wallet)
async def get_wallet(wallet_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    repo = WalletsRepo(db)
    rec = await repo.get(wallet_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found"
        )
    return Wallet.model_validate(rec.model_dump(by_alias=True, exclude={"enc_privkey"}))


@router.post("/{wallet_id}/transfer")
async def transfer(
    wallet_id: str, tx: TransferRequest, db: AsyncIOMotorDatabase = Depends(get_db)
):
    repo = WalletsRepo(db)
    res = await repo.transfer_sun(wallet_id, tx.to_address, tx.amount_sun)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found"
        )
    return res
