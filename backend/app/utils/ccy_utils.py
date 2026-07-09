"""Currency-pair string utilities."""

from __future__ import annotations


def split_ccy_pair(ccy_pair: str | None) -> tuple[str | None, str | None]:
    """Split ``"USD/CNY"`` -> ``("USD", "CNY")``.

    Returns ``(None, None)`` when *ccy_pair* is empty or not in
    ``"BASE/QUOTE"`` format.  Whitespace is stripped from each leg; the
    original case is preserved.
    """
    if not ccy_pair or "/" not in ccy_pair:
        return None, None
    parts = ccy_pair.split("/")
    if len(parts) != 2:
        return None, None
    base = parts[0].strip()
    quote = parts[1].strip()
    if not base or not quote:
        return None, None
    return base, quote
