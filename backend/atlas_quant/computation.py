"""Bound memory-heavy reads while leaving control endpoints available."""
from functools import wraps
from threading import BoundedSemaphore

_SLOTS = BoundedSemaphore(2)


class ComputationBusy(RuntimeError):
    pass


def bounded_calculation(function):
    @wraps(function)
    def run(*args, **kwargs):
        if not _SLOTS.acquire(blocking=False):
            raise ComputationBusy('Hay dos cálculos en curso. Espera a que terminen y vuelve a consultar.')
        try:
            return function(*args, **kwargs)
        finally:
            _SLOTS.release()
    return run
