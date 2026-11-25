import os, sys, json, subprocess, tkinter as tk
sys.path.insert(0, os.getcwd())
import ZA_Battle_Loop as M
root = tk.Tk(); root.geometry('700x500+0+0')
orig_show = M._SettingsDialog.show
state = {}
def show(self):
    root.after(800, lambda: state['fn'](self)); return orig_show(self)
M._SettingsDialog.show = show

def is_disabled(w): return 'disabled' in w.state()
def timing_states(d):
    return {k: is_disabled(d.timing_rows[k].winfo_children()[1]) for k in d.timing_rows}

def check(d):
    d._stop_countdown()
    res = {}
    for m in ('yukari', 'restaurant', 'pukurin'):
        d.v_mode.set(m); d._update_mode(); root.update()
        res[m] = (is_disabled(d.skip_check), timing_states(d), d.no_move_label.cget('text') != '')
        if m == 'pukurin':
            subprocess.run(['import', '-window', 'root', 'ui_6_pukurin.png'])
    state['res'] = res
    d._ok()
state['fn'] = check
cmd = M.ZA_Battle_Loop(None, root)
print('start ->', cmd.start(None, None), '| mode:', cmd.cfg['mode'], '| 保存:', json.load(open('config.json'))['mode'])
for m, (skip_dis, t, note) in state['res'].items():
    print(f'{m}: 移動スキップ灰色={skip_dis} 注意表示={note} 待ち時間灰色={[k for k,v in t.items() if v]}')
r = state['res']
ok = (r['pukurin'][0] and all(r['pukurin'][1].values()) and r['pukurin'][2]
      and not r['yukari'][0] and not r['yukari'][2] and [k for k,v in r['yukari'][1].items() if v] == ['restaurant_walk_right']
      and [k for k,v in r['restaurant'][1].items() if v] == ['yukari_elevator_wait'])
state['fn'] = lambda d: (print('次回の初期表示:', d.v_mode.get(), '/ 移動スキップ灰色:', is_disabled(d.skip_check)), d._cancel())
M.ZA_Battle_Loop(None, root).start(None, None)
print('UI OK' if ok else 'UI NG')
root.destroy()
