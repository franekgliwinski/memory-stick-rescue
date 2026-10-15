"""Read-only Linux importer for Sony MSAC-US1 (054c:002d), original 32 MB cards.

Requires Python 3.9+, root and util-linux. Does not erase, repair or format.
"""
import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def run(*args, check=True):
    return subprocess.run(args, check=check, text=True, capture_output=True)


def read(path):
    try:
        return Path(path).read_text().strip()
    except (FileNotFoundError, OSError):
        return None


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(1024 * 1024):
            h.update(data)
    return h.hexdigest()


def copy_verified(source, target, expected_size):
    h = hashlib.sha256()
    size = 0
    with source.open('rb', buffering=0) as src, target.open('xb') as dst:
        while data := src.read(1024 * 1024):
            dst.write(data)
            h.update(data)
            size += len(data)
        dst.flush()
        os.fsync(dst.fileno())
    if size != expected_size:
        raise RuntimeError(f'Unexpected source size while copying {source.name}.')
    copied_hash = digest(target)
    if copied_hash != h.hexdigest():
        raise RuntimeError(f'Copy hash mismatch for {source.name}.')
    return {'bytes': size, 'sha256_source_stream': h.hexdigest(), 'sha256_copy': copied_hash, 'verified': True}


def walk_error(error):
    raise error


def identify_card():
    usb = [p.resolve() for p in Path('/sys/bus/usb/devices').iterdir()
           if read(p / 'idVendor') == '054c' and read(p / 'idProduct') == '002d']
    if len(usb) != 1:
        raise RuntimeError('Exactly one Sony 054C:002D must be connected to this Linux system.')
    blocks = [p for p in Path('/sys/class/block').iterdir() if usb[0] in p.resolve().parents]
    disks = [p for p in blocks if not (p / 'partition').exists()]
    if len(disks) != 1:
        raise RuntimeError('The exact Sony reader did not expose one card disk.')
    size = int(read(disks[0] / 'size') or '0') * 512
    if not 16_000_000 <= size <= 40_000_000:
        raise RuntimeError(f'This version supports original 32 MB cards (16-40 MB guard); detected {size} bytes. Do not format.')
    parts = [p for p in blocks if (p / 'partition').exists()]
    if len(parts) > 1:
        raise RuntimeError('Unexpected multiple card partitions; manual inspection required.')
    volume = parts[0] if parts else disks[0]
    # Compare kernel device numbers, including bind mounts and alternate /dev aliases.
    device_numbers = {read(block / 'dev') for block in blocks}
    mounted_numbers = {line.split()[2] for line in Path('/proc/self/mountinfo').read_text().splitlines()}
    if device_numbers & mounted_numbers:
        raise RuntimeError('The card is already mounted. Finish the other operation first.')
    for block in blocks:
        device = '/dev/' + block.name
        run('blockdev', '--setro', device)
        if run('blockdev', '--getro', device).stdout.strip() != '1':
            raise RuntimeError('Read-only block protection could not be verified.')
    volume_path = '/dev/' + volume.name
    probe = run('blkid', '-p', '-o', 'export', volume_path)
    properties = dict(line.split('=', 1) for line in probe.stdout.splitlines() if '=' in line)
    if properties.get('TYPE') != 'vfat':
        raise RuntimeError('Expected the original FAT card filesystem; do not format or repair it.')
    return '/dev/' + disks[0].name, volume_path, size, properties


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--result-json', type=Path, required=True)
    parser.add_argument('--capture-image', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('This importer runs inside Linux, not directly in Windows or macOS.')
    missing = [name for name in ('mount', 'umount', 'findmnt', 'blockdev', 'blkid') if not shutil.which(name)]
    if missing:
        parser.error('Missing util-linux tools: ' + ', '.join(missing))
    result = {'status': 'IN_PROGRESS', 'files_copied': 0, 'cleanup_complete': False, 'safe_to_detach': False,
              'started_at_utc': datetime.now(timezone.utc).isoformat()}
    started = time.monotonic()
    mountpoint = Path('/mnt') / f'sony-memory-stick-import-{os.getpid()}'
    mounted = False
    batch = None
    lock = None
    destinations_safe = False
    try:
        if os.geteuid() != 0:
            raise RuntimeError('Run this Linux helper as root (sudo); Windows uses the existing WSL distro.')
        lock = open('/run/lock/sony-memory-stick-import.lock', 'a')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        output_root = args.output_root.resolve()
        if output_root == Path('/'):
            raise RuntimeError('Choose a dedicated backup folder, not filesystem root.')
        disk, volume, size, properties = identify_card()
        result['source'] = {'vid': '054C', 'pid': '002D', 'disk': disk, 'volume': volume,
                            'capacity_bytes': size, 'filesystem': properties, 'read_only': True}
        result['safe_to_detach'] = True
        # Check that neither destination nor result is on the card filesystem.
        protected = {os.stat('/dev/' + p.name).st_rdev for p in Path('/sys/class/block').iterdir()
                     if p.name == Path(disk).name or (p / 'partition').exists() and p.resolve().parent.name == Path(disk).name}
        for destination in (output_root, args.result_json.resolve()):
            ancestor = destination
            while not ancestor.exists():
                ancestor = ancestor.parent
            if ancestor.is_file():
                ancestor = ancestor.parent
            if os.stat(ancestor).st_dev in protected:
                raise RuntimeError('Backup and result destinations must be separate from the source card.')
        result_path = args.result_json.resolve()
        if output_root not in result_path.parents or result_path.suffix != '.json':
            raise RuntimeError('The result JSON must be a file inside the dedicated backup folder.')
        if result_path.exists():
            raise RuntimeError('Result JSON already exists; use a fresh path for each import.')
        destinations_safe = True
        output_root.mkdir(parents=True, exist_ok=True)
        required = size * (2 if args.capture_image else 1) + 10_000_000
        if shutil.disk_usage(output_root).free < required:
            raise RuntimeError('Insufficient free space for a complete verified backup.')
        name = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S_%f_UTC')
        batch = output_root / (name + '.partial')
        batch.mkdir()
        result['backup_path_linux'] = str(batch)
        dump(batch / 'manifest.json', result)
        if args.capture_image:
            print(json.dumps({'stage': 'card_image', 'bytes': size}), flush=True)
            result['card_image'] = copy_verified(Path(disk), batch / 'CARD.img', size)
        mountpoint.mkdir(mode=0o755)
        run('mount', '-t', 'vfat', '-o', 'ro,nosuid,nodev,noexec,noatime', volume, str(mountpoint))
        mounted = True
        options = run('findmnt', '-n', '-o', 'OPTIONS', '--mountpoint', str(mountpoint)).stdout.strip().split(',')
        if 'ro' not in options:
            raise RuntimeError('The card is not mounted read-only.')
        files_root = batch / 'Files'
        files_root.mkdir()
        entries = []
        for folder, directories, names in os.walk(mountpoint, onerror=walk_error):
            if any((Path(folder) / item).is_symlink() for item in directories):
                raise RuntimeError('Unexpected directory symlink on the card.')
            relative_dir = Path(folder).relative_to(mountpoint)
            (files_root / relative_dir).mkdir(parents=True, exist_ok=True)
            for item in sorted(names):
                source = Path(folder) / item
                if source.is_symlink() or not source.is_file():
                    raise RuntimeError('Unexpected special file on the card.')
                entries.append((source, source.relative_to(mountpoint)))
        result['expected_file_count'] = len(entries)
        result['files'] = []
        for index, (source, relative) in enumerate(entries, 1):
            before = source.stat()
            target = files_root / relative
            evidence = copy_verified(source, target, before.st_size)
            after = source.stat()
            if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                raise RuntimeError('A source file changed while being copied.')
            os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
            evidence.update({'path': relative.as_posix(), 'mtime_ns': before.st_mtime_ns})
            result['files'].append(evidence)
            result['files_copied'] = index
            print(json.dumps({'stage': 'copy', 'done': index, 'total': len(entries)}), flush=True)
        result['total_file_bytes'] = sum(f['bytes'] for f in result['files'])
        (batch / 'SHA256SUMS.txt').write_text(''.join(f"{f['sha256_copy']}  Files/{f['path']}\n" for f in result['files']), encoding='utf-8')
        run('umount', str(mountpoint))
        mounted = False
        result['cleanup_complete'] = True
        result['status'] = 'VERIFIED_COPY'
        result['elapsed_seconds'] = round(time.monotonic() - started, 2)
        result['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        final_batch = output_root / name
        result['backup_path_linux'] = str(final_batch)
        dump(batch / 'manifest.json', result)
        batch.rename(final_batch)
        batch = final_batch
    except (Exception, KeyboardInterrupt) as error:
        result['status'] = 'FAILED_PARTIAL' if batch is not None else 'FAILED'
        result['error'] = str(error) or 'Interrupted by user'
    finally:
        if mounted:
            cleanup = run('umount', str(mountpoint), check=False)
            result['cleanup_complete'] = cleanup.returncode == 0
            if cleanup.returncode != 0:
                result['cleanup_error'] = cleanup.stderr.strip()
                result['safe_to_detach'] = False
        elif not result['cleanup_complete']:
            result['cleanup_complete'] = True
        if mountpoint.exists() and not os.path.ismount(mountpoint):
            mountpoint.rmdir()
        if batch is not None:
            dump(batch / 'manifest.json', result)
        if destinations_safe:
            result_path.parent.mkdir(parents=True, exist_ok=True)
            dump(result_path, result)
        if lock is not None:
            lock.close()
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}, ensure_ascii=False), flush=True)
    return 0 if result['status'] == 'VERIFIED_COPY' and result['cleanup_complete'] else 1


if __name__ == '__main__':
    sys.exit(main())
