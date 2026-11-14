"""Scalability sweep for cadl check/verify (in-process timing).

Generates synthetic CADL descriptions with K contracts and 2K actor
declarations in two topologies:
  star  - every contract has the party HUB, so every pair of contracts
          shares a party (K(K-1)/2 pairs are checked);
  chain - contract i has parties AGENT_i and AGENT_{i+1}, so only
          neighbouring contracts share a party (K-1 pairs).
Each contract has 3 assumptions and 2 guarantees over its own variables and
one variable shared with its neighbour; all descriptions are satisfiable.
With --lifecycle, every contract also gets a 4-state lifecycle and a monitor.
Times are the median of the process CPU time (time.process_time) and of the
wall-clock time over the repetitions; CPU time is reported because other
processes were active during the measurement.
Usage: python -I scale.py OUT.csv [--reps 5]
"""
import csv, os, statistics, sys, tempfile, time, json

from cadl.parser import parse_file
from cadl.type_checker import type_check
from cadl.verifier import verify
from cadl.deadlock import detect_deadlocks


def gen(K, topo, lifecycle):
    L = ['sos:', '  name: "Scale"', '  type: Collaborative', '  version: "1.0.0"']
    if lifecycle:
        L += ['  extensions:', '    - sos-dsl: 0.1']
    L += ['  actors:', '    - id: HUB', '      role: "hub"']
    for i in range(K + 1):
        L += [f'    - id: "AGENT_{i}[1..N]"' if i % 2 else f'    - id: AGENT_{i}', f'      role: "agent"']
    L += ['  contracts:']
    for i in range(K):
        a, b = f'AGENT_{i}', f'AGENT_{i+1}'
        ra = f'"{a}[*]"' if i % 2 else a
        rb = f'"{b}[*]"' if (i + 1) % 2 else b
        parties = f'[HUB, {ra}]' if topo == 'star' else f'[{ra}, {rb}]'
        L += [f'    - id: C{i}', f'      parties: {parties}',
              '      assume:',
              f'        - "x{i} >= 0"', f'        - "x{i} <= 100"', f'        - "s{i} <= 50"',
              '      guarantee:',
              f'        - "y{i} <= x{i} + 10"', f'        - "s{i+1} >= 0"',
              '      authority:', f'        decision_holder: {"HUB" if topo=="star" else a}', '        beta: 0.5',
              '      information:', '        alpha: 0.5',
              '      incentives:', '        lambda: 0.5']
        if lifecycle:
            L += ['      lifecycle:', '        states: [Open, Active, Done, Failed]',
                  '        initial: Open', '        terminal: [Done, Failed]', '        transitions:',
                  '          - id: start', '            from: Open', '            to: Active',
                  f'            on: "HUB -> {a} : start"' if topo == 'star' else f'            on: "{a} -> {b} : start"',
                  '          - id: finish', '            from: Active', '            to: Done',
                  f'            on: "y{i} >= 0"', '            deadline: 10s',
                  '            on_violation:', '              transition: Failed', '              severity: Minor',
                  '      monitors:', f'        - id: m{i}', f'          observe: "HUB.load"',
                  '          sampling: periodic(1s)', f'          rule: "HUB.load > 90 AND state == Active"',
                  '          on_match:', '            transition: Failed', '            severity: Major']
    return '\n'.join(L) + '\n'


def timed(fn, *a):
    t = time.process_time(); w = time.perf_counter(); r = fn(*a)
    return (time.process_time() - t, time.perf_counter() - w), r


def main():
    out = sys.argv[1]; reps = int(sys.argv[sys.argv.index('--reps') + 1]) if '--reps' in sys.argv else 5
    sizes = [10, 25, 50, 100, 200]
    rows = []
    tmp = tempfile.mkdtemp()
    for lifecycle in (False, True):
        for topo in ('star', 'chain'):
            for K in sizes:
                path = os.path.join(tmp, f'{topo}_{K}_{int(lifecycle)}.cadl')
                open(path, 'w').write(gen(K, topo, lifecycle))
                tp, tt, tv, td = [], [], [], []
                for _ in range(reps):
                    d, sos = timed(parse_file, path); tp.append(d)
                    d, tc = timed(type_check, sos); tt.append(d)
                    d, vr = timed(verify, sos); tv.append(d)
                    d, dr = timed(detect_deadlocks, sos); td.append(d)
                med = lambda xs, k: statistics.median(x[k] for x in xs)
                assert tc.ok, (path, [str(e) for e in tc.errors][:3])
                failed = [r.check_name for r in vr if r.status == 'failed']
                assert not failed, (path, failed[:3])
                cross = sum(1 for r in vr if r.check_name.startswith('Cross-contract'))
                lines = open(path).read().count('\n')
                rows.append(dict(topology=topo, lifecycle=int(lifecycle), contracts=K, actor_decls=K + 2,
                                 lines=lines, cross_pairs=cross, verify_items=len(vr),
                                 parse_cpu_s=med(tp, 0), check_cpu_s=med(tt, 0),
                                 verify_cpu_s=med(tv, 0), deadlock_cpu_s=med(td, 0),
                                 parse_wall_s=med(tp, 1), check_wall_s=med(tt, 1),
                                 verify_wall_s=med(tv, 1), deadlock_wall_s=med(td, 1),
                                 loadavg1=os.getloadavg()[0]))
                print(json.dumps(rows[-1]), flush=True)
                if lifecycle is False and topo == 'star' and K == 50:
                    open(os.path.join(os.path.dirname(out), 'sample_star_50.cadl'), 'w').write(gen(K, topo, lifecycle))
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == '__main__':
    main()
