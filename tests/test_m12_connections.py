"""Candidate flow topology: isolated media, complete branches and closed exits."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CandidateConnections(unittest.TestCase):
    def setUp(self):
        self.graph = json.loads((ROOT/'web/map-prototype/m10-system-runtime.json').read_text())

    def test_every_visible_edge_has_compatible_declared_ports(self):
        ports = {p['port_id']: p for p in self.graph['ports']}
        for edge in self.graph['connections']:
            a, b = ports[edge['from_port_id']], ports[edge['to_port_id']]
            self.assertEqual((a['medium'], a['circuit_id']), (b['medium'], b['circuit_id']))
            self.assertEqual((a['direction'], b['direction']), ('in', 'out') if edge.get('role')=='internal' else ('out', 'in'))
            self.assertEqual(edge['model_status'], 'schematic_connected')

    def test_ptes_has_separate_complete_returns_and_stays_idle(self):
        edges = self.graph['connections']
        pairs = {(e['from_object_id'], e['to_object_id']) for e in edges}
        for path in [
            ['HUB_011_WATER','STORE_012_CHARGE_VHOT','STORE_012_CHARGE_PUMP','STORE_012','STORE_012_CHARGE_VRETURN','HUB_011_WATER'],
            ['STORE_012','STORE_012_DIS_VHOT','STORE_012_DIS_PUMP','STORE_012_DIS_CHECK','HUB_011_WATER','STORE_012_DIS_VRETURN','STORE_012'],
            ['HUB_011_WATER','BOILER_CAND_001_RETURN_VALVE','BOILER_CAND_001','BOILER_CAND_001_PUMP','BOILER_CAND_001_CHECK','HUB_011_WATER']
        ]:
            for a, b in zip(path, path[1:]): self.assertIn((a,b), pairs)
        self.assertEqual(self.graph['ptes']['initial_mode'], 'IDLE')
        self.assertFalse(self.graph['ptes']['execution_allowed'])
        self.assertFalse(self.graph['ptes']['simultaneous_charge_discharge_allowed'])

    def test_co2_never_leaves_hub_and_p1_never_mixes_with_user(self):
        for edge in self.graph['connections']:
            if edge['medium']=='co2':
                self.assertTrue(edge['from_object_id'].startswith('HUB_'))
                self.assertTrue(edge['to_object_id'].startswith('HUB_'))
            self.assertNotEqual({edge['from_object_id'],edge['to_object_id']}, {'HUB_011_P1_HX','HUB_011_WATER'})
        self.assertTrue(self.graph['energy_transfers'])
        self.assertTrue(all(t['kind']=='heat_transfer_no_mass_flow' for t in self.graph['energy_transfers']))

    def test_c2_hx_primary_branches_are_parallel_and_isolated(self):
        edges = self.graph['connections']
        for i in [1,2,3]:
            hx=f'DRY_019_HX_{i}'
            self.assertTrue(any(e['from_object_id']=='DRY_019' and e['to_object_id']==hx and e['circuit_id']=='DRY_019_HEAT' for e in edges))
            self.assertTrue(any(e['from_object_id']==hx and e['to_object_id']=='DRY_019' and e['circuit_id']=='DRY_019_HEAT' for e in edges))
            self.assertFalse(any(e['from_object_id']==hx and e['to_object_id'].startswith('DRY_019_HX_') and e['to_object_id']!=hx for e in edges))


if __name__=='__main__': unittest.main()
