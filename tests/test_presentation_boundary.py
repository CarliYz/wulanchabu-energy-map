"""Protect the public result-to-presentation boundary from misleading labels."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PresentationBoundary(unittest.TestCase):
    def test_prepare_rejects_stale_and_non_hourly_results(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            with (ROOT/'data/inputs.csv').open(newline='') as handle:
                rows = list(csv.DictReader(handle))
            for label, duration, stale, expected in [
                ('valid', '1', False, None),
                ('stale', '1', True, 'input digest mismatch'),
                ('half-hour', '0.5', False, 'requires 1h steps'),
            ]:
                with self.subTest(label=label):
                    for row in rows:
                        row['dt_h'] = duration
                    source = target/(label+'.csv')
                    with source.open('w', newline='') as handle:
                        writer = csv.DictWriter(handle, fieldnames=rows[0])
                        writer.writeheader(); writer.writerows(rows)
                    output = target/label
                    result = subprocess.run([sys.executable, str(ROOT/'src/dispatch.py'),
                        '--input', str(source), '--parameters', str(ROOT/'data/parameters.json'),
                        '--output', str(output)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    if stale:
                        source.write_text(source.read_text()+'\n')
                    request = target/(label+'-request.json')
                    prepared = subprocess.run([sys.executable, str(ROOT/'src/prepare_mcp.py'),
                        '--input', str(source), '--results', str(output/'results.json'),
                        '--blend', str(target/'scene.blend'), '--request', str(request)],
                        capture_output=True, text=True)
                    if expected:
                        self.assertNotEqual(prepared.returncode, 0)
                        self.assertIn(expected, prepared.stderr)
                        self.assertFalse(request.exists())
                    else:
                        self.assertEqual(prepared.returncode, 0, prepared.stderr)
                        self.assertEqual(json.loads(request.read_text())['tool'], 'execute_blender_code')
