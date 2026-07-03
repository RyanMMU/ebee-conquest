from engine.runtime import getmapcacheplan


def test_stationary_no_hover_layer_warms_then_hits():
    key = ("camera", 1)

    first_hit, first_build = getmapcacheplan(True, key, None, None, None)
    assert (first_hit, first_build) == (False, False)

    second_hit, second_build = getmapcacheplan(True, key, None, key, None)
    assert (second_hit, second_build) == (False, True)

    third_hit, third_build = getmapcacheplan(True, key, key, key, None)
    assert (third_hit, third_build) == (True, False)


def test_stationary_hover_key_stays_on_live_vector_path():
    key = ("camera", 1, "mouse", 100, 200)

    cache_hit, cache_build = getmapcacheplan(True, key, key, key, key)

    assert (cache_hit, cache_build) == (False, False)
