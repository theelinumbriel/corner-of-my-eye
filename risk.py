"""risk.py — scores how much attention a Claude Code permission request deserves: 1, 2 or 3.

  1  glance and approve   read-only, or editing a file inside this project (undoable)
  2  read it              runs code, installs things, fetches from the web, uses an app
  3  stop and think       deletes, pushes, sends data out, admin rights, touches
                          secrets or anything outside this project

Claude Code runs this as a PermissionRequest hook: it reads the request (JSON) on
stdin and writes "ask <level> <reason>" to /tmp/claude_lamp_state for lamp.py.
It prints nothing, so it never approves or denies anything itself: you still decide.
Deliberately simple rules you can read in one minute, not an AI judging an AI.
"""
import json
import os
import re
import sys

STATE = "/tmp/claude_lamp_state"

HIGH = [
    (r"\brm\s|-delete\b|-exec\s+rm|\bshred\b", "deletes files"),
    (r"\bgit\s+push\b", "pushes to a remote"),
    (r"\bgit\s+(reset\s+--hard|clean|checkout\s+--|restore)\b", "throws away git changes"),
    (r"\bsudo\b", "runs as admin"),
    (r"(curl|wget)[^|]*\|\s*(ba|z)?sh", "runs a script straight from the internet"),
    (r"\b(dd|mkfs|diskutil)\b", "touches disks"),
    (r"\bchmod\b|\bchown\b", "changes permissions"),
    (r"\b(ssh|scp|rsync|sftp)\b", "connects to another machine"),
    (r"\bcurl\b.*(-X\s*(POST|PUT|DELETE|PATCH)|--data|\s-d\s|-F\s)", "sends data out"),
    (r"\b(npm|cargo|gem)\s+publish\b|\btwine\s+upload\b", "publishes a package"),
    (r"\b(kill|killall|pkill)\b", "kills processes"),
    (r"(\.env\b|\.ssh|\.aws|id_rsa|\.zshrc|\.bashrc|\.claude/settings|keychain)", "touches secrets or config"),
    (r">\s*(~|/(?!tmp/|dev/null))", "writes outside the project"),
]
LOW_CMD = r"^\s*(ls|pwd|cat|head|tail|wc|echo|grep|rg|which|date|git\s+(status|diff|log|show|branch))\b"
READ_ONLY = {"Read", "Glob", "Grep", "LS", "NotebookRead", "WebSearch", "TodoWrite", "TaskList", "TaskGet"}
EDITS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def score(tool, inp, project):
    tool, inp = tool or "", inp or {}
    if tool in READ_ONLY:
        return 1, "only reads"
    if tool in EDITS:
        p = inp.get("file_path") or inp.get("notebook_path") or ""
        full = os.path.realpath(os.path.join(project, os.path.expanduser(p)))
        root = os.path.realpath(project)
        if re.search(HIGH[11][0], full):
            return 3, f"edits a secret/config file ({os.path.basename(full)})"
        if not (full + os.sep).startswith(root + os.sep):
            return 3, f"writes outside the project ({full})"
        return 1, f"edits {os.path.relpath(full, root)} in this project"
    if tool == "Bash":
        cmd = inp.get("command", "")
        for pat, why in HIGH:
            if re.search(pat, cmd):
                return 3, f"{why}: {cmd[:60]}"
        parts = [s for s in re.split(r"&&|\|\||;|\|", cmd) if s.strip()]
        if parts and all(re.match(LOW_CMD, s) for s in parts):
            return 1, f"only looks: {cmd[:60]}"
        return 2, f"runs: {cmd[:60]}"
    if tool == "WebFetch":
        return 2, f"fetches {inp.get('url', '')[:60]}"
    if tool.startswith("mcp__"):
        if re.search(r"send|post|delete|remove|create|update|write|publish|pay|transfer|share", tool, re.I):
            return 3, f"acts in an outside app ({tool})"
        return 2, f"reads an outside app ({tool})"
    return 2, f"uses {tool or 'a tool'}"


def main():
    try:
        data = json.load(sys.stdin)
        project = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
        level, why = score(data.get("tool_name"), data.get("tool_input"), project)
    except Exception:
        level, why = 2, "couldn't read the request"
    with open(STATE, "w") as f:
        f.write(f"ask {level} {why}".replace("\n", " "))


if __name__ == "__main__":
    main()
