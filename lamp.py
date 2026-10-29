"""lamp.py - drives the 7-segment display from Claude Code state.

Reads /tmp/claude_lamp_state and turns each line into light + a tap:
  working, ask 1|2|3 <why>, done, idle.

  python3 lamp.py            light + taps
  python3 lamp.py --quiet    light only
"""
import csv
import fcntl
import glob
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import serial  # noqa: E402

STATE = "/tmp/claude_lamp_state"
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lamp_log.csv")
BUZZ = "--quiet" not in sys.argv
SAY = "--bg" not in sys.argv
BLINK = {1: 0.8, 2: 0.4, 3: 0.15}
TAP = {1: "s", 2: "d", 3: "l"}
DONE_GLYPH, DONE_S = "m1C", 4.0
LABEL = {1: "glance & approve", 2: "read it", 3: "STOP AND THINK"}


def say(*a):
    if SAY:
        print(*a, flush=True)


def find_port():
    if os.environ.get("LAMP_PORT"):
        return os.environ["LAMP_PORT"]
    found = sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.wchusbserial*"))
    if not found:
        sys.exit("Uno not found. Plug it in (and close Haptic Chat / the Arduino IDE), then run this again.")
    return found[0]


def read_state():
    try:
        st = os.stat(STATE)
        with open(STATE) as f:
            return st.st_mtime_ns, f.read().strip()
    except OSError:
        return None, ""


def parse(line):
    parts = line.split(" ", 2)
    kind = parts[0] if parts else ""
    if kind == "ask":
        try:
            level = min(3, max(1, int(parts[1])))
        except (IndexError, ValueError):
            level = 2
        return kind, level, parts[2] if len(parts) > 2 else ""
    return kind, 0, ""


def summary(waits):
    if not waits:
        return
    print("\nHow long you took to answer:")
    for lvl in (1, 2, 3):
        w = waits.get(lvl, [])
        if w:
            print(f"  risk {lvl} ({LABEL[lvl]}): {len(w)} request(s), average {sum(w) / len(w):.1f} s")


def main(waits):
    lock = open("/tmp/claude_lamp.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("A lamp is already running in another window. Use that one (or Ctrl+C it first).")
    port = find_port()
    try:
        ser = serial.serial_for_url(port, 9600, timeout=0, exclusive=not port.startswith("loop://"))
    except serial.SerialException:
        sys.exit("The Uno is busy: close Haptic Chat, the Arduino IDE or the display fixer, then try again.")
    say(f"Connected to {port}. Waiting for the Uno to restart...")
    time.sleep(2.5)
    send = lambda c: ser.write(c.encode())  # noqa: E731
    send("t"); time.sleep(1.2); send("x")

    new_log = not os.path.exists(LOG)
    logf = open(LOG, "a", newline="")
    log = csv.writer(logf)
    if new_log:
        log.writerow(["time", "state", "risk", "reason", "seconds_in_previous_state"])

    last_mtime, _ = read_state()
    state, level, since = "idle", 0, time.time()
    blink_on, next_blink, done_until = False, 0.0, 0.0
    say("Lamp on. Ctrl+C to stop.\n")

    while True:
        mtime, line = read_state()
        now = time.time()
        if mtime is not None and mtime != last_mtime:
            last_mtime = mtime
            new, new_level, why = parse(line)
            if new in ("working", "ask", "done", "idle") and (new, new_level) != (state, level):
                spent = now - since
                if state == "ask":
                    waits.setdefault(level, []).append(spent)
                    say(f"           answered after {spent:.1f} s")
                log.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), new, new_level or "", why, f"{spent:.2f}"]); logf.flush()
                state, level, since = new, new_level, now
                stamp = time.strftime("%H:%M:%S")
                if new == "working":
                    say(stamp, "working")
                    send("t")
                elif new == "ask":
                    say(stamp, f"NEEDS YOU  risk {level} = {LABEL[level]}  ({why})")
                    if BUZZ:
                        send(TAP[level])
                    blink_on, next_blink = False, now
                elif new == "done":
                    say(stamp, "done")
                    if BUZZ:
                        send("s")
                    send(DONE_GLYPH); done_until = now + DONE_S
                else:
                    say(stamp, "idle")
                    send("x")
        if state == "ask" and now >= next_blink:
            blink_on = not blink_on
            send(str(level) if blink_on else "x")
            next_blink = now + BLINK[level]
        if state == "done" and done_until and now >= done_until:
            send("x"); done_until = 0.0
        if ser.in_waiting:
            ser.read(ser.in_waiting)
        time.sleep(0.03)


if __name__ == "__main__":
    waits = {}
    try:
        main(waits)
    except KeyboardInterrupt:
        print("\nLamp off.")
        summary(waits)
    except serial.SerialException as e:
        print(f"\nLost the Uno ({e}). Plug it back in and run this again.")
