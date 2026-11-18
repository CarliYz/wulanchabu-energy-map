import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DispatchBehavior(unittest.TestCase):
    def run_model(self, rows=None):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            inp = ROOT / 'data/inputs.csv'
            if rows is not None:
                inp = target / 'changed.csv'
                with inp.open('w', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
            result = subprocess.run([sys.executable, str(ROOT/'src/dispatch.py'), '--input', str(inp),
                                     '--parameters', str(ROOT/'data/parameters.json'), '--output', str(target/'out')],
                                    text=True, capture_output=True)
            data = json.loads((target/'out/results.json').read_text()) if result.returncode == 0 else None
            return result, data

    def test_source_outage_exhausts_storage_and_reports_unserved(self):
        result, data = self.run_model()
        self.assertEqual(result.returncode, 0, result.stderr)
        s = data['summary']
        for scenario, expected in [('MVP_NORMAL', (48, 0, 20, 4)),
                                   ('MVP_SOURCE_OUTAGE', (44, 4, 12, 4))]:
            self.assertEqual(tuple(s[scenario][k] for k in ['delivered_mwh', 'unserved_mwh',
                                                          'curtailed_mwh', 'final_storage_mwh']), expected)
        outage = [r for r in data['rows'] if r['scenario_id'] == 'MVP_SOURCE_OUTAGE']
        self.assertEqual([outage[t]['discharge_mw'] for t in (4, 5, 6, 7)], [2, 2, 0, 0])
        self.assertEqual([outage[t]['unserved_mw'] for t in (4, 5, 6, 7)], [0, 0, 2, 2])

    def input_rows(self):
        with (ROOT/'data/inputs.csv').open(newline='') as f:
            return list(csv.DictReader(f))

    def test_changed_input_changes_delivery_and_deficit(self):
        rows = self.input_rows()
        next(r for r in rows if r['scenario_id']=='MVP_SOURCE_OUTAGE' and r['hour_index']=='6')['source_mw']='1'
        result, data = self.run_model(rows)
        self.assertEqual(result.returncode, 0, result.stderr)
        r = next(r for r in data['rows'] if r['scenario_id']=='MVP_SOURCE_OUTAGE' and r['hour_index']==6)
        self.assertEqual((r['delivered_mw'], r['unserved_mw']), (1, 1))

    def test_invalid_and_missing_inputs_fail_explicitly(self):
        for value in ('', 'NaN', 'Infinity', '-1', 'not-a-number'):
            with self.subTest(value=value):
                rows=self.input_rows(); rows[0]['source_mw']=value
                result, data=self.run_model(rows)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ValueError', result.stderr)
                self.assertIsNone(data)
        rows=self.input_rows(); rows.append(rows[0].copy())
        self.assertIn('duplicate key', self.run_model(rows)[0].stderr)
        rows=self.input_rows()[1:]
        self.assertIn('contiguous', self.run_model(rows)[0].stderr)
        rows=self.input_rows();rows[0]['pump_electric_mw']='0';rows[0]['assumed_grid_input_mw']='0'
        self.assertIn('electric outage',self.run_model(rows)[0].stderr)

    def test_non_hourly_energy_integrates_step_duration(self):
        rows=self.input_rows()
        for r in rows: r['dt_h']='0.5'
        result,data=self.run_model(rows)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data['summary']['MVP_NORMAL']['delivered_mwh'],24)
        self.assertEqual(data['summary']['MVP_NORMAL']['curtailed_mwh'],8)
        for r in data['rows']:
            self.assertAlmostEqual(r['source_mw']+r['discharge_mw'],r['delivered_mw']+r['charge_mw']+r['curtailed_mw'])
            self.assertAlmostEqual(r['demand_mw'],r['delivered_mw']+r['unserved_mw'])
            self.assertAlmostEqual(r['storage_end_mwh'],r['storage_start_mwh']+(r['charge_mw']-r['discharge_mw'])*r['dt_h'])
            self.assertGreaterEqual(r['storage_end_mwh'],0)
            self.assertLessEqual(r['storage_end_mwh'],4)


if __name__ == '__main__':
    unittest.main()
