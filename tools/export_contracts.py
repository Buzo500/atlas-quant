"""Export local OpenAPI schemas as TypeScript without a generator dependency.

Only the JSON Schema vocabulary emitted by ATLAS is accepted. Unsupported
schema shapes fail explicitly instead of weakening a contract to ``any``.
Schema discovery uses an isolated temporary store and never starts the worker.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "frontend" / "lib" / "api-types.ts"


def _name(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_$]", "_", value)
    return result if re.match(r"[A-Za-z_$]", result) else "Schema_" + result


def _literal(value) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _typescript(schema: dict, names: set[str]) -> str:
    if "$ref" in schema:
        reference = schema["$ref"]
        if not reference.startswith("#/components/schemas/"):
            raise ValueError(f"Referencia de esquema no admitida: {reference}")
        name = reference.rsplit("/", 1)[-1]
        if name not in names:
            raise ValueError(f"Referencia de esquema ausente: {name}")
        return _name(name)
    if "const" in schema:
        return _literal(schema["const"])
    if "enum" in schema:
        return " | ".join(_literal(value) for value in schema["enum"]) or "never"
    for composition, operator in (("anyOf", " | "), ("oneOf", " | "), ("allOf", " & ")):
        if composition in schema:
            return operator.join("(" + _typescript(item, names) + ")" for item in schema[composition])
    kind = schema.get("type")
    if isinstance(kind, list):
        return " | ".join(_typescript({**schema, "type": item}, names) for item in kind)
    if kind in ("number", "integer"):
        return "number"
    if kind in ("string", "boolean", "null"):
        return kind
    if kind == "array":
        return "Array<" + _typescript(schema.get("items", {}), names) + ">"
    if kind == "object" or "properties" in schema:
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        fields = [f"  {_literal(name)}{'' if name in required else '?'}: {_typescript(value, names)};"
                  for name, value in properties.items()]
        additional = schema.get("additionalProperties", True)
        if additional is not False:
            item_type = "unknown" if additional is True else _typescript(additional, names)
            fields.append(f"  [key: string]: {item_type};")
        return "{\n" + "\n".join(fields) + "\n}"
    if not schema or not set(schema) - {"title", "description", "default"}:
        return "unknown"
    raise ValueError(f"Forma de esquema no admitida: {schema}")


def render_openapi(document: dict) -> str:
    schemas = document["components"]["schemas"]
    names = set(schemas)
    if len({_name(name) for name in names}) != len(names):
        raise ValueError("Los nombres de esquema colisionan al convertirlos a TypeScript.")
    header = ("// Generated from the ATLAS local OpenAPI contracts. Do not edit manually.\n"
              "// Regenerate: python tools/export_contracts.py\n"
              "// Verify: python tools/export_contracts.py --check\n\n")
    return header + "\n\n".join(f"export type {_name(name)} = {_typescript(schemas[name], names)};"
                                for name in sorted(names)) + "\n"


def local_openapi() -> dict:
    # Importing app.py creates a default app, so isolate its store before import.
    sys.path.insert(0, str(ROOT / "backend"))
    temporary_root = ROOT / "var" / "validation"
    temporary_root.mkdir(parents=True, exist_ok=True)
    previous = os.environ.get("ATLAS_DATA_DIR")
    try:
        with tempfile.TemporaryDirectory(prefix="contracts-", dir=temporary_root) as directory:
            os.environ["ATLAS_DATA_DIR"] = directory
            from atlas_quant.app import create_app

            return create_app(directory, run_worker=False).openapi()
    finally:
        if previous is None:
            os.environ.pop("ATLAS_DATA_DIR", None)
        else:
            os.environ["ATLAS_DATA_DIR"] = previous


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render_openapi(local_openapi())
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
            print("Contratos TypeScript ausentes o desactualizados; ejecuta tools/export_contracts.py.", file=sys.stderr)
            return 1
        print("Contratos TypeScript coherentes con OpenAPI.")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Contratos TypeScript generados: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
