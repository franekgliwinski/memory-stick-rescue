"""Bounded release allowlist and common accidental-private-data checks. Not a secret scanner guarantee."""
import json
import re
from pathlib import Path

ALLOWED = {
    '.gitattributes', '.gitignore', 'LICENSE', 'README.md',
    'docs/START-PL.md', 'docs/windows.md', 'docs/linux.md', 'docs/macos.md', 'docs/SAFETY.md', 'docs/TESTED.md',
    'linux/import_card.py', 'linux/inspect_reader.py', 'macos/diagnose.py',
    'tests/test_integrity.py', 'tools/verify_backup.py', 'tools/check_source.py',
    'windows/Import-MemoryStick.ps1', 'windows/Import Memory Stick.cmd', 'windows/Setup-Windows.ps1',
}


def audit(root):
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*')
              if p.is_file() and '.git' not in p.relative_to(root).parts and '__pycache__' not in p.relative_to(root).parts}
    if actual != ALLOWED:
        raise ValueError('Source allowlist mismatch: ' + repr(sorted(actual ^ ALLOWED)))
    # Patterns are assembled to avoid matching the checker's own source.
    patterns = [r'[A-Za-z]:[\\/]Users[\\/][a-zA-Z]', r'/' + r'Users/[a-zA-Z]',
                r'gh' + r'p_[A-Za-z0-9]{30,}', r'github' + r'_pat_[A-Za-z0-9_]{20,}',
                r'sk' + r'-[A-Za-z0-9_-]{32,}', r'-----BEGIN ' + r'(?:RSA |OPENSSH |EC )?PRIVATE KEY']
    for relative in sorted(actual):
        path = root / relative
        if path.is_symlink() or path.stat().st_size > 100_000:
            raise ValueError('Unexpected symlink or oversized source: ' + relative)
        content = path.read_text(encoding='utf-8-sig')
        if any(re.search(pattern, content) for pattern in patterns):
            raise ValueError('Potential private data in: ' + relative)
    return {'status': 'PASS', 'source_files': len(actual), 'scope': 'Explicit source allowlist; no media or binary dependencies'}


if __name__ == '__main__':
    try:
        print(json.dumps(audit(Path(__file__).resolve().parents[1])))
    except (OSError, ValueError) as exc:
        print(json.dumps({'status': 'FAILED', 'error': str(exc)}))
        raise SystemExit(1)
