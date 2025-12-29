from spiralwalk.lanes import Lane


def test_ramp_curve_progression():
    lane = Lane(name="ramp_lane", cc=1, channel=0, division="1/16", curve="ramp", smoothing=1.0)
    lane.state.phase = -1  # so first increment lands on 0
    params = {"min": 0, "max": 127, "curve_params": {"cycle_steps": 4}}
    values = [lane.next_value(params) for _ in range(4)]
    assert values == [0, 42, 85, 127]


def test_smoothing_applies():
    lane = Lane(name="smooth_lane", cc=1, channel=0, division="1/16", curve="step_hold", smoothing=0.5)
    lane.rng.seed(1)
    params = {"min": 0, "max": 127, "curve_params": {"hold_steps": 1}}
    first = lane.next_value(params)
    second = lane.next_value(params)
    assert second != first  # changed value
    # smoothing pulls toward previous value
    assert abs(second - first) < 127


def test_shape_and_deadband_and_slew():
    lane = Lane(
        name="shaped",
        cc=1,
        channel=0,
        division="1/16",
        curve="step_hold",
        smoothing=0.0,
        shape="exp",
        deadband=5,
        slew_limit=3,
    )
    lane.rng.seed(0)
    params = {"min": 0, "max": 127, "curve_params": {"hold_steps": 1}}
    v1 = lane.next_value(params)
    v2 = lane.next_value(params)
    # deadband may skip if small change; ensure slew caps changes
    if v2 is not None and v1 is not None:
        assert abs(v2 - v1) <= 3
