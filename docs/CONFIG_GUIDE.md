# Config Guide

## Files

- `configs/starter_roles.yaml`: stable lane roles + ports + scenes.
- `configs/example.yaml`: earlier example.

## Transport

- `phrase_bars`: bars per phrase before a scene change.
- `ppq_division`: MIDI clocks per quarter (24 typical).
- `scene_order`: explicit order; if omitted, natural sort keeps scene2 before scene10.

## Spiral

- `k_step`: step size around the scene ring (relatively prime to scene count).
- `memory_k`: avoid last K scenes.
- `p_jump`: probability of random jump.
- `seed`: deterministic random.

## MIDI

- `in_port_name`: clock/transport input (use SpiralWalk_Clock_In).
- `out_port_name`: CC output (use SpiralWalk_CC_Out).
- `max_messages_per_sec`: rate limit CCs.

## Lanes

Shared keys:

- `name`: lane id.
- `cc`: MIDI CC number.
- `channel`: MIDI channel (0-based).
- `division`: update rate ("1/16", "1/8", ...).
- `curve`: sine | ramp | random_walk | step_hold.
- `smoothing`: one-pole alpha (0..1).
- `role`: semantic role (energy/brightness/space/time/motion/focus/width/grain/restraint/contrast).
- `shape`: linear | exp | log | s_curve.
- `deadband`: skip CCs if delta is below this.
- `slew_limit`: cap per-tick delta.

## Scenes

Per scene, per lane:

- `min` / `max`: 0–127 range bounds.
- `curve_params`: curve-specific (e.g., `cycle_steps`, `step_size`, `hold_steps`).

## Meta lanes

- `restraint` squeezes ranges toward midpoints.
- `contrast` expands ranges.
- Map these to CC28/29; other lanes stay mapped to musical macros.

## Replay

- Wall-clock: `--replay session.jsonl --replay-interval 0.5`
- Tempo-locked: `--replay-live session.jsonl` (listens to clock/start/stop; emits frames on bars).

## Reset semantics

- Start = hard reset (clock/spiral/lane state/last values) unless `--soft-start`.
- Continue = soft resume.
