import json

import pytest
from pydantic import ValidationError

from engine.ai.graph_based import GraphBasedProvider
from engine.ai.provider import AIProviderError
from engine.npc.personality import NpcPersonality
from engine.peace import (
    NegotiationDecision,
    PeaceNegotiation,
    PeaceProposal,
    parse_ai_response,
)
from engine.settings import ILMU_MODEL, loadsettings, savesettings


class FakeAIManager:
    def __init__(self, response):
        self.response = response

    def ask(self, _prompt):
        return self.response


class FailingAIManager:
    def __init__(self):
        self.calls = 0

    def ask(self, _prompt):
        self.calls += 1
        raise AIProviderError("credential rejected")


def makenegotiation(response="{}"):
    return PeaceNegotiation(
        ai_manager=FakeAIManager(response),
        victor="Malaysia",
        defeated="Thailand",
        player_name="Commander",
        personality=NpcPersonality(
            diplomacy=1.1,
            pragmatism=1.2,
            pride=1.0,
            territoriality=1.0,
        ),
        victor_strength=200,
        defeated_strength=100,
        available_state_ids={"Siam", "Isan"},
    )


def test_ai_response_is_pydantic_validated_and_cannot_invent_territory():
    rawresponse = json.dumps({
        "decision": "ACCEPT",
        "message": "Accepted.",
        "concession_delta": 2,
        "territory_state_ids": ["Invented_State"],
    })
    response = parse_ai_response(rawresponse, posture_score=80, finalproposal=True)
    assert response.decision == NegotiationDecision.accept
    assert response.message != "Accepted."


def test_low_posture_cannot_be_overridden_by_ai_acceptance():
    rawresponse = json.dumps({
        "decision": "ACCEPT",
        "message": "The model accepts impossible terms.",
        "concession_delta": 0,
    })
    response = parse_ai_response(rawresponse, posture_score=10, finalproposal=True)
    assert response.decision == NegotiationDecision.reject


def test_overlong_valid_ai_dialogue_is_safely_normalized():
    rawresponse = json.dumps({
        "decision": "CONTINUE",
        "message": "Diplomatic sentence. " * 80,
        "concession_delta": 0,
    })
    response = parse_ai_response(rawresponse, posture_score=60, finalproposal=False)
    assert response.decision == NegotiationDecision.continue_talks
    assert len(response.message) <= 500
    assert response.message.startswith("Diplomatic sentence.")


def test_proposal_rejects_unavailable_territory():
    negotiation = makenegotiation()
    with pytest.raises(ValueError):
        negotiation.validate_proposal(
            {"CEASEFIRE", "STATE TRANSFER"},
            {"Invented_State"},
        )


def test_proposal_requires_state_transfer_for_territory():
    negotiation = makenegotiation()
    with pytest.raises(ValueError):
        negotiation.validate_proposal({"CEASEFIRE"}, {"Siam"})


def test_peace_proposal_rejects_unknown_demands():
    with pytest.raises(ValidationError):
        PeaceProposal(
            proposer="Malaysia",
            recipient="Thailand",
            demands=["TAKE EVERYTHING"],
            territory_state_ids=[],
            final=True,
        )


def test_respectful_negotiation_improves_posture():
    negotiation = makenegotiation()
    before = negotiation.posture_score({"CEASEFIRE"}, set())
    negotiation.record_player_message(
        "Please accept a fair peace. We respect your people and guarantee stability."
    )
    after = negotiation.posture_score({"CEASEFIRE"}, set())
    assert after > before


def test_graph_provider_follows_posture_state_graph():
    provider = GraphBasedProvider()
    response = json.loads(provider.ask("POSTURE_SCORE: 75\nFINAL_PROPOSAL: yes"))
    assert response["decision"] == "ACCEPT"


def test_valid_ai_counteroffer_is_limited_to_available_states():
    manager = FakeAIManager(json.dumps({
        "decision": "COUNTER",
        "message": "We will cede Isan, but not Siam.",
        "concession_delta": 1,
        "suggested_demands": ["CEASEFIRE", "STATE TRANSFER"],
        "suggested_territory_state_ids": ["Isan"],
    }))
    negotiation = makenegotiation()
    negotiation.ai_manager = manager
    response = negotiation.ask(
        {"CEASEFIRE", "STATE TRANSFER"},
        {"Siam", "Isan"},
        finalproposal=True,
    )
    assert response.decision == NegotiationDecision.counter
    assert response.suggested_demands == ["CEASEFIRE", "STATE TRANSFER"]
    assert response.suggested_territory_state_ids == ["Isan"]


def test_total_occupation_forces_acceptance_without_calling_ai():
    manager = FailingAIManager()
    negotiation = PeaceNegotiation(
        ai_manager=manager,
        victor="Malaysia",
        defeated="Thailand",
        player_name="Commander",
        personality=NpcPersonality(pride=2.0, territoriality=2.0),
        victor_strength=100,
        defeated_strength=500,
        available_state_ids={"Siam", "Isan"},
        occupation_ratio=1.0,
    )
    response = negotiation.ask(
        {"CEASEFIRE", "STATE TRANSFER", "PUPPET STATE"},
        {"Siam", "Isan"},
        finalproposal=True,
    )
    assert response.decision == NegotiationDecision.accept
    assert negotiation.posture_score(set(), set()) == 100.0
    assert manager.calls == 0


def test_plain_language_all_territory_updates_formal_proposal():
    negotiation = makenegotiation()
    demands, territories = negotiation.interpret_player_message(
        "Give us all your territory.",
        {"CEASEFIRE"},
        set(),
    )
    assert demands == {"CEASEFIRE", "STATE TRANSFER"}
    assert territories == {"Siam", "Isan"}


def test_asking_for_npc_proposal_creates_counteroffer_during_chat():
    manager = FakeAIManager(json.dumps({
        "decision": "CONTINUE",
        "message": "We are listening.",
        "concession_delta": 0,
        "suggested_demands": [],
        "suggested_territory_state_ids": [],
    }))
    negotiation = makenegotiation()
    negotiation.ai_manager = manager
    negotiation.record_player_message("What would you like to offer?")
    response = negotiation.ask(
        {"CEASEFIRE", "STATE TRANSFER"},
        {"Siam", "Isan"},
        finalproposal=False,
    )
    assert response.decision == NegotiationDecision.counter
    assert response.suggested_demands == ["CEASEFIRE", "STATE TRANSFER"]
    assert len(response.suggested_territory_state_ids) == 1


def test_settings_round_trip_preserves_setup_fields(tmp_path):
    settingspath = tmp_path / "settings.json"
    savesettings(
        {
            "volume": 64,
            "setup_complete": True,
            "player_name": "Amina",
            "llm_mode": "graph",
        },
        settingspath,
    )
    settings = loadsettings(settingspath)
    assert settings["volume"] == 64
    assert settings["player_name"] == "Amina"
    assert settings["llm_mode"] == "graph"


def test_existing_demo_settings_migrate_to_accessible_model(tmp_path):
    settingspath = tmp_path / "settings.json"
    settingspath.write_text(
        json.dumps({
            "setup_complete": True,
            "llm_mode": "online",
            "use_demo_key": True,
            "online_model": "nemo-super",
        }),
        encoding="utf-8",
    )
    assert loadsettings(settingspath)["online_model"] == ILMU_MODEL


def test_provider_failure_stays_out_of_dialogue_and_uses_circuit_breaker():
    manager = FailingAIManager()
    negotiation = makenegotiation()
    negotiation.ai_manager = manager

    first = negotiation.ask({"CEASEFIRE"}, set())
    second = negotiation.ask({"CEASEFIRE"}, set())

    assert manager.calls == 1
    assert negotiation.provider_available is False
    assert negotiation.last_provider_error == "credential rejected"
    assert "AIProviderError" not in first.message
    assert "credential rejected" not in first.message
    assert "offline" not in second.message.lower()
