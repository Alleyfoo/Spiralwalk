import argparse
import json
import sys
import time
from pathlib import Path

from .config import load_settings
from .engine import AutomationEngine
from .midi_io import MidiOutput, list_ports
from .derive import derive_scenes
from .replay import TempoReplay


def cmd_list_ports(_: argparse.Namespace) -> int:
    ins, outs = list_ports()
    print("MIDI Inputs:")
    for name in ins:
        print(f"  {name}")
    print("MIDI Outputs:")
    for name in outs:
        print(f"  {name}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)
    if args.replay:
        if args.replay_live:
            return replay_tempo_locked(
                settings=settings,
                path=args.replay,
                dry_run=args.dry_run,
                virtual=args.virtual,
                virtual_in_name=args.virtual_in_name,
                virtual_out_name=args.virtual_out_name,
                arm_ticks=args.arm_ticks,
            )
        return replay_session(
            settings=settings,
            path=args.replay,
            interval=args.replay_interval,
            dry_run=args.dry_run,
            virtual=args.virtual,
            virtual_out_name=args.virtual_out_name,
        )

    if args.calibrate or args.hold is not None:
        return run_calibration(
            settings,
            calibrate_cc=args.calibrate_cc,
            hold_value=args.hold,
            channel_override=args.calibrate_channel,
            dry_run=args.dry_run,
            virtual=args.virtual,
            virtual_out_name=args.virtual_out_name,
        )

    engine = AutomationEngine(
        settings=settings,
        dry_run=args.dry_run,
        freeze_scene=args.freeze_scene,
        frozen_lanes=args.freeze_lane,
        session_log_path=args.session_log,
        arm_ticks=args.arm_ticks,
        virtual_in=args.virtual,
        virtual_out=args.virtual,
        in_port_override=args.virtual_in_name,
        out_port_override=args.virtual_out_name,
        soft_start=args.soft_start,
    )
    engine.run()
    return 0


def _pick_calibration_lane(settings, calibrate_cc: int | None):
    if calibrate_cc is None:
        return settings.lanes[0].cc, settings.lanes[0].channel
    for lane in settings.lanes:
        if lane.cc == calibrate_cc:
            return lane.cc, lane.channel
    return calibrate_cc, settings.lanes[0].channel


def run_calibration(settings, calibrate_cc: int | None, hold_value: int | None, channel_override: int | None, dry_run: bool, virtual: bool, virtual_out_name: str | None) -> int:
    cc, channel = _pick_calibration_lane(settings, calibrate_cc)
    if channel_override is not None:
        channel = channel_override

    out_name = virtual_out_name or settings.midi.out_port_name
    out = MidiOutput(out_name, max_messages_per_sec=settings.midi.max_messages_per_sec, dry_run=dry_run, use_virtual=virtual)
    out.open()
    print(f"Calibration mode on CC {cc} channel {channel + 1} (Ctrl+C to exit)")
    try:
        if hold_value is not None:
            hold_value = max(0, min(127, hold_value))
            while True:
                out.send_cc(cc, hold_value, channel=channel)
                time.sleep(0.25)
        else:
            sweep = list(range(0, 128)) + list(range(126, -1, -1))
            while True:
                for v in sweep:
                    out.send_cc(cc, v, channel=channel)
                    time.sleep(0.02)
    except KeyboardInterrupt:
        print("Calibration stopped.")
    finally:
        out.close()
    return 0


def replay_session(settings, path: str, interval: float, dry_run: bool, virtual: bool, virtual_out_name: str | None) -> int:
    out_name = virtual_out_name or settings.midi.out_port_name
    out = MidiOutput(out_name, max_messages_per_sec=settings.midi.max_messages_per_sec, dry_run=dry_run, use_virtual=virtual)
    out.open()
    print(f"Replaying log from {path} every {interval} sec (Ctrl+C to stop)")
    lane_map = {lane.name: (lane.cc, lane.channel) for lane in settings.lanes}
    try:
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            lanes = data.get("lanes", {})
            for lane_name, value in lanes.items():
                mapping = lane_map.get(lane_name)
                if mapping is None:
                    continue
                cc, channel = mapping
                out.send_cc(cc, int(value), channel=channel)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Replay stopped.")
    finally:
        out.close()
    return 0


def replay_tempo_locked(settings, path: str, dry_run: bool, virtual: bool, virtual_in_name: str | None, virtual_out_name: str | None, arm_ticks: int) -> int:
    frames = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        frames.append({k: int(v) for k, v in data.get("lanes", {}).items()})
    replay = TempoReplay(
        settings=settings,
        frames=frames,
        virtual=virtual,
        in_port_override=virtual_in_name,
        out_port_override=virtual_out_name,
        arm_ticks=arm_ticks,
        dry_run=dry_run,
    )
    replay.run()
    return 0


def cmd_derive(args: argparse.Namespace) -> int:
    text = derive_scenes(args.log, scene_count=args.scenes)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote scenes to {args.output}")
    else:
        print(text)
    return 0


def cmd_listen_clock(args: argparse.Namespace) -> int:
    import mido
    settings = load_settings(args.config)
    port_name = settings.midi.in_port_name
    if not port_name:
        print("No MIDI input port configured.")
        return 1
    print(f"Listening for clock on {port_name} for up to {args.timeout} seconds...")
    start_time = time.time()
    tick_times = []
    clocks = 0

    def on_msg(msg):
        nonlocal clocks
        if msg.type == "clock":
            clocks += 1
            tick_times.append(time.time())
            if clocks % 24 == 0:
                elapsed = time.time() - start_time
                if elapsed > 0:
                    bpm = (clocks / 24) / (elapsed / 60)
                    print(f"Beat {clocks//24} approx BPM {bpm:.2f}")
        elif msg.type in ("start", "continue", "stop"):
            print(f"Transport: {msg.type}")

    with mido.open_input(port_name, callback=on_msg):
        while time.time() - start_time < args.timeout:
            time.sleep(0.1)
    if clocks == 0:
        print("No clock received.")
        return 1
    return 0


def _iter_ccs(cc_range):
    return range(cc_range[0], cc_range[1] + 1)


def cmd_send_test(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)
    out_name = settings.midi.out_port_name
    if not out_name:
        print("No MIDI output port configured.")
        return 1
    out = MidiOutput(out_name, max_messages_per_sec=settings.midi.max_messages_per_sec, dry_run=False, use_virtual=False)
    out.open()
    mode = args.mode
    hold_val = max(0, min(127, args.hold))
    cc_range = args.cc_range
    duration = args.seconds
    print(f"Sending test CCs ({mode}) to {out_name} for {duration}s on CCs {cc_range[0]}-{cc_range[1]}")
    start = time.time()
    try:
        while time.time() - start < duration:
            if mode == "hold":
                for cc in _iter_ccs(cc_range):
                    out.send_cc(cc, hold_val, channel=0)
                time.sleep(0.25)
            elif mode == "pulse":
                val = 127 if int((time.time() - start) * 2) % 2 == 0 else 0
                for cc in _iter_ccs(cc_range):
                    out.send_cc(cc, val, channel=0)
                time.sleep(0.25)
            else:  # sweep
                for val in list(range(0, 128, 8)) + list(range(127, -1, -8)):
                    for cc in _iter_ccs(cc_range):
                        out.send_cc(cc, val, channel=0)
                    time.sleep(0.01)
    except KeyboardInterrupt:
        print("Test stopped.")
    finally:
        out.close()
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    print("Doctor: listening for clock...")
    listen_args = argparse.Namespace(config=args.config, timeout=args.clock_seconds)
    rc = cmd_listen_clock(listen_args)
    if rc != 0:
        return rc
    print("Doctor: sending test CCs...")
    send_args = argparse.Namespace(
        config=args.config,
        mode=args.mode,
        hold=64,
        cc_range=[20, 29],
        seconds=args.send_seconds,
    )
    return cmd_send_test(send_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Spiral Walk Automation Driver")
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list-ports", help="List MIDI input/output ports")
    list_p.set_defaults(func=cmd_list_ports)

    run_p = sub.add_parser("run", help="Run the automation engine")
    run_p.add_argument("--config", required=True, help="Path to YAML/JSON config file")
    run_p.add_argument("--dry-run", action="store_true", help="Print CC events instead of sending MIDI")
    run_p.add_argument("--arm-ticks", type=int, default=0, help="Require this many clock ticks after Start before emitting CC")
    run_p.add_argument("--freeze-scene", action="store_true", help="Prevent spiral from changing scenes")
    run_p.add_argument("--freeze-lane", action="append", default=[], help="Lane names to freeze (can repeat)")
    run_p.add_argument("--session-log", help="Write JSONL session log to this path")
    run_p.add_argument("--replay", help="Replay a JSONL session log instead of running live")
    run_p.add_argument("--replay-interval", type=float, default=0.5, help="Seconds between log frames during replay")
    run_p.add_argument("--replay-live", action="store_true", help="Replay log tempo-locked to incoming clock (Start/Stop)")
    run_p.add_argument("--calibrate", action="store_true", help="Calibration mode: sweep CC 0→127→0 repeatedly")
    run_p.add_argument("--calibrate-cc", type=int, help="CC number to use for calibration")
    run_p.add_argument("--calibrate-channel", type=int, help="MIDI channel to use for calibration (0-15)")
    run_p.add_argument("--hold", type=int, help="Hold a constant CC value (0-127) for mapping")
    run_p.add_argument("--virtual", action="store_true", help="Create virtual MIDI in/out ports (if backend supports)")
    run_p.add_argument("--virtual-in-name", help="Name for virtual MIDI input port")
    run_p.add_argument("--virtual-out-name", help="Name for virtual MIDI output port")
    run_p.add_argument("--soft-start", action="store_true", help="Start does not reset lane state (hard reset is default)")
    run_p.set_defaults(func=cmd_run)

    derive_p = sub.add_parser("derive-scenes", help="Generate scene ranges from a session log (JSONL)")
    derive_p.add_argument("--log", required=True, help="Path to session log JSONL")
    derive_p.add_argument("--scenes", type=int, default=8, help="Number of scenes to propose")
    derive_p.add_argument("--output", help="Write derived YAML snippet to this file (otherwise print)")
    derive_p.set_defaults(func=cmd_derive)

    listen_p = sub.add_parser("listen-clock", help="Listen for MIDI clock/start/stop and print ticks/BPM")
    listen_p.add_argument("--config", required=True, help="Path to YAML/JSON config file")
    listen_p.add_argument("--timeout", type=float, default=10.0, help="Seconds to listen before exiting")
    listen_p.set_defaults(func=cmd_listen_clock)

    test_p = sub.add_parser("send-test", help="Send test CC messages to validate mapping")
    test_p.add_argument("--config", required=True, help="Path to YAML/JSON config file")
    test_p.add_argument("--mode", choices=["sweep", "pulse", "hold"], default="sweep", help="Test signal mode")
    test_p.add_argument("--hold", type=int, default=64, help="Value for hold mode")
    test_p.add_argument("--cc-range", nargs=2, type=int, metavar=("MIN", "MAX"), default=[20, 29], help="CC range to test (inclusive)")
    test_p.add_argument("--seconds", type=float, default=10.0, help="How long to run the test")
    test_p.set_defaults(func=cmd_send_test)

    doctor_p = sub.add_parser("doctor", help="Basic health check: listen to clock then send test CCs")
    doctor_p.add_argument("--config", required=True, help="Path to YAML/JSON config file")
    doctor_p.add_argument("--clock-seconds", type=float, default=5.0, help="Seconds to listen for clock")
    doctor_p.add_argument("--send-seconds", type=float, default=10.0, help="Seconds to send test CCs")
    doctor_p.add_argument("--mode", choices=["sweep", "pulse", "hold"], default="sweep", help="Test signal mode")
    doctor_p.set_defaults(func=cmd_doctor)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
