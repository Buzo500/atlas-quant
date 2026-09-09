"""Explicit instrument identity. Tickers and external codes never merge entities."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class IdentityNotFound(ValueError):
    pass


class RevisionConflict(ValueError):
    pass


class CatalogInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_revision: int = Field(ge=0)


class ExternalCode(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    scheme: str = Field(min_length=1, max_length=30)
    value: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=3, max_length=500)
    verified: bool = False


class InstrumentInput(CatalogInput):
    name: str = Field(min_length=1, max_length=100)
    instrument_type: Literal["equity", "ETF", "unknown"] = "unknown"
    source: str = Field(min_length=3, max_length=500)
    codes: list[ExternalCode] = Field(default_factory=list, max_length=20)
    verified: bool = False


class ListingInput(CatalogInput):
    instrument_id: str = Field(min_length=1, max_length=100)
    currency: Literal["EUR", "USD"]
    market: str | None = Field(default=None, min_length=1, max_length=50)
    calendar: str | None = Field(default=None, min_length=1, max_length=100)
    verified: bool = False

    @field_validator("market")
    @classmethod
    def canonical_market(cls, value):
        return value.upper() if value else value


class AliasInput(CatalogInput):
    listing_id: str = Field(min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=100)
    symbol: str = Field(min_length=1, max_length=50)
    valid_from: str | None = None
    valid_to: str | None = None
    source: str = Field(min_length=3, max_length=500)

    @field_validator("provider")
    @classmethod
    def canonical_provider(cls, value):
        return value.casefold()

    @field_validator("valid_from", "valid_to")
    @classmethod
    def iso_date(cls, value):
        if value is not None and date.fromisoformat(value).isoformat() != value:
            raise ValueError("Fecha ISO diaria requerida.")
        return value

    @model_validator(mode="after")
    def interval(self):
        if self.valid_from and self.valid_to and self.valid_from >= self.valid_to:
            raise ValueError("El fin del alias es exclusivo y debe ser posterior al inicio.")
        if self.provider.startswith("legacy:"):
            raise ValueError("El espacio de alias legacy está reservado a la importación local.")
        return self


class CatalogService:
    def __init__(self, store):
        self.store = store

    def read(self, revision=None):
        try:
            return self.store.atomic(lambda work: work.catalog(revision))
        except KeyError as exc:
            raise IdentityNotFound(exc.args[0]) from exc

    def add(self, kind, request):
        model = {"instrument": InstrumentInput, "listing": ListingInput, "alias": AliasInput}[kind]
        values = model.model_validate(request).model_dump()
        expected = values.pop("expected_revision")

        def save(work):
            catalog = work.catalog()
            if expected != catalog["revision"]:
                raise RevisionConflict("El catálogo ha cambiado. Actualiza antes de confirmar.")
            if kind == "instrument":
                work.insert_instrument(values)
            elif kind == "listing":
                if values["instrument_id"] not in {item["id"] for item in catalog["instruments"]}:
                    raise IdentityNotFound("Instrumento no encontrado.")
                work.insert_listing(values)
            else:
                listings = {item["id"]: item for item in catalog["listings"]}
                listing = listings.get(values["listing_id"])
                if listing is None:
                    raise IdentityNotFound("Cotización no encontrada.")
                for alias in catalog["aliases"]:
                    if (alias["provider"] == values["provider"] and alias["symbol"] == values["symbol"]
                            and listings[alias["listing_id"]].get("market") == listing.get("market")
                            and (values["valid_from"] or "0001-01-01") < (alias["valid_to"] or "9999-12-31")
                            and (alias["valid_from"] or "0001-01-01") < (values["valid_to"] or "9999-12-31")):
                        raise ValueError("Alias ambiguo: ya existe para ese proveedor, mercado y periodo.")
                work.insert_alias(values)
            result = work.save_catalog_revision()
            work.audit("catalog." + kind + "_created", details={"revision": result["revision"]})
            return result
        return self.store.atomic(save)

    def resolve(self, provider, symbol, effective_date, market=None, revision=None):
        provider = provider.strip().casefold()
        market = market.strip().upper() if market else None
        if date.fromisoformat(effective_date).isoformat() != effective_date:
            raise ValueError("Fecha ISO diaria requerida.")
        catalog = self.read(revision)
        listings = {item["id"]: item for item in catalog["listings"]}
        found = {alias["listing_id"] for alias in catalog["aliases"]
                 if alias["provider"] == provider and alias["symbol"] == symbol
                 and (market is None or listings[alias["listing_id"]].get("market") == market)
                 and (alias["valid_from"] is None or alias["valid_from"] <= effective_date)
                 and (alias["valid_to"] is None or effective_date < alias["valid_to"])}
        if not found:
            raise IdentityNotFound("No existe un alias vigente para esa consulta.")
        if len(found) != 1:
            raise ValueError("Alias ambiguo: especifica el mercado.")
        return listings[next(iter(found))]
