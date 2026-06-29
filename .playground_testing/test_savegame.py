import json

from engine import savegame


def test_frontline_assignments_round_trip_through_json():
    assignments = [
        {
            "frontlineid": "Blue_frontline_1",
            "frontlineedgekeys": {
                ("Blue_1", "Red_1"),
                ("Blue_2", "Red_2"),
            },
            "frontlineedges": [
                {
                    "playerprovinceid": "Blue_1",
                    "foreignprovinceid": "Red_1",
                    "edgekey": ("Blue_1", "Red_1"),
                }
            ],
        }
    ]

    serialized = savegame.serializefrontlineassignments(assignments)
    jsondata = json.loads(json.dumps(serialized))
    restored = savegame.deserializefrontlineassignments(jsondata)

    assert restored[0]["frontlineedgekeys"] == assignments[0]["frontlineedgekeys"]
    assert restored[0]["frontlineedges"][0]["edgekey"] == ("Blue_1", "Red_1")
    assert isinstance(assignments[0]["frontlineedgekeys"], set)


def test_writes_save_with_serialized_frontline_assignments(tmp_path, monkeypatch):
    monkeypatch.setattr(savegame, "SAVES_DIRECTORY", str(tmp_path))
    assignments = [{
        "frontlineid": "Blue_frontline_1",
        "frontlineedgekeys": {("Blue_1", "Red_1")},
        "frontlineedges": [],
    }]
    snapshot = {
        "playercountry": "Blue",
        "frontlineassignmentlist": savegame.serializefrontlineassignments(assignments),
    }

    savegame.writesaveslot(1, snapshot)
    loaded = savegame.readsaveslot(1)
    restored = savegame.deserializefrontlineassignments(
        loaded["frontlineassignmentlist"]
    )

    assert restored[0]["frontlineedgekeys"] == {("Blue_1", "Red_1")}
