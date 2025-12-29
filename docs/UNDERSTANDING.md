# SpiralWalk: Mental Model

Use this when Future-You forgets why this exists.

## What it is

- A clock-following macro-modulation driver.
- Listens to MIDI clock/start/stop from the DAW.
- Chooses “scenes” (behavior envelopes) via a spiral walk.
- Drives multiple lanes (CC20–29) that act like macro knobs.
- Meta lanes (restraint, contrast) reshape the others globally.

## ASCII map

```
                      (DAW is the clock boss)
┌───────────────────────────────────────────────────────────────┐
│                           DAW / Cubase                        │
│  Sends: MIDI CLOCK + START/STOP/CONTINUE                      │
│  Receives: MIDI CC automation                                 │
└───────────────┬───────────────────────────────────────┬───────┘
                │                                       │
         (clock/transport in)                     (automation out)
                │                                       │
                v                                       v
┌──────────────────────────┐                   ┌──────────────────────────┐
│      MidiInput Port       │                   │      MidiOutput Port      │
│   SpiralWalk_Clock_In     │                   │    SpiralWalk_CC_Out      │
└───────────────┬──────────┘                   └───────────────┬──────────┘
                │                                               │
                v                                               │
        ┌───────────────────────┐                               │
        │     ClockFollower      │                               │
        │  - counts PPQ ticks    │                               │
        │  - tracks bars         │                               │
        │  - emits divisions     │                               │
        └───────────┬───────────┘                               │
                    │ callbacks (1/16, 1/8, 1/4...)              │
                    v                                           │
        ┌─────────────────────────────┐                         │
        │       AutomationEngine       │                         │
        │  - arming (arm_ticks)        │                         │
        │  - bar logging               │                         │
        │  - freeze lane/scene         │                         │
        │  - applies meta scaling      │                         │
        └───────────┬─────────────────┘                         │
                    │ phrase boundaries                          │
                    v                                            │
        ┌─────────────────────────────┐                          │
        │        SpiralWalker          │                          │
        │  - k-step, memory, jump      │                          │
        │  - scene order or natural    │                          │
        └───────────┬─────────────────┘                          │
                    │ current scene parameters                   │
                    v                                           │
        ┌─────────────────────────────────────────────────┐     │
        │                      Lanes                       │     │
        │  CC20–27: energy, brightness, space, time, ...   │     │
        │  CC28–29: restraint, contrast (meta)             │     │
        │  - curves + smoothing/shape/deadband/slew        │     │
        │  - meta reshapes ranges                          │     │
        └───────────┬───────────────────────────────────────┘     │
                    │ CC messages (per lane)                       │
                    └─────────────────────────────────────────────┘
```

## Why it’s not “just a sequencer”

- Modular sequencer metaphor:
  - Clock in → notes/gates out, some probability/ratchets.
  - Focuses on event generation (notes).
- SpiralWalk metaphor:
  - Clock in → macro-modulation out.
  - Scenes are “behavior envelopes” (bounds + curve hints).
  - Lanes are CV-like modulators for big knobs (energy, brightness, space…).
  - Meta lanes reshape everything (restraint squeezes ranges, contrast expands).
- Value: turns a static loop into an evolving arrangement via automation, not note changes. “Automation is arrangement.”

## Reset semantics (what Start vs Continue means)

- Start: hard reset — clock, spiral, lane state (phase/filters), last values cleared. Use this for a clean downbeat.
- Continue: soft resume — keeps lane state/filters/last values; clock resumes.
- CLI `--soft-start`: opt into soft behavior on Start if you really want to keep motion.

## Scenes in plain language

- A scene is a bounded character: per-lane min/max and optional curve params.
- Example: “Spacey intro” = low energy range, wide space range, slow motion.
- SpiralWalk hops scenes every phrase: new bounds, same lane roles.

## Lane roles (stable mapping, not chaos knobs)

- CC20 energy: drive/comp input/velocity bias.
- CC21 brightness: filter cutoff / tilt EQ.
- CC22 space: reverb send/mix.
- CC23 time: delay feedback/time/mod depth (higher deadband + slew).
- CC24 motion: chorus/phaser mix (step-hold OK).
- CC25 focus: dynamics/transient emphasis.
- CC26 width: stereo width/spread.
- CC27 grain: distortion/bitcrush/noise.
- CC28 restraint (meta): compress all ranges toward mids.
- CC29 contrast (meta): expand ranges; more change between scenes.

## Safety + feel

- Arming: wait N clocks after Start (`--arm-ticks`) to dodge “first bar weirdness.”
- Deadband/slew: jitter control. Use stricter deadband/slew on time/space.
- Smoothing: character, not safety. Use lightly.

## Replay modes

- Wall-clock replay: fixed interval (quick check).
- Tempo-locked replay: listens to clock/start/stop; emits frames on bars. Use for “perform once, rerun in sync.”
