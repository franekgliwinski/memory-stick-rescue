import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify = load('verify_backup', 'tools/verify_backup.py')


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        folder = self.root / 'Files' / 'DCIM'
        folder.mkdir(parents=True)
        self.file = folder / 'synthetic.dat'
        self.file.write_bytes(b'synthetic bytes\x00\xff' * 300)
        h = verify.digest(self.file)
        self.entry = {'path': 'DCIM/synthetic.dat', 'bytes': self.file.stat().st_size,
                      'sha256_source_stream': h, 'sha256_copy': h, 'verified': True}
        self.manifest = {'status': 'VERIFIED_COPY', 'cleanup_complete': True,
                         'files_copied': 1, 'expected_file_count': 1,
                         'files': [self.entry], 'total_file_bytes': self.entry['bytes']}
        self.save()

    def save(self):
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def fail(self):
        self.save()
        with self.assertRaises((ValueError, OSError, KeyError)):
            verify.verify(self.root)

    def test_complete_copy(self):
        self.assertEqual(verify.verify(self.root)['files'], 1)

    def test_corruption_same_size(self):
        data = bytearray(self.file.read_bytes())
        data[10] ^= 1
        self.file.write_bytes(data)
        self.fail()

    def test_truncated_copy(self):
        self.file.write_bytes(b'short')
        self.fail()

    def test_missing_file(self):
        self.file.unlink()
        self.fail()

    def test_incomplete_status(self):
        self.manifest['status'] = 'FAILED_PARTIAL'
        self.fail()

    def test_cleanup_failure(self):
        self.manifest['cleanup_complete'] = False
        self.fail()

    def test_source_hash_mismatch(self):
        self.entry['sha256_source_stream'] = '0' * 64
        self.fail()

    def test_unverified_entry(self):
        self.entry['verified'] = False
        self.fail()

    def test_count_mismatch(self):
        self.manifest['expected_file_count'] = 2
        self.fail()

    def test_total_bytes_mismatch(self):
        self.manifest['total_file_bytes'] += 1
        self.fail()

    def test_duplicate_paths(self):
        self.manifest['files'].append(dict(self.entry))
        self.manifest['files_copied'] = self.manifest['expected_file_count'] = 2
        self.manifest['total_file_bytes'] *= 2
        self.fail()

    def test_extra_file(self):
        (self.root / 'Files' / 'extra.dat').write_bytes(b'extra')
        self.fail()

    def test_path_traversal(self):
        for name in ('../outside', '/etc/passwd', 'C:/outside', 'DCIM\\outside', 'DCIM/file:stream'):
            with self.subTest(name=name):
                self.entry['path'] = name
                self.fail()

    def test_raw_image(self):
        image = self.root / 'CARD.img'
        image.write_bytes(b'synthetic raw image')
        h = verify.digest(image)
        self.manifest['card_image'] = {'bytes': image.stat().st_size, 'sha256_source_stream': h, 'sha256_copy': h, 'verified': True}
        self.save()
        self.assertTrue(verify.verify(self.root)['image_verified'])
        image.write_bytes(b'bad')
        self.fail()

    def test_empty_card(self):
        self.file.unlink()
        self.manifest.update(files=[], files_copied=0, expected_file_count=0, total_file_bytes=0)
        self.save()
        self.assertEqual(verify.verify(self.root)['files'], 0)

    @unittest.skipIf(sys.platform == 'win32', 'Windows symlink creation depends on local permissions')
    def test_symlink_escape(self):
        outside = self.root / 'outside.dat'
        outside.write_bytes(self.file.read_bytes())
        self.file.unlink()
        self.file.symlink_to(outside)
        self.fail()


@unittest.skipUnless(sys.platform == 'linux', 'Importer runs inside Linux')
class LinuxCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.importer = load('import_card', 'linux/import_card.py')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.dat'
        self.source.write_bytes(b'original synthetic source' * 5000)
        self.target = self.root / 'target.dat'

    def test_copy_and_independent_hash(self):
        result = self.importer.copy_verified(self.source, self.target, self.source.stat().st_size)
        self.assertTrue(result['verified'])
        self.assertEqual(self.source.read_bytes(), self.target.read_bytes())
        self.assertEqual(result['sha256_source_stream'], result['sha256_copy'])

    def test_existing_destination_is_not_overwritten(self):
        self.target.write_bytes(b'keep this')
        with self.assertRaises(FileExistsError):
            self.importer.copy_verified(self.source, self.target, self.source.stat().st_size)
        self.assertEqual(self.target.read_bytes(), b'keep this')

    def test_wrong_source_size(self):
        with self.assertRaises(RuntimeError):
            self.importer.copy_verified(self.source, self.target, self.source.stat().st_size + 1)

    def test_bad_destination_readback(self):
        with patch.object(self.importer, 'digest', return_value='0' * 64):
            with self.assertRaises(RuntimeError):
                self.importer.copy_verified(self.source, self.target, self.source.stat().st_size)

    def test_directory_read_errors_are_fatal(self):
        with self.assertRaises(OSError):
            self.importer.walk_error(OSError('synthetic I/O failure'))


@unittest.skipUnless(sys.platform == 'linux', 'Linux sysfs safety tests')
class LinuxDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.importer = load('import_card_discovery', 'linux/import_card.py')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.usb = self.root / 'usb'
        self.blocks = self.root / 'blocks'
        self.usb.mkdir()
        self.blocks.mkdir()
        self.device = self.usb / '1-1'
        self.device.mkdir()
        (self.device / 'idVendor').write_text('054c')
        (self.device / 'idProduct').write_text('002d')
        disk = self.device / 'interface' / 'sdf'
        disk.mkdir(parents=True)
        (disk / 'size').write_text(str(32473088 // 512))
        (disk / 'dev').write_text('8:80')
        (self.blocks / 'sdf').symlink_to(disk)
        partition = disk / 'sdf1'
        partition.mkdir()
        (partition / 'partition').write_text('1')
        (partition / 'dev').write_text('8:81')
        (self.blocks / 'sdf1').symlink_to(partition)
        self.mounts = self.root / 'mountinfo'
        self.mounts.write_text('1 0 0:1 / / rw - tmpfs tmpfs rw\n')
        routes = {'/sys/bus/usb/devices': self.usb, '/sys/class/block': self.blocks, '/proc/self/mountinfo': self.mounts}
        self.patcher = patch.object(self.importer, 'Path', side_effect=lambda x: routes.get(str(x), Path(x)))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.calls = []
        def run(*args, **kwargs):
            from types import SimpleNamespace
            self.calls.append(args)
            out = '1\n' if args[:2] == ('blockdev', '--getro') else 'TYPE=vfat\n'
            return SimpleNamespace(stdout=out, returncode=0)
        self.runner = patch.object(self.importer, 'run', side_effect=run)
        self.runner.start()
        self.addCleanup(self.runner.stop)

    def test_exact_reader_dynamic_disk(self):
        disk, volume, size, props = self.importer.identify_card()
        self.assertEqual((disk, volume, size), ('/dev/sdf', '/dev/sdf1', 32473088))
        self.assertEqual(props['TYPE'], 'vfat')
        self.assertIn(('blockdev', '--setro', '/dev/sdf'), self.calls)
        self.assertIn(('blockdev', '--setro', '/dev/sdf1'), self.calls)

    def test_wrong_reader_id_rejected_before_any_command(self):
        (self.device / 'idProduct').write_text('ffff')
        with self.assertRaises(RuntimeError):
            self.importer.identify_card()
        self.assertEqual(self.calls, [])

    def test_already_mounted_alias_rejected(self):
        self.mounts.write_text('1 0 8:81 / /other rw - vfat /dev/disk/by-uuid/ANY rw\n')
        with self.assertRaises(RuntimeError):
            self.importer.identify_card()
        self.assertEqual(self.calls, [])

    def test_wrong_capacity_rejected(self):
        (self.device / 'interface/sdf/size').write_text('999999999')
        with self.assertRaises(RuntimeError):
            self.importer.identify_card()
        self.assertEqual(self.calls, [])

    def test_duplicate_reader_rejected(self):
        other = self.usb / '1-2'
        other.mkdir()
        (other / 'idVendor').write_text('054c')
        (other / 'idProduct').write_text('002d')
        with self.assertRaises(RuntimeError):
            self.importer.identify_card()
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
