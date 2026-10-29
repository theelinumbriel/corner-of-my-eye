# Claude lamp

A one-digit display in the corner of your eye that shows what your coding agent is doing — so you notice when it needs you without a sound and without looking at its window.

| What you see | Meaning | Comes from (Claude Code hook) |
|---|---|---|
| a segment chasing around the edge | Claude is working | `UserPromptSubmit`, `PreToolUse`, `PostToolUse` |
| a **blinking 1**, slow (+ one tap) | low risk: glance and approve (read-only, or editing a file in this project) | `PermissionRequest` → `risk.py` |
| a **blinking 2** (+ double tap) | medium risk: read it (runs code, installs, fetches from the web, reads an outside app) | `PermissionRequest` → `risk.py` |
| a **blinking 3**, fast (+ long buzz) | high risk: stop and think (deletes, git push, sends data out, sudo, secrets, anything outside the project) | `PermissionRequest` → `risk.py` |
| a "u" for 4 s (+ one tap), then dark | Claude has finished its turn | `Stop` |
| dark | nothing happening | `SessionEnd` |

## Why

An agent is only as fast as the human who approves it, so the slow part of the loop is the moment it stops to ask "may I run this?". Sounds take over your attention; pop-ups hide behind other windows. Peripheral vision is the right channel: continuous motion for *working* fades into the background; a hard on/off blink for *needs you* breaks that rhythm. The digit triages before you look — a 1 you can approve on reflex, a 3 blinks faster and buzzes longer so you arrive already careful. The scorer (`risk.py`) is a page of plain rules, not a model; it never approves anything, only sets how loudly it asks.

Every state change is logged to `lamp_log.csv`; Ctrl+C prints average approval latency per risk level.

## How it works

`lamp_hooks.json` holds the Claude Code hooks (copy into `.claude/settings.json`); each hook writes a line to `/tmp/claude_lamp_state`. `lamp.py` watches that file and drives the display over USB. The Uno runs `haptic_buzzer.ino` from the companion [haptic-feedback](https://github.com/theelinumbriel/haptic-feedback) project.

## Try it without Claude

With the lamp running, in another Terminal:

    printf working > /tmp/claude_lamp_state
    printf 'ask 1 edits hello.txt' > /tmp/claude_lamp_state
    printf 'ask 3 deletes files' > /tmp/claude_lamp_state
    printf done > /tmp/claude_lamp_state
