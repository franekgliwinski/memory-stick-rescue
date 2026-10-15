"""Offline integrity verification. Never opens the USB reader or modifies a backup."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(1024 * 1024):
            h.update(data)
    return h.hexdigest()


def safe_file(root, relative):
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError('Invalid manifest path')
    p = PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or PureWindowsPath(relative).drive or ':' in relative:
        raise ValueError('Path escapes backup')
    path = root.joinpath(*p.parts)
    if root.resolve() not in path.resolve().parents:
        raise ValueError('Path escapes backup')
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != root.parent):
        raise ValueError('Symlinks are not supported in a verified backup')
    if not path.is_file():
        raise ValueError('Missing backup file')
    return path


def verify(backup):
    backup = Path(backup).resolve()
    manifest_path = backup / 'manifest.json'
    if manifest_path.is_symlink():
        raise ValueError('Manifest must be a regular file')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    if manifest.get('status') != 'VERIFIED_COPY' or manifest.get('cleanup_complete') is not True:
        raise ValueError('Import was not successfully completed')
    files = manifest.get('files')
    if not isinstance(files, list) or manifest.get('files_copied') != len(files) or manifest.get('expected_file_count') != len(files):
        raise ValueError('Manifest file count mismatch')
    root = backup / 'Files'
    if not root.is_dir() or root.is_symlink():
        raise ValueError('Missing regular Files directory')
    seen = set()
    total = 0
    for entry in files:
        relative = entry['path']
        path = safe_file(root, relative)
        normalized = path.relative_to(root).as_posix()
        if normalized.casefold() in seen:
            raise ValueError('Duplicate or case-colliding manifest path')
        seen.add(normalized.casefold())
        if entry.get('verified') is not True or entry['sha256_source_stream'] != entry['sha256_copy']:
            raise ValueError('Source and destination hashes disagree')
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256_copy']:
            raise ValueError('Backup file integrity failure')
        total += entry['bytes']
    actual = set()
    for p in root.rglob('*'):
        if p.is_symlink():
            raise ValueError('Unexpected symlink in backup')
        if p.is_file():
            actual.add(p.relative_to(root).as_posix().casefold())
    if actual != seen or total != manifest.get('total_file_bytes'):
        raise ValueError('Backup contains unexpected files or byte count mismatch')
    image = manifest.get('card_image')
    if image:
        path = safe_file(backup, 'CARD.img')
        if image.get('verified') is not True or image['sha256_source_stream'] != image['sha256_copy'] or path.stat().st_size != image['bytes'] or digest(path) != image['sha256_copy']:
            raise ValueError('Card image integrity failure')
    return {'status': 'VERIFIED', 'files': len(files), 'bytes': total, 'image_verified': bool(image)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup', type=Path, help='Timestamped folder containing manifest.json and Files/')
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.backup)))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'FAILED', 'error': str(exc)}))
        raise SystemExit(1)
