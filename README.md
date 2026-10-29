# Claude lamp

A one-digit display in the corner of your eye that shows what your coding agent is doing, so you notice when it needs you without a sound and without looking at its window.

| What you see | Meaning | Comes from (Claude Code hook) |
|---|---|---|
| a segment chasing around the edge | Claude is working | `UserPromptSubmit`, `PreToolUse`, `PostToolUse` |
| a **blinking 1**, slow (+ one tap) | Claude needs approval, low risk: **glance and approve** (read-only, or editing a file in this project) | `PermissionRequest` → `risk.py` |
| a **blinking 2** (+ double tap) | medium risk: **read it** (runs code, installs, fetches from the web, reads an outside app) | `PermissionRequest` → `risk.py` |
| a **blinking 3**, fast (+ long buzz) | high risk: **stop and think** (deletes, git push, sends data out, sudo, secrets, anything outside the project) | `PermissionRequest` → `risk.py` |
| a "u" for 4 s (+ one tap), then dark | Claude has finished its turn | `Stop` |
| dark | nothing happening | `SessionEnd` |

## Why (the rationale)

**An agent is only as fast as the human who approves it.** Once Claude can run for minutes on its own, the slow part of the loop is the moment it stops to ask "may I run this?" while you're reading something else. Every second it waits for you is wasted.

**Sounds are the wrong channel for that.** A chime takes over your attention completely (foveal *and* auditory), it interrupts whoever is near you in a library or open office, and after a day you either tune it out or mute it. A pop-up has the opposite problem: it's hidden behind whatever window you're in.

**Peripheral vision is the right channel.** The edge of your vision is bad at detail but very good at motion and flicker. So the encoding is designed for it:
- *Working* is gentle, continuous motion. You get used to it within seconds and stop noticing it. That's the point: it reassures you without asking for anything.
- *Needs you* breaks that rhythm with a hard on/off blink, the strongest peripheral cue there is. A change in rhythm gets noticed even when the light itself has been there all along.
- *How much of you* is the digit. Not every approval deserves the same attention: reading a file and `rm -rf` arrive in the same identical dialog, so people end up either reading everything (slow) or rubber-stamping everything (dangerous). The lamp triages *before* you look: a 1 you can approve on reflex, a 3 blinks faster and buzzes longer so you arrive already careful. You spend attention where the risk is.
- The scorer (`risk.py`) is a page of plain rules (deletes? pushes? sends data out? outside the project?), not another model. Something that decides how much a human should trust an agent should be readable and predictable. It never approves anything itself; it only sets how loudly it asks.
- *Done* is still and then goes away by itself, so it needs nothing from you.
- Touch is the escalation channel. One quiet tap goes to you only, not the room, and can be turned off (`--quiet`).

This is "calm technology" (Weiser & Brown, 1995): information that moves between the periphery and the centre of attention only when it should. It's the same design problem as an industrial andon light or the status LED on a 3D printer. The new part is that the machine on the other end is an AI agent, so *being interrupted* is the critical resource, not compute.

**It measures itself.** Every state change is logged to `lamp_log.csv`. How long each `ask` lasted is your *approval latency*: how long the agent sat waiting for a human. Ctrl+C prints the average per risk level. The hypothesis: with the lamp, risk-1 answers get faster and risk-3 answers get *slower* (more deliberate). That's attention going where it should.

## How it works

1. `lamp_hooks.json` holds Claude Code hooks; the launcher copies it to `.claude/settings.json` in this folder. Each one runs `printf <state> > /tmp/claude_lamp_state` when Claude's state changes; the `PermissionRequest` hook runs `risk.py`, which reads the request and writes `ask <1-3> <reason>`. Hooks in a project's `.claude/settings.json` only apply when Claude Code runs in that folder, so nothing else on the computer changes.
2. `lamp.py` keeps the USB connection to the Uno open (opening it resets the Uno, so it's done only once), watches that file, and sends the display commands: `t` spinner, `1`–`3` digits, `m1C` "u", `x` clear, `s`/`d`/`l` taps.
3. The Uno runs `haptic_buzzer.ino` from the *haptic feedback from llm + chat window* project (same board, same wiring).

To use it in **every** project, copy the `"hooks"` block into `~/.claude/settings.json`.

## Try it without Claude

With the lamp running, in another Terminal:

    printf working > /tmp/claude_lamp_state
    printf 'ask 1 edits hello.txt' > /tmp/claude_lamp_state
    printf 'ask 3 deletes files' > /tmp/claude_lamp_state
    printf done > /tmp/claude_lamp_state
