from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

import pytest

import pneuma_lab.resampling_null.prefix_index as prefix_index_module
from pneuma_lab.resampling_null import run_prefix, seal_prefix_index
from pneuma_lab.resampling_null.artifacts import validate_record
from pneuma_lab.resampling_null.evidence import (
    FrozenPrefixReceipt,
    load_controller_provider_cost_closure,
    load_controller_provider_event,
    load_controller_provider_settlement,
    load_provider_attempt,
    load_provider_attempt_ledger,
    load_provider_dispatch_intent,
    load_tool_boundary_ledger,
)
from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.prefix_contracts import (
    CONTROLLER_ROLE_MEDIA,
    RawProviderCompletionKind,
    SyntheticClockRead,
    load_synthetic_prefix_program,
)
from pneuma_lab.resampling_null.synthetic_prefix_loop import (
    _open_prefix_loop,
)
from pneuma_lab.resampling_null.types import (
    ArtifactRef,
    CallSeedReceipt,
    FrozenVerifierReceipt,
    GradeReceipt,
    TriggerReason,
)
from tests.resampling_null.provider_authority_fixture import (
    ProviderAuthorityFixture,
)
from tests.resampling_null.test_s02c_prefix_loop import _loop_authority


def _completed_candidates(
    tmp_path: Path,
) -> tuple[Path, ProviderAuthorityFixture, tuple[ArtifactRef, ArtifactRef]]:
    run_root = tmp_path / "run"
    fixture = ProviderAuthorityFixture.build(
        run_root,
        executable_sources=True,
        requires_simulator=False,
        simulator_present=False,
    )
    schedule_path = run_root / "prefix-schedule.json"
    schedule = json.loads(schedule_path.read_bytes())
    registry = json.loads((run_root / "sources/tasks.json").read_bytes())
    second = json.loads(json.dumps(schedule["payload"]["tasks"][0]))
    second["task"] = {
        "task_id": registry["tasks"][1]["task_id"],
        "benchmark": registry["tasks"][1]["benchmark"],
        "stratum": registry["tasks"][1]["stratum"],
        "lineage": registry["tasks"][1]["lineage"],
        "sensitivity_groups": registry["tasks"][1]["groups"],
    }
    second["prefix_seed"] = 12
    schedule["payload"]["tasks"].append(second)
    validate_record(schedule)
    schedule_bytes = canonical_json_bytes(schedule, indent=None)
    schedule_path.write_bytes(schedule_bytes)
    fixture = ProviderAuthorityFixture(
        schedule_ref=ArtifactRef(
            role="resampling_prefix_schedule",
            relative_path="prefix-schedule.json",
            sha256=hashlib.sha256(schedule_bytes).hexdigest(),
            byte_count=len(schedule_bytes),
            media_type="application/json",
        ),
        refs=fixture.refs,
    )
    candidates = tuple(
        run_prefix(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            task_id=task_id,
        )
        for task_id in ("task-1", "task-foreign")
    )
    return run_root, fixture, candidates


def _nonempty_execution_graph(
    tmp_path: Path,
) -> prefix_index_module._CandidateGraph:
    authority = _loop_authority(tmp_path)
    opened = _open_prefix_loop(run_root=tmp_path, authority=authority)

    def payload(ref: ArtifactRef) -> bytes:
        return (tmp_path / ref.relative_path).read_bytes()

    def controller_ref(role: str, salt: str) -> ArtifactRef:
        digest = hashlib.sha256(f"{role}:{salt}".encode()).hexdigest()
        return ArtifactRef(
            role,
            f"controller-artifacts/{role}/{digest}",
            digest,
            1,
            CONTROLLER_ROLE_MEDIA[role],
        )

    snapshot_ref = controller_ref("composite_snapshot", "snapshot")
    visible_ref = controller_ref("visible_context", "visible")
    token_ref = controller_ref("token_ids", "tokens")
    receipt = FrozenPrefixReceipt(
        task_id=authority.task_schedule.task.task_id,
        schedule_sha256=authority.schedule_ref.sha256,
        prefix_caps=authority.prefix_caps,
        snapshot_ref=snapshot_ref,
        visible_context_ref=visible_ref,
        visible_sha256=visible_ref.sha256,
        token_ids_ref=token_ref,
        token_ids_sha256=token_ref.sha256,
        branch_pending_calls=opened.branch_pending_calls,
        terminal_unexecuted_remainder=opened.terminal_unexecuted_remainder,
        trigger_reason=opened.trigger_reason,
        terminal_failure_kind=opened.failure_kind,
        y0_grade=GradeReceipt(
            0,
            0.0,
            False,
            controller_ref("grade_evidence", "grade"),
        ),
        grade_execution_receipt_ref=controller_ref(
            "grade_evidence_receipt",
            "grade-receipt",
        ),
        verifier_receipt=FrozenVerifierReceipt(
            authority.task_schedule.task.task_id,
            authority.schedule_ref.sha256,
            snapshot_ref,
            controller_ref("verifier_evidence", "verifier"),
            0,
        ),
        verifier_execution_receipt_ref=controller_ref(
            "verifier_evidence_receipt",
            "verifier-receipt",
        ),
        counters=opened.primary_counters,
        simulator_counters=opened.simulator_counters,
        call_seeds=tuple(
            CallSeedReceipt(intent.subject_role, intent.call_index, intent.seed)
            for intent in opened.intents
        ),
        provider_attempts_ref=opened.provider_attempts_ref,
        boundary_ledger_ref=opened.boundary_ledger_ref,
        provider_cost_ref=opened.provider_cost_ref,
    )
    ledger = load_provider_attempt_ledger(payload(opened.provider_attempts_ref))
    cost = load_controller_provider_cost_closure(payload(opened.provider_cost_ref))
    tool_ledger = load_tool_boundary_ledger(payload(opened.boundary_ledger_ref))
    intents = {
        ref: load_provider_dispatch_intent(payload(ref))
        for ref in ledger.ledger.intent_refs
    }
    attempts = {ref: load_provider_attempt(payload(ref)) for ref in ledger.attempt_refs}
    events = {
        attempt.provider_event_ref: load_controller_provider_event(
            payload(attempt.provider_event_ref)
        )
        for attempt in attempts.values()
    }
    settlements = {
        ref: load_controller_provider_settlement(payload(ref))
        for ref in cost.settlement_refs
    }
    payloads = dict(opened._payloads)
    reachable_controller_refs = {
        receipt.provider_attempts_ref,
        receipt.provider_cost_ref,
        receipt.boundary_ledger_ref,
        *ledger.ledger.intent_refs,
        *ledger.attempt_refs,
        *events,
        *cost.settlement_refs,
        *(boundary.tool_call_ref for boundary in tool_ledger.boundaries),
        *(boundary.tool_result_ref for boundary in tool_ledger.boundaries),
    }
    payloads.update({ref: payload(ref) for ref in reachable_controller_refs})
    graph = prefix_index_module._CandidateGraph(
        receipt=receipt,
        authority=authority,
        program=opened._program,
        program_bytes=opened._program_bytes,
        payloads=payloads,
        snapshot=None,  # type: ignore[arg-type]
        initial_restore=None,  # type: ignore[arg-type]
        grade_restore=None,  # type: ignore[arg-type]
        verifier_restore=None,  # type: ignore[arg-type]
        grade_execution=None,  # type: ignore[arg-type]
        verifier_execution=None,  # type: ignore[arg-type]
        provider_ledger=ledger,
        cost_record=cost,
        tool_ledger=tool_ledger,
        intents=intents,
        attempts=attempts,
        events=events,
        settlements=settlements,
        subject_attestations=(),
        simulator_attestations=(),
        runtime_attestations=(),
        container_attestations=(),
    )
    opened.close()
    return graph


@pytest.mark.parametrize(
    "tamper",
    [
        "completion_claim",
        "raw_transport",
        "clock_elapsed",
        "tool_clock_elapsed",
        "intent_deadline",
        "typed_queue",
        "per_call_cap",
        "per_call_turns",
        "aggregate_tokens",
        "aggregate_models",
        "aggregate_turns",
        "branch_pending",
        "terminal_remainder",
    ],
)
def test_s02d_replays_execution_semantics_from_raw_evidence(
    tmp_path: Path,
    tamper: str,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    if tamper == "completion_claim":
        graph.program = replace(
            graph.program,
            provider_transcript=(
                replace(
                    row,
                    completion_kind=RawProviderCompletionKind.REFUSAL,
                ),
            ),
        )
    elif tamper == "raw_transport":
        raw_event = json.loads(graph.payloads[row.provider_event_ref])
        raw_event["transport_kind"] = "provider_error"
        graph.payloads[row.provider_event_ref] = canonical_json_bytes(
            raw_event,
            indent=None,
        )
    elif tamper == "clock_elapsed":
        graph.program = replace(
            graph.program,
            clock_trace=tuple(
                replace(read, uint64_ms=read.uint64_ms + 1)
                if read.label == "after_primary_subject_0"
                else read
                for read in graph.program.clock_trace
            ),
        )
    elif tamper == "tool_clock_elapsed":
        graph.program = replace(
            graph.program,
            clock_trace=tuple(
                replace(read, uint64_ms=read.uint64_ms + 1)
                if read.label == "after_tool_call-1"
                else read
                for read in graph.program.clock_trace
            ),
        )
    elif tamper == "intent_deadline":
        intent_ref = graph.provider_ledger.ledger.intent_refs[0]
        intent = replace(
            graph.provider_ledger.ledger.intents[0],
            absolute_deadline_ms=(
                graph.provider_ledger.ledger.intents[0].absolute_deadline_ms + 1
            ),
        )
        graph.provider_ledger = replace(
            graph.provider_ledger,
            ledger=replace(
                graph.provider_ledger.ledger,
                intents=(intent,),
            ),
        )
        graph.intents[intent_ref] = intent
    elif tamper == "typed_queue":
        assert row.typed_turn is not None
        calls = row.typed_turn.tool_calls
        graph.program = replace(
            graph.program,
            provider_transcript=(
                replace(
                    row,
                    typed_turn=replace(
                        row.typed_turn,
                        tool_calls=(calls[1], calls[0], *calls[2:]),
                    ),
                ),
            ),
        )
    elif tamper == "per_call_cap":
        graph.authority = replace(
            graph.authority,
            subject_contract_caps=replace(
                graph.authority.subject_contract_caps,
                per_call_generated_tokens=0,
            ),
        )
    elif tamper == "per_call_turns":
        graph.authority = replace(
            graph.authority,
            subject_contract_caps=replace(
                graph.authority.subject_contract_caps,
                per_call_turns=0,
            ),
        )
    elif tamper == "aggregate_tokens":
        graph.authority = replace(
            graph.authority,
            subject_contract_caps=replace(
                graph.authority.subject_contract_caps,
                aggregate_generated_tokens=0,
            ),
        )
    elif tamper == "aggregate_models":
        graph.authority = replace(
            graph.authority,
            subject_contract_caps=replace(
                graph.authority.subject_contract_caps,
                aggregate_model_calls=0,
            ),
        )
    elif tamper == "aggregate_turns":
        graph.authority = replace(
            graph.authority,
            subject_contract_caps=replace(
                graph.authority.subject_contract_caps,
                aggregate_turns=0,
            ),
        )
    elif tamper == "branch_pending":
        graph.receipt = replace(
            graph.receipt,
            branch_pending_calls=(row.typed_turn.tool_calls[0],),  # type: ignore[union-attr]
        )
    else:
        graph.receipt = replace(
            graph.receipt,
            trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
            terminal_failure_kind=prefix_index_module.FailureKind.MODEL,
            terminal_unexecuted_remainder=(
                row.typed_turn.tool_calls[0],  # type: ignore[union-attr]
            ),
        )

    with pytest.raises(ValueError):
        prefix_index_module._assert_execution_semantics(graph)


@pytest.mark.parametrize("overshoot", ["wall_before_mutation", "token_before_mutation"])
def test_s02d_replays_terminal_precedence_before_mutation_trigger(
    tmp_path: Path,
    overshoot: str,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    first = graph.tool_ledger.boundaries[0]
    graph.tool_ledger = replace(
        graph.tool_ledger,
        boundaries=(
            replace(
                first,
                mutation_committed=True,
                verifier_eligible_after=True,
                elapsed_ms=(
                    graph.authority.prefix_caps.wall_clock_ms + 1
                    if overshoot == "wall_before_mutation"
                    else first.elapsed_ms
                ),
            ),
        ),
    )
    row = graph.program.provider_transcript[0]
    assert row.typed_turn is not None
    if overshoot == "wall_before_mutation":
        cutoff = graph.authority.prefix_caps.wall_clock_ms + 1
        after_first = False
        shifted = []
        for read in graph.program.clock_trace:
            if read.label == "after_tool_call-1":
                after_first = True
            shifted.append(
                replace(read, uint64_ms=read.uint64_ms + cutoff - 5)
                if after_first
                else read
            )
        graph.program = replace(
            graph.program,
            clock_trace=tuple(shifted),
        )
    else:
        graph.authority = replace(
            graph.authority,
            prefix_caps=replace(
                graph.authority.prefix_caps,
                generated_tokens=row.reported_generated_tokens - 1,
            ),
        )
        graph.tool_ledger = replace(graph.tool_ledger, boundaries=())
    graph.program = replace(
        graph.program,
        expected_trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        tool_observations=(
            replace(
                graph.program.tool_observations[0],
                mutation_committed=True,
                verifier_eligible=True,
            ),
            *graph.program.tool_observations[1:],
        ),
    )
    expected_wall = (
        graph.authority.prefix_caps.wall_clock_ms + 1
        if overshoot == "wall_before_mutation"
        else graph.provider_ledger.ledger.attempts[0].elapsed_ms
    )
    graph.receipt = replace(
        graph.receipt,
        prefix_caps=graph.authority.prefix_caps,
        trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        terminal_failure_kind=(
            prefix_index_module.FailureKind.TIMEOUT
            if overshoot == "wall_before_mutation"
            else prefix_index_module.FailureKind.TOKEN_CAP
        ),
        branch_pending_calls=(),
        terminal_unexecuted_remainder=(
            row.typed_turn.tool_calls[1:]
            if overshoot == "wall_before_mutation"
            else row.typed_turn.tool_calls
        ),
        counters=replace(
            graph.receipt.counters,
            tool_calls=1 if overshoot == "wall_before_mutation" else 0,
            wall_clock_ms=expected_wall,
        ),
        simulator_counters=replace(
            graph.receipt.simulator_counters,
            wall_clock_ms=expected_wall,
        ),
    )

    prefix_index_module._assert_execution_semantics(graph)


def test_s02d_counts_parser_valid_turn_with_noncompleted_transport(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    assert row.typed_turn is not None
    graph.program = replace(
        graph.program,
        provider_transcript=(
            replace(
                row,
                subject_role="user_simulator",
                completion_kind=RawProviderCompletionKind.PROVIDER_ERROR,
                typed_turn=replace(row.typed_turn, tool_calls=()),
            ),
        ),
    )

    assert (
        prefix_index_module._parsed_response_turn_count(
            program=graph.program,
            payloads=graph.payloads,
            subject_role="user_simulator",
        )
        == 1
    )


def test_s02d_rejects_provider_row_after_first_adverse_status(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    first_row = graph.program.provider_transcript[0]
    first_intent = graph.provider_ledger.ledger.intents[0]
    first_attempt = replace(
        graph.provider_ledger.ledger.attempts[0],
        status=prefix_index_module.ProviderAttemptStatus.PROVIDER_ERROR,
    )

    def fresh_controller_ref(role: str, salt: str) -> ArtifactRef:
        digest = hashlib.sha256(f"{role}:{salt}".encode()).hexdigest()
        return ArtifactRef(
            role,
            f"controller-artifacts/{role}/{digest}",
            digest,
            1,
            CONTROLLER_ROLE_MEDIA[role],
        )

    second_intent_ref = fresh_controller_ref(
        "provider_dispatch_intent",
        "second-intent",
    )
    second_attempt_ref = fresh_controller_ref("provider_attempt", "second-attempt")
    second_event_ref = fresh_controller_ref("provider_event", "second-event")
    second_settlement_ref = fresh_controller_ref(
        "provider_settlement",
        "second-settlement",
    )
    second_seed = first_row.seed + 1
    second_row = replace(first_row, call_index=1, seed=second_seed)
    second_intent = replace(first_intent, call_index=1, seed=second_seed)
    second_attempt = replace(
        graph.provider_ledger.ledger.attempts[0],
        dispatch_intent_ref=second_intent_ref,
        call_index=1,
        seed=second_seed,
        provider_event_ref=second_event_ref,
        elapsed_ms=13,
    )
    graph.provider_ledger = replace(
        graph.provider_ledger,
        ledger=replace(
            graph.provider_ledger.ledger,
            intents=(first_intent, second_intent),
            intent_refs=(
                graph.provider_ledger.ledger.intent_refs[0],
                second_intent_ref,
            ),
            attempts=(first_attempt, second_attempt),
        ),
        attempt_refs=(
            graph.provider_ledger.attempt_refs[0],
            second_attempt_ref,
        ),
    )
    first_settlement_ref = graph.cost_record.settlement_refs[0]
    graph.cost_record = replace(
        graph.cost_record,
        attempt_refs=(
            graph.provider_ledger.attempt_refs[0],
            second_attempt_ref,
        ),
        settlement_refs=(first_settlement_ref, second_settlement_ref),
    )
    graph.settlements[second_settlement_ref] = replace(
        graph.settlements[first_settlement_ref],
        call_index=1,
        seed=second_seed,
    )
    raw_event = json.loads(graph.payloads[first_row.provider_event_ref])
    raw_event["transport_kind"] = "provider_error"
    graph.payloads[first_row.provider_event_ref] = canonical_json_bytes(
        raw_event,
        indent=None,
    )
    graph.program = replace(
        graph.program,
        provider_transcript=(
            replace(
                first_row,
                completion_kind=RawProviderCompletionKind.PROVIDER_ERROR,
            ),
            second_row,
        ),
        failure_injection=replace(
            graph.program.failure_injection,
            stage="provider_transport",
            subject_role="primary_subject",
            call_index=0,
        ),
        clock_trace=(
            *graph.program.clock_trace,
            SyntheticClockRead(
                "before_primary_subject_1",
                13,
            ),
            SyntheticClockRead(
                "after_primary_subject_1",
                14,
            ),
        ),
    )

    with pytest.raises(ValueError, match="continues after terminal outcome"):
        prefix_index_module._assert_execution_semantics(graph)


def test_s02d_derives_trigger_instead_of_trusting_program_claim(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    graph.program = replace(
        graph.program,
        expected_trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
    )

    with pytest.raises(ValueError, match="fresh replay outcome"):
        prefix_index_module._assert_execution_semantics(graph)


def test_s02d_seals_exact_schedule_order_after_fresh_graph_reload(
    tmp_path: Path,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    out = run_root / "prefix-index.json"

    ref = seal_prefix_index(
        run_root=run_root,
        schedule_ref=fixture.schedule_ref,
        candidate_refs=candidates,
        out=out,
    )

    assert ref.role == "resampling_prefix_receipt"
    assert ref.relative_path == "prefix-index.json"
    assert ref.media_type == "application/json"
    record = validate_record(json.loads(out.read_bytes()))
    assert record["payload"]["schedule_ref"] == asdict(fixture.schedule_ref)  # type: ignore[index]
    assert [
        receipt["task_id"]  # type: ignore[index]
        for receipt in record["payload"]["task_receipts"]  # type: ignore[index]
    ] == ["task-1", "task-foreign"]


def test_s02d_full_seal_routes_candidates_through_nonempty_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    nonempty = _nonempty_execution_graph(tmp_path / "nonempty")
    real_replay = prefix_index_module._assert_execution_semantics
    replayed_nonempty = False

    def replay_with_nonempty_probe(
        graph: prefix_index_module._CandidateGraph,
    ) -> None:
        nonlocal replayed_nonempty
        if not replayed_nonempty:
            real_replay(nonempty)
            replayed_nonempty = True
        real_replay(graph)

    monkeypatch.setattr(
        prefix_index_module,
        "_assert_execution_semantics",
        replay_with_nonempty_probe,
    )

    seal_prefix_index(
        run_root=run_root,
        schedule_ref=fixture.schedule_ref,
        candidate_refs=candidates,
        out=run_root / "prefix-index.json",
    )

    assert replayed_nonempty


def test_s02d_reconciles_nonselected_reachable_program_leaves(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run"
    fixture = ProviderAuthorityFixture.build(
        run_root,
        executable_sources=True,
    )
    selected_ref = fixture.refs["task-1_program"]
    foreign_ref = fixture.refs["task-foreign_program"]
    selected = load_synthetic_prefix_program(
        (run_root / selected_ref.relative_path).read_bytes()
    )
    foreign = load_synthetic_prefix_program(
        (run_root / foreign_ref.relative_path).read_bytes()
    )
    foreign = replace(
        foreign,
        grade_result=replace(foreign.grade_result, partial_reward=0.5),
    )
    leaf_refs = {
        selected.grade_result.evidence_ref,
        selected.verifier_result.evidence_ref,
    }
    payloads = {
        ref: (run_root / ref.relative_path).read_bytes()
        for ref in (selected_ref, foreign_ref, *leaf_refs)
    }
    traversal = prefix_index_module._FreshTraversal(
        visited={},
        path_bindings={},
        physical_bindings={},
        payloads=payloads,
        nested={},
        decoded={selected_ref: selected, foreign_ref: foreign},
        scientific_refs=set(),
    )

    with pytest.raises(ValueError, match="grade"):
        prefix_index_module._assert_all_program_occurrences(traversal)


@pytest.mark.parametrize("case", ["duplicate", "reverse"])
def test_s02d_rejects_nonexact_candidate_roster(
    tmp_path: Path,
    case: str,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    invalid = (
        (candidates[0], candidates[0])
        if case == "duplicate"
        else tuple(reversed(candidates))
    )

    with pytest.raises((TypeError, ValueError)):
        seal_prefix_index(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            candidate_refs=invalid,
            out=run_root / "prefix-index.json",
        )

    assert not (run_root / "prefix-index.json").exists()


def test_s02d_rejects_reserved_or_existing_destination(tmp_path: Path) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    existing = run_root / "prefix-index.json"
    existing.write_bytes(b"do not overwrite")

    for out in (
        existing,
        run_root / "controller-artifacts" / "prefix-index.json",
    ):
        with pytest.raises((FileExistsError, ValueError)):
            seal_prefix_index(
                run_root=run_root,
                schedule_ref=fixture.schedule_ref,
                candidate_refs=candidates,
                out=out,
            )

    assert existing.read_bytes() == b"do not overwrite"


def test_s02d_rejects_symlink_destination_component(tmp_path: Path) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (run_root / "publication-link").symlink_to(outside, target_is_directory=True)

    with pytest.raises((OSError, ValueError)):
        seal_prefix_index(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            candidate_refs=candidates,
            out=run_root / "publication-link" / "prefix-index.json",
        )

    assert not (outside / "prefix-index.json").exists()


def test_s02d_uses_one_scientific_reader_for_the_whole_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    real_enter = prefix_index_module.ScientificRefReader.__enter__
    entered = 0

    def counted_enter(
        reader: object,
    ) -> object:
        nonlocal entered
        entered += 1
        return real_enter(reader)  # type: ignore[arg-type]

    monkeypatch.setattr(
        prefix_index_module.ScientificRefReader,
        "__enter__",
        counted_enter,
    )
    real_authority_load = (
        prefix_index_module._load_prefix_execution_authority_with_reader
    )

    def reader_bound_authority_load(*args: object, **kwargs: object) -> object:
        assert kwargs.get("scientific_reader") is not None
        return real_authority_load(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        prefix_index_module,
        "_load_prefix_execution_authority_with_reader",
        reader_bound_authority_load,
    )
    seal_prefix_index(
        run_root=run_root,
        schedule_ref=fixture.schedule_ref,
        candidate_refs=candidates,
        out=run_root / "prefix-index.json",
    )

    assert entered == 1


@pytest.mark.parametrize(
    "reader_type",
    [
        prefix_index_module.ScientificRefReader,
        prefix_index_module.ControllerArtifactResolver,
        prefix_index_module.AuthorityRefReader,
    ],
)
def test_s02d_rejects_reader_bound_to_another_root_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reader_type: type[object],
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    monkeypatch.setattr(
        reader_type,
        "bound_root_identity",
        property(lambda _reader: (-1, -1)),
        raising=False,
    )

    with pytest.raises(
        ValueError,
        match="reader root identity differs",
    ):
        seal_prefix_index(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            candidate_refs=candidates,
            out=run_root / "prefix-index.json",
        )

    assert not (run_root / "prefix-index.json").exists()


def test_s02d_rejects_cross_class_physical_alias_in_one_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    shared_identity = (999_991, 999_983)
    real_scientific = prefix_index_module.ScientificRefReader.read_bound
    real_authority = prefix_index_module.AuthorityRefReader.read_bound

    def scientific_alias(reader: object, ref: ArtifactRef) -> object:
        bound = real_scientific(reader, ref)  # type: ignore[arg-type]
        return (
            replace(
                bound,
                st_dev=shared_identity[0],
                st_ino=shared_identity[1],
            )
            if ref == fixture.schedule_ref
            else bound
        )

    def authority_alias(reader: object, ref: ArtifactRef) -> object:
        bound = real_authority(reader, ref)  # type: ignore[arg-type]
        return replace(
            bound,
            st_dev=shared_identity[0],
            st_ino=shared_identity[1],
        )

    monkeypatch.setattr(
        prefix_index_module.ScientificRefReader,
        "read_bound",
        scientific_alias,
    )
    monkeypatch.setattr(
        prefix_index_module.AuthorityRefReader,
        "read_bound",
        authority_alias,
    )

    with pytest.raises(ValueError, match="physical file"):
        seal_prefix_index(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            candidate_refs=candidates,
            out=run_root / "prefix-index.json",
        )


@pytest.mark.parametrize("operation", ["write", "close"])
def test_s02d_publication_fault_removes_only_owned_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    target = run_root / "prefix-index.json"
    real_write = prefix_index_module.os.write
    real_close = prefix_index_module.os.close
    injected = False

    def is_target(descriptor: int) -> bool:
        try:
            return Path(f"/proc/self/fd/{descriptor}").resolve() == target
        except OSError:
            return False

    def failing_write(descriptor: int, payload: object) -> int:
        nonlocal injected
        if not injected and is_target(descriptor):
            injected = True
            raise OSError("injected write failure")
        return real_write(descriptor, payload)  # type: ignore[arg-type]

    def failing_close(descriptor: int) -> None:
        nonlocal injected
        if not injected and is_target(descriptor):
            injected = True
            real_close(descriptor)
            raise OSError("injected close failure")
        real_close(descriptor)

    monkeypatch.setattr(
        prefix_index_module.os,
        operation,
        failing_write if operation == "write" else failing_close,
    )
    root_descriptor = prefix_index_module.os.open(
        run_root,
        prefix_index_module._DIRECTORY_FLAGS,
    )
    try:
        with pytest.raises(BaseException):
            prefix_index_module._publish_once(
                root_descriptor=root_descriptor,
                relative_path="prefix-index.json",
                payload=b"payload",
            )
    finally:
        prefix_index_module.os.close(root_descriptor)

    assert injected
    assert not target.exists()


@pytest.mark.parametrize(
    "stage",
    [
        "parent_fsync",
        "reopen",
        "read",
        "verification_stat",
        "semantic_validation",
        "directory_close",
        "verification_close",
        "rollback_guard_dup",
        "final_root_close",
    ],
)
def test_s02d_late_publication_failure_rolls_back_and_retry_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    target = run_root / "prefix-index.json"
    real_open = prefix_index_module.os.open
    real_read = prefix_index_module.os.read
    real_fsync = prefix_index_module.os.fsync
    real_stat = prefix_index_module.os.stat
    real_dup = prefix_index_module.os.dup
    real_close = prefix_index_module.os.close
    real_validate = prefix_index_module.validate_record
    real_seal_bound = prefix_index_module._seal_bound_prefix_index
    injected = False
    verification_read = False
    outer_root_descriptor: int | None = None

    def descriptor_path(descriptor: int) -> Path | None:
        try:
            return Path(f"/proc/self/fd/{descriptor}").resolve()
        except OSError:
            return None

    def failing_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        nonlocal injected
        if (
            stage == "reopen"
            and not injected
            and target.exists()
            and path == "prefix-index.json"
            and flags & prefix_index_module.os.O_ACCMODE
            == prefix_index_module.os.O_RDONLY
        ):
            injected = True
            raise OSError("injected reopen failure")
        return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

    def failing_read(descriptor: int, count: int) -> bytes:
        nonlocal injected, verification_read
        if descriptor_path(descriptor) == target:
            verification_read = True
            if stage == "read" and not injected:
                injected = True
                raise OSError("injected verification read failure")
        return real_read(descriptor, count)

    def failing_stat(
        path: object,
        *args: object,
        **kwargs: object,
    ) -> object:
        nonlocal injected
        if (
            stage == "verification_stat"
            and not injected
            and verification_read
            and path == "prefix-index.json"
        ):
            injected = True
            raise OSError("injected verification stat failure")
        return real_stat(path, *args, **kwargs)

    def failing_dup(descriptor: int) -> int:
        nonlocal injected
        if (
            stage == "rollback_guard_dup"
            and not injected
            and target.exists()
            and descriptor == outer_root_descriptor
        ):
            injected = True
            raise OSError("injected rollback guard dup failure")
        return real_dup(descriptor)

    def failing_validate(record: object) -> object:
        nonlocal injected
        if stage == "semantic_validation" and not injected and verification_read:
            injected = True
            raise ValueError("injected semantic verification failure")
        return real_validate(record)  # type: ignore[arg-type]

    def failing_fsync(descriptor: int) -> None:
        nonlocal injected
        if (
            stage == "parent_fsync"
            and not injected
            and target.exists()
            and descriptor_path(descriptor) == run_root
        ):
            injected = True
            raise OSError("injected parent fsync failure")
        real_fsync(descriptor)

    def failing_close(descriptor: int) -> None:
        nonlocal injected
        path = descriptor_path(descriptor)
        should_fail = (
            (
                stage == "directory_close"
                and not injected
                and target.exists()
                and path == run_root
                and descriptor != outer_root_descriptor
            )
            or (
                stage == "verification_close"
                and not injected
                and verification_read
                and path == target
            )
            or (
                stage == "final_root_close"
                and not injected
                and descriptor == outer_root_descriptor
            )
        )
        if should_fail:
            injected = True
            real_close(descriptor)
            raise OSError(f"injected {stage} failure")
        real_close(descriptor)

    def capture_outer_root(*args: object, **kwargs: object) -> object:
        nonlocal outer_root_descriptor
        outer_root_descriptor = kwargs["root_descriptor"]  # type: ignore[assignment]
        return real_seal_bound(*args, **kwargs)  # type: ignore[arg-type]

    with monkeypatch.context() as scoped:
        scoped.setattr(prefix_index_module.os, "open", failing_open)
        scoped.setattr(prefix_index_module.os, "read", failing_read)
        scoped.setattr(prefix_index_module.os, "stat", failing_stat)
        scoped.setattr(prefix_index_module.os, "dup", failing_dup)
        scoped.setattr(prefix_index_module.os, "fsync", failing_fsync)
        scoped.setattr(prefix_index_module.os, "close", failing_close)
        scoped.setattr(prefix_index_module, "validate_record", failing_validate)
        scoped.setattr(
            prefix_index_module,
            "_seal_bound_prefix_index",
            capture_outer_root,
        )
        with pytest.raises(BaseException):
            seal_prefix_index(
                run_root=run_root,
                schedule_ref=fixture.schedule_ref,
                candidate_refs=candidates,
                out=target,
            )

    assert injected
    assert not target.exists()
    seal_prefix_index(
        run_root=run_root,
        schedule_ref=fixture.schedule_ref,
        candidate_refs=candidates,
        out=target,
    )
    assert target.is_file()
