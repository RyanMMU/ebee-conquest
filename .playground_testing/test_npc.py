from engine.npc import NpcDirector


def _economy_config():
    return {
        "startinggold": 1000,
        "startingpopulation": 1000,
        "recruitamount": 10,
        "recruitgoldcostperunit": 1,
        "recruitpopulationcostperunit": 1,
        "mingoldincome": 0,
        "goldincomedivisor": 1,
        "minpopulationgrowth": 0,
        "populationgrowthdivisor": 1,
    }


def _province(provinceid, ownercountry, controllercountry=None, troops=0, center=(0.0, 0.0)):
    if controllercountry is None:
        controllercountry = ownercountry
    return {
        "id": provinceid,
        "ownercountry": ownercountry,
        "controllercountry": controllercountry,
        "country": controllercountry,
        "countrycolor": (90, 90, 90),
        "troops": troops,
        "center": center,
    }


def _director(provincemap, provincegraph, playercountry, wars, economy_config=None):
    events = []
    director = NpcDirector(
        provincemap,
        provincegraph,
        countrytocolorlookup={"A": (10, 10, 10), "B": (20, 20, 20)},
        emit=lambda eventname, payload: events.append((eventname, payload)),
        economyconfig=economy_config or _economy_config(),
    )
    director.setplayercountry(playercountry)
    director.sync_player_wars(playercountry, wars)
    return director, events


def test_npc_recruits_for_non_player_country():
    provincemap = {
        "A1": _province("A1", "A", troops=0, center=(0.0, 0.0)),
        "B1": _province("B1", "B", troops=0, center=(1.0, 0.0)),
        "B2": _province("B2", "B", troops=5, center=(2.0, 0.0)),
    }
    provincegraph = {
        "A1": {"B1"},
        "B1": {"A1", "B2"},
        "B2": {"B1"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars=set())
    movementorderlist = []

    summary = director.executeturn(movementorderlist, turnnumber=1)

    totaltroops_b = provincemap["B1"]["troops"] + provincemap["B2"]["troops"]
    assert summary["countriesProcessed"] == 1
    assert summary["recruits"] == 1
    assert summary["ordersCreated"] == 0
    assert totaltroops_b == 15


def test_npc_recruitment_splits_across_multiple_core_provinces():
    provincemap = {
        "A1": _province("A1", "A", troops=0, center=(0.0, 0.0)),
        "B1": _province("B1", "B", troops=0, center=(1.0, 0.0)),
        "B2": _province("B2", "B", troops=0, center=(2.0, 0.0)),
    }
    provincegraph = {
        "A1": set(),
        "B1": {"B2"},
        "B2": {"B1"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars=set())
    movementorderlist = []
    summary = director.executeturn(movementorderlist, turnnumber=1)

    assert summary["recruits"] == 1
    assert provincemap["B1"]["troops"] == 5
    assert provincemap["B2"]["troops"] == 5


def test_npc_idle_recruit_prefers_border_core_province():
    provincemap = {
        "A1": _province("A1", "A", troops=0, center=(0.0, 0.0)),
        "B1": _province("B1", "B", troops=80, center=(1.0, 0.0)),
        "B2": _province("B2", "B", troops=0, center=(1.0, 1.0)),
    }
    provincegraph = {
        "A1": {"B1"},
        "B1": {"A1", "B2"},
        "B2": {"B1"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars=set())
    movementorderlist = []
    summary = director.executeturn(movementorderlist, turnnumber=1)

    assert summary["recruits"] == 1
    # Border province B1 should still receive recruits even when interior is weaker.
    assert provincemap["B1"]["troops"] >= 85


def test_npc_recruit_uses_gold_and_slight_population_cost():
    economyconfig = _economy_config()
    economyconfig.update(
        {
            "startinggold": 200,
            "startingpopulation": 200,
            "recruitamount": 20,
            "recruitgoldcostperunit": 1,
            "recruitpopulationcostperunit": 1,
            "mingoldincome": 0,
            "goldincomedivisor": 9999,
            "minpopulationgrowth": 0,
            "populationgrowthdivisor": 9999,
        }
    )

    provincemap = {
        "A1": _province("A1", "A", troops=0, center=(0.0, 0.0)),
        "B1": _province("B1", "B", troops=0, center=(1.0, 0.0)),
    }
    provincegraph = {
        "A1": {"B1"},
        "B1": {"A1"},
    }

    director, _events = _director(
        provincemap,
        provincegraph,
        playercountry="A",
        wars=set(),
        economy_config=economyconfig,
    )
    beforegold = director.countryeconomy["B"]["gold"]
    beforepopulation = director.countryeconomy["B"]["population"]

    movementorderlist = []
    summary = director.executeturn(movementorderlist, turnnumber=1)

    assert summary["recruits"] == 1
    # Gold uses full recruit cost, population uses a lighter NPC recruit cost.
    assert director.countryeconomy["B"]["gold"] == beforegold - 20
    assert director.countryeconomy["B"]["population"] == beforepopulation - 5


def test_npc_development_mode_does_not_bypass_recruit_costs():
    economyconfig = _economy_config()
    economyconfig.update(
        {
            "startinggold": 0,
            "startingpopulation": 0,
            "recruitamount": 10,
            "recruitgoldcostperunit": 10,
            "recruitpopulationcostperunit": 10,
            "mingoldincome": 0,
            "goldincomedivisor": 9999,
            "minpopulationgrowth": 0,
            "populationgrowthdivisor": 9999,
        }
    )

    provincemap = {
        "A1": _province("A1", "A", troops=0, center=(0.0, 0.0)),
        "B1": _province("B1", "B", troops=0, center=(1.0, 0.0)),
    }
    provincegraph = {
        "A1": {"B1"},
        "B1": {"A1"},
    }

    director, _events = _director(
        provincemap,
        provincegraph,
        playercountry="A",
        wars=set(),
        economy_config=economyconfig,
    )
    movementorderlist = []

    summary = director.executeturn(movementorderlist, turnnumber=1, developmentmode=True)

    assert summary["recruits"] == 0
    assert provincemap["B1"]["troops"] == 0


def test_npc_economy_slightly_favors_more_states():
    economyconfig = _economy_config()
    economyconfig.update(
        {
            "startinggold": 0,
            "startingpopulation": 0,
            "recruitamount": 10,
            "recruitgoldcostperunit": 100,
            "recruitpopulationcostperunit": 100,
            "mingoldincome": 0,
            "goldincomedivisor": 9999,
            "minpopulationgrowth": 0,
            "populationgrowthdivisor": 9999,
            "npcstategoldbonusperextrastate": 2,
            "npcstatepopulationbonusperextrastate": 3,
        }
    )

    provincemap = {
        "A1": _province("A1", "A", troops=0, center=(0.0, 0.0)),
        "B1": {
            **_province("B1", "B", troops=0, center=(1.0, 0.0)),
            "parentstateid": "S1",
        },
        "B2": {
            **_province("B2", "B", troops=0, center=(2.0, 0.0)),
            "parentstateid": "S2",
        },
        "C1": {
            **_province("C1", "C", troops=0, center=(3.0, 0.0)),
            "parentstateid": "T1",
        },
        "C2": {
            **_province("C2", "C", troops=0, center=(4.0, 0.0)),
            "parentstateid": "T1",
        },
    }
    provincegraph = {
        "A1": set(),
        "B1": {"B2"},
        "B2": {"B1"},
        "C1": {"C2"},
        "C2": {"C1"},
    }

    director, _events = _director(
        provincemap,
        provincegraph,
        playercountry="A",
        wars=set(),
        economy_config=economyconfig,
    )
    movementorderlist = []
    director.executeturn(movementorderlist, turnnumber=1)

    assert director.countryeconomy["B"]["gold"] > director.countryeconomy["C"]["gold"]
    assert director.countryeconomy["B"]["population"] > director.countryeconomy["C"]["population"]


def test_npc_cannot_recruit_without_core_province():
    provincemap = {
        "A1": _province("A1", "A", controllercountry="B", troops=0, center=(0.0, 0.0)),
        "A2": _province("A2", "A", controllercountry="A", troops=0, center=(1.0, 0.0)),
    }
    provincegraph = {
        "A1": {"A2"},
        "A2": {"A1"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars={"B"})
    movementorderlist = []

    summary = director.executeturn(movementorderlist, turnnumber=2)

    assert summary["recruits"] == 0
    assert provincemap["A1"]["troops"] == 0


def test_npc_reacts_to_invasion_by_reinforcing_frontline():
    provincemap = {
        "A1": _province("A1", "A", controllercountry="A", troops=10, center=(0.0, 0.0)),
        "B1": _province("B1", "B", controllercountry="A", troops=0, center=(1.0, 0.0)),
        "B2": _province("B2", "B", controllercountry="B", troops=0, center=(2.0, 0.0)),
        "B3": _province("B3", "B", controllercountry="B", troops=40, center=(3.0, 0.0)),
    }
    provincegraph = {
        "A1": {"B1"},
        "B1": {"A1", "B2"},
        "B2": {"B1", "B3"},
        "B3": {"B2"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars={"B"})
    movementorderlist = []

    summary = director.executeturn(movementorderlist, turnnumber=3)

    if summary["defenseOrders"] >= 1:
        assert any(
            order["country"] == "B"
            and order["path"][0] == "B3"
            and order["path"][-1] == "B2"
            for order in movementorderlist
        )
    else:
        # If frontline recruitment already covered the immediate need,
        # reserve movement is optional.
        assert summary["recruits"] >= 1
        assert provincemap["B2"]["troops"] > 0


def test_npc_invades_enemy_when_player_war_exists():
    provincemap = {
        "A1": _province("A1", "A", controllercountry="A", troops=6, center=(0.0, 0.0)),
        "A2": _province("A2", "A", controllercountry="A", troops=0, center=(0.0, 1.0)),
        "B1": _province("B1", "B", controllercountry="B", troops=20, center=(1.0, 0.0)),
        "B2": _province("B2", "B", controllercountry="B", troops=0, center=(2.0, 0.0)),
    }
    provincegraph = {
        "A1": {"A2", "B1"},
        "A2": {"A1"},
        "B1": {"A1", "B2"},
        "B2": {"B1"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars={"B"})
    movementorderlist = []

    summary = director.executeturn(movementorderlist, turnnumber=5)

    assert summary["invasionOrders"] >= 1
    assert any(
        order["country"] == "B"
        and order["path"][0] == "B1"
        and order["path"][-1] == "A1"
        for order in movementorderlist
    )


def test_npc_does_not_instantly_exploit_fresh_zero_troop_target():
    provincemap = {
        "A1": _province("A1", "A", controllercountry="A", troops=50, center=(0.0, 0.0)),
        "B1": _province("B1", "B", controllercountry="B", troops=30, center=(1.0, 0.0)),
        "B2": _province("B2", "B", controllercountry="B", troops=0, center=(2.0, 0.0)),
    }
    provincegraph = {
        "A1": {"B1"},
        "B1": {"A1", "B2"},
        "B2": {"B1"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars={"B"})

    # Simulate the player just moving troops out this turn.
    provincemap["A1"]["troops"] = 0
    movementorderlist = []

    summary = director.executeturn(movementorderlist, turnnumber=2)

    assert summary["invasionOrders"] == 0
    assert not any(order["country"] == "B" and order["path"][-1] == "A1" for order in movementorderlist)


def test_npc_countries_fight_each_other_when_they_are_at_war():
    provincemap = {
        "A1": _province("A1", "A", controllercountry="A", troops=0, center=(0.0, 0.0)),
        "B1": _province("B1", "B", controllercountry="B", troops=40, center=(1.0, 0.0)),
        "C1": _province("C1", "C", controllercountry="C", troops=8, center=(2.0, 0.0)),
    }
    provincegraph = {
        "A1": set(),
        "B1": {"C1"},
        "C1": {"B1"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars=set())
    director.sync_player_wars("A", set(), warpairset={("b", "c")})

    movementorderlist = []
    summary = director.executeturn(movementorderlist, turnnumber=6)

    assert summary["invasionOrders"] >= 1
    assert any(
        (order["country"] == "B" and order["path"][-1] == "C1")
        or (order["country"] == "C" and order["path"][-1] == "B1")
        for order in movementorderlist
    )


def test_npc_uses_attrition_attack_to_break_stalemate():
    provincemap = {
        "A1": _province("A1", "A", controllercountry="A", troops=45, center=(0.0, 0.0)),
        "B1": _province("B1", "B", controllercountry="B", troops=35, center=(1.0, 0.0)),
    }
    provincegraph = {
        "A1": {"B1"},
        "B1": {"A1"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars={"B"})
    movementorderlist = []
    summary = director.executeturn(movementorderlist, turnnumber=8)

    assert summary["invasionOrders"] >= 1
    assert any(order["country"] == "B" and order["path"][-1] == "A1" for order in movementorderlist)


def test_npc_distributes_single_large_reserve_across_frontline():
    provincemap = {
        "A1": _province("A1", "A", controllercountry="A", troops=15, center=(0.0, 0.0)),
        "B1": _province("B1", "B", controllercountry="B", troops=120, center=(1.0, 0.0)),
        "B2": _province("B2", "B", controllercountry="B", troops=0, center=(2.0, 0.0)),
        "B3": _province("B3", "B", controllercountry="B", troops=0, center=(2.0, 1.0)),
        "C1": _province("C1", "C", controllercountry="C", troops=25, center=(3.0, 0.0)),
        "C2": _province("C2", "C", controllercountry="C", troops=20, center=(3.0, 1.0)),
    }
    provincegraph = {
        "A1": set(),
        "B1": {"B2", "B3"},
        "B2": {"B1", "C1"},
        "B3": {"B1", "C2"},
        "C1": {"B2"},
        "C2": {"B3"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars=set())
    director.sync_player_wars("A", set(), warpairset={("B", "C")})

    movementorderlist = []
    summary = director.executeturn(movementorderlist, turnnumber=9)

    frontline_destinations = {order["path"][-1] for order in movementorderlist if order["country"] == "B"}
    assert summary["ordersCreated"] >= 2
    assert "B2" in frontline_destinations
    assert "B3" in frontline_destinations


def test_npc_idle_buildup_moves_interior_reserve_to_border():
    provincemap = {
        "A1": _province("A1", "A", controllercountry="A", troops=0, center=(0.0, 0.0)),
        "B1": _province("B1", "B", controllercountry="B", troops=120, center=(1.0, 0.0)),
        "B2": _province("B2", "B", controllercountry="B", troops=0, center=(2.0, 0.0)),
    }
    provincegraph = {
        "A1": {"B2"},
        "B1": {"B2"},
        "B2": {"B1", "A1"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars=set())
    movementorderlist = []
    summary = director.executeturn(movementorderlist, turnnumber=9)

    borderorders = [
        order
        for order in movementorderlist
        if order["country"] == "B"
        and order["path"][0] == "B1"
        and order["path"][-1] == "B2"
    ]
    assert summary["idleBorderOrders"] >= 1
    assert len(borderorders) >= 1


def test_npc_large_stack_attacks_multiple_enemy_targets():
    provincemap = {
        "A1": _province("A1", "A", controllercountry="A", troops=0, center=(0.0, 0.0)),
        "B1": _province("B1", "B", controllercountry="B", troops=120, center=(1.0, 0.0)),
        "C1": _province("C1", "C", controllercountry="C", troops=12, center=(2.0, 0.0)),
        "C2": _province("C2", "C", controllercountry="C", troops=10, center=(2.0, 1.0)),
    }
    provincegraph = {
        "A1": set(),
        "B1": {"C1", "C2"},
        "C1": {"B1"},
        "C2": {"B1"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars=set())
    director.sync_player_wars("A", set(), warpairset={("B", "C")})

    movementorderlist = []
    summary = director.executeturn(movementorderlist, turnnumber=10)

    invadedtargets = {
        order["path"][-1]
        for order in movementorderlist
        if order["country"] == "B" and order["path"][-1] in {"C1", "C2"}
    }
    assert summary["invasionOrders"] >= 2
    assert "C1" in invadedtargets
    assert "C2" in invadedtargets


def test_npc_dominant_country_sends_multiple_waves_on_single_front():
    provincemap = {
        "A1": _province("A1", "A", controllercountry="A", troops=0, center=(0.0, 0.0)),
        "B1": _province("B1", "B", controllercountry="B", troops=180, center=(1.0, 0.0)),
        "B2": _province("B2", "B", controllercountry="B", troops=60, center=(1.0, 1.0)),
        "C1": _province("C1", "C", controllercountry="C", troops=90, center=(2.0, 0.0)),
    }
    provincegraph = {
        "A1": set(),
        "B1": {"C1", "B2"},
        "B2": {"B1"},
        "C1": {"B1"},
    }

    director, _events = _director(provincemap, provincegraph, playercountry="A", wars=set())
    director.sync_player_wars("A", set(), warpairset={("B", "C")})

    movementorderlist = []
    summary = director.executeturn(movementorderlist, turnnumber=11)

    frontlinewaves = [
        order
        for order in movementorderlist
        if order["country"] == "B" and order["path"][-1] == "C1"
    ]
    totalcommitted = sum(order["amount"] for order in frontlinewaves)

    assert summary["invasionOrders"] >= 2
    assert len(frontlinewaves) >= 2
    assert totalcommitted > 90
