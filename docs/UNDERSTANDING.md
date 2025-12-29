# Understanding Spiralwalk (Mental Model + Why It’s Useful)

Spiralwalk is a Python tool that listens to **DAW MIDI clock + transport** and outputs **MIDI CC automation**.  
Think of it as a **macro-conductor**: it doesn’t generate notes. It generates **movement** (automation) that can turn a static loop into a developing piece.

This document explains:
- what the parts are,
- how data flows,
- how it differs from a modular sequencer,
- and how to think about “scenes” and “lanes” musically.

---

## 1) Big idea in one sentence

**Spiralwalk walks through “scenes” and drives multiple automation lanes (CCs) in sync with your DAW.**

---

## 2) Architecture at a glance (ASCII map)

```
                     (DAW is the clock boss)


┌───────────────────────────────────────────────────────────────┐
│ DAW / Host                                                     │
│                                                                │
│ Sends: MIDI CLOCK + START/STOP/CONTINUE                        │
│ Receives: MIDI CC automation                                   │
└───────────────┬───────────────────────────────────────┬───────┘
                │                                       │
         (clock/transport in)                     (automation out)
                │                                       │
                v                                       v
┌──────────────────────────┐                   ┌──────────────────────────┐
│ MidiInput Port           │                   │ MidiOutput Port          │
│ (loopMIDI In / virtual)  │                   │ (loopMIDI Out / virtual) │
└───────────────┬──────────┘                   └───────────────┬──────────┘
                │                                               │
                v                                               │
┌───────────────────────┐                                       │
│ ClockFollower         │                                       │
│ - counts PPQ ticks    │                                       │
│ - tracks bars         │                                       │
│ - calls callbacks     │                                       │
└───────────┬───────────┘                                       │
            │ callbacks (1/16, 1/8, 1/4...)                     │
            v                                                   │
┌─────────────────────────────┐                                 │
│ AutomationEngine             │                                 │
│ - arming gate (arm_ticks)    │                                 │
│ - bar logging (JSONL)        │                                 │
│ - freeze lane/scene          │                                 │
│ - chooses current scene      │                                 │
└───────────┬─────────────────┘                                 │
            │ phrase boundaries                                  │
            v                                                   │
┌─────────────────────────────┐                                 │
│ SpiralWalker                 │                                 │
│ - chooses next scene         │                                 │
│ - avoids recent repeats      │                                 │
│ - occasional jumps           │                                 │
└───────────┬─────────────────┘                                 │
            │ current scene parameters                           │
            v                                                   │
┌─────────────────────────────────────────────────┐             │
│ Lanes                                           │             │
│ energy  brightness  space  time  motion ...     │             │
│ - curve generator (sine/ramp/...)               │             │
│ - smoothing/shape/deadband/slew                 │             │
│ - meta lanes: restraint/contrast reshape ranges │             │
└───────────┬───────────────────────────────────────┘             │
            │ CC messages (per lane)                               │
            └─────────────────────────────────────────────┘
```

---

## 3) Key concepts

### Transport / Clock
Spiralwalk does not invent time. It follows the DAW:
- **MIDI clock ticks** advance the internal counters.
- **Start/Stop/Continue** controls whether output is active.

### Lanes
A **lane** outputs one stream of CC values (0–127), at a musical division:
- e.g. every 1/16, 1/8, 1/4 note.
Each lane has a curve type (sine/ramp/random_walk/step_hold) plus shaping.

A lane is not “a track.” It’s a **modulation source**.

### Scenes
A **scene** is a **bounded behavior mode** for lanes.  
Each scene defines, per lane:
- min/max range
- optional curve parameters (e.g., random walk step size)

A scene is not “verse/chorus.”  
It’s more like: “in this section, brightness stays between 40–110 and space is allowed to wander.”

### Spiral Walker
The **SpiralWalker** chooses which scene is active at phrase boundaries.  
It uses:
- `k_step`: deterministic stepping through the scene pool
- `memory_k`: avoid immediate repeats
- `p_jump`: occasional “teleport” for contrast

Result: structured variation instead of a fixed playlist.

### Meta lanes: restraint + contrast
Two lanes can act globally:
- **restraint** shrinks other lanes’ ranges toward their midpoint
- **contrast** expands other lanes’ ranges

This gives you a single “tame vs wild” control without rewriting scenes.

---

## 4) Why this is not a modular sequencer (useful metaphor)

### Modular sequencer (typical)
In modular terms, a sequencer is mainly:
- clock in
- pitch/gate out
- maybe probability/ratchets/memory

It generates **events** (notes).

### Spiralwalk (what it really is)
Spiralwalk is closer to:
- multiple function generators / random sources
- controlled by a scene/preset walker
- all clocked by the DAW
- outputting **automation** (macro CV)

In modular metaphor:

- DAW clock = master clock
- SpiralWalker = preset/scene sequencer
- Lanes = LFOs + random walks + stepped modulation
- Scenes = “range limits + behavior constraints”
- MIDI CC out = CV out (for big knobs)

It generates **evolution**, not notes.

### Why that has value
Automation is arrangement.

Even a simple loop becomes a piece when:
- brightness changes over time,
- space grows and shrinks,
- texture becomes gritty then clean,
- energy swells, then recedes.

Spiralwalk gives you “long-form motion” without hand-drawing automation lanes.

---

## 5) What happens when you press Play

1) DAW sends **Start** and **MIDI clock**
2) Spiralwalk’s ClockFollower starts counting ticks/bars
3) If `--arm-ticks N` is used, Spiralwalk waits for N clock ticks after Start/Continue  
   (prevents “first-bar weirdness”)
4) On each lane’s division (e.g., 1/16), Spiralwalk:
   - reads current scene’s lane ranges
   - applies meta lanes (restraint/contrast)
   - generates lane value via curve + smoothing + shape
   - sends MIDI CC
5) On phrase boundary (e.g. every 8 bars):
   - SpiralWalker chooses next scene (unless frozen)

---

## 6) Practical workflow (how to use it musically)

### Step 1: Map CCs to meaningful macro targets
Do not map 10 lanes to 10 random plugin parameters.  
Map lanes to macro-style targets first:
- energy → drive / compressor input
- brightness → filter cutoff or EQ tilt
- space → reverb send/mix
- time → delay feedback (use deadband/slew)
- motion → chorus/phaser depth
- grain → saturation/bitcrush/noise layer

### Step 2: Use calibration and hold for mapping
- Sweep one CC for MIDI-learn: `--calibrate --calibrate-cc 21`
- Hold a value for stable mapping: `--hold 64`

### Step 3: Record and reuse good accidents
Run with a session log:
- `--session-log session.jsonl`

Then replay:
- `--replay session.jsonl`

Optional: derive scene ranges from a good run:
- `derive-scenes --log session.jsonl --scenes 8 --output configs/derived.yaml`

---

## 7) Controls and safety features

- **Arming (`--arm-ticks`)**: waits for stable clock before emitting CC
- **Freeze scene (`--freeze-scene`)**: hold current scene; lanes still move within it
- **Freeze lane (`--freeze-lane name`)**: hold the last value for that lane
- **Rate limit**: avoids sending too many MIDI messages per second
- **Deadband**: skip tiny changes (prevents jitter / reduces spam)
- **Slew limit**: caps step-to-step change (prevents parameter “teleporting”)

---

## 8) Glossary (fast lookup)

- **PPQ**: pulses per quarter note (MIDI clock is usually 24 PPQ)
- **Division**: musical update interval (1/16, 1/8, 1/4…)
- **Lane**: one modulation stream mapped to one CC
- **Scene**: per-lane min/max (and optional curve params) defining a behavior mode
- **Phrase**: number of bars between scene changes
- **Arming**: delay before emitting after transport start/continue
- **Deadband**: ignore small output changes
- **Slew limit**: cap output change per tick

---

## 9) What’s next (future modules)
Spiralwalk currently covers the “spiral walk + lane modulators” part.

A future expansion (inspired by multi-panel Max patches) could add:
- routing presets (which lanes affect which instruments)
- scene families + long-term arcs (intro → development → dissolve)
- live controls (hotkeys or MIDI controller input)
- feedback rules (“if energy stayed high too long, bias calmer scenes”)
