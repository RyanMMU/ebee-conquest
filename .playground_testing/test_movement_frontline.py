from engine import movement


def _province(provinceid, controllercountry, troops, center):
    return {
        "id": provinceid,
        "ownercountry": controllercountry,
        "controllercountry": controllercountry,
        "country": controllercountry,
        "countrycolor": (90, 90, 90),
        "troops": troops,
        "center": center,
        "frontlineassignments": {},
    }


def test_interrupted_defender_resumes_after_successful_defense():
    provincemap = {
        "A": _province("A", "Blue", 0, (0.0, 0.0)),
        "B": _province("B", "Blue", 0, (1.0, 0.0)),
        "C": _province("C", "Blue", 0, (2.0, 0.0)),
        "X": _province("X", "Red", 0, (1.0, 1.0)),
    }

    movementorderlist = [
        {
            "amount": 3,
            "path": ["X", "B"],
            "index": 0,
            "current": "X",
            "speedmodifier": 1.0,
            "controllercountry": "Red",
            "country": "Red",
            "countrycolor": (200, 50, 50),
        },
        {
            "amount": 5,
            "path": ["A", "B", "C"],
            "index": 1,
            "current": "B",
            "speedmodifier": 1.0,
            "controllercountry": "Blue",
            "country": "Blue",
            "countrycolor": (50, 50, 200),
        },
    ]

    movement.processmovementorders(
        movementorderlist,
        provincemap,
        emit=None,
        currentturnnumber=5,
    )

    assert len(movementorderlist) == 1
    survivingorder = movementorderlist[0]
    assert survivingorder["country"] == "Blue"
    assert survivingorder["current"] == "B"
    assert survivingorder["amount"] == 2
    assert survivingorder.get("_resumeonturn") == 6
    assert provincemap["B"]["troops"] == 0

    movement.processmovementorders(
        movementorderlist,
        provincemap,
        emit=None,
        currentturnnumber=6,
    )

    assert movementorderlist == []
    assert provincemap["C"]["troops"] == 2


def test_frontline_division_rebalances_forward_when_border_moves(monkeypatch):
    sharedborders = {
        frozenset(("E1", "F1")),
    }

    def fake_sharedbordersegments(firstprovince, secondprovince, **_kwargs):
        if frozenset((firstprovince["id"], secondprovince["id"])) in sharedborders:
            return [((0.0, 0.0), (1.0, 0.0))]
        return []

    monkeypatch.setattr(movement, "getsharedbordersegments", fake_sharedbordersegments)

    provincemap = {
        "P1": _province("P1", "Blue", 10, (0.0, 0.0)),
        "E1": _province("E1", "Blue", 0, (1.0, 0.0)),
        "F1": _province("F1", "Red", 0, (2.0, 0.0)),
    }
    movement.setprovincefrontlinetroops(provincemap["P1"], "fl_1", 10)

    provincegraph = {
        "P1": {"E1"},
        "E1": {"P1", "F1"},
        "F1": {"E1"},
    }
    movementorderlist = []
    frontlineassignment = {
        "frontlineid": "fl_1",
        "country": "Blue",
        "anchorprovinceid": "P1",
        "targetcountry": "Red",
        "nearbydepth": 2,
        "fallbackforeignprovinceid": "F1",
        "active": True,
        "frontlineprovinceids": ["P1"],
        "frontlineedgekeys": set(),
        "frontlineedges": [],
        "transferplan": [],
    }

    refreshresult = movement.refreshfrontlineassignment(
        frontlineassignment,
        provincemap,
        provincegraph,
        movementorderlist,
        emit=None,
        currentturnnumber=7,
    )

    assert refreshresult["success"] is True
    assert frontlineassignment["anchorprovinceid"] == "E1"
    assert frontlineassignment["frontlineprovinceids"] == ["E1"]
    assert provincemap["P1"]["troops"] == 0
    assert movement.getprovincefrontlinetroops(provincemap["P1"], "fl_1") == 0
    assert len(movementorderlist) == 1
    assert movementorderlist[0]["frontlineid"] == "fl_1"
    assert movementorderlist[0]["path"] == ["P1", "E1"]

    movement.processmovementorders(
        movementorderlist,
        provincemap,
        emit=None,
        currentturnnumber=8,
    )

    assert movementorderlist == []
    assert provincemap["E1"]["troops"] == 10
    assert movement.getprovincefrontlinetroops(provincemap["E1"], "fl_1") == 10


def test_balanced_frontline_does_not_shuffle_when_anchor_reorders_targets():
    transferplanresult = movement.buildbalancedtransferplan(
        {
            "A": 5,
            "B": 5,
        },
        ["B", "A"],
    )

    assert transferplanresult["totalassignedtroops"] == 10
    assert transferplanresult["transferplan"] == [
        {"sourceprovinceid": "B", "targetprovinceid": "B", "amount": 5},
        {"sourceprovinceid": "A", "targetprovinceid": "A", "amount": 5},
    ]
