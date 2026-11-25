import os, sys, io, contextlib
sys.path.insert(0, os.getcwd())
from Commands import PythonCommandBase as B
import v100, v110

def run(mod, cfg):
    B.LOG.clear(); n = mod.ZA_Battle_Loop(None); n.cfg = mod.normalize_config(cfg)
    with contextlib.redirect_stdout(io.StringIO()):
        try: n.do()
        except B.Stop: pass
    return list(B.LOG)

ok = True
for mode in ('yukari', 'restaurant'):
    a = run(v100, {'mode': mode, 'max_loop': 3}); b = run(v110, {'mode': mode, 'max_loop': 3})
    print(f'{mode}: 既定(X)が v1.0.0 と一致:', a == b, len(a)); ok &= a == b
    b2 = run(v110, {'mode': mode, 'max_loop': 3, 'move_button': 'X'}); ok &= a == b2
base = run(v110, {'mode': 'yukari', 'skip_move': True, 'max_loop': 2, 'move_button': 'X'})
bA = run(v110, {'mode': 'yukari', 'skip_move': True, 'max_loop': 2, 'move_button': 'a'})
diff = [(i, x, y) for i, (x, y) in enumerate(zip(base, bA)) if x != y]
print('A 選択: 差分', diff, '長さ同じ:', len(base) == len(bA))
ok &= len(base) == len(bA) and [d[1] for d in diff] == [('press','X',0.1,0.1)]*2 and all(d[2] == ('press','A',0.1,0.1) for d in diff)
print('1ループ(A):', bA[:8])
with contextlib.redirect_stdout(io.StringIO()) as f:
    for bad in ('Y', 'B', '', None, 1):
        c = v110.normalize_config({'move_button': bad}); ok &= c['move_button'] == 'X'
print('不正値→X:', f.getvalue().count('[Warning]'), '件の警告')
ok &= v110.normalize_config({'move_button': ' x '})['move_button'] == 'X'
ok &= v110.normalize_config({})['move_button'] == 'X'
print('ALL OK' if ok else 'NG')
