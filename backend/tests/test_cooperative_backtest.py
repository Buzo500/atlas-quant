"""Cancellation reaches the real numerical loop, without changing its policy."""
import pytest

from atlas_quant.backtest import backtest, run_research
from atlas_quant.controls import WorkStopped
from test_service import history


@pytest.mark.parametrize("research", [False, True])
def test_real_calculation_honors_stop_between_blocks(research):
    checkpoints = 0

    def stop():
        nonlocal checkpoints
        checkpoints += 1
        if checkpoints == 3:
            raise WorkStopped()

    rule = {"kind": "buy_hold", "symbol": "ETF"}
    with pytest.raises(WorkStopped):
        if research:
            run_research(history(500), [rule], checkpoint=stop)
        else:
            backtest(history(500), rule, checkpoint=stop)
    assert checkpoints == 3
