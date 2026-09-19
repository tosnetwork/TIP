#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
"""Check TIP-0002 PQ-native consensus examples.

Three case kinds are modeled:

  derivation  - the frozen key_id derivation, actually computed with SHA-256
  certificate - PQ certificate acceptance: identity binding, key_id consistency,
                uniqueness, absence of classical fallback, weighted quorum
  config      - ConfigParam 16 admission against the PQ resource envelope

Only the derivation kind performs real cryptographic work. Elsewhere
`signature_valid` is a supplied verification outcome, not a signature: this
model has no verifier, runs no consensus, and is not evidence of performance.

Every guard below is reachable from the corpus. Removing one makes at least one
case fail.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any

KEY_ID_DOMAIN = b"TOS-PQ-CONSENSUS-KEY-v1"
MAX_TOTAL_WEIGHT = ((1 << 64) - 1) // 3

# Deterministic worst-case certificate size, in bytes, for n signers: each
# signature pair carries the suite signature plus validator_id and algorithm_id.
SIGNER_OVERHEAD_BYTES = 34
CERTIFICATE_OVERHEAD_BYTES = 64


def key_id_failure(algorithm_id: Any, public_key: bytes,
                   suite: dict[str, Any]) -> str | None:
    """Return why derivation must fail closed, or None when it is admissible."""
    if algorithm_id != suite["algorithm_id"]:
        return "reject_suite"
    if len(public_key) != suite["public_key_bytes"]:
        return "reject_key_length"
    return None


def key_id_of(algorithm_id: int, public_key: bytes) -> str:
    """Derive key_id from already admitted material, per TIP-0002 Section 3."""
    preimage = KEY_ID_DOMAIN + struct.pack("<H", algorithm_id) + public_key
    return hashlib.sha256(preimage).hexdigest()


def material(spec: Any) -> bytes:
    """Expand a {fill, length} byte description used to keep the corpus small."""
    if not isinstance(spec, dict):
        raise ValueError("Byte material must be an object")
    fill = bytes.fromhex(spec["fill"])
    if len(fill) != 1:
        raise ValueError("Byte material fill must be exactly one byte")
    length = spec["length"]
    if type(length) is not int or not 0 <= length <= 1 << 16:
        raise ValueError("Byte material length out of range")
    return fill * length


def positive_weight(value: Any) -> bool:
    return type(value) is int and 0 < value <= MAX_TOTAL_WEIGHT


def load_set(descriptors: Any, suite: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Validate a PQ validator set; return (outcome, members keyed by validator_id)."""
    if not isinstance(descriptors, list) or not descriptors:
        return "reject_set", {}
    members: dict[str, Any] = {}
    key_ids: set[str] = set()
    total = 0
    for descriptor in descriptors:
        validator_id = descriptor["validator_id"]
        public_key = material(descriptor["public_key"])
        failure = key_id_failure(descriptor["algorithm_id"], public_key, suite)
        if failure is not None:
            return failure, {}
        key_id = key_id_of(descriptor["algorithm_id"], public_key)
        if descriptor.get("key_id", key_id) != key_id:
            return "reject_key_id", {}
        if not descriptor.get("adnl_addr"):
            return "reject_adnl", {}
        if validator_id in members:
            return "reject_duplicate_validator", {}
        if key_id in key_ids:
            return "reject_duplicate_key", {}
        if not positive_weight(descriptor["weight"]):
            return "reject_weight", {}
        members[validator_id] = {"key_id": key_id, "weight": descriptor["weight"]}
        key_ids.add(key_id)
        total += descriptor["weight"]
    if total > MAX_TOTAL_WEIGHT:
        return "reject_weight", {}
    return "accept", members


def worst_case_certificate_bytes(signers: int, suite: dict[str, Any]) -> int:
    return CERTIFICATE_OVERHEAD_BYTES + signers * (
        suite["signature_bytes"] + SIGNER_OVERHEAD_BYTES
    )


def evaluate_derivation(case: dict[str, Any], suite: dict[str, Any]) -> str:
    public_key = material(case["public_key"])
    failure = key_id_failure(case["algorithm_id"], public_key, suite)
    if failure is not None:
        return failure
    key_id = key_id_of(case["algorithm_id"], public_key)
    if key_id != case["expected_key_id"]:
        return "reject_key_id"
    return "match"


def evaluate_certificate(case: dict[str, Any], suite: dict[str, Any],
                         default_set: Any) -> str:
    """Return the modeled outcome, not a production consensus error code."""
    outcome, members = load_set(case.get("validator_set", default_set), suite)
    if outcome != "accept":
        return outcome
    if case.get("well_formed", True) is not True:
        return "reject_encoding"
    if case.get("set_commitment_matches", True) is not True:
        return "reject_set_commitment"
    signers = case["signers"]
    if not isinstance(signers, list):
        return "reject_encoding"
    if len(signers) > suite["max_certificate_signers"]:
        return "reject_budget_signers"
    if worst_case_certificate_bytes(len(signers), suite) > suite["max_certificate_bytes"]:
        return "reject_budget_bytes"
    seen: set[str] = set()
    signed = 0
    for signature in signers:
        validator_id = signature["validator_id"]
        if validator_id not in members:
            return "reject_unknown_signer"
        if validator_id in seen:
            return "reject_duplicate_signer"
        seen.add(validator_id)
        member = members[validator_id]
        signed_length = signature.get("signature_bytes", suite["signature_bytes"])
        if signature.get("classical", False) is not False:
            return "reject_classical_signature"
        if signature["algorithm_id"] != suite["algorithm_id"]:
            return "reject_suite"
        if signed_length != suite["signature_bytes"]:
            return "reject_signature_length"
        if signature.get("key_id", member["key_id"]) != member["key_id"]:
            return "reject_key_id"
        if signature.get("context", case["context"]) != case["context"]:
            return "reject_context"
        if signature.get("signature_valid", False) is not True:
            return "reject_authentication"
        signed += member["weight"]
    total = sum(member["weight"] for member in members.values())
    if 3 * signed < 2 * total:
        return "reject_quorum"
    return "accept"


def evaluate_config(case: dict[str, Any], suite: dict[str, Any]) -> str:
    """Model ConfigParam 16 admission: reject before the value is authoritative."""
    min_validators = case["min_validators"]
    max_main = case["max_main_validators"]
    max_validators = case["max_validators"]
    if not all(type(value) is int for value in (min_validators, max_main, max_validators)):
        return "reject_config_shape"
    if min_validators < 1:
        return "reject_config_shape"
    if not min_validators <= max_main <= max_validators:
        return "reject_config_shape"
    if max_main > suite["max_certificate_signers"]:
        return "reject_budget_signers"
    if worst_case_certificate_bytes(max_main, suite) > suite["max_certificate_bytes"]:
        return "reject_budget_bytes"
    return "accept"


def evaluate(case: dict[str, Any], default_suite: dict[str, Any],
             default_set: Any) -> str:
    suite = dict(default_suite)
    suite.update(case.get("suite", {}))
    kind = case["kind"]
    if kind == "derivation":
        return evaluate_derivation(case, suite)
    if kind == "certificate":
        return evaluate_certificate(case, suite, default_set)
    if kind == "config":
        return evaluate_config(case, suite)
    return "reject_kind"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="?", type=Path,
                        default=Path(__file__).with_name("pq-consensus-cases.json"))
    args = parser.parse_args()
    try:
        corpus = json.loads(args.cases.read_text(encoding="utf-8"))
        cases = corpus["cases"]
        suite = corpus["suite"]
        default_set = corpus["default_validator_set"]
        if not isinstance(cases, list) or not cases:
            raise ValueError("Case corpus must be a nonempty list")
        identities = [case["id"] for case in cases]
        if len(set(identities)) != len(identities):
            raise ValueError("Duplicate case IDs")
        failures = 0
        for case in cases:
            actual = evaluate(case, suite, default_set)
            if actual != case["expected"]:
                failures += 1
                print(f"FAIL {case['id']}: expected {case['expected']}, got {actual}",
                      file=sys.stderr)
        if failures:
            print(f"{failures}/{len(cases)} cases failed", file=sys.stderr)
            return 1
        print(f"PASS: {len(cases)} PQ-consensus model cases "
              f"(only key_id derivation is real cryptography)")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Invalid corpus: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
