import json, os, sys
sys.path.insert(0, os.getcwd())
from Commands import PythonCommandBase as B
import orig, new

def orig_loop(loops):
    B.LOG.clear(); o = orig.ZA_Yukari_Infinity(None); o.LIMIT = loops
    try: o.do()
    except B.Stop: pass
    return list(B.LOG)

def new_run(cfg):
    B.LOG.clear(); n = new.ZA_Battle_Loop(None)
    n.cfg = new.normalize_config(cfg)
    try: n.do()
    except B.Stop: pass
    return list(B.LOG)

ok = True
# 1) ユカリ: 元の do() と完全一致（2ループ）
a = orig_loop(2)
b = new_run({'mode':'yukari','max_loop':2})
b = [x for x in b if x[0] != 'finish']
same = (a == b[:-1] and b[-1] == ('wait',0.2)); print('yukari 一致:', same, len(a)); ok &= same

# 2) レストラン: 元のメソッド（Right→RIGHT に読み替え）＋ループ
import enum
B.LOG.clear(); o = orig.ZA_Yukari_Infinity(None)
o.move_to_RolingzDreamer()
try: o.move_to_Restaurant(); print('orig restaurant: 例外なし')
except AttributeError as e: print('orig restaurant 例外（想定どおり）:', e)
src = open('orig.py').read().replace('Direction.Right','Direction.RIGHT')
ns = {}; exec(compile(src,'orig_fixed','exec'), ns)
B.LOG.clear(); o = ns['ZA_Yukari_Infinity'](None)
o.move_to_RolingzDreamer(); o.move_to_Restaurant(); o.LIMIT=None
exp = list(B.LOG)
b = new_run({'mode':'restaurant','max_loop':2})
moves = b[:len(exp)]
print('restaurant 移動一致:', moves == exp, len(exp)); ok &= moves == exp
print('restaurant ループ数:', sum(1 for x in b if x[0]=='holdEnd'), '末尾:', b[-1])

# 3) skip_move: 移動なし
b = new_run({'mode':'restaurant','skip_move':True,'max_loop':1})
print('skip 先頭:', b[0], '総数', len(b)); ok &= b[0] == ('hold','ZL')

# 4) 待ち時間の設定が効く
b = new_run({'mode':'restaurant','max_loop':1,'fly_load_wait':6.5,'enter_load_wait':5,'restaurant_walk_right':3.2})
print('timing:', ('wait',6.5) in b, ('wait',5.0) in b, ('press','RIGHT',3.2,0.1) in b)
ok &= ('wait',6.5) in b and ('wait',5.0) in b and ('press','RIGHT',3.2,0.1) in b
b = new_run({'mode':'yukari','max_loop':1,'yukari_elevator_wait':3.0})
print('elevator:', ('wait',3.0) in b); ok &= ('wait',3.0) in b

# 5) 不正値の正規化
c = new.normalize_config({'mode':'xxx','max_loop':'-5','fly_load_wait':'abc','skip_move':'true'})
print('normalize:', c['mode'], c['max_loop'], c['fly_load_wait'], c['skip_move'])
ok &= (c['mode'],c['max_loop'],c['fly_load_wait'],c['skip_move'])==('yukari',0,4.0,True)

# 6) config.json 読み込み（do() が start() を通らない場合）
n = new.ZA_Battle_Loop(None); B.LOG.clear(); n.LIMIT=1
try: n.do()
except B.Stop: pass
print('config 無しでも動く:', n.cfg['mode'])

# 7) Tk 無し → start は設定画面なしで開始
n = new.ZA_Battle_Loop(None)
print('start (gui=None):', n.start(None, lambda: None), n.cfg['mode'])
print('ALL OK' if ok else 'NG')
