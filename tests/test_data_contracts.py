import copy
import json
import unittest
from pathlib import Path
from scripts.validate_contracts import ContractError, load_bundle, object_results, validate_bundle


class DataContracts(unittest.TestCase):
    def setUp(self):
        self.bundle = load_bundle()

    def reject(self, text):
        with self.assertRaisesRegex(ContractError, text):
            validate_bundle(self.bundle)

    def test_valid_bundle_with_source_hashes(self):
        self.assertEqual(validate_bundle(self.bundle, verify_sources=True)['status'], 'pass')

    def test_unknown_parent_and_cycle(self):
        self.bundle['objects']['objects'][0]['parent_id'] = 'MISSING'
        self.reject('unknown parent')
        self.bundle['objects']['objects'][0]['parent_id'] = 'AGRI_018_HX'
        self.reject('parent cycle')

    def test_ids_unique_and_alias_unambiguous(self):
        self.bundle['objects']['objects'].append(copy.deepcopy(self.bundle['objects']['objects'][0]))
        self.reject('duplicate object_id')
        self.bundle['objects']['objects'].pop()
        self.bundle['objects']['objects'][0]['asset_id'] = 'HUB_011'
        self.reject('ambiguous asset_id')

    def test_unknown_and_zero_are_distinct(self):
        self.bundle['results']['results'][1]['metrics'][0]['value'] = 0
        self.reject('results:')

    def test_cannot_claim_operation_without_measured_evidence(self):
        self.bundle['objects']['objects'][0]['installation_status'] = 'operational_verified'
        self.reject('no operational evidence')

    def test_hot_water_cannot_connect_to_nutrient(self):
        edge = self.bundle['connections']['connections'][0]
        edge['to_port_id'] = next(p['port_id'] for p in self.bundle['ports']['ports']
                                  if p['medium'] == 'nutrient' and p['direction'] == 'in')
        self.reject('circuit mixing')

    def test_same_medium_is_not_permission_to_mix_hx_sides(self):
        edge = next(e for e in self.bundle['connections']['connections'] if 'C1_HEAT' in e['from_port_id'])
        edge['to_port_id'] = next(p['port_id'] for p in self.bundle['ports']['ports']
                                  if p['circuit_id'] == 'USER' and p['direction'] == 'in')
        self.reject('circuit mixing')

    def test_co2_must_stay_in_station(self):
        p = next(p for p in self.bundle['ports']['ports'] if p['medium'] == 'co2')
        p['object_id'] = 'AGRI_018'
        self.reject('CO2 outside station')

    def test_co2_circuit_cannot_relabel_a_greenhouse_as_station_scope(self):
        circuit = next(c for c in self.bundle['ports']['circuits'] if c['medium'] == 'co2')
        circuit['scope_object_id'] = 'AGRI_018'
        self.reject('CO2 scope is not a station')
        self.bundle = load_bundle()
        self.bundle['ports']['circuits'].append(dict(circuit_id='EMPTY_CO2', medium='co2',
                                                    scope_object_id='AGRI_018', purpose='invalid'))
        self.reject('CO2 scope is not a station')

    def test_endpoint_and_flow_and_geometric_claim(self):
        edge = self.bundle['connections']['connections'][0]
        original = edge['to_port_id']
        edge['to_port_id'] = 'MISSING'
        self.reject('unknown endpoint')
        edge['to_port_id'] = edge['from_port_id']
        self.reject('wrong flow')
        edge['to_port_id'] = original
        edge['model_status'] = 'connected_verified'
        self.reject('unlocated verified connection')

    def test_two_greenhouses_have_both_separate_circuit_paths(self):
        edges = self.bundle['connections']['connections']
        ports = {p['port_id']: p for p in self.bundle['ports']['ports']}
        for cid in ('C1_HEAT', 'C1_NUTRIENT'):
            adjacency = {}
            for e in edges:
                a, b = ports[e['from_port_id']], ports[e['to_port_id']]
                if a['circuit_id'] == cid:
                    adjacency.setdefault(a['object_id'], set()).add(b['object_id'])
            for gh in ('AGRI_018_GH1', 'AGRI_018_GH2'):
                visited, queue = set(), list(adjacency[gh])
                while queue:
                    node = queue.pop()
                    if node not in visited:
                        visited.add(node)
                        queue.extend(adjacency.get(node, ()))
                self.assertIn(gh, visited, f'{gh} needs a closed {cid} loop')

    def test_ptes_is_optional_branch(self):
        ports = {p['port_id']: p for p in self.bundle['ports']['ports']}
        edges = self.bundle['connections']['connections']
        pairs = {(ports[e['from_port_id']]['object_id'], ports[e['to_port_id']]['object_id']) for e in edges}
        self.assertIn(('HUB_011_WATER', 'AGRI_018_HX'), pairs)
        self.assertIn(('HUB_011_WATER', 'STORE_012'), pairs)
        self.assertIn(('STORE_012', 'HUB_011_WATER'), pairs)

    def test_no_legacy_fallback_to_c1(self):
        c1 = object_results(self.bundle, 'AGRI_018', 'MVP_NORMAL', 0)
        self.assertEqual(len(c1), 1)
        self.assertEqual(c1[0]['status'], 'missing_inputs')
        self.assertIsNone(c1[0]['metrics'][0]['value'])
        self.assertEqual(object_results(self.bundle, 'HUB_011', 'MVP_NORMAL', 0), [])
        row = self.bundle['results']['results'][2]
        row.update(object_id='AGRI_018', binding_status='bound', unbound_reason=None, hour_index=1)
        self.reject('synthetic result assigned')

    def test_synthetic_source_cannot_be_relabelled_measured(self):
        row = self.bundle['results']['results'][0]
        row.update(object_id='AGRI_018', data_kind='measured', hour_index=1)
        self.reject('synthetic source relabeled')

    def test_viewer_results_must_match_selection_scenario_and_time(self):
        state = self.bundle['viewer-state']
        state.update(selectedObjectId='AGRI_018', resultStatus='available',
                     objectResults=[copy.deepcopy(self.bundle['results']['results'][0])])
        self.reject('state result selection mismatch')

    def test_nonfinite_values_are_rejected(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            self.bundle['results']['results'][0]['metrics'][0]['value'] = value
            self.reject('non-finite number')

    def test_wrong_units_missing_hash_and_no_time_rejected(self):
        row = self.bundle['results']['results'][0]
        row['metrics'][0]['unit'] = 'MWh'
        self.reject('wrong metric unit')
        row['metrics'][0]['unit'] = 'MW'
        row['input_sha256'] = None
        self.reject('results:')
        row['input_sha256'] = 'a' * 64
        row['hour_index'] = None
        self.reject('results:')

    def test_coordinate_axes_roundtrip_and_manifest_identity(self):
        root = Path(__file__).resolve().parents[1]
        c = json.loads((root/'data/contracts/coordinate-contract.json').read_text())
        m = json.loads((root/'data/map-v2/geographic-manifest.json').read_text())
        self.assertEqual(c['origin_utm_egm2008_m'], m['origin'])
        a, b = c['blender_to_glb_matrix_row_major'], c['glb_to_local_matrix_row_major']
        for i in range(4):
            for j in range(4):
                self.assertEqual(sum(a[i][k]*b[k][j] for k in range(4)), int(i == j))
        self.assertIsNone(c['map_world_matrix'])
        self.assertEqual(c['independent_registration_status'], 'not_run')


if __name__ == '__main__':
    unittest.main()
