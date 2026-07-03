from engine import movement
from engine.npc import NpcDirector


def _province(
    provinceid,
    country,
    troops=0,
    center=(0.0, 0.0),
    iscoastal=None,
    terrain="plains",
):
    province = {
        "id": provinceid,
        "ownercountry": country,
        "controllercountry": country,
        "country": country,
        "countrycolor": (90, 90, 90),
        "troops": troops,
        "center": center,
        "terrain": terrain,
    }
    if iscoastal is not None:
        province["iscoastal"] = iscoastal
    return province


def _squareprovince(provinceid, x, y):
    province = _province(provinceid, "A", center=(x + 0.5, y + 0.5))
    province["polygons"] = [
        {
            "points": [
                (x, y),
                (x + 1.0, y),
                (x + 1.0, y + 1.0),
                (x, y + 1.0),
            ]
        }
    ]
    return province


def _economyconfig():
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


def test_coastal_detection_finds_exposed_edges_but_not_interior_province():
    movement.bordersegmentcache.clear()
    provincemap = {}
    provincegraph = {}
    for y in range(3):
        for x in range(3):
            provinceid = f"P{x}{y}"
            provincemap[provinceid] = _squareprovince(provinceid, x, y)
            provincegraph[provinceid] = set()

    for y in range(3):
        for x in range(3):
            provinceid = f"P{x}{y}"
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighborid = f"P{x + dx}{y + dy}"
                if neighborid in provincemap:
                    provincegraph[provinceid].add(neighborid)

    coastalprovinceids = movement.buildcoastalprovinceidset(provincemap, provincegraph)

    assert "P11" not in coastalprovinceids
    assert provincemap["P11"]["iscoastal"] is False
    assert coastalprovinceids == set(provincemap) - {"P11"}


def test_naval_path_requires_two_coastal_endpoints():
    provincemap = {
        "A": _province("A", "Blue", iscoastal=True),
        "B": _province("B", "Red", iscoastal=True),
        "C": _province("C", "Red", iscoastal=False),
    }
    coastalprovinceids = {"A", "B"}

    assert movement.findnavalinvasionpath(
        "A",
        "B",
        provincemap,
        coastalprovinceidset=coastalprovinceids,
    ) == ["A", "B"]
    assert movement.findnavalinvasionpath(
        "A",
        "C",
        provincemap,
        coastalprovinceidset=coastalprovinceids,
    ) == []


def test_naval_order_waits_before_landing_and_resolving_combat():
    provincemap = {
        "A": _province("A", "Blue", center=(0.0, 0.0), iscoastal=True),
        "B": _province(
            "B",
            "Red",
            troops=3,
            center=(20.0, 0.0),
            iscoastal=True,
            terrain="mountains",
        ),
    }
    movementorderlist = [
        {
            "amount": 8,
            "path": ["A", "B"],
            "index": 0,
            "current": "A",
            "speedmodifier": 1.0,
            "controllercountry": "Blue",
            "country": "Blue",
            "countrycolor": (20, 30, 200),
            "isnavalinvasion": True,
        }
    ]

    movement.processmovementorders(
        movementorderlist,
        provincemap,
        emit=None,
        currentturnnumber=1,
        provincegraph={"A": set(), "B": set()},
    )

    assert len(movementorderlist) == 1
    assert movementorderlist[0]["navalturnstotal"] == 2
    assert movementorderlist[0]["navalturnsremaining"] == 1
    assert movement.getprovincecontroller(provincemap["B"]) == "Red"

    movement.processmovementorders(
        movementorderlist,
        provincemap,
        emit=None,
        currentturnnumber=2,
        provincegraph={"A": set(), "B": set()},
    )

    assert movementorderlist == []
    assert movement.getprovincecontroller(provincemap["B"]) == "Blue"
    assert provincemap["B"]["troops"] == 5


def test_distant_naval_invasion_takes_more_turns():
    provincemap = {
        "A": _province("A", "Blue", center=(0.0, 0.0), iscoastal=True),
        "B": _province("B", "Red", center=(95.0, 0.0), iscoastal=True),
    }
    navaltraveltime = movement.getnavalinvasiontraveltime("A", "B", provincemap)
    movementorderlist = [
        {
            "amount": 8,
            "path": ["A", "B"],
            "index": 0,
            "current": "A",
            "speedmodifier": 1.0,
            "controllercountry": "Blue",
            "country": "Blue",
            "countrycolor": (20, 30, 200),
            "isnavalinvasion": True,
            "navalturnstotal": navaltraveltime,
            "navalturnsremaining": navaltraveltime,
        }
    ]

    assert navaltraveltime == 4
    for turnnumber, expectedremaining in ((1, 3), (2, 2), (3, 1)):
        movement.processmovementorders(
            movementorderlist,
            provincemap,
            emit=None,
            currentturnnumber=turnnumber,
            provincegraph={"A": set(), "B": set()},
        )
        assert movementorderlist[0]["navalturnsremaining"] == expectedremaining
        assert movement.getprovincecontroller(provincemap["B"]) == "Red"

    movement.processmovementorders(
        movementorderlist,
        provincemap,
        emit=None,
        currentturnnumber=4,
        provincegraph={"A": set(), "B": set()},
    )
    assert movementorderlist == []
    assert movement.getprovincecontroller(provincemap["B"]) == "Blue"


def test_npc_can_invade_disconnected_enemy_coastline():
    provincemap = {
        "A_coast": _province(
            "A_coast",
            "A",
            troops=5,
            center=(0.0, 0.0),
            iscoastal=True,
        ),
        "B_coast": _province(
            "B_coast",
            "B",
            troops=30,
            center=(20.0, 0.0),
            iscoastal=True,
        ),
    }
    provincegraph = {"A_coast": set(), "B_coast": set()}
    director = NpcDirector(
        provincemap,
        provincegraph,
        countrytocolorlookup={"A": (10, 10, 10), "B": (20, 20, 20)},
        economyconfig=_economyconfig(),
    )
    director.setplayercountry("A")
    director.sync_player_wars("A", {"B"})
    movementorderlist = []

    summary = director.executeturn(movementorderlist, turnnumber=1)

    assert summary["invasionOrders"] >= 1
    assert any(
        order["country"] == "B"
        and order["path"] == ["B_coast", "A_coast"]
        and order["isnavalinvasion"] is True
        and order["navalturnstotal"] == 2
        and order["navalturnsremaining"] == 2
        for order in movementorderlist
    )
