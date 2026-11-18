"""Deterministic teaching heat dispatch; CSV is the public calculation boundary."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def number(value, field):
    try:
        value = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f'{field}: missing or non-numeric value') from e
    if not math.isfinite(value) or value < 0:
        raise ValueError(f'{field}: expected finite non-negative value')
    return value


def calculate(input_path, parameters_path):
    p = json.loads(parameters_path.read_text())
    if p.get('efficiency') != 1 or p.get('loss') != 0:
        raise ValueError('this teaching fixture requires efficiency=1 and loss=0')
    for k in ['storage_initial_mwh', 'storage_capacity_mwh', 'charge_limit_mw', 'discharge_limit_mw']:
        p[k] = number(p[k], k)
    if p['storage_initial_mwh'] > p['storage_capacity_mwh']:
        raise ValueError('initial storage exceeds capacity')
    with input_path.open(newline='') as f:
        raw = list(csv.DictReader(f))
    if not raw:
        raise ValueError('empty scenario input')
    groups = {}
    for r in raw:
        scenario = r['scenario_id']
        if scenario not in ('MVP_NORMAL', 'MVP_SOURCE_OUTAGE'):
            raise ValueError(f'unknown scenario: {scenario}')
        if r['time_basis'] != 'synthetic_teaching_not_local':
            raise ValueError('time basis must explicitly identify synthetic teaching data')
        t = int(r['hour_index'])
        group = groups.setdefault(scenario, {})
        if t in group:
            raise ValueError(f'duplicate key: {scenario} t={t}')
        for key in ['source_mw', 'demand_mw', 'dt_h', 'pump_electric_mw', 'assumed_grid_input_mw']:
            r[key] = number(r.get(key), f'{scenario} t={t} {key}')
        if r['dt_h'] <= 0:
            raise ValueError('dt_h must be positive')
        group[t] = r
    if set(groups) != {'MVP_NORMAL', 'MVP_SOURCE_OUTAGE'}:
        raise ValueError('both frozen scenarios are required')
    rows, summary = [], {}
    for scenario, group in sorted(groups.items()):
        if sorted(group) != list(range(24)):
            raise ValueError(f'{scenario}: expected contiguous t=0..23')
        energy = p['storage_initial_mwh']
        totals = {k: 0.0 for k in ['source', 'delivered', 'unserved', 'curtailed', 'pump_electricity']}
        for t, r in sorted(group.items()):
            dt, source, demand = r['dt_h'], r['source_mw'], r['demand_mw']
            if r['pump_electric_mw'] != 0.02 or r['assumed_grid_input_mw'] != r['pump_electric_mw']:
                raise ValueError('electric outage is outside this fixture; grid and pump must match')
            direct = min(source, demand)
            discharge = min(demand-direct, p['discharge_limit_mw'], energy/dt)
            charge = min(source-direct, p['charge_limit_mw'],
                         (p['storage_capacity_mwh']-energy)/dt)
            delivered = direct + discharge
            curtailed, unserved = source-direct-charge, demand-delivered
            next_energy = energy + (charge-discharge)*dt
            residual = source+discharge-delivered-charge-curtailed
            if abs(residual) > 0.001 or not -1e-9 <= next_energy <= p['storage_capacity_mwh']+1e-9:
                raise ArithmeticError(f'invariant violation at {scenario} t={t}')
            row = dict(scenario_id=scenario, hour_index=t, dt_h=dt, time_basis=r['time_basis'],
                       source_mw=source, demand_mw=demand, direct_mw=direct, delivered_mw=delivered,
                       unserved_mw=unserved, charge_mw=charge, discharge_mw=discharge,
                       curtailed_mw=curtailed, storage_start_mwh=energy, storage_end_mwh=next_energy,
                       pump_electric_mw=r['pump_electric_mw'], assumed_grid_input_mw=r['assumed_grid_input_mw'],
                       heat_balance_residual_mw=residual, temperature_model='assumed_feasible_not_simulated')
            rows.append(row)
            for k, q in [('source', source), ('delivered', delivered), ('unserved', unserved),
                         ('curtailed', curtailed), ('pump_electricity', r['pump_electric_mw'])]:
                totals[k] += q*dt
            energy = next_energy
        summary[scenario] = {k+'_mwh': v for k, v in totals.items()}
        summary[scenario]['final_storage_mwh'] = energy
        summary[scenario]['thermal_residual_mwh'] = totals['source']-totals['delivered']-totals['curtailed']-(energy-p['storage_initial_mwh'])
    return dict(schema_version=1, requirement_revision='energy-mvp-v1', design_revision='design-v1',
                input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
                parameters_sha256=hashlib.sha256(parameters_path.read_bytes()).hexdigest(),
                basis='synthetic teaching, no local operational validation', rows=rows, summary=summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = calculate(args.input, args.parameters)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    with (args.output/'results.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=result['rows'][0]); w.writeheader(); w.writerows(result['rows'])
    print(json.dumps({'operation': 'dispatch', 'outcome': 'pass', 'rows': len(result['rows']),
                      'input_sha256': result['input_sha256'], 'summary': result['summary']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
