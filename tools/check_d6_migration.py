"""Validate schema 4 -> 5, EUR compatibility and recovery on disposable copies."""
import argparse
from pathlib import Path

from check_d5_migration import check, values
from atlas_quant.book import POLICY
from atlas_quant.book_service import BookService
from atlas_quant.corporate_service import CorporateService
from atlas_quant.valuation_store import DDL


def d6_values(store, day):
    result = values(store, day)
    for ident, value in result.items():
        value['eur_api'] = BookService(store).read(ident, day)
        value['native_api'] = BookService(store, multicurrency=True).read(ident, day)
        if value['detail']['portfolio']['accounting_policy'] == POLICY:
            value['corporate'] = CorporateService(store).read(ident, day)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup', type=Path)
    check(parser.parse_args().backup.resolve(), schema_before=4, new_tables=DDL,
          read_values=d6_values, run_prefix='d6')
