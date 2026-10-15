"""Non-mutating Linux status for the exact reader. No card reads or mount changes."""
import argparse
import json
from pathlib import Path

def inspect():
    root = Path('/sys/bus/usb/devices')
    matches = []
    if root.exists():
        for p in root.iterdir():
            try:
                if (p/'idVendor').read_text().strip() == '054c' and (p/'idProduct').read_text().strip() == '002d':
                    matches.append(p.resolve())
            except OSError:
                pass
    blocks = []
    if Path('/sys/class/block').exists():
        blocks = [p for p in Path('/sys/class/block').iterdir() if any(u in p.resolve().parents for u in matches)]
    mounted = []
    if Path('/proc/self/mountinfo').exists():
        for line in Path('/proc/self/mountinfo').read_text().splitlines():
            fields = line.split()
            for p in blocks:
                if (p/'dev').read_text().strip() == fields[2]:
                    mounted.append(p.name)
    return {'reader_count': len(matches), 'disks': [p.name for p in blocks if not (p/'partition').exists()],
            'mounted_blocks': sorted(set(mounted)), 'vid_pid': '054c:002d'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ready', action='store_true')
    parser.add_argument('--safe-detach', action='store_true')
    args = parser.parse_args()
    info = inspect()
    print(json.dumps(info))
    if args.ready:
        raise SystemExit(0 if info['reader_count'] == 1 and len(info['disks']) == 1 else 1)
    if args.safe_detach:
        raise SystemExit(0 if info['reader_count'] <= 1 and not info['mounted_blocks'] else 1)
