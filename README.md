# Spiral Walk Automation Driver

Python tool that listens to MIDI clock + transport from a DAW and outputs MIDI CC automation on a virtual MIDI port. Designed for a "spiral walk" through scenes that each set value ranges and movement behaviors for multiple automation lanes.

## Quickstart

1) Install Python 3.10+ and create a virtualenv.
2) Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3) Create virtual MIDI ports (e.g., loopMIDI on Windows). Configure your DAW to send MIDI clock/transport to the input port and receive CC from the output port.
4) Run:
   ```
   python -m spiralwalk.cli list-ports
   python -m spiralwalk.cli run --config configs/example.yaml
   ```
   Use `--dry-run` to print events instead of sending MIDI.

### Calibration + mapping

To map CCs in your DAW without guessing:

- Sweep one CC: `python -m spiralwalk.cli run --config configs/example.yaml --calibrate --calibrate-cc 21`
- Hold a constant value: `... --hold 64`

Stops with Ctrl+C.

### Virtual ports

If your backend supports it (ALSA/CoreMIDI, some Windows drivers), you can ask the script to create virtual ports instead of loopMIDI-style routing:

```
python -m spiralwalk.cli run --config configs/example.yaml --virtual --virtual-in-name "Spiralwalk In" --virtual-out-name "Spiralwalk Out"
```

On Windows, many setups still require loopMIDI/loopBe; if virtual creation fails, fall back to an external virtual port.

Routing template: use two ports to avoid loops — `SpiralWalk_Clock_In` for DAW → Python clock/start/stop, `SpiralWalk_CC_Out` for Python → DAW CC.

## Repo layout

- `spiralwalk/` core modules: config, clock follower, spiral walker, lane curves, engine, MIDI I/O, CLI.
- `configs/starter_roles.yaml` stable lane roles + routing template (CC20–29).
- `configs/example.yaml` earlier example configuration.
- `tests/` light unit tests for spiral logic, curve generators, and clock simulation.
- `docs/UNDERSTANDING.md` mental model + ASCII map.
- `docs/DAW_SETUP_CUBASE.md` routing/mapping template.
- `docs/CONFIG_GUIDE.md` config keys and roles.

## Behavior

- Listens for MIDI Clock (0xF8) and Start/Stop (0xFA/0xFC). On Start the engine resets counters and begins emitting lane CC updates; on Stop it halts output.
- Clock subdivides PPQ (24) into musical divisions (1/4, 1/8, 1/16) and tracks bars (4/4). Phrase boundaries trigger a spiral-walk scene change.
- Each lane maps to a CC/channel and updates at a division using curve types (`sine`, `ramp`, `random_walk`, `step_hold`) with smoothing. Scenes provide per-lane value ranges.
- Rate limits CC output (default 200 messages/sec) and handles Ctrl+C gracefully.
- Arming: `--arm-ticks N` waits for N clock pulses after Start/Continue before emitting CC to avoid first-bar weirdness.
- Freeze: `--freeze-scene` holds the current scene; `--freeze-lane name` holds selected lanes.
- Session log / replay: `--session-log session.jsonl` writes bar snapshots; `--replay session.jsonl` replays logged CCs at a fixed interval.
- Meta lanes: roles `restraint` (compress ranges) and `contrast` (expand ranges) scale all other lanes; map CC28/29 to these for global control.
- Per-lane shaping: `shape` (linear/exp/log/s_curve), `deadband` (skip tiny changes), `slew_limit` (cap CC delta per tick).
- Scene order: define `transport.scene_order` or rely on natural sort so `scene10` comes after `scene2`.
- Reset semantics: Start = hard reset (unless `--soft-start`), Continue = soft resume (keeps lane phases/filters).
- Tempo-locked replay: `--replay-live` replays logs on bar boundaries driven by incoming clock/start/stop.

### Derive scenes from a performance log

After running with `--session-log session.jsonl`, propose scene ranges from the capture:

```
python -m spiralwalk.cli derive-scenes --log session.jsonl --scenes 8 --output configs/derived.yaml
```

This takes 10th/90th percentiles per lane in consecutive segments to suggest min/max pairs.

## Notes

- The DAW mapping from CC to plugin parameters is external to this tool.
- The random seed in config makes dry-run deterministic.
