"""Paired timing of two cadl source trees under the same machine load.

    python -I paired.py OLD_SRC NEW_SRC out.csv [--reps 3]

For each configuration, the two versions run alternately in fresh processes
(old, new, old, new, ...), and each run reports the process CPU time of
parse, type_check and verify on the same generated description.
"""
import csv, json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
WORKER = r'''
import sys, json, time
sys.path.insert(0, sys.argv[1]); sys.path.insert(1, sys.argv[2])
import cadl
from cadl.parser import parse_file
from cadl.type_checker import type_check
from cadl.verifier import verify
def t(fn, *a):
    c = time.process_time(); r = fn(*a); return time.process_time() - c, r
p, ast = t(parse_file, sys.argv[3])
c, _ = t(type_check, ast)
v, res = t(verify, ast)
print(json.dumps({"version": cadl.__version__, "parse": p, "check": c, "verify": v, "items": len(res)}))
'''
CONFIGS = [('star', 0, 50), ('star', 0, 100), ('star', 1, 100), ('star', 0, 200), ('chain', 0, 200)]

def main():
    old, new, out = sys.argv[1:4]
    reps = int(sys.argv[sys.argv.index('--reps') + 1]) if '--reps' in sys.argv else 3
    sys.path.insert(0, HERE)
    import scale
    rows = []
    for topo, lc, k in CONFIGS:
        fd, path = tempfile.mkstemp(suffix='.cadl'); os.write(fd, scale.gen(k, topo, lc).encode()); os.close(fd)
        for r in range(reps):
            for src in (old, new):
                o = subprocess.run([sys.executable, '-I', '-c', WORKER, src, HERE, path], capture_output=True, text=True)
                d = json.loads(o.stdout); d.update(topology=topo, lifecycle=lc, contracts=k, rep=r, loadavg1=os.getloadavg()[0])
                rows.append(d); print(json.dumps(d), flush=True)
        os.unlink(path)
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

if __name__ == '__main__':
    main()
