"""Read-only daily price projections of an explicitly selected immutable version.

This boundary never fills gaps, adjusts quotes, aggregates bars or downloads data.
The preceding close is evidence for the first selected session, not a zero return.
"""
from __future__ import annotations

from datetime import date
import re


MAX_PRICE_BARS = 100_000
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_BAR_FIELDS = ("date", "open", "high", "low", "close", "volume")


class PricesNotFound(LookupError):
    """The requested immutable dataset version or symbol does not exist."""


def validate_price_range(start: str | None, end: str | None) -> None:
    for name, value in (("start", start), ("end", end)):
        if value is None:
            continue
        try:
            if not _ISO_DATE.fullmatch(value):
                raise ValueError
            date.fromisoformat(value)
        except ValueError:
            raise ValueError(f"{name} debe ser una fecha real con formato YYYY-MM-DD.") from None
    if start is not None and end is not None and start > end:
        raise ValueError("La fecha inicial no puede ser posterior a la final.")


def project_prices(dataset: dict, symbol: str, start: str | None = None,
                   end: str | None = None) -> dict:
    """Return faithful OHLCV values for one symbol and inclusive date bounds."""
    validate_price_range(start, end)
    bars = sorted((bar for bar in dataset["bars"] if bar["symbol"] == symbol),
                  key=lambda bar: bar["date"])
    if not bars:
        raise PricesNotFound("El símbolo no existe en la versión solicitada del conjunto.")
    currencies = {bar.get("currency", "EUR") for bar in bars}
    if len(currencies) != 1:
        raise ValueError("El símbolo contiene monedas distintas; no se puede representar como una serie única.")

    selected = []
    preceding = None
    for bar in bars:
        if start is not None and bar["date"] < start:
            preceding = bar
            continue
        if end is not None and bar["date"] > end:
            break
        selected.append({field: bar[field] for field in _BAR_FIELDS})
        if len(selected) > MAX_PRICE_BARS:
            raise ValueError("La consulta supera 100.000 barras. Recorta el intervalo de fechas; no se han truncado datos.")

    manifest = dataset["manifest"]
    metadata = dataset.get("source_metadata")
    warnings = list(dict.fromkeys([*manifest["warnings"], *(dataset.get("warnings") or [])]))
    if not selected:
        preceding = None
        warnings.append("No hay sesiones del símbolo dentro del intervalo seleccionado.")
    return {
        "dataset_id": dataset["id"], "dataset_version": dataset["version"],
        "manifest_hash": manifest["sha256"], "symbol": symbol,
        "currency": next(iter(currencies)), "source_kind": dataset["source_kind"],
        "source": dataset["source"], "source_metadata": metadata,
        "price_basis": metadata["price_basis"] if metadata else manifest["price_basis"],
        "calendar": manifest["calendar"], "warnings": warnings,
        "available_start": bars[0]["date"], "available_end": bars[-1]["date"],
        "first_date": selected[0]["date"] if selected else None,
        "last_date": selected[-1]["date"] if selected else None,
        "preceding_close": preceding["close"] if preceding else None,
        "preceding_date": preceding["date"] if preceding else None,
        "bars": selected,
    }
