"""Explicit economic assumptions for isolated v0.6 research, never a mandate."""
from typing import Annotated, Literal

from pydantic import Field, field_validator

from .book import number
from .quality import digest
from .strategy_spec import FrozenContract

SIMULATOR_VERSION = 'sma-economics-eur-v1'
DecimalText = Annotated[str, Field(min_length=1, max_length=32)]


class SimulationConfig(FrozenContract):
    policy: Literal['sma-economics-eur-v1'] = SIMULATOR_VERSION
    initial_cash_eur: DecimalText
    strategy_weight: DecimalText = '1'
    max_position_weight: DecimalText = '1'
    quantity_step: DecimalText = '1'
    fixed_fee_eur: DecimalText = '1'
    fee_bps: DecimalText = '5'
    slippage_bps: DecimalText = '5'
    purchases_enabled: bool = True

    @field_validator('initial_cash_eur', 'strategy_weight', 'max_position_weight',
                     'quantity_step', 'fixed_fee_eur', 'fee_bps', 'slippage_bps')
    @classmethod
    def economic_number(cls, value, info):
        name = info.field_name
        scale = 2 if name in ('initial_cash_eur', 'fixed_fee_eur') else 12
        positive = name in ('initial_cash_eur', 'strategy_weight', 'quantity_step')
        result = number(value, name, scale, None, positive=positive)
        maximum = (1 if name.endswith('weight') else
                   1000 if name.endswith('bps') else 10**12)
        if result > maximum:
            raise ValueError(f'{name}: supera el máximo {maximum}.')
        return value.rstrip('0').rstrip('.') if '.' in value else value

    @property
    def fingerprint(self):
        return digest(self.model_dump(mode='json'))
