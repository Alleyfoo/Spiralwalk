from spiralwalk.clock import ClockFollower


def test_clock_counts_divisions():
    clock = ClockFollower()
    sixteenth_hits = []

    def on_sixteenth(bar, quarter, tick):
        sixteenth_hits.append((bar, quarter, tick))

    clock.register_callback("1/16", on_sixteenth)

    clock.start()
    for _ in range(96):  # one bar of 4/4 at 24 ppq
        clock.handle_clock_tick()
    assert clock.bar == 1
    assert len(sixteenth_hits) == 16


def test_stop_halts_ticks():
    clock = ClockFollower()
    clock.start()
    clock.handle_clock_tick()
    clock.stop()
    before = clock.tick_count
    clock.handle_clock_tick()
    assert clock.tick_count == before
