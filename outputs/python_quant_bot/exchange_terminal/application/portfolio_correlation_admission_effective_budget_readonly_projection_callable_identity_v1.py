"""Strict canonical callable identity for the read-only projection V1."""
from __future__ import annotations
import inspect
from typing import Any
from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document, strict_json_contract_equal
CALLABLE_IDENTITY_SCHEMA_VERSION="portfolio-correlation-admission-effective-budget-readonly-projection-callable-identity-v1"
STATIC_FINGERPRINT="20260825-portfolio-correlation-admission-effective-budget-readonly-projection-callable-identity-v1-lock-1"
CALLABLE_MODULE="exchange_terminal.application.ports.portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1"
CALLABLE_QUALNAME="build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1"
PARAMETER_CONTRACT=(("request_payload","POSITIONAL_OR_KEYWORD"),("provider_binding_document","KEYWORD_ONLY"),("internal_provider_positional","KEYWORD_ONLY"),("internal_provider_keyword","KEYWORD_ONLY"))
EXPECTED_CALLABLE_IDENTITY_HASH="aeaa931f01a2aa1f67643ff59b5f2927a418bd6576d6586244dc46abab95781f"
def build_portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1()->dict[str,Any]:
    return seal_strict_canonical_document({"schema_version":CALLABLE_IDENTITY_SCHEMA_VERSION,"static_fingerprint":STATIC_FINGERPRINT,"module":CALLABLE_MODULE,"qualname":CALLABLE_QUALNAME,"parameters":[{"name":n,"kind":k} for n,k in PARAMETER_CONTRACT]},"identity_hash")
def verify_portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1(document:Any,callable_object:Any)->bool:
    expected=build_portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1()
    if expected.get("identity_hash")!=EXPECTED_CALLABLE_IDENTITY_HASH or not strict_json_contract_equal(document,expected) or not callable(callable_object) or getattr(callable_object,"__module__",None)!=CALLABLE_MODULE or getattr(callable_object,"__qualname__",None)!=CALLABLE_QUALNAME:return False
    try: parameters=tuple(inspect.signature(callable_object).parameters.values())
    except (TypeError,ValueError): return False
    return tuple((p.name,p.kind.name) for p in parameters)==PARAMETER_CONTRACT
__all__=["CALLABLE_IDENTITY_SCHEMA_VERSION","CALLABLE_MODULE","CALLABLE_QUALNAME","EXPECTED_CALLABLE_IDENTITY_HASH","PARAMETER_CONTRACT","STATIC_FINGERPRINT","build_portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1","verify_portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1"]
