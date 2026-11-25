import os, sys, json, subprocess, tkinter as tk
sys.path.insert(0, os.getcwd())
import ZA_Battle_Loop as M
root = tk.Tk(); root.geometry('700x500+0+0')
orig_show = M._SettingsDialog.show
state = {}
def show(self):
    root.after(800, lambda: state['fn'](self)); return orig_show(self)
M._SettingsDialog.show = show
def pick_a(d):
    print('初期表示:', d.v_move_button.get())
    d._stop_countdown(); d.v_move_button.set('A'); root.update()
    subprocess.run(['import', '-window', 'root', 'ui_5_move_button_A.png']); d._ok()
state['fn'] = pick_a
cmd = M.ZA_Battle_Loop(None, root); print('start ->', cmd.start(None, None), '| cfg:', cmd.cfg['move_button'])
print('保存:', json.load(open('config.json'))['move_button'])
state['fn'] = lambda d: (print('次回の初期表示:', d.v_move_button.get()), d._cancel())
M.ZA_Battle_Loop(None, root).start(None, None)
root.destroy()
