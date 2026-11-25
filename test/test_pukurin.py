"""v1.2.0 の確認。比較元として v1.1.0 を v110.py、本版を v120.py として同じフォルダに置いて実行する"""
import os, sys, io, contextlib
sys.path.insert(0, os.getcwd())
from Commands import PythonCommandBase as B
import v110, v120

def run(mod, cfg):
    B.LOG.clear(); n = mod.ZA_Battle_Loop(None); n.cfg = mod.normalize_config(cfg)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try: n.do()
        except B.Stop: pass
    return list(B.LOG), out.getvalue()

ok = True
# 1) 既存モードは v1.1.0 と同じ入力
for mode in ('yukari', 'restaurant'):
    for extra in ({}, {'move_button': 'A'}, {'skip_move': True}, {'fly_load_wait': 6, 'enter_load_wait': 5}):
        cfg = dict({'mode': mode, 'max_loop': 3}, **extra)
        a, _ = run(v110, cfg); b, _ = run(v120, cfg)
        ok &= a == b
        print(f'{mode} {extra}: v1.1.0 と一致', a == b, len(a))

# 2) プクリン: 移動なし、最初からバトルループだけ
loop1 = [('hold','ZL'),('press','A',0.1,0.1),('wait',0.2),('press','X',0.1,0.1),('wait',0.1),('holdEnd','ZL'),('wait',0.2)]
b, out = run(v120, {'mode': 'pukurin', 'max_loop': 3})
print('pukurin 入力:', len(b), '件 / 期待', len(loop1)*3 + 1)
ok &= b == loop1*3 + [('finish',)]
ok &= '移動: なし' in out
print('pukurin ログ:', [l for l in out.splitlines() if '移動' in l or '技ボタン' in l])

# 3) プクリン + skip_move=True でも同じ / 待ち時間を変えても入力は変わらない
b2, _ = run(v120, {'mode': 'pukurin', 'max_loop': 3, 'skip_move': True, 'fly_load_wait': 9})
ok &= b2 == b; print('pukurin skip/待ち時間の影響なし:', b2 == b)

# 4) プクリン + 技ボタン A
b3, _ = run(v120, {'mode': 'pukurin', 'max_loop': 1, 'move_button': 'A'})
ok &= b3[3] == ('press','A',0.1,0.1); print('pukurin 技ボタンA:', b3[3])

# 5) mode の正規化
ok &= v120.normalize_config({'mode': ' PUKURIN '})['mode'] == 'pukurin'
ok &= [v120.mode_has_move(m) for m in ('yukari','restaurant','pukurin')] == [True, True, False]
print('ALL OK' if ok else 'NG')
