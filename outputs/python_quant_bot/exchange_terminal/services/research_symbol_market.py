from __future__ import annotations

import re


RESEARCH_SYMBOL_MARKET_CLASSIFIER_VERSION = "research-symbol-market-v1"

_PLAIN_US_EQUITY = re.compile(r"^[A-Z][A-Z0-9]{0,4}(?:[.-][A-Z])?$")
_FUTU_EQUITY = re.compile(r"^(?:US\.[A-Z][A-Z0-9.-]{0,9}|HK\.\d{5})$")
_PLAIN_CRYPTO_BASES = {"BTC", "ETH", "SOL", "BNB", "DOGE"}


def research_market_for_symbol(symbol: str) -> str:
    """Classify the frozen research symbol without config or filesystem I/O."""

    text = str(symbol or "").strip().upper()
    if not text:
        raise ValueError("research_symbol_missing")
    if "-" in text or text in _PLAIN_CRYPTO_BASES:
        return "crypto"
    if _PLAIN_US_EQUITY.fullmatch(text) or _FUTU_EQUITY.fullmatch(text):
        return "stock"
    raise ValueError("research_symbol_market_unsupported")


__all__ = [
    "RESEARCH_SYMBOL_MARKET_CLASSIFIER_VERSION",
    "research_market_for_symbol",
]
