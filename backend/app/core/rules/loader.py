"""MCG rule loader — loads and validates the rules JSON once at startup."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_RULES_DIR = Path(__file__).resolve().parent.parent.parent / "rules_data"


@dataclass(frozen=True)
class Rule:
    """A single MCG rule."""
    id: str
    category: str
    severity: str
    predicate: dict[str, Any]
    citation: str
    clinical_explanation: str


@dataclass(frozen=True)
class CoreField:
    """Core diagnostic field definition. Present iff any of `satisfied_by` fields exist in facts."""
    name: str
    satisfied_by: tuple[str, ...]


@dataclass(frozen=True)
class RuleSet:
    """Full rule set."""
    guideline_id: str
    version: str
    rules: list[Rule]
    core_fields: tuple[CoreField, ...] = field(default_factory=tuple)
    missing_threshold_unknown: int = 2


def load_rules(filename: str = "mcg_diabetes.json") -> RuleSet:
    """Load and validate a rules JSON file."""
    path = _RULES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Basic schema validation
    assert "guidelineId" in data, "missing guidelineId"
    assert "rules" in data, "missing rules array"

    rules: list[Rule] = []
    for item in data["rules"]:
        _validate_rule_item(item)
        rules.append(Rule(
            id=item["id"],
            category=item["category"],
            severity=item["severity"],
            predicate=item["predicate"],
            citation=item["citation"],
            clinical_explanation=item["clinicalExplanation"],
        ))

    core_fields = tuple(
        CoreField(name=cf["name"], satisfied_by=tuple(cf["satisfied_by"]))
        for cf in data.get("core_fields", [])
    )
    threshold = int(data.get("missing_threshold_unknown", 2))

    logger.info(
        "Loaded %d MCG rules (guideline=%s, core_fields=%d)",
        len(rules), data["guidelineId"], len(core_fields),
    )
    return RuleSet(
        guideline_id=data["guidelineId"],
        version=data.get("version", "unknown"),
        rules=rules,
        core_fields=core_fields,
        missing_threshold_unknown=threshold,
    )


def _validate_rule_item(item: dict) -> None:
    """Validate the required fields of a single rule entry."""
    required = ["id", "category", "severity", "predicate", "citation", "clinicalExplanation"]
    for key in required:
        if key not in item:
            raise ValueError(f"Rule {item.get('id', '?')} is missing field: {key}")
    pred = item["predicate"]
    if "op" not in pred:
        raise ValueError(f"Rule {item['id']} predicate is missing 'op'")
