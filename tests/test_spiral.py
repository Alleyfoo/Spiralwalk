from spiralwalk.spiral import SpiralWalker


def test_spiral_sequence_no_recent_repeats():
    walker = SpiralWalker(scene_count=8, k_step=5, memory_k=2, p_jump=0.0, seed=123)
    seq = [walker.on_phrase_boundary() for _ in range(6)]
    assert seq == [5, 2, 7, 4, 1, 6]


def test_spiral_respects_memory_window():
    walker = SpiralWalker(scene_count=4, k_step=1, memory_k=3, p_jump=0.0, seed=1)
    seq = [walker.on_phrase_boundary() for _ in range(4)]
    # with memory=3, it should skip recently used scenes and wrap
    assert len(set(seq)) == 4
