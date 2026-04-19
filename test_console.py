from engine.console import rundevcommand
from engine.events import EngineEventType, EventBus


def _provincemap_for_countries():
    return {
        "P1": {
            "id": "P1",
            "ownercountry": "Malaysia",
            "controllercountry": "Malaysia",
            "country": "Malaysia",
            "troops": 0,
        },
        "P2": {
            "id": "P2",
            "ownercountry": "Thailand",
            "controllercountry": "Thailand",
            "country": "Thailand",
            "troops": 0,
        },
    }


def test_console_war_command_emits_war_event():
    bus = EventBus()
    captured = []

    def on_war(payload):
        captured.append(payload)

    bus.subscribe(EngineEventType.WARDECLARED, on_war)

    result = rundevcommand(
        "war malaysia thailand",
        provincemap=_provincemap_for_countries(),
        playercountry="Malaysia",
        countrytocolor={},
        fallbackcolor=(0, 0, 0),
        troopbadgelist=[],
        eventbus=bus,
        currentturnnumber=7,
    )

    assert result == "ok war declared: Malaysia -> Thailand"
    assert len(captured) == 1
    assert captured[0]["attacker"] == "Malaysia"
    assert captured[0]["defender"] == "Thailand"
    assert captured[0]["turn"] == 7


def test_console_war_command_rejects_same_country():
    bus = EventBus()
    captured = []
    bus.subscribe(EngineEventType.WARDECLARED, lambda payload: captured.append(payload))

    result = rundevcommand(
        "war Malaysia malaysia",
        provincemap=_provincemap_for_countries(),
        playercountry="Malaysia",
        countrytocolor={},
        fallbackcolor=(0, 0, 0),
        troopbadgelist=[],
        eventbus=bus,
        currentturnnumber=3,
    )

    assert result == "countries must differ"
    assert captured == []


def test_console_war_command_rejects_unknown_country():
    bus = EventBus()
    captured = []
    bus.subscribe(EngineEventType.WARDECLARED, lambda payload: captured.append(payload))

    result = rundevcommand(
        "war Malaysia Atlantis",
        provincemap=_provincemap_for_countries(),
        playercountry="Malaysia",
        countrytocolor={},
        fallbackcolor=(0, 0, 0),
        troopbadgelist=[],
        eventbus=bus,
        currentturnnumber=3,
    )

    assert result == "unknown country: Atlantis"
    assert captured == []


def test_country_stats_without_arg_lists_npc_troops():
    provincemap = {
        "P1": {
            "id": "P1",
            "ownercountry": "Malaysia",
            "controllercountry": "Malaysia",
            "country": "Malaysia",
            "troops": 12,
        },
        "P2": {
            "id": "P2",
            "ownercountry": "Thailand",
            "controllercountry": "Thailand",
            "country": "Thailand",
            "troops": 40,
        },
    }

    result = rundevcommand(
        "country_stats",
        provincemap=provincemap,
        playercountry="Malaysia",
        countrytocolor={},
        fallbackcolor=(0, 0, 0),
        troopbadgelist=[],
        eventbus=None,
        currentturnnumber=1,
    )

    assert "Malaysia" in result
    assert "Thailand" in result
    assert "controlled_troops=40" in result
