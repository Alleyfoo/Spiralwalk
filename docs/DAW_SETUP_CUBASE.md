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
