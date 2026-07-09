"""Helpers for valuation-parameter validation and error messages."""

from __future__ import annotations


def build_missing_params_error(
    params: list[tuple[float | None, str]],
    *,
    joiner: str = "、",
    suffix: str = "（曲线未解析且未提供覆盖值，请在参数表中填写）",
) -> str | None:
    """Build a ``"缺少估值参数：..."`` error message listing missing params.

    *params* is a list of ``(value, label)`` pairs; entries whose value is
    ``None`` are considered missing.  Returns ``None`` when nothing is
    missing so the caller can treat it as a guard.
    """
    missing = [label for value, label in params if value is None]
    if not missing:
        return None
    return "缺少估值参数：" + joiner.join(missing) + suffix
