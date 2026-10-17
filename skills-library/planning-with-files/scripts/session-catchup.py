#!/usr/bin/env python3
"""
Session Catchup Script for planning-with-files

Analyzes the previous session to find unsynced context after the last
planning file update. Designed to run on SessionStart.

Usage: python3 session-catchup.py [project-path]
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PLANNING_DIR_REL = os.environ.get("PLANNING_DIR", "").strip() or ".claude/planning"
PLANNING_FILE_NAMES = ["task_plan.md", "progress.md", "findings.md"]
SESSION_SOURCE_ENV = "PLANNING_SESSION_SOURCE"


def planning_files_for(project_path: str) -> List[Path]:
    base = Path(project_path)
    return [base / PLANNING_DIR_REL / name for name in PLANNING_FILE_NAMES]


def normalize_path(project_path: str) -> str:
    """Normalize project path to match Claude Code's internal representation.

    Claude Code stores session directories using the Windows-native path
    (e.g., C:\\Users\\...) sanitized with separators replaced by dashes.
    Git Bash passes /c/Users/... which produces a DIFFERENT sanitized
    string. This function converts Git Bash paths to Windows paths first.
    """
    p = project_path

    # Git Bash / MSYS2: /c/Users/... -> C:/Users/...
    if len(p) >= 3 and p[0] == '/' and p[2] == '/':
        p = p[1].upper() + ':' + p[2:]

    # Resolve to absolute path to handle relative paths and symlinks
    try:
        resolved = str(Path(p).resolve())
        # On Windows, resolve() returns C:\Users\... which is what we want
        if os.name == 'nt' or '\\' in resolved:
            p = resolved
    except (OSError, ValueError):
        pass

    return p


def sanitize_project_path(normalized_path: str) -> str:
    """Match Claude Code's project-directory sanitization.

    Keep underscores intact. Claude project paths distinguish `foo_bar`
    from `foo-bar`; collapsing both to `foo-bar` can cross-read sessions
    from a different project.
    """
    sanitized = normalized_path.replace('\\', '-').replace('/', '-').replace(':', '-')
    if sanitized.startswith('-'):
        sanitized = sanitized[1:]
    return sanitized


def detect_session_source() -> str:
    """Pick the session backend without depending on the script install path."""
    explicit_source = os.environ.get(SESSION_SOURCE_ENV, "").strip().lower()
    if explicit_source in {"codex", "claude", "none"}:
        return explicit_source

    if any(key.startswith("CODEX_") and value for key, value in os.environ.items()):
        return "codex"

    if any(key.startswith("CLAUDE_") and value for key, value in os.environ.items()):
        return "claude"

    return "claude"


def get_project_dir(project_path: str) -> Tuple[Optional[Path], Optional[str]]:
    """Resolve session storage path for the current runtime variant."""
    normalized = normalize_path(project_path)
    sanitized = sanitize_project_path(normalized)
    session_source = detect_session_source()

    if session_source == "none":
        return None, (
            f"[planning-with-files] Session catchup skipped: {SESSION_SOURCE_ENV}=none."
        )

    if session_source == "codex":
        return None, (
            "[planning-with-files] Session catchup skipped: Codex runtime detected. "
            "Codex stores sessions in ~/.codex/sessions and native Codex parsing is "
            "not implemented yet."
        )

    claude_path = Path.home() / '.claude' / 'projects' / sanitized
    return claude_path, None


def get_sessions_sorted(project_dir: Path) -> List[Path]:
    """Get all session files sorted by modification time (newest first)."""
    sessions = list(project_dir.glob('*.jsonl'))
    main_sessions = [s for s in sessions if not s.name.startswith('agent-')]
    return sorted(main_sessions, key=lambda p: p.stat().st_mtime, reverse=True)


def parse_session_messages(session_file: Path) -> List[Dict]:
    """Parse all messages from a session file, preserving order."""
    messages = []
    with open(session_file, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f):
            try:
                data = json.loads(line)
                data['_line_num'] = line_num
                messages.append(data)
            except json.JSONDecodeError:
                pass
    return messages


def find_last_planning_update(messages: List[Dict]) -> Tuple[int, Optional[str]]:
    """
    Find the last time a planning file was written/edited.
    Returns (line_number, filename) or (-1, None) if not found.
    """
    last_update_line = -1
    last_update_file = None

    for msg in messages:
        msg_type = msg.get('type')

        if msg_type == 'assistant':
            content = msg.get('message', {}).get('content', [])
            if isinstance(content, list):
                for item in content:
                    if item.get('type') == 'tool_use':
                        tool_name = item.get('name', '')
                        tool_input = item.get('input', {})

                        if tool_name in ('Write', 'Edit'):
                            file_path = tool_input.get('file_path', '')
                            normalized_path = file_path.replace("\\", "/")
                            for pf in PLANNING_FILE_NAMES:
                                if normalized_path.endswith(pf):
                                    last_update_line = msg['_line_num']
                                    last_update_file = pf

    return last_update_line, last_update_file


def extract_messages_after(messages: List[Dict], after_line: int) -> List[Dict]:
    """Extract conversation messages after a certain line number."""
    result = []
    for msg in messages:
        if msg['_line_num'] <= after_line:
            continue

        msg_type = msg.get('type')
        is_meta = msg.get('isMeta', False)

        if msg_type == 'user' and not is_meta:
            content = msg.get('message', {}).get('content', '')
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        content = item.get('text', '')
                        break
                else:
                    content = ''

            if content and isinstance(content, str):
                if content.startswith(('<local-command', '<command-', '<task-notification')):
                    continue
                if len(content) > 20:
                    result.append({'role': 'user', 'content': content, 'line': msg['_line_num']})

        elif msg_type == 'assistant':
            msg_content = msg.get('message', {}).get('content', '')
            text_content = ''
            tool_uses = []

            if isinstance(msg_content, str):
                text_content = msg_content
            elif isinstance(msg_content, list):
                for item in msg_content:
                    if item.get('type') == 'text':
                        text_content = item.get('text', '')
                    elif item.get('type') == 'tool_use':
                        tool_name = item.get('name', '')
                        tool_input = item.get('input', {})
                        if tool_name == 'Edit':
                            tool_uses.append(f"Edit: {tool_input.get('file_path', 'unknown')}")
                        elif tool_name == 'Write':
                            tool_uses.append(f"Write: {tool_input.get('file_path', 'unknown')}")
                        elif tool_name == 'Bash':
                            cmd = tool_input.get('command', '')[:80]
                            tool_uses.append(f"Bash: {cmd}")
                        else:
                            tool_uses.append(f"{tool_name}")

            if text_content or tool_uses:
                result.append({
                    'role': 'assistant',
                    'content': text_content[:600] if text_content else '',
                    'tools': tool_uses,
                    'line': msg['_line_num']
                })

    return result


def main():
    project_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    # Check if planning files exist (indicates active task)
    has_planning_files = any(path.exists() for path in planning_files_for(project_path))
    if not has_planning_files:
        # No planning files in this project; skip catchup to avoid noise.
        return

    project_dir, skip_reason = get_project_dir(project_path)
    if skip_reason:
        print(skip_reason)
        return

    if not project_dir.exists():
        # No previous sessions, nothing to catch up on
        return

    sessions = get_sessions_sorted(project_dir)
    if len(sessions) < 1:
        return

    # Find a substantial previous session
    target_session = None
    for session in sessions:
        if session.stat().st_size > 5000:
            target_session = session
            break

    if not target_session:
        return

    messages = parse_session_messages(target_session)
    last_update_line, last_update_file = find_last_planning_update(messages)

    # No planning updates in the target session; skip catchup output.
    if last_update_line < 0:
        return

    # Only output if there's unsynced content
    messages_after = extract_messages_after(messages, last_update_line)

    if not messages_after:
        return

    # Output catchup report
    print("\n[planning-with-files] SESSION CATCHUP DETECTED")
    print(f"Previous session: {target_session.stem}")

    print(f"Last planning update: {last_update_file} at message #{last_update_line}")
    print(f"Unsynced messages: {len(messages_after)}")

    print("\n--- UNSYNCED CONTEXT ---")
    for msg in messages_after[-15:]:  # Last 15 messages
        if msg['role'] == 'user':
            print(f"USER: {msg['content'][:300]}")
        else:
            if msg.get('content'):
                print(f"CLAUDE: {msg['content'][:300]}")
            if msg.get('tools'):
                print(f"  Tools: {', '.join(msg['tools'][:4])}")

    print("\n--- RECOMMENDED ---")
    print("1. Run: git diff --stat")
    print(
        "2. Read: "
        + f"{PLANNING_DIR_REL}/task_plan.md, "
        + f"{PLANNING_DIR_REL}/progress.md, "
        + f"{PLANNING_DIR_REL}/findings.md"
    )
    print("3. Update planning files based on above context")
    print("4. Continue with task")


if __name__ == '__main__':
    main()
