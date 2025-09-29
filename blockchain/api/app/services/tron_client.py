from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from tronpy import Tron
from tronpy.providers import HTTPProvider

from app.config import get_settings

_logger = logging.getLogger("app.tron")


@dataclass(slots=True, frozen=True)
class ChainInfo:
    network: str
    node: str
    latest_block: int
    block_id: str | None
    block_time: int | None  # unix ms
    block_onion: str | None
    block_rpc_url: str | None


class TronService:
    def __init__(self) -> None:
        self.settings = get_settings()
        endpoint = self._resolve_endpoint()
        headers = {}
        if self.settings.TRONGRID_API_KEY:
            headers["TRON-PRO-API-KEY"] = self.settings.TRONGRID_API_KEY

        self.provider = HTTPProvider(
            endpoint, client=httpx.Client(headers=headers, timeout=10)
        )
        self.tron = Tron(provider=self.provider)

        _logger.info(
            "TronService ready network=%s endpoint=%s",
            self.settings.TRON_NETWORK,
            endpoint,
        )

    def _resolve_endpoint(self) -> str:
        if self.settings.TRON_HTTP_ENDPOINT:
            return self.settings.TRON_HTTP_ENDPOINT
        if self.settings.TRON_NETWORK.lower() == "shasta":
            # public shasta requires api key via trongrid; keep standard domain
            return "https://api.shasta.trongrid.io"
        return "https://api.trongrid.io"

    def get_chain_info(self) -> ChainInfo:
        blk = self.tron.get_latest_block()
        height = blk["block_header"]["raw_data"]["number"]
        block_id = blk.get("blockID") or None
        ts = blk["block_header"]["raw_data"].get("timestamp")
        return ChainInfo(
            network=self.settings.TRON_NETWORK,
            node=self._resolve_endpoint(),
            latest_block=height,
            block_id=block_id,
            block_time=ts,
            block_onion=(self.settings.BLOCK_ONION or None),
            block_rpc_url=(self.settings.BLOCK_RPC_URL or None),
        )

    def get_height(self) -> int:
        return self.get_chain_info().latest_block

    def get_balance_sun(self, address_base58: str) -> int:
        # returns integer in sun (1 TRX = 1_000_000 sun)
        acct = self.tron.get_account(address_base58)
        return int(acct.get("balance", 0))

    def transfer_sun(
        self, private_key_hex: str, to_address_base58: str, amount_sun: int
    ) -> dict[str, Any]:
        """
        Create, sign, and broadcast a TRX transfer.
        Returns a dict with txid and raw result from node.
        """
        from tronpy.keys import PrivateKey

        pk = PrivateKey(bytes.fromhex(private_key_hex))
        txn = (
            self.tron.trx.transfer(
                pk.public_key.to_base58check_address(), to_address_base58, amount_sun
            )
            .build()
            .sign(pk)
        )
        ret = txn.broadcast().wait()
        # ret contains receipt like {'id': '...', 'result': True, 'txid': '...'}
        return {"txid": ret.get("id") or ret.get("txid"), "result": ret}
