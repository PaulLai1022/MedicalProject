"""Predicate DSL evaluator — supports comparison, boolean, existence, and string operators.

Field namespaces:
  - Plain fields: "arterial_ph", "glucose_mg_dl", etc.
  - Clinical phrases: "clinical_phrase:AMS", "clinical_phrase:DKA", etc.
  - Medications: "medication:SGLT2i", etc.
"""

from __future__ import annotations

from typing import Any


def eval_predicate(predicate: dict, context: dict[str, Any]) -> bool:
    """Recursively evaluate a predicate expression.

    Args:
        predicate: the predicate object from the rules JSON
        context: flattened fact context, i.e. {field_name: value}

    Returns:
        True iff the rule matches.
    """
    op = predicate.get("op", "")

    # Boolean combinators
    if op == "and":
        return all(eval_predicate(p, context) for p in predicate["operands"])
    if op == "or":
        return any(eval_predicate(p, context) for p in predicate["operands"])
    if op == "not":
        return not eval_predicate(predicate["operand"], context)

    # Operators that take a `field`
    field = predicate.get("field", "")
    field_value = context.get(field)

    # Existence operators
    if op == "exists":
        return field_value is not None
    if op == "truthy":
        return bool(field_value)

    # Comparison operators — if the field is absent, skip (no match).
    if field_value is None:
        return False

    target = predicate.get("value")

    if op == "lt":
        return _numeric(field_value) < target
    if op == "le":
        return _numeric(field_value) <= target
    if op == "gt":
        return _numeric(field_value) > target
    if op == "ge":
        return _numeric(field_value) >= target
    if op == "eq":
        return field_value == target
    if op == "ne":
        return field_value != target

    # String operator
    if op == "contains":
        return str(target).lower() in str(field_value).lower()

    return False


def _numeric(value: Any) -> float:
    """Safely convert to numeric; non-numeric returns float('nan')."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")
