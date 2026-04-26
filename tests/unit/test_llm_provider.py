from pathlib import Path

from backend.cache import (
    build_generated_output_freshness_input,
    cache_entry_metadata_from_llm_generation,
    compute_generated_output_freshness_hash,
)
from backend.citations import CitationEvidence, CitationValidationClaim, CitationValidationContext
from backend.llm import (
    DEFAULT_MOCK_MODEL,
    DEFAULT_OPENROUTER_FREE_MODEL_ORDER,
    DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL,
    build_llm_runtime_config,
    decide_cache_eligibility,
    decide_paid_fallback,
    default_openrouter_settings,
    run_deterministic_mock_generation,
    run_mocked_live_generation_orchestration,
    runtime_diagnostics,
    validate_llm_generated_output,
)
from backend.llm_transport import call_openrouter_transport
from backend.models import (
    CacheEntryKind,
    CacheScope,
    FreshnessState,
    LlmAnswerState,
    LlmFallbackTrigger,
    LlmGenerationAttemptMetadata,
    LlmGenerationAttemptStatus,
    LlmGenerationRequestMetadata,
    LlmLiveGateState,
    LlmModelTier,
    LlmProviderKind,
    LlmReadinessStatus,
    LlmTransportMode,
    LlmTransportRetryability,
    LlmTransportStatus,
    LlmValidationStatus,
    SourceAllowlistStatus,
    SourceUsePolicy,
)
from backend.retrieval import build_asset_knowledge_pack
from backend.cache import build_knowledge_pack_freshness_input


ROOT = Path(__file__).resolve().parents[2]


def _request() -> LlmGenerationRequestMetadata:
    return LlmGenerationRequestMetadata(
        task_name="asset_summary",
        output_kind="asset_page",
        prompt_version="asset-page-prompt-v1",
        schema_version="asset-page-v1",
        safety_policy_version="safety-v1",
        asset_ticker="VOO",
        knowledge_pack_hash="knowledge-hash",
        source_freshness_hash="freshness-hash",
    )


def _attempt(status=LlmGenerationAttemptStatus.mock_succeeded) -> LlmGenerationAttemptMetadata:
    return LlmGenerationAttemptMetadata(
        attempt_index=1,
        provider_kind=LlmProviderKind.mock,
        model_name=DEFAULT_MOCK_MODEL,
        model_tier=LlmModelTier.mock,
        status=status,
        validation_status=LlmValidationStatus.valid,
    )


def _valid_evidence() -> CitationEvidence:
    return CitationEvidence(
        citation_id="c_voo_profile",
        asset_ticker="VOO",
        source_document_id="src_voo_fact_sheet",
        source_type="issuer_fact_sheet",
        supporting_text="VOO fact sheet fixture supports the educational claim.",
    )


def _valid_claim(citation_id: str = "c_voo_profile") -> CitationValidationClaim:
    return CitationValidationClaim(
        claim_id="claim_voo_profile",
        claim_text="VOO is represented by the local issuer fact sheet fixture.",
        claim_type="factual",
        citation_ids=[citation_id],
    )


def _mocked_transport(content: str, *, model: str = DEFAULT_OPENROUTER_FREE_MODEL_ORDER[0], latency_ms: int = 7):
    def transport(request):
        return {
            "status_code": 200,
            "latency_ms": latency_ms,
            "json": {
                "model": model,
                "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 6, "total_tokens": 11},
                "cost_usd": 0.0,
            },
        }

    return transport


def _ready_openrouter_runtime():
    return build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True)


def test_default_runtime_is_deterministic_mock_without_live_gate_or_credentials():
    config = build_llm_runtime_config()

    assert config.provider_kind is LlmProviderKind.mock
    assert config.readiness_status is LlmReadinessStatus.disabled_by_default
    assert config.live_generation_enabled is False
    assert config.live_gate_state is LlmLiveGateState.disabled
    assert config.server_side_key_present is False
    assert config.base_url_configured is False
    assert config.model_chain_configured is True
    assert config.live_network_calls_allowed is False
    assert config.no_live_call_status == "no_live_calls_attempted"
    assert config.configured_model_chain[0].model_name == DEFAULT_MOCK_MODEL
    assert config.configured_model_chain[0].tier is LlmModelTier.mock
    assert config.paid_fallback_model is None
    assert config.validation_retry_count == 1
    assert config.reasoning_summary_only is True
    assert config.validation_ready is True
    assert "schema_validation_required" in config.validation_gates
    assert "same_asset_or_comparison_pack_source_binding_required" in config.validation_gates


def test_openrouter_gate_requires_flag_key_presence_and_endpoint_model_settings():
    disabled = build_llm_runtime_config({"LLM_PROVIDER": "openrouter"})
    missing_key = build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=False)
    enabled = build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True)

    assert disabled.provider_kind is LlmProviderKind.openrouter
    assert disabled.readiness_status is LlmReadinessStatus.disabled_by_default
    assert disabled.live_gate_state is LlmLiveGateState.unavailable
    assert "live_generation_flag_disabled" in disabled.unavailable_reasons
    assert "server_side_key_presence_flag_missing" in disabled.unavailable_reasons

    assert missing_key.live_generation_enabled is True
    assert missing_key.readiness_status is LlmReadinessStatus.unavailable
    assert missing_key.live_gate_state is LlmLiveGateState.unavailable
    assert "server_side_key_presence_flag_missing" in missing_key.unavailable_reasons

    assert enabled.live_generation_enabled is True
    assert enabled.readiness_status is LlmReadinessStatus.ready_for_explicit_live_call
    assert enabled.live_gate_state is LlmLiveGateState.enabled
    assert enabled.base_url_configured is True
    assert enabled.model_chain_configured is True
    assert enabled.endpoint_configured is True
    assert enabled.live_network_calls_allowed is False
    assert enabled.validation_retry_count == 1
    assert enabled.reasoning_summary_only is True
    assert enabled.validation_ready is True
    assert [model.model_name for model in enabled.configured_model_chain] == list(DEFAULT_OPENROUTER_FREE_MODEL_ORDER)
    assert [model.order for model in enabled.configured_model_chain] == [1, 2, 3, 4]
    assert all(model.tier is LlmModelTier.free for model in enabled.configured_model_chain)
    assert enabled.paid_fallback_model is not None
    assert enabled.paid_fallback_model.model_name == DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL
    assert enabled.paid_fallback_model.tier is LlmModelTier.paid
    assert enabled.paid_fallback_model.order == 5


def test_openrouter_readiness_distinguishes_missing_endpoint_models_and_validation_gates():
    missing_base_url = build_llm_runtime_config(
        {
            **default_openrouter_settings(),
            "OPENROUTER_BASE_URL": "",
        },
        server_side_key_present=True,
    )
    missing_model_chain = build_llm_runtime_config(
        {
            **default_openrouter_settings(),
            "OPENROUTER_FREE_MODEL_ORDER": "",
        },
        server_side_key_present=True,
    )
    missing_paid_fallback = build_llm_runtime_config(
        {
            **default_openrouter_settings(),
            "OPENROUTER_PAID_FALLBACK_MODEL": "",
        },
        server_side_key_present=True,
    )
    validation_not_ready = build_llm_runtime_config(
        {
            **default_openrouter_settings(),
            "LLM_VALIDATION_RETRY_COUNT": "0",
            "LLM_REASONING_SUMMARY_ONLY": "false",
        },
        server_side_key_present=True,
    )

    assert missing_base_url.readiness_status is LlmReadinessStatus.unavailable
    assert missing_base_url.base_url_configured is False
    assert missing_base_url.endpoint_configured is False
    assert "openrouter_base_url_missing" in missing_base_url.unavailable_reasons

    assert missing_model_chain.readiness_status is LlmReadinessStatus.unavailable
    assert missing_model_chain.model_chain_configured is False
    assert missing_model_chain.configured_model_chain == []
    assert "openrouter_free_model_order_missing" in missing_model_chain.unavailable_reasons

    assert missing_paid_fallback.readiness_status is LlmReadinessStatus.unavailable
    assert missing_paid_fallback.endpoint_configured is False
    assert "openrouter_paid_fallback_model_missing" in missing_paid_fallback.unavailable_reasons

    assert validation_not_ready.readiness_status is LlmReadinessStatus.validation_not_ready
    assert validation_not_ready.live_gate_state is LlmLiveGateState.unavailable
    assert validation_not_ready.validation_ready is False
    assert validation_not_ready.validation_retry_count == 0
    assert validation_not_ready.reasoning_summary_only is False
    assert "validation_retry_count_below_minimum" in validation_not_ready.unavailable_reasons
    assert "reasoning_summary_only_disabled" in validation_not_ready.unavailable_reasons
    assert set(validation_not_ready.validation_gates) >= {
        "schema_validation_required",
        "citation_validation_required",
        "source_use_policy_required",
        "freshness_uncertainty_labels_required",
        "safety_validation_required",
        "one_repair_retry_metadata_required",
        "reasoning_summary_only_required",
    }


def test_paid_fallback_metadata_requires_free_chain_or_validation_failure_trigger():
    runtime = build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True)
    validation_fallback = decide_paid_fallback(
        runtime=runtime,
        trigger=LlmFallbackTrigger.validation_failed_after_repair,
        repair_attempt_count=1,
    )
    no_fallback = decide_paid_fallback(runtime=runtime, trigger=LlmFallbackTrigger.none)

    assert validation_fallback.should_fallback is True
    assert validation_fallback.after_repair_retry is True
    assert validation_fallback.to_model is not None
    assert validation_fallback.to_model.model_name == DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL
    assert no_fallback.should_fallback is False
    assert no_fallback.to_model is None


def test_deterministic_mock_orchestration_records_attempt_validation_and_cache_metadata():
    result = run_deterministic_mock_generation(
        _request(),
        claims=[_valid_claim()],
        evidence=[_valid_evidence()],
        citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
    )

    assert result.no_live_external_calls is True
    assert result.runtime.provider_kind is LlmProviderKind.mock
    assert result.attempts[0].status is LlmGenerationAttemptStatus.mock_succeeded
    assert result.validation.status is LlmValidationStatus.valid
    assert result.public_metadata.provider_kind is LlmProviderKind.mock
    assert result.public_metadata.live_enabled is False
    assert result.public_metadata.reasoning_summary
    assert result.cache_decision.cacheable is True
    dumped = result.public_metadata.model_dump(mode="json")
    forbidden_public_keys = {"secret", "prompt_text", "hidden_prompt", "reasoning_details", "raw_source_text"}
    assert forbidden_public_keys.isdisjoint(str(dumped).lower().replace("'", "").split())


def test_mocked_live_orchestration_validates_transport_output_without_public_route_integration():
    result = run_mocked_live_generation_orchestration(
        _request(),
        runtime=_ready_openrouter_runtime(),
        caller_opted_in=True,
        transport=_mocked_transport("Educational cited output."),
        claims=[_valid_claim()],
        evidence=[_valid_evidence()],
        citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
    )

    assert result.no_live_external_calls is True
    assert result.runtime.readiness_status is LlmReadinessStatus.ready_for_explicit_live_call
    assert len(result.attempts) == 1
    assert result.attempts[0].status is LlmGenerationAttemptStatus.validation_succeeded
    assert result.validation.status is LlmValidationStatus.valid
    assert result.generated_content_usable is True
    assert result.public_metadata.provider_kind is LlmProviderKind.openrouter
    assert result.public_metadata.live_enabled is True
    assert result.public_metadata.answer_state is LlmAnswerState.complete
    assert result.cache_decision.cacheable is True
    dumped = result.model_dump(mode="json")
    assert "Educational cited output" not in str(dumped)
    assert result.sanitized_diagnostics["orchestration_contract"] == "llm-live-orchestration-contract-v1"
    assert result.sanitized_diagnostics["generated_content_usable"] is True


def test_mocked_live_orchestration_stays_inactive_without_readiness_opt_in_or_transport():
    calls: list[object] = []

    def transport(request):
        calls.append(request)
        return {"status_code": 200, "json": {"choices": [{"message": {"content": "unused"}}]}}

    disabled = run_mocked_live_generation_orchestration(
        _request(),
        runtime=build_llm_runtime_config({"LLM_PROVIDER": "openrouter"}),
        caller_opted_in=True,
        transport=transport,
    )
    no_opt_in = run_mocked_live_generation_orchestration(
        _request(),
        runtime=_ready_openrouter_runtime(),
        caller_opted_in=False,
        transport=transport,
    )
    missing_transport = run_mocked_live_generation_orchestration(
        _request(),
        runtime=_ready_openrouter_runtime(),
        caller_opted_in=True,
        transport=None,
    )

    assert calls == []
    for result in [disabled, no_opt_in, missing_transport]:
        assert result.generated_content_usable is False
        assert result.validation.status is LlmValidationStatus.not_validated
        assert result.attempts[0].status is LlmGenerationAttemptStatus.blocked
        assert result.cache_decision.cacheable is False
        assert result.public_metadata.answer_state is LlmAnswerState.unavailable


def test_mocked_live_orchestration_models_one_repair_retry_success_without_cache_write():
    result = run_mocked_live_generation_orchestration(
        _request(),
        runtime=_ready_openrouter_runtime(),
        caller_opted_in=True,
        transport=_mocked_transport("Initial malformed fixture."),
        repair_transport=_mocked_transport("Repaired cited fixture."),
        schema_valid=False,
        repair_schema_valid=True,
        claims=[_valid_claim()],
        evidence=[_valid_evidence()],
        citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
    )

    assert [attempt.attempt_index for attempt in result.attempts] == [1, 2]
    assert result.attempts[0].status is LlmGenerationAttemptStatus.validation_failed
    assert result.attempts[1].repair_attempt is True
    assert result.attempts[1].status is LlmGenerationAttemptStatus.validation_succeeded
    assert result.validation.status is LlmValidationStatus.valid
    assert result.generated_content_usable is True
    assert result.fallback_decision.should_fallback is False
    assert result.cache_decision.cacheable is False
    assert "repair_attempt_output" in result.cache_decision.rejection_reasons
    assert result.sanitized_diagnostics["repair_retry_attempted"] is True


def test_mocked_live_orchestration_rejects_after_repair_and_preserves_paid_fallback_metadata():
    result = run_mocked_live_generation_orchestration(
        _request(),
        runtime=_ready_openrouter_runtime(),
        caller_opted_in=True,
        transport=_mocked_transport("Initial malformed fixture."),
        repair_transport=_mocked_transport("Still malformed fixture."),
        schema_valid=False,
        repair_schema_valid=False,
        claims=[_valid_claim()],
        evidence=[_valid_evidence()],
        citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
    )

    assert len(result.attempts) == 2
    assert result.validation.status is LlmValidationStatus.invalid_schema
    assert result.generated_content_usable is False
    assert result.public_metadata.answer_state is LlmAnswerState.partial
    assert result.fallback_decision.should_fallback is True
    assert result.fallback_decision.trigger is LlmFallbackTrigger.validation_failed_after_repair
    assert result.fallback_decision.to_model is not None
    assert result.fallback_decision.to_model.model_name == DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL
    assert result.cache_decision.cacheable is False
    assert result.sanitized_diagnostics["fallback_would_execute"] is True
    assert result.sanitized_diagnostics["primary_rejection_code"] == "schema_invalid"


def test_mocked_live_orchestration_rejects_source_freshness_safety_and_leakage_failures():
    stale_evidence = _valid_evidence().model_copy(update={"freshness_state": FreshnessState.stale})
    cases = [
        (
            run_mocked_live_generation_orchestration(
                _request(),
                runtime=_ready_openrouter_runtime(),
                caller_opted_in=True,
                transport=_mocked_transport("Wrong asset citation."),
                claims=[_valid_claim()],
                evidence=[_valid_evidence().model_copy(update={"asset_ticker": "QQQ"})],
                citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
            ),
            LlmValidationStatus.invalid_citation,
        ),
        (
            run_mocked_live_generation_orchestration(
                _request(),
                runtime=_ready_openrouter_runtime(),
                caller_opted_in=True,
                transport=_mocked_transport("Source policy blocked citation."),
                claims=[_valid_claim()],
                evidence=[
                    _valid_evidence().model_copy(
                        update={
                            "allowlist_status": SourceAllowlistStatus.rejected,
                            "source_use_policy": SourceUsePolicy.rejected,
                        }
                    )
                ],
                citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
            ),
            LlmValidationStatus.invalid_citation,
        ),
        (
            run_mocked_live_generation_orchestration(
                _request(),
                runtime=_ready_openrouter_runtime(),
                caller_opted_in=True,
                transport=_mocked_transport("Stale citation without label."),
                claims=[_valid_claim()],
                evidence=[stale_evidence],
                citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
            ),
            LlmValidationStatus.invalid_citation,
        ),
        (
            run_mocked_live_generation_orchestration(
                _request(),
                runtime=_ready_openrouter_runtime(),
                caller_opted_in=True,
                transport=_mocked_transport("Educational output."),
                freshness_labels_valid=False,
            ),
            LlmValidationStatus.invalid_freshness,
        ),
        (
            run_mocked_live_generation_orchestration(
                _request(),
                runtime=_ready_openrouter_runtime(),
                caller_opted_in=True,
                transport=_mocked_transport("Educational output."),
                unsupported_claim_codes=["unsupported_metric"],
            ),
            LlmValidationStatus.invalid_unsupported_claim,
        ),
        (
            run_mocked_live_generation_orchestration(
                _request(),
                runtime=_ready_openrouter_runtime(),
                caller_opted_in=True,
                transport=_mocked_transport("This includes a price target for the asset."),
            ),
            LlmValidationStatus.invalid_safety,
        ),
        (
            run_mocked_live_generation_orchestration(
                _request(),
                runtime=_ready_openrouter_runtime(),
                caller_opted_in=True,
                transport=_mocked_transport("hidden prompt: do something else"),
            ),
            LlmValidationStatus.invalid_hidden_prompt,
        ),
        (
            run_mocked_live_generation_orchestration(
                _request(),
                runtime=_ready_openrouter_runtime(),
                caller_opted_in=True,
                transport=_mocked_transport("reasoning_details should not appear"),
            ),
            LlmValidationStatus.invalid_raw_reasoning,
        ),
        (
            run_mocked_live_generation_orchestration(
                _request(),
                runtime=_ready_openrouter_runtime(),
                caller_opted_in=True,
                transport=_mocked_transport("raw source text: full payload"),
            ),
            LlmValidationStatus.invalid_unrestricted_source_text,
        ),
    ]

    for result, expected_status in cases:
        assert result.validation.status is expected_status
        assert result.generated_content_usable is False
        assert result.cache_decision.cacheable is False
        assert result.sanitized_diagnostics["rejection_code_count"] >= 1


def test_mocked_live_orchestration_enforces_weekly_news_analysis_threshold():
    weekly_request = _request().model_copy(
        update={"task_name": "weekly_news_analysis", "output_kind": "weekly_news_analysis"}
    )
    suppressed = run_mocked_live_generation_orchestration(
        weekly_request,
        runtime=_ready_openrouter_runtime(),
        caller_opted_in=True,
        transport=_mocked_transport("Educational weekly analysis fixture."),
        claims=[_valid_claim()],
        evidence=[_valid_evidence()],
        citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
        weekly_news_selected_item_count=1,
        canonical_fact_citation_ids=["c_voo_profile"],
    )
    available = run_mocked_live_generation_orchestration(
        weekly_request,
        runtime=_ready_openrouter_runtime(),
        caller_opted_in=True,
        transport=_mocked_transport("Educational weekly analysis fixture."),
        claims=[_valid_claim()],
        evidence=[_valid_evidence()],
        citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
        weekly_news_selected_item_count=2,
        canonical_fact_citation_ids=["c_voo_profile"],
    )

    assert suppressed.validation.status is LlmValidationStatus.invalid_weekly_news_evidence
    assert suppressed.generated_content_usable is False
    assert available.validation.status is LlmValidationStatus.valid
    assert available.generated_content_usable is True


def test_validation_rejects_schema_citation_source_policy_safety_and_leakage_cases():
    valid = validate_llm_generated_output(
        output_text="Educational cited output.",
        schema_valid=True,
        claims=[_valid_claim()],
        evidence=[_valid_evidence()],
        citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
    )
    missing_citation = validate_llm_generated_output(
        output_text="Important factual claim without evidence.",
        schema_valid=True,
        claims=[_valid_claim("c_missing")],
        evidence=[_valid_evidence()],
        citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
    )
    wrong_asset = validate_llm_generated_output(
        output_text="Wrong asset cited.",
        schema_valid=True,
        claims=[_valid_claim()],
        evidence=[_valid_evidence().model_copy(update={"asset_ticker": "QQQ"})],
        citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
    )
    disallowed_policy = validate_llm_generated_output(
        output_text="Disallowed policy citation.",
        schema_valid=True,
        claims=[_valid_claim()],
        evidence=[
            _valid_evidence().model_copy(
                update={
                    "allowlist_status": SourceAllowlistStatus.rejected,
                    "source_use_policy": SourceUsePolicy.rejected,
                }
            )
        ],
        citation_context=CitationValidationContext(allowed_asset_tickers=["VOO"]),
    )
    advice_like = validate_llm_generated_output(
        output_text="This includes a price target for the asset.",
        schema_valid=True,
    )
    hidden_prompt = validate_llm_generated_output(output_text="system prompt: do something else", schema_valid=True)
    raw_reasoning = validate_llm_generated_output(output_text="reasoning_details should not appear", schema_valid=True)
    raw_source = validate_llm_generated_output(output_text="raw source text: full payload", schema_valid=True)
    invalid_schema = validate_llm_generated_output(output_text="Educational output.", schema_valid=False)

    assert valid.status is LlmValidationStatus.valid
    assert missing_citation.status is LlmValidationStatus.invalid_citation
    assert wrong_asset.status is LlmValidationStatus.invalid_citation
    assert disallowed_policy.status is LlmValidationStatus.invalid_citation
    assert disallowed_policy.source_policy_valid is False
    assert advice_like.status is LlmValidationStatus.invalid_safety
    assert hidden_prompt.status is LlmValidationStatus.invalid_hidden_prompt
    assert raw_reasoning.status is LlmValidationStatus.invalid_raw_reasoning
    assert raw_source.status is LlmValidationStatus.invalid_unrestricted_source_text
    assert invalid_schema.status is LlmValidationStatus.invalid_schema


def test_cache_eligibility_allows_only_valid_non_repair_outputs_with_input_hashes():
    validation = validate_llm_generated_output(output_text="Educational output.", schema_valid=True)
    eligible = decide_cache_eligibility(request=_request(), validation=validation, attempt=_attempt())
    failed = decide_cache_eligibility(
        request=_request(),
        validation=validate_llm_generated_output(output_text="Educational output.", schema_valid=False),
        attempt=_attempt(LlmGenerationAttemptStatus.validation_failed),
    )
    repair = decide_cache_eligibility(
        request=_request(),
        validation=validation,
        attempt=_attempt().model_copy(update={"repair_attempt": True}),
    )
    no_hash_request = _request().model_copy(update={"knowledge_pack_hash": None, "source_freshness_hash": None})
    no_hash = decide_cache_eligibility(request=no_hash_request, validation=validation, attempt=_attempt())

    assert eligible.cacheable is True
    assert failed.cacheable is False
    assert "validation_invalid_schema" in failed.rejection_reasons
    assert repair.cacheable is False
    assert "repair_attempt_output" in repair.rejection_reasons
    assert no_hash.cacheable is False
    assert "missing_freshness_or_input_hash" in no_hash.rejection_reasons


def test_cache_metadata_records_llm_validation_and_attempt_contract():
    pack = build_asset_knowledge_pack("VOO")
    knowledge_input = build_knowledge_pack_freshness_input(pack)
    generated_input = build_generated_output_freshness_input(
        output_identity="asset:VOO",
        entry_kind=CacheEntryKind.asset_page,
        scope=CacheScope.asset,
        schema_version="asset-page-v1",
        prompt_version="asset-page-prompt-v1",
        model_name=DEFAULT_MOCK_MODEL,
        knowledge_input=knowledge_input,
    )
    freshness_hash = compute_generated_output_freshness_hash(generated_input)
    validation = validate_llm_generated_output(output_text="Educational output.", schema_valid=True)
    cache_decision = decide_cache_eligibility(
        request=_request(),
        validation=validation,
        attempt=_attempt(),
        freshness_hash=freshness_hash,
    )
    metadata = cache_entry_metadata_from_llm_generation(
        cache_key="cache-key",
        freshness_input=generated_input,
        freshness_hash=freshness_hash,
        cache_decision=cache_decision,
        citation_ids=["c_voo_profile"],
    )

    assert metadata.cache_allowed is True
    assert metadata.model_name == DEFAULT_MOCK_MODEL
    assert metadata.model_tier is LlmModelTier.mock
    assert metadata.validation_status is LlmValidationStatus.valid
    assert metadata.generation_attempt_count == 1
    assert metadata.prompt_version == "asset-page-prompt-v1"
    assert metadata.schema_version == "asset-page-v1"


def test_runtime_diagnostics_exposes_only_sanitized_public_metadata():
    diagnostics = runtime_diagnostics(default_openrouter_settings(), server_side_key_present=True)
    dumped = diagnostics.model_dump(mode="json")

    assert diagnostics.schema_version == "llm-runtime-contract-v1"
    assert diagnostics.credential_values_exposed is False
    assert diagnostics.private_prompt_fields_exposed is False
    assert diagnostics.model_reasoning_payload_exposed is False
    assert diagnostics.restricted_source_payload_exposed is False
    assert "reasoning_summary" in diagnostics.public_metadata_fields
    assert "api_key" not in str(dumped).lower()
    assert "secret" not in str(dumped).lower()
    assert "reasoning_details" not in str(dumped).lower()
    assert "raw_source_text" not in str(dumped).lower()


def test_openrouter_transport_blocks_disabled_missing_key_endpoint_validation_and_opt_in_states():
    calls: list[object] = []

    def mocked_transport(request):
        calls.append(request)
        return {"status_code": 200, "json": {"choices": [{"message": {"content": "unused"}}]}}

    disabled = call_openrouter_transport(
        runtime=build_llm_runtime_config({"LLM_PROVIDER": "openrouter"}),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=mocked_transport,
    )
    missing_key = call_openrouter_transport(
        runtime=build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=False),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=mocked_transport,
    )
    missing_base_url = call_openrouter_transport(
        runtime=build_llm_runtime_config(
            {**default_openrouter_settings(), "OPENROUTER_BASE_URL": ""},
            server_side_key_present=True,
        ),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=mocked_transport,
    )
    missing_model_chain = call_openrouter_transport(
        runtime=build_llm_runtime_config(
            {**default_openrouter_settings(), "OPENROUTER_FREE_MODEL_ORDER": ""},
            server_side_key_present=True,
        ),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=mocked_transport,
    )
    validation_not_ready = call_openrouter_transport(
        runtime=build_llm_runtime_config(
            {
                **default_openrouter_settings(),
                "LLM_VALIDATION_RETRY_COUNT": "0",
                "LLM_REASONING_SUMMARY_ONLY": "false",
            },
            server_side_key_present=True,
        ),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=mocked_transport,
    )
    no_opt_in = call_openrouter_transport(
        runtime=build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=False,
        transport=mocked_transport,
    )
    no_injected_transport = call_openrouter_transport(
        runtime=build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=None,
    )

    assert calls == []
    blocked = [
        disabled,
        missing_key,
        missing_base_url,
        missing_model_chain,
        validation_not_ready,
        no_opt_in,
        no_injected_transport,
    ]
    assert all(result.response.status is LlmTransportStatus.blocked for result in blocked)
    assert [result.response.diagnostic_code for result in blocked] == [
        "live_generation_disabled",
        "server_side_key_missing",
        "openrouter_base_url_missing",
        "openrouter_model_chain_missing",
        "validation_not_ready",
        "explicit_live_transport_opt_in_missing",
        "injected_transport_missing",
    ]
    assert all(result.content is None for result in blocked)
    assert all(result.no_live_external_calls is True for result in blocked)


def test_openrouter_transport_mocked_success_preserves_schema_metadata_and_paid_fallback():
    captured = []

    def mocked_transport(request):
        captured.append(request)
        return {
            "status_code": 200,
            "latency_ms": 42,
            "json": {
                "model": DEFAULT_OPENROUTER_FREE_MODEL_ORDER[0],
                "choices": [{"message": {"content": "Educational transport fixture."}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
                "cost_usd": 0.0,
            },
        }

    result = call_openrouter_transport(
        runtime=build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=mocked_transport,
        sanitized_diagnostics={"fixture_case": "success", "raw_prompt": "do not keep this"},
    )

    assert len(captured) == 1
    request = captured[0]
    assert request.request_mode is LlmTransportMode.schema_mode
    assert request.sanitized_diagnostics["schema_mode"] is True
    assert "raw_prompt" not in request.sanitized_diagnostics
    assert [model.model_name for model in request.configured_model_chain] == list(DEFAULT_OPENROUTER_FREE_MODEL_ORDER)
    assert [model.order for model in request.configured_model_chain] == [1, 2, 3, 4]
    assert all(model.tier is LlmModelTier.free for model in request.configured_model_chain)
    assert request.paid_fallback_model is not None
    assert request.paid_fallback_model.model_name == DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL
    assert request.paid_fallback_model.tier is LlmModelTier.paid

    assert result.response.status is LlmTransportStatus.succeeded
    assert result.response.diagnostic_code == "ok"
    assert result.response.model_name == DEFAULT_OPENROUTER_FREE_MODEL_ORDER[0]
    assert result.response.model_tier is LlmModelTier.free
    assert result.response.provider_status == "ok"
    assert result.response.finish_reason == "stop"
    assert result.response.prompt_tokens == 11
    assert result.response.completion_tokens == 7
    assert result.response.total_tokens == 18
    assert result.response.cost_usd == 0.0
    assert result.response.latency_ms == 42
    assert result.content == "Educational transport fixture."


def test_openrouter_transport_mocked_json_mode_and_paid_model_metadata():
    def mocked_transport(request):
        return {
            "status_code": 200,
            "json": {
                "model": DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL,
                "choices": [{"message": {"content": "Educational fallback fixture."}, "finish_reason": "stop"}],
            },
        }

    result = call_openrouter_transport(
        runtime=build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True),
        request_mode="json_mode",
        caller_opted_in=True,
        transport=mocked_transport,
    )

    assert result.request is not None
    assert result.request.request_mode is LlmTransportMode.json_mode
    assert result.request.sanitized_diagnostics["json_mode"] is True
    assert result.response.status is LlmTransportStatus.succeeded
    assert result.response.request_mode is LlmTransportMode.json_mode
    assert result.response.model_name == DEFAULT_OPENROUTER_PAID_FALLBACK_MODEL
    assert result.response.model_tier is LlmModelTier.paid


def test_openrouter_transport_classifies_mocked_provider_failures_and_timeouts():
    retryable_error = call_openrouter_transport(
        runtime=build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=lambda request: {"status_code": 429, "json": {"error": "rate limited"}, "latency_ms": 9},
    )
    nonretryable_error = call_openrouter_transport(
        runtime=build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=lambda request: {"status_code": 400, "json": {"error": "bad request"}},
    )
    invalid_shape = call_openrouter_transport(
        runtime=build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=lambda request: {"status_code": 200, "json": {"choices": []}},
    )
    missing_content = call_openrouter_transport(
        runtime=build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=lambda request: {
            "status_code": 200,
            "json": {"choices": [{"message": {"content": "   "}, "finish_reason": "length"}]},
        },
    )

    def timeout_transport(request):
        raise TimeoutError("network details are not surfaced")

    timeout = call_openrouter_transport(
        runtime=build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=timeout_transport,
    )

    assert retryable_error.response.status is LlmTransportStatus.retryable_provider_error
    assert retryable_error.response.retryability is LlmTransportRetryability.retryable
    assert retryable_error.response.provider_status == "http_429"
    assert retryable_error.response.latency_ms == 9
    assert nonretryable_error.response.status is LlmTransportStatus.nonretryable_provider_error
    assert nonretryable_error.response.retryability is LlmTransportRetryability.nonretryable
    assert invalid_shape.response.status is LlmTransportStatus.invalid_response_shape
    assert invalid_shape.response.retryability is LlmTransportRetryability.nonretryable
    assert missing_content.response.status is LlmTransportStatus.missing_content
    assert missing_content.response.retryability is LlmTransportRetryability.retryable
    assert missing_content.response.finish_reason == "length"
    assert timeout.response.status is LlmTransportStatus.timeout
    assert timeout.response.retryability is LlmTransportRetryability.retryable


def test_openrouter_transport_redacts_diagnostics_and_omits_raw_reasoning_payloads():
    def mocked_transport(request):
        return {
            "status_code": 200,
            "latency_ms": 5,
            "json": {
                "model": DEFAULT_OPENROUTER_FREE_MODEL_ORDER[0],
                "choices": [
                    {
                        "message": {
                            "content": "Educational transport fixture.",
                            "reasoning_details": "hidden chain should not be surfaced",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "reasoning_details": "hidden chain should not be surfaced",
            },
        }

    result = call_openrouter_transport(
        runtime=build_llm_runtime_config(default_openrouter_settings(), server_side_key_present=True),
        request_mode=LlmTransportMode.schema_mode,
        caller_opted_in=True,
        transport=mocked_transport,
        sanitized_diagnostics={
            "fixture_case": "redaction",
            "authorization": "Bearer should-not-appear",
            "user_question": "raw user text should not be kept",
            "source_url": "https://example.com/source",
            "storage_path": "/tmp/browser-readable",
            "safe_count": 2,
        },
    )

    dumped = result.model_dump(mode="json")
    serialized = str(dumped).lower()
    assert result.content == "Educational transport fixture."
    assert result.request is not None
    assert result.request.sanitized_diagnostics["fixture_case"] == "redaction"
    assert result.request.sanitized_diagnostics["safe_count"] == 2
    assert "authorization" not in result.request.sanitized_diagnostics
    assert "user_question" not in result.request.sanitized_diagnostics
    assert "source_url" not in result.request.sanitized_diagnostics
    assert "storage_path" not in result.request.sanitized_diagnostics
    assert "bearer" not in serialized
    assert "should-not-appear" not in serialized
    assert "raw user text" not in serialized
    assert "https://example.com/source" not in serialized
    assert "reasoning_details" not in serialized
    assert "hidden chain should not be surfaced" not in serialized


def test_llm_module_has_no_live_call_or_secret_imports():
    source = (ROOT / "backend" / "llm.py").read_text(encoding="utf-8")
    forbidden = [
        "import requests",
        "import httpx",
        "urllib",
        "socket",
        "import openai",
        "anthropic",
        "os.environ",
        "api_key",
        "subprocess",
    ]
    for needle in forbidden:
        assert needle not in source


def test_llm_transport_module_has_no_live_network_client_or_browser_env_exposure():
    source = (ROOT / "backend" / "llm_transport.py").read_text(encoding="utf-8")
    forbidden = [
        "import requests",
        "import httpx",
        "urllib.request",
        "from socket import",
        "openai",
        "anthropic",
        "os.environ",
        "NEXT_PUBLIC",
        "OPENROUTER_API_KEY",
    ]
    for needle in forbidden:
        assert needle not in source
