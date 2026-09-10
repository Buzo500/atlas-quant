"""Optional Yahoo daily history adapter via the official yfinance package.

This is a read-only end-of-day research feed, not a real-time feed or broker.
Public documentation: https://github.com/ranaroussi/yfinance and
https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html
"""

from __future__ import annotations

import importlib
import math
import os
import queue
import re
import threading
from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from .analytics import decimal_value, iso_date, normalize_bars


REQUEST_TIMEOUT_SECONDS = 10
FETCH_DEADLINE_SECONDS = 45
_FETCH_SLOTS = threading.BoundedSemaphore(2)
_PROVIDER_LOCK = threading.Lock()
_PROVIDER_CACHE = None
_SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9.\-]{0,24}\Z", re.ASCII)
_REQUIRED_COLUMNS = {"Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits"}
_METADATA_KEYS = ("currency", "symbol", "instrumentType", "exchangeName", "exchangeTimezoneName")


class FeedError(ValueError):
    """No verified daily snapshot is available; callers must preserve old data."""


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _load_provider():
    global _PROVIDER_CACHE
    try:
        provider = importlib.import_module("yfinance")
    except ImportError as exc:
        raise FeedError("Falta la dependencia opcional yfinance. Instálala en el entorno virtual del backend para activar la descarga diaria.") from exc
    # yfinance's default AppData SQLite cache may be inaccessible to the local
    # launcher. Keep all three provider caches in ATLAS's writable data tree.
    directory = (Path(os.environ.get("ATLAS_DATA_DIR", Path(__file__).resolve().parents[2] / "var" / "atlas")) / "cache" / "yfinance").resolve()
    with _PROVIDER_LOCK:
        if _PROVIDER_CACHE and _PROVIDER_CACHE[0] is provider:
            if _PROVIDER_CACHE[1] != directory:
                raise FeedError("Reinicia el motor para cambiar la carpeta de caché de Yahoo.")
            return provider
        try:
            directory.mkdir(parents=True, exist_ok=True)
            provider.set_tz_cache_location(str(directory))
        except OSError as exc:
            raise FeedError("No se puede preparar la caché de Yahoo en la carpeta de datos de ATLAS.") from exc
        _PROVIDER_CACHE = provider, directory
    return provider


def _call_provider(symbol: str, start: str, end: str) -> tuple[Any, dict, str]:
    provider = _load_provider()
    ticker = provider.Ticker(symbol)
    # Explicit choices avoid changing economics when library defaults change.
    frame = ticker.history(
        start=start, end=end, interval="1d", auto_adjust=False,
        back_adjust=False, actions=True, repair=False, keepna=True,
        prepost=False, rounding=False, timeout=REQUEST_TIMEOUT_SECONDS,
        raise_errors=True,
    )
    metadata = ticker.get_history_metadata()
    if not isinstance(metadata, Mapping):
        raise FeedError("Yahoo no devolvió metadata verificable para la moneda del instrumento.")
    # Current yfinance metadata may lazily fetch tradingPeriods. Read only the
    # base quote metadata, never iterate/copy the full lazy mapping.
    selected = {key: metadata.get(key) for key in _METADATA_KEYS}
    return frame, selected, str(getattr(provider, "__version__", "unknown"))


def _bounded_snapshot(symbol: str, start: str, end: str) -> tuple[Any, dict, str]:
    """Bound caller latency and concurrent workers without automatic retries.

    Python cannot interrupt a third-party synchronous call safely. On deadline,
    its daemon worker can finish in the background but its result is discarded.
    It holds its slot until it exits: at most two provider workers can exist,
    including timed-out ones. No worker can mutate datasets or execute orders.
    """
    slots = _FETCH_SLOTS
    if not slots.acquire(blocking=False):
        raise FeedError("Ya hay dos descargas en curso. No se inicia otra petición al proveedor.")
    result: queue.Queue = queue.Queue(maxsize=1)

    def work():
        try:
            result.put((True, _call_provider(symbol, start, end)))
        except Exception as exc:
            result.put((False, exc))
        finally:
            slots.release()

    worker = threading.Thread(target=work, name="atlas-yahoo-eod", daemon=True)
    try:
        worker.start()
    except Exception:
        slots.release()
        raise
    try:
        success, payload = result.get(timeout=FETCH_DEADLINE_SECONDS)
    except queue.Empty as exc:
        raise FeedError(f"La descarga superó {FETCH_DEADLINE_SECONDS} segundos. Se descarta cualquier respuesta tardía; no se han cambiado los datos.") from exc
    if not success:
        if isinstance(payload, FeedError):
            raise payload
        raise FeedError(f"Yahoo/yfinance no pudo completar la descarga ({type(payload).__name__}). No se generan precios de sustitución.") from payload
    return payload


def _ten_year_limit(start: date) -> date:
    try:
        return start.replace(year=start.year + 10)
    except ValueError:
        if start.year > 9989:
            return date.max
        # The ten-year anniversary of February 29 is February 28.
        return start.replace(year=start.year + 10, day=28)


def _session_date(index: Any) -> str:
    # yfinance's timezone-aware index represents the exchange's session date.
    # Do not shift it to UTC: that can move European midnight to the prior day.
    if isinstance(index, str):
        return iso_date(index)
    if isinstance(index, datetime):
        return iso_date(index.date().isoformat())
    if isinstance(index, date):
        return iso_date(index.isoformat())
    try:
        return iso_date(index.date().isoformat())
    except (AttributeError, TypeError, ValueError) as exc:
        raise FeedError("El proveedor devolvió una fecha de sesión inválida.") from exc


def _missing_quote(value: Any) -> bool:
    """Only explicit missing values qualify; zero/infinity are invalid quotes."""
    if value is None:
        return True
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def fetch_daily(symbol: str, start: str, end: str | None = None) -> dict[str, Any]:
    """Fetch validated daily OHLCV for one EUR equity or ETF.

    start is inclusive; end is exclusive and defaults to today UTC. The request
    spans at most ten calendar years. Explicit future end dates are capped to
    today, and returned dates >= today are always excluded as unclosed sessions.
    Currency must be EUR in provider metadata: ticker suffixes never imply FX.

    OHLC columns are obtained with auto_adjust=False, back_adjust=False and
    repair=False. This preserves the provider's conventions, not independently
    verified unadjusted exchange tape. Dividends, splits and capital gains are
    returned separately, never credited to a portfolio or silently adjusted.
    An empty or invalid response fails closed; a one-session update is allowed.
    A row with all four OHLC values missing and zero volume is excluded with an
    explicit date/count warning while retaining its corporate actions. It is a
    gap, never an inferred holiday or fabricated quote. Partial OHLC rows fail.
    """
    if not isinstance(symbol, str):
        raise FeedError("symbol debe ser un ticker de Yahoo de hasta 25 caracteres.")
    symbol = symbol.strip().upper()
    if not _SYMBOL.fullmatch(symbol):
        raise FeedError("Ticker inválido: usa hasta 25 letras, números, puntos o guiones; un solo instrumento.")
    try:
        first = date.fromisoformat(iso_date(start))
        today = _today_utc()
        requested_end = date.fromisoformat(iso_date(end)) if end is not None else today
    except ValueError as exc:
        raise FeedError("start/end deben ser fechas válidas YYYY-MM-DD.") from exc
    if first >= requested_end:
        raise FeedError("start debe ser anterior a end; end es exclusivo.")
    if requested_end > _ten_year_limit(first):
        raise FeedError("La descarga está limitada a un intervalo máximo de diez años.")
    cutoff = min(requested_end, today)
    if first >= cutoff:
        raise FeedError("El rango no contiene sesiones anteriores a hoy UTC.")
    frame, metadata, version = _bounded_snapshot(symbol, first.isoformat(), cutoff.isoformat())
    currency = metadata.get("currency")
    if currency != "EUR":
        raise FeedError(f"La moneda confirmada por Yahoo es {currency!r}. Solo se admite EUR; no se infiere moneda ni se convierte FX.")
    kind = metadata.get("instrumentType")
    if kind not in {"EQUITY", "ETF"}:
        raise FeedError(f"Tipo de instrumento {kind!r} no admitido o no verificado; ATLAS cubre acciones y ETF.")
    reported_symbol = metadata.get("symbol")
    if reported_symbol is not None and (not isinstance(reported_symbol, str) or reported_symbol.upper() != symbol):
        raise FeedError("El símbolo devuelto por Yahoo difiere del solicitado; revisa el identificador.")
    if frame is None or not hasattr(frame, "columns") or not hasattr(frame, "iterrows"):
        raise FeedError("Yahoo no devolvió una tabla OHLCV válida.")
    columns = list(frame.columns)
    if len(columns) != len(set(columns)) or not _REQUIRED_COLUMNS.issubset(columns):
        raise FeedError("Faltan columnas OHLCV o acciones corporativas verificables, o hay columnas duplicadas.")
    warnings = [
        "Datos diarios descargados de Yahoo mediante yfinance: no son cotizaciones en tiempo real ni un feed de ejecución.",
        "yfinance no está afiliado ni avalado por Yahoo. Su documentación describe uso personal/de investigación; consulta los términos de Yahoo para los derechos sobre los datos.",
        "No hay garantía de exactitud, disponibilidad ni puntualidad; pueden existir límites de peticiones y revisiones históricas.",
        "OHLC del proveedor sin autoajuste ni reparación adicionales; no constituyen una serie verificada de rentabilidad total. No se abonan dividendos ni se aplican splits al libro mayor.",
        "Solo se incluyen fechas de sesión anteriores a hoy UTC. No se certifica el calendario bursátil ni la integridad del historial de acciones corporativas.",
    ]
    if requested_end > cutoff:
        warnings.append("end se ha limitado a hoy UTC para excluir sesiones sin cerrar.")
    raw_bars = []
    actions = []
    excluded = 0
    empty_quote_dates = []
    received_rows = 0
    seen_dates = set()
    fields = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
    for index, row in frame.iterrows():
        received_rows += 1
        day = _session_date(index)
        if not first.isoformat() <= day < cutoff.isoformat():
            excluded += 1
            continue
        if day in seen_dates:
            raise FeedError(f"El proveedor devolvió una fecha duplicada: {day}.")
        seen_dates.add(day)
        try:
            values = {target: row[source] for target, source in fields.items()}
            volume = decimal_value(values["volume"], f"{day}.volume")
            # Preserve distributions/splits even on provider action-only rows.
            for column, action_kind in (("Dividends", "dividend"), ("Stock Splits", "split"), ("Capital Gains", "capital_gain")):
                if column not in columns:
                    continue
                amount = decimal_value(row[column], f"{day}.{column}")
                if amount:
                    actions.append({"date": day, "symbol": symbol, "kind": action_kind, "value": float(amount), "currency": "EUR", "applied_to_ledger": False})
        except (ValueError, TypeError, KeyError) as exc:
            raise FeedError(f"Fila inválida del proveedor para {day}: {exc}") from exc
        missing = [field for field in ("open", "high", "low", "close") if _missing_quote(values[field])]
        if len(missing) == 4 and volume == 0:
            empty_quote_dates.append(day)
            continue
        if missing:
            raise FeedError(f"Cotización incompleta para {day}: faltan {', '.join(missing)}; volumen={volume}. No se omiten filas parciales ni se rellenan precios.")
        raw_bars.append({"date": day, "symbol": symbol, "currency": "EUR", **values})
    try:
        normalized = normalize_bars(raw_bars)
    except (ValueError, TypeError, KeyError) as exc:
        raise FeedError(f"La respuesta contiene barras inválidas: {exc}") from exc
    if not normalized:
        raise FeedError("Yahoo no devolvió sesiones cerradas dentro del rango. No se inventan precios ni se rellenan huecos.")
    if excluded:
        warnings.append(f"Se excluyeron {excluded} filas fuera del rango solicitado o de sesiones todavía no cerradas.")
    if empty_quote_dates:
        warnings.append(f"Se excluyeron {len(empty_quote_dates)} filas sin ningún OHLC y con volumen cero: {', '.join(empty_quote_dates)}. Permanecen como huecos sin precios; no se presume que sean festivos. Sus acciones corporativas se conservan.")
    if actions:
        warnings.append("Se detectaron acciones corporativas sin conciliar: bloquea la promoción automática hasta resolver su tratamiento contable y el ajuste de la serie.")
    bars = [{key: float(value) if isinstance(value, Decimal) else value for key, value in bar.items()} for bar in normalized]
    source = f"Yahoo Finance mediante yfinance {version}; histórico diario OHLCV, moneda EUR verificada."
    return {
        "bars": bars, "source": source, "source_kind": "observed",
        "warnings": warnings, "corporate_actions": sorted(actions, key=lambda action: (action["date"], action["kind"])),
        "source_metadata": {
            "provider": "yahoo", "adapter": "yfinance", "adapter_version": version,
            "symbol": symbol, "currency": "EUR", "currency_verified": True,
            "instrument_type": kind, "exchange": metadata.get("exchangeName"),
            "exchange_timezone": metadata.get("exchangeTimezoneName"),
            "interval": "1d", "is_realtime": False, "auto_adjust": False,
            "back_adjust": False, "repair": False,
            "price_basis": "provider_ohlc_auto_adjust_false",
            "start_inclusive": first.isoformat(), "end_exclusive": cutoff.isoformat(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "closed_before_utc_date": today.isoformat(),
            "corporate_actions_present": bool(actions), "corporate_actions_applied": False,
            "action_columns": [column for column in ("Dividends", "Stock Splits", "Capital Gains") if column in columns],
            "received_rows": received_rows, "accepted_rows": len(bars),
            "excluded_out_of_range_rows": excluded,
            "excluded_empty_quote_rows": len(empty_quote_dates),
            "excluded_empty_quote_dates": empty_quote_dates,
            "documentation": "https://github.com/ranaroussi/yfinance",
            "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
            "fetch_deadline_seconds": FETCH_DEADLINE_SECONDS,
        },
    }
