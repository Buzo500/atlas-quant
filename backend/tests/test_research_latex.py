"""The printable document is a verified view, never an executable user template."""
import hashlib
import io
import json
import zipfile

import pytest

from atlas_quant.quality import digest
from atlas_quant.research_latex import archive, make_files, number, tex_text, verify_archive, provenance_rows
from atlas_quant.retrospective import RetrospectiveRequest, freeze
from atlas_quant.retrospective_package import encoded, run
from test_retrospective_v06 import inputs, frozen_inputs

STAMP = '2026-09-13T18:00:00+00:00'


def test_long_provenance_is_paginated_without_losing_words():
    raw = ' '.join(f'palabra{i}' for i in range(280))
    rows = provenance_rows(dict(provider='Fuente', calendar_source='Calendario', event_review=raw))
    assert len(rows) > 5
    assert ' '.join(value for label, value in rows if label.startswith('Eventos')) == raw
    assert all(len(value) <= 500 for _, value in rows)


def test_export_preserves_originals_full_curve_metrics_and_reserved_prices_absent():
    report = run(frozen_inputs())
    files = make_files(report, generated_at=STAMP)
    source = files['report.tex'].decode('utf-8')
    assert files['report.json'] == encoded(report)
    assert len(files['nav-plot.csv'].splitlines()) == 8
    assert b'2025-01-08' not in files['prices.csv']
    assert b'2025-01-08' not in files['nav.csv']
    assert '800,00' in source and '801,00' in source and '-20,00' in source
    assert '08/01/2025' in source  # Reservation metadata, no values.
    assert 'sin calcular' in source and 'No acredita' in source
    manifest = verify_archive(archive(files))
    assert manifest['source_report_hash'] == report['report_hash']
    for name, meta in manifest['files'].items():
        assert meta == dict(sha256=hashlib.sha256(files[name]).hexdigest(), bytes=len(files[name]))
    assert archive(files) == archive(make_files(report, generated_at=STAMP))


def test_previous_code_is_recalculated_without_overwriting_its_original_fingerprint():
    report = run(frozen_inputs())
    report['code_sha256'] = {'old.py': 'f'*64}
    report['report_hash'] = digest({k:v for k,v in report.items() if k != 'report_hash'})
    files = make_files(report, generated_at=STAMP)
    assert json.loads(files['report.json']) == report
    assert verify_archive(archive(files))['code_matches'] is False
    assert 'Se conservan las huellas originales' in files['report.tex'].decode('utf-8')


@pytest.mark.parametrize('target', ['metrics', 'curve', 'trades', 'reserve', 'hash'])
def test_manipulated_results_never_render_even_with_rehashed_outer_document(target):
    report = run(frozen_inputs())
    if target == 'metrics': report['result']['development']['metrics'][0]['final_nav_eur'] = '99999'
    elif target == 'curve': report['result']['development']['curve'][-1]['sma_eur'] = '99999'
    elif target == 'trades': report['result']['development']['trades'][0]['fee_eur'] = '99999'
    elif target == 'reserve': report['result']['holdout']['evaluated'] = True
    else: report['frozen']['frozen_hash'] = 'a'*64
    report['report_hash'] = digest({k:v for k,v in report.items() if k != 'report_hash'})
    with pytest.raises(ValueError): make_files(report)


@pytest.mark.parametrize('value', ['\x00', '\x1b', '\u202e', '\u2066'])
def test_invisible_controls_and_bidi_are_rejected(value):
    with pytest.raises(ValueError, match='control'): tex_text('texto'+value)


def test_tex_commands_are_data_and_long_source_tokens_can_wrap():
    body, csv, _ = inputs()
    body['provider'] = r'Fuente \input{secreto} \write18{comando} % $ # _ & ~ ^ ' + 'a'*120
    report = run(freeze(RetrospectiveRequest.model_validate_json(json.dumps(body)), csv))
    source = make_files(report, generated_at=STAMP)['report.tex'].decode('utf-8')
    assert r'\input{secreto}' not in source
    assert r'\write18{comando}' not in source
    assert r'\textbackslash{}input\{secreto\}' in source
    assert r'\% \$ \# \_ \& \textasciitilde{} \textasciicircum{}' in source
    assert 'a'*120 not in source and r'a\allowbreak{}a' in source


@pytest.mark.parametrize('timestamp', ['2026-09-13', '2026-09-13T18:00:00+02:00', 'not-a-date'])
def test_generation_timestamp_must_be_utc(timestamp):
    with pytest.raises(ValueError): make_files(run(frozen_inputs()), generated_at=timestamp)


@pytest.mark.parametrize('target', ['report.tex','atlas-style.tex','nav-plot.csv','manifest.json','../outside'])
def test_source_manifest_data_and_path_tampering_are_rejected_without_extraction(target):
    files = make_files(run(frozen_inputs()), generated_at=STAMP)
    if target == '../outside': files[target] = files.pop('report.tex')
    else: files[target] += b'\nchanged'
    with pytest.raises(ValueError): verify_archive(archive(files))


def test_duplicate_zip_members_are_rejected():
    files = make_files(run(frozen_inputs()), generated_at=STAMP)
    data = io.BytesIO(archive(files))
    with zipfile.ZipFile(data, 'a') as zipped, pytest.warns(UserWarning):
        zipped.writestr('report.tex', 'malicious')
    with pytest.raises(ValueError): verify_archive(data.getvalue())


def test_spanish_rounding_is_presentation_only():
    assert number('1234567.895') == '1.234.567,90'
    assert number('-15.8661') == '-15,87'
    assert number('20.92045678', 4) == '20,9205'


def test_cli_missing_engine_keeps_verified_source_bundle_and_refuses_overwrites(tmp_path, monkeypatch):
    import export_research_latex as cli
    original = tmp_path/'input.json'
    original.write_bytes(encoded(run(frozen_inputs())))
    output = tmp_path/'source.zip'
    monkeypatch.setattr(cli.sys, 'argv', ['export_research_latex', str(original), '--output', str(output), '--pdf'])
    monkeypatch.setattr(cli, 'engine_path', lambda: (_ for _ in ()).throw(ValueError('Sin compilador')))
    with pytest.raises(SystemExit) as failure: cli.main()
    assert failure.value.code == 1
    assert verify_archive(output.read_bytes())['source_report_hash'] == json.loads(original.read_bytes())['report_hash']
    before = output.read_bytes()
    with pytest.raises(SystemExit): cli.main()
    assert output.read_bytes() == before
