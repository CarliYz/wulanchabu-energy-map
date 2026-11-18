"""Validate the shared contract bundle; semantic failures are never coerced to defaults."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / 'data/contracts'


class ContractError(ValueError):
    pass


def load_bundle(directory=CONTRACTS / 'fixtures'):
    return {name: json.loads((Path(directory) / f'{name}.json').read_text())
            for name in ('objects', 'ports', 'connections', 'results', 'viewer-state')}


def validate_bundle(bundle, verify_sources=False):
    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ContractError('non-finite number is not valid contract JSON')
        if isinstance(value, dict):
            for item in value.values():
                finite(item)
        elif isinstance(value, list):
            for item in value:
                finite(item)
    finite(bundle)
    schemas = [json.loads(p.read_text()) for p in CONTRACTS.glob('*.schema.json')]
    registry = Registry().with_resources((s['$id'], Resource.from_contents(s)) for s in schemas)
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
    for name, data in bundle.items():
        schema = next(s for s in schemas if s['$id'].endswith(f'/{name}.schema.json'))
        errors = list(Draft202012Validator(schema, registry=registry, format_checker=FormatChecker()).iter_errors(data))
        if errors:
            raise ContractError(f'{name}: {errors[0].json_path}: {errors[0].message}')

    def require(condition, message):
        if not condition:
            raise ContractError(message)

    def index(items, key):
        result = {item[key]: item for item in items}
        require(len(result) == len(items), f'duplicate {key}')
        return result

    objects = index(bundle['objects']['objects'], 'object_id')
    ports = index(bundle['ports']['ports'], 'port_id')
    circuits = index(bundle['ports']['circuits'], 'circuit_id')
    index(bundle['connections']['connections'], 'connection_id')
    index(bundle['connections']['energy_transfers'], 'transfer_id')
    index(bundle['results']['results'], 'result_id')
    sources = bundle['objects']['sources']

    def check_sources(item):
        require(all(s in sources for s in item['source_ids']), f'unknown source: {item}')

    def descendant(oid, ancestor):
        seen = set()
        while oid is not None:
            require(oid not in seen, f'parent cycle: {oid}')
            seen.add(oid)
            if oid == ancestor:
                return True
            oid = objects[oid]['parent_id']
        return False

    aliases = set()
    for item in objects.values():
        oid = item['object_id']
        require(item['parent_id'] is None or item['parent_id'] in objects, f'unknown parent: {oid}')
        check_sources(item)
        alias = item['asset_id']
        if alias is not None:
            require(alias not in aliases and (alias == oid or alias not in objects), f'ambiguous asset_id: {alias}')
            aliases.add(alias)
        # Walk the entire ancestry, even when no circuit currently references it.
        descendant(oid, '__not_an_object__')
        if item['planning_area']:
            require(item['planning_area']['min'] <= item['planning_area']['max'], f'reversed area: {oid}')
        if item['focus_bounds']:
            bounds = item['focus_bounds']
            require(all(a <= b for a, b in zip(bounds['min'], bounds['max'])), f'reversed bounds: {oid}')
        if item['installation_status'] == 'operational_verified':
            require(any(sources[s]['nature'] == 'measured' for s in item['source_ids']), f'no operational evidence: {oid}')

    for c in circuits.values():
        require(c['scope_object_id'] in objects, f'unknown circuit scope: {c["circuit_id"]}')
        if c['medium'] == 'co2':
            require(objects[c['scope_object_id']]['kind'] == 'hub', f'CO2 scope is not a station: {c["circuit_id"]}')
    for p in ports.values():
        require(p['object_id'] in objects, f'unknown port object: {p["port_id"]}')
        require(p['circuit_id'] in circuits, f'unknown circuit: {p["port_id"]}')
        c = circuits[p['circuit_id']]
        require(p['medium'] == c['medium'], f'port medium mismatch: {p["port_id"]}')
        check_sources(p)
        if p['medium'] == 'co2':
            require(descendant(p['object_id'], c['scope_object_id']), f'CO2 outside station: {p["port_id"]}')

    for edge in bundle['connections']['connections']:
        require(edge['from_port_id'] in ports and edge['to_port_id'] in ports, f'unknown endpoint: {edge["connection_id"]}')
        a, b = ports[edge['from_port_id']], ports[edge['to_port_id']]
        require(a['direction'] == 'out' and b['direction'] == 'in', f'wrong flow: {edge["connection_id"]}')
        require(a['circuit_id'] == b['circuit_id'] and a['medium'] == b['medium'], f'circuit mixing: {edge["connection_id"]}')
        if edge['model_status'] == 'connected_verified':
            require(all(p['position']['xyz_m'] is not None for p in (a, b)), f'unlocated verified connection: {edge["connection_id"]}')
        check_sources(edge)
    for link in bundle['connections']['energy_transfers']:
        require(link['object_id'] in objects, f'unknown heat transfer object: {link["transfer_id"]}')
        a, b = link['from_circuit_id'], link['to_circuit_id']
        require(a in circuits and b in circuits and a != b, f'invalid heat transfer circuits: {link["transfer_id"]}')
        owned = {p['circuit_id'] for p in ports.values() if p['object_id'] == link['object_id']}
        require(a in owned and b in owned, f'heat transfer lacks both sides: {link["transfer_id"]}')
        check_sources(link)

    units = {'heat_delivered': 'MW', 'storage_energy': 'MWh', 'supply_temperature': 'degC'}
    result_keys = set()
    for row in bundle['results']['results']:
        require(row['object_id'] is None or row['object_id'] in objects, f'unknown result object: {row["result_id"]}')
        check_sources(row)
        key = (row['scenario_id'], row['object_id'], row['timestamp'], row['hour_index'])
        require(key not in result_keys, f'duplicate result binding: {key}')
        result_keys.add(key)
        names = [m['metric'] for m in row['metrics']]
        require(len(names) == len(set(names)), f'duplicate metric: {row["result_id"]}')
        for m in row['metrics']:
            require(m['unit'] == units[m['metric']], f'wrong metric unit: {row["result_id"]}')
        if row['data_kind'] == 'synthetic' and row['object_id']:
            require(objects[row['object_id']]['kind'] == 'demo', f'synthetic result assigned to geographic object: {row["object_id"]}')
        natures = {sources[s]['nature'] for s in row['source_ids']}
        if row['status'] == 'available':
            require('synthetic' not in natures or row['data_kind'] == 'synthetic', f'synthetic source relabeled: {row["result_id"]}')
            if row['data_kind'] == 'measured':
                require('measured' in natures, f'measured result lacks measured source: {row["result_id"]}')
            if row['data_kind'] == 'planning':
                require('planning' in natures, f'planning result lacks planning source: {row["result_id"]}')

    state = bundle['viewer-state']
    require(state['selectedObjectId'] is None or state['selectedObjectId'] in objects, 'unknown selected object')
    require(state['selectedCircuitId'] is None or state['selectedCircuitId'] in circuits, 'unknown selected circuit')
    for row in state['objectResults']:
        require(row in bundle['results']['results'], 'state result absent from validated result bundle')
        require(row['binding_status'] == 'bound' and row['object_id'] == state['selectedObjectId']
                and row['scenario_id'] == state['analysisScenarioId']
                and row['hour_index'] == state['analysisTime']['hour_index']
                and row['timestamp'] == state['analysisTime']['timestamp'], 'state result selection mismatch')
    if state['resultStatus'] == 'available':
        require(any(r['status'] == 'available' for r in state['objectResults']), 'available state lacks available result')

    if verify_sources:
        for sid, source in sources.items():
            path = (ROOT / source['path']).resolve()
            require(path.is_relative_to(ROOT), f'source outside repository: {sid}')
            require(path.is_file(), f'missing source file: {sid}')
            require(hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256'], f'stale source hash: {sid}')
    return {'status': 'pass', 'objects': len(objects), 'ports': len(ports), 'circuits': len(circuits),
            'connections': len(bundle['connections']['connections']), 'results': len(result_keys)}


def object_results(bundle, object_id, scenario_id, hour_index=None, timestamp=None):
    """An unbound legacy row cannot be used as an object-specific fallback."""
    return [r for r in bundle['results']['results'] if r['binding_status'] == 'bound'
            and r['object_id'] == object_id and r['scenario_id'] == scenario_id
            and r['hour_index'] == hour_index and r['timestamp'] == timestamp]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixtures', type=Path, default=CONTRACTS / 'fixtures')
    args = parser.parse_args()
    print(json.dumps(validate_bundle(load_bundle(args.fixtures), verify_sources=True), ensure_ascii=False))
