"""Read-only Mac USB diagnosis. Does not claim USB, mount cards, install or change settings."""
import json
import platform
import plistlib
import shutil
import subprocess
import sys


def walk(nodes):
    if isinstance(nodes, dict):
        nodes = [nodes]
    for node in nodes:
        if isinstance(node, dict):
            yield node
            yield from walk(node.get('IORegistryEntryChildren', []))


def diagnose():
    if sys.platform != 'darwin':
        raise RuntimeError('Run this diagnostic on macOS')
    output = subprocess.check_output(['/usr/sbin/ioreg', '-p', 'IOUSB', '-l', '-a'], timeout=20)
    nodes = [n for n in walk(plistlib.loads(output)) if n.get('idVendor') == 0x054c and n.get('idProduct') == 0x002d]
    disks = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'list', '-plist', 'external', 'physical'], timeout=20))
    # Do not expose unrelated volume names, serials, user paths or raw registry data.
    summary = [{'identifier': d.get('DeviceIdentifier'), 'size_bytes': d.get('Size')} for d in disks.get('AllDisksAndPartitions', [])]
    return {'platform': platform.mac_ver()[0], 'architecture': platform.machine(),
            'reader_count': len(nodes), 'vid_pid': '054c:002d',
            'external_disk_summary': summary, 'free_bytes': shutil.disk_usage('.').free,
            'status': 'USB_VISIBLE' if nodes else 'READER_NOT_FOUND',
            'note': 'USB visibility alone does not prove card access. See docs/macos.md.'}


if __name__ == '__main__':
    try:
        print(json.dumps(diagnose(), indent=2))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'FAILED', 'error': str(exc)}))
        raise SystemExit(1)
