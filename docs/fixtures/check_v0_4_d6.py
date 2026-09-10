"""Check documentary arithmetic only; no ATLAS imports, database or network.

The semantic scenarios are listed, not claimed as passing application tests.
The expression language permits decimal literals, previous results in the same
case, arithmetic and the two documented rounding functions; never eval().
"""
import ast
import json
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path


def calculate(formula, values):
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return Decimal(ast.get_source_segment(formula, node))
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -visit(node.operand)
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and len(node.args) == 1 and not node.keywords):
            scale = {"money": "0.01", "cost": "0.000000000001"}.get(node.func.id)
            if scale:
                return visit(node.args[0]).quantize(Decimal(scale))
        raise ValueError(f"Unsupported reference expression: {formula}")
    return visit(ast.parse(formula, mode="eval").body)


def main():
    source = Path(__file__).with_name("v0_4_d6_referencias.json")
    reference = json.loads(source.read_text(encoding="utf-8"))
    all_cases = reference["numeric_cases"] + reference["semantic_cases"]
    ids = [case["id"] for case in all_cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate reference id")
    checks = 0
    with localcontext() as context:
        context.prec = 64
        context.rounding = ROUND_HALF_EVEN
        for case in reference["numeric_cases"]:
            values = {}
            for step in case["calculations"]:
                if step["name"] in values:
                    raise ValueError(f"Duplicate result in {case['id']}")
                actual = calculate(step["formula"], values)
                expected = Decimal(step["expected"])
                if not actual.is_finite() or actual != expected:
                    raise ValueError(f"{case['id']}/{step['name']}: {actual} != {expected}")
                values[step["name"]] = actual
                checks += 1
    print(json.dumps({
        "numeric_cases_checked": len(reference["numeric_cases"]),
        "exact_results_checked": checks,
        "semantic_cases_specified_not_executed": len(reference["semantic_cases"]),
        "application_tests_executed": 0,
        "result": "Reference arithmetic matches; this checker does not exercise application code.",
    }, indent=2))


if __name__ == "__main__":
    main()
