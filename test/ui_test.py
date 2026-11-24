import os, sys, json, subprocess, tkinter as tk
sys.path.insert(0, os.getcwd())
import ZA_Battle_Loop as M

root = tk.Tk(); root.geometry('700x500+0+0'); root.title('PokeCon (dummy)')
def shot(name):
    root.update(); subprocess.run(['import','-window','root',name])

results = {}
def scenario1():
    # 既定表示 → スクショ → レストラン＋待ち時間変更 → 開始（保存あり）
    d = M._SettingsDialog
    dlg = d._current
    shot('ui_1_default_yukari.png')
    dlg.v_mode.set('restaurant'); dlg._update_mode()
    dlg.v_timing['fly_load_wait'].set('6.0'); dlg.v_timing['restaurant_walk_right'].set('3.5')
    dlg._stop_countdown()
    shot('ui_2_restaurant.png')
    dlg.v_skip.set(True); dlg._update_mode(); shot('ui_3_skip.png'); dlg.v_skip.set(False)
    dlg._ok()

# show() が呼ばれたら _current に入れる
orig_show = M._SettingsDialog.show
def show(self):
    M._SettingsDialog._current = self
    root.after(800, results['next'])
    return orig_show(self)
M._SettingsDialog.show = show

cmd = M.ZA_Battle_Loop(None, root)
results['next'] = scenario1
r = cmd.start(None, lambda: print('postProcess'))
print('1) start ->', r, '| cfg:', cmd.cfg['mode'], cmd.cfg['fly_load_wait'], cmd.cfg['restaurant_walk_right'])
saved = json.load(open('config.json'))
print('   保存:', saved['mode'], saved['fly_load_wait'], saved['restaurant_walk_right'])

# 2) キャンセル
def scenario2(): M._SettingsDialog._current._cancel()
results['next'] = scenario2
cmd2 = M.ZA_Battle_Loop(None, root)
r = cmd2.start(None, lambda: print('   postProcess 呼ばれた'))
root.update()
print('2) cancel ->', r, cmd2.cfg)

# 3) 不正値 → messagebox（showinfo を差し替えて確認）
msgs = []
M._SettingsDialog._current = None
import tkinter.messagebox as mb
def scenario3():
    dl = M._SettingsDialog._current
    dl.messagebox.showinfo = lambda t, m, parent=None: msgs.append(m)
    dl.v_timing['enter_load_wait'].set('abc'); dl._ok()
    dl.v_timing['enter_load_wait'].set('99'); dl._ok()
    dl._cancel()
results['next'] = scenario3
M.ZA_Battle_Loop(None, root).start(None, None)
print('3) 入力チェック:', msgs)

# 4) 自動開始カウントダウン（2秒）
json.dump(dict(saved, settings_ui_timeout_seconds=2), open('config.json','w'), ensure_ascii=False)
def scenario4(): shot('ui_4_countdown.png')
results['next'] = scenario4
cmd4 = M.ZA_Battle_Loop(None, root)
r = cmd4.start(None, None)
print('4) 自動開始 ->', r, cmd4.cfg['mode'])

# 5) show_settings_ui=false → 画面なし
json.dump(dict(saved, show_settings_ui=False), open('config.json','w'), ensure_ascii=False)
results['next'] = lambda: print('   NG: 画面が出た')
cmd5 = M.ZA_Battle_Loop(None, root)
print('5) 画面なし ->', cmd5.start(None, None), cmd5.cfg['mode'])
root.destroy()
