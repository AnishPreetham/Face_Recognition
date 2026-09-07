"""Minimal local/simulated append-only hash-linked blockchain.

This is NOT a distributed ledger. It demonstrates the core tamper-evidence
property the hackathon task asks for: each block cryptographically commits
to its own data and to the previous block's hash. Editing any past block's
data (or its previous_hash link) makes recomputation disagree with the
stored hash, which verify_block() / verify_chain() detect.

The hackathon task explicitly permits a local/simulated chain as an
alternative to a public testnet/mainnet.
"""
import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict, field
from typing import Optional

CHAIN_FILE = os.path.join(os.path.dirname(__file__), "chain.json")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Block:
    index: int
    timestamp: float
    data_hash: str            # SHA-256 fingerprint of the verification record
    data: dict = field(default_factory=dict)  # metadata only, never biometrics
    previous_hash: str = ""
    hash: str = ""

    def compute_hash(self) -> str:
        payload = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "data_hash": self.data_hash,
                "previous_hash": self.previous_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return _sha256(payload)


class LocalBlockchain:
    def __init__(self, path: str = CHAIN_FILE):
        self.path = path
        self.chain: list = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.chain = [Block(**b) for b in raw]
        else:
            self.chain = [self._genesis_block()]
            self._save()

    def _genesis_block(self) -> Block:
        b = Block(
            index=0,
            timestamp=time.time(),
            data_hash=_sha256("genesis"),
            data={"note": "genesis block"},
            previous_hash="0" * 64,
        )
        b.hash = b.compute_hash()
        return b

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([asdict(b) for b in self.chain], f, indent=2)

    def add_record(self, data_hash: str, data: dict) -> Block:
        prev = self.chain[-1]
        block = Block(
            index=prev.index + 1,
            timestamp=time.time(),
            data_hash=data_hash,
            data=data,
            previous_hash=prev.hash,
        )
        block.hash = block.compute_hash()
        self.chain.append(block)
        self._save()
        return block

    def get_block(self, index: int) -> Optional[Block]:
        for b in self.chain:
            if b.index == index:
                return b
        return None

    def verify_block(self, index: int) -> dict:
        block = self.get_block(index)
        if block is None:
            return {"valid": False, "reason": "block not found"}
        recomputed = block.compute_hash()
        prev = self.get_block(index - 1)
        prev_ok = (prev is not None) and (block.previous_hash == prev.hash)
        return {
            "valid": (recomputed == block.hash) and prev_ok,
            "stored_hash": block.hash,
            "recomputed_hash": recomputed,
            "previous_hash_ok": prev_ok,
        }

    def verify_chain(self) -> bool:
        for b in self.chain[1:]:
            if not self.verify_block(b.index)["valid"]:
                return False
        return True