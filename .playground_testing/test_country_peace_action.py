from game.ingame_ui import InGameUI


def test_peace_negotiation_is_available_only_for_active_player_war():
    assert InGameUI.cannegotiatepeace(
        "Malaysia",
        "Thailand",
        {"Thailand"},
    )
    assert not InGameUI.cannegotiatepeace(
        "Malaysia",
        "Thailand",
        set(),
    )
    assert not InGameUI.cannegotiatepeace(
        "Malaysia",
        "Malaysia",
        {"Malaysia"},
    )
    assert not InGameUI.cannegotiatepeace(
        None,
        "Thailand",
        {"Thailand"},
    )
