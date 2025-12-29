# DAW Setup (Cubase-oriented)

Goal: one repeatable template that avoids MIDI loops.

## Ports

- SpiralWalk_Clock_In (DAW → Python): clock/start/stop only.
- SpiralWalk_CC_Out (Python → DAW): CC automation only.
- If virtual ports fail on Windows, create two loopMIDI ports with these names.

## Cubase template

1) Devices > MIDI Port Setup: enable sending clock to SpiralWalk_Clock_In; disable “in all MIDI inputs” for the CC output to avoid feedback.
2) Project: add a MIDI track “SpiralWalk Control”.
   - Input: SpiralWalk_CC_Out.
   - Output: target instrument (or MIDI insert/router).
3) Transport > Project Synchronization: send MIDI Clock to SpiralWalk_Clock_In.
4) Save as template “SpiralWalk Template”.

## Mapping strategy (keep roles stable)

Map CC20–27 to macro-style targets on one instrument first:

- CC20 energy → Drive/Comp input.
- CC21 brightness → Filter cutoff / EQ tilt.
- CC22 space → Reverb send/mix.
- CC23 time → Delay feedback/time (use deadband/slew in config).
- CC24 motion → Chorus/Phaser mix.
- CC25 focus → Compressor threshold / transient shaper.
- CC26 width → Stereo width/spread.
- CC27 grain → Distortion/bitcrush/noise.
- CC28 restraint (meta) → optionally map to a global macro or leave internal.
- CC29 contrast (meta) → optional global macro or internal only.

## First run

1) Dry-run to verify transport:  
   `python -m spiralwalk.cli run --config configs/starter_roles.yaml --dry-run --arm-ticks 8`
2) Live with logging:  
   `python -m spiralwalk.cli run --config configs/starter_roles.yaml --arm-ticks 8 --session-log session.jsonl`
3) Map/learn CCs in Cubase while running `--calibrate --calibrate-cc 21` (or other CC).

## Avoiding loops

- Do not echo SpiralWalk_CC_Out back into SpiralWalk_Clock_In.
- Keep control input (if added later) on a separate port from clock.

## Outline (fill with screenshots later)

1) Create virtual MIDI ports (loopMIDI)  
   - SpiralWalk_Clock_In (DAW → Python)  
   - SpiralWalk_CC_Out (Python → DAW)

2) Configure Cubase to send MIDI clock/transport  
   - Transport settings → enable clock to SpiralWalk_Clock_In  
   - Ensure Start/Stop is sent

3) Create Spiralwalk Control track  
   - MIDI track input: SpiralWalk_CC_Out  
   - Route to instrument or control rack  
   - Disable echo back to Clock_In

4) Map CC to plugin parameters  
   - Use MIDI Learn / Quick Controls / MIDI Remote  
   - Map CC20–CC27 to macros (not random params)  
   - Map CC28/CC29 optionally (restraint/contrast) as performance macros

5) Test procedure  
   - Run `python -m spiralwalk.cli list-ports`  
   - Run `python -m spiralwalk.cli run --config configs/starter_roles.yaml --dry-run --arm-ticks 8`  
   - Run `python -m spiralwalk.cli run --config configs/starter_roles.yaml --calibrate --calibrate-cc 21`  
   - Run live with `--session-log`

6) Troubleshooting  
   - No movement: check clock input port + DAW sending clock  
   - Movement but jitter: raise deadband/slew or lower update rate  
   - First-bar weirdness: increase arm-ticks  
   - MIDI feedback loop: verify port routing

## Validation
- `python -m spiralwalk.cli listen-clock --config configs/starter_roles.yaml` → press play in DAW → see ticks/BPM.
- `python -m spiralwalk.cli send-test --config configs/starter_roles.yaml --mode sweep --seconds 5` → mapped knobs should move.
- `python -m spiralwalk.cli run --config configs/starter_roles.yaml --arm-ticks 8 --session-log session.jsonl` → full run with logging.
