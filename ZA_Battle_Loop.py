#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZA_Battle_Loop
『Pokémon Legends Z-A』の周回バトルを自動で繰り返すスクリプト（ZA_Yukari_Infinity の汎用版）。

モード
  - yukari     : ユカリトーナメント∞（ホテル シュールリッシュ）
  - restaurant : レストラン ローリングドリーマー（5連戦。2回目以降は 30,000円で再挑戦）

Start を押すと設定画面が出る（モード・移動スキップ・待ち時間など）。
設定は config.json に保存でき、実行リストから呼ばれたときは config.json の値で動く。
"""

import json
import os

from Commands.PythonCommandBase import ImageProcPythonCommand
from Commands.Keys import KeyPress, Hat, Button, Direction

VERSION = '1.1.0'

SCRIPT_DIR_ABS = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = 'config.json'
CONFIG_FILE_ABS = os.path.join(SCRIPT_DIR_ABS, CONFIG_FILE)

# =============================================================================
# モード定義
#   fly   : 空を飛ぶメソッド名
#   enter : 到着後、バトル相手の前まで行くメソッド名
# 新しい周回先を足すときは、ここに 1 行足して、移動メソッドを 2 つ書く
# =============================================================================
MODES = {
    'yukari': {
        'label': 'ユカリトーナメント∞（ホテル シュールリッシュ）',
        'fly': 'move_to_Surrealish',
        'enter': 'move_to_yukari',
    },
    'restaurant': {
        'label': 'レストラン ローリングドリーマー',
        'fly': 'move_to_RolingzDreamer',
        'enter': 'move_to_Restaurant',
    },
}

# 待ち時間（秒）。ロード時間は端末で違うので、設定画面か config.json で調整する
TIMING_KEYS = [
    # (キー, 画面の表示名, 説明, 使うモード（None = 共通）)
    ('fly_load_wait', '空を飛んだ後のロード待ち', '秒（到着画面が出るまで）', None),
    ('enter_load_wait', '建物に入った後のロード待ち', '秒（ドアを開けてから）', None),
    ('yukari_elevator_wait', 'エレベーター後の待ち', '秒（ユカリ用）', 'yukari'),
    ('restaurant_walk_right', '店員まで右へ歩く時間', '秒（レストラン用）', 'restaurant'),
]

# 技ボタン（バトルループで A の後に押すボタン）
MOVE_BUTTONS = ['A', 'X']

DEFAULT_CONFIG = {
    'mode': 'yukari',
    'move_button': 'X',              # 技ボタン（MOVE_BUTTONS のどれか）
    'skip_move': False,              # True: すでにバトル相手の前にいる（移動しない）
    'max_loop': 0,                   # バトルループの回数（0 = 止めるまで無限）
    'fly_load_wait': 4.0,
    'enter_load_wait': 3.5,
    'yukari_elevator_wait': 2.0,
    'restaurant_walk_right': 4.0,
    'debug_log': False,
    'show_settings_ui': True,
    'settings_ui_timeout_seconds': 30,  # 設定画面で操作がなければ自動で開始（0 = しない）
}


def _is_true(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def normalize_config(cfg):
    """読み込んだ設定を既定値で埋め、型と範囲をそろえる（おかしい値は既定値に戻す）"""
    out = dict(DEFAULT_CONFIG)
    if isinstance(cfg, dict):
        out.update(cfg)
    mode = str(out.get('mode', '')).strip().lower()
    if mode not in MODES:
        print(f"[Warning] mode '{out.get('mode')}' は使えません。'{DEFAULT_CONFIG['mode']}' で動きます。")
        mode = DEFAULT_CONFIG['mode']
    out['mode'] = mode
    btn = str(out.get('move_button', '')).strip().upper()
    if btn not in MOVE_BUTTONS:
        print(f"[Warning] move_button '{out.get('move_button')}' は使えません。'{DEFAULT_CONFIG['move_button']}' で動きます。")
        btn = DEFAULT_CONFIG['move_button']
    out['move_button'] = btn
    for key in ('skip_move', 'debug_log', 'show_settings_ui'):
        out[key] = _is_true(out[key])
    for key in ('max_loop', 'settings_ui_timeout_seconds'):
        try:
            out[key] = max(0, int(float(out[key])))
        except (TypeError, ValueError):
            out[key] = DEFAULT_CONFIG[key]
    for key, _, _, _ in TIMING_KEYS:
        try:
            v = float(out[key])
            out[key] = v if 0.0 <= v <= 60.0 else DEFAULT_CONFIG[key]
        except (TypeError, ValueError):
            out[key] = DEFAULT_CONFIG[key]
    return out


def load_config_file(path=CONFIG_FILE_ABS):
    if not os.path.exists(path):
        return dict(DEFAULT_CONFIG)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else dict(DEFAULT_CONFIG)
    except Exception as e:
        print(f"[Warning] {path} を読めませんでした（既定値で動きます）: {e}")
        return dict(DEFAULT_CONFIG)


def save_config_file(cfg, path=CONFIG_FILE_ABS):
    """ファイルにあるキーの順番はそのまま、無いキーは後ろに足す（知らないキーも消さない）"""
    data = {}
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}
    data.update(cfg)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, path)


def _is_main_thread():
    import threading
    return threading.current_thread() is threading.main_thread()


class ZA_Battle_Loop(ImageProcPythonCommand):
    # PCME 0.2.0 以降は NAME を構文解析だけで読むので、必ず文字列リテラルで書く。
    # バージョンを上げるときは VERSION とこの NAME の両方を書き換えること。
    NAME = "ZA 周回バトル v1.1.0"

    def __init__(self, cam, gui=None):
        # PCME 0.2.0: 第2引数にプレビュー（CaptureArea）が渡される。設定画面の親ウィンドウに使う
        try:
            super().__init__(cam, gui)
        except TypeError:
            super().__init__(cam)
        self.gui = gui
        self.cfg = None

    # ===================================================================
    # 移動用メソッド
    # ===================================================================
    def fly_to(self, name, point_up_count):
        """マップを開いて、エリア選択 → ポイントを ↑ point_up_count 回 → 空を飛ぶ"""
        print(f"移動: {name}")
        self.press(Button.PLUS, 0.2, 0.5)
        self.press(Button.Y, 0.2, 0.4)
        self.press(Button.MINUS, 0.2, 0.5)

        # エリア選択
        self.pressRep(Hat.BTM, repeat=1, duration=0.1, interval=0.1)
        self.press(Button.A, 0.2, 0.5)

        # ポイント選択
        self.pressRep(Hat.TOP, repeat=point_up_count, duration=0.1, interval=0.1)

        # 決定してロード待ち
        self.press(Button.A, 0.2, 0.5)  # 確認
        self.press(Button.A, 0.2, 0.5)  # 移動決定

        wait = self.cfg['fly_load_wait']
        print(f"ロード待機中({wait}秒)...")
        self.wait(wait)

    # --- 移動用メソッド 1: ユカリトーナメント∞
    def move_to_Surrealish(self):
        """ホテル シュールリッシュへ空を飛ぶ"""
        self.fly_to('ホテル シュールリッシュ', 7)

    def move_to_yukari(self):
        """施設に入りエレベーターを経てユカリの前へ"""
        print("移動: ユカリの元へ")

        # 施設へ入る～エレベーターまで
        self.press(Direction.UP, 2.0)
        self.wait(1.0)
        self.press(Button.A, 0.2, 0.5)  # ドアなど
        self.wait(self.cfg['enter_load_wait'])

        # エレベーター内～ユカリ前
        self.press(Direction.UP, 4.0)
        self.wait(1.0)
        self.press(Button.A, 0.2, 0.5)
        self.wait(self.cfg['yukari_elevator_wait'])

        # 最終調整
        self.press(Direction.UP, 2.0)
        self.wait(0.5)

    # --- 移動用メソッド 2: レストラン ローリングドリーマー
    def move_to_RolingzDreamer(self):
        """レストラン ローリングドリーマーへ空を飛ぶ"""
        self.fly_to('レストラン ローリングドリーマー', 3)

    def move_to_Restaurant(self):
        """レストランに入り、店員に話しかける"""
        print("移動: レストランに入る")

        # 施設へ入る
        self.press(Direction.UP, 2.0)
        self.wait(1.0)
        self.press(Button.A, 0.2, 0.5)  # ドアなど
        self.wait(self.cfg['enter_load_wait'])

        # 店員に話しかける
        self.press(Direction.RIGHT, self.cfg['restaurant_walk_right'])
        self.wait(1.0)
        self.press(Button.A, 0.2, 0.5)
        self.wait(2.0)

    # ===================================================================
    # バトル
    # ===================================================================
    def battle_step(self):
        """ZL ホールド中に A → 技ボタンを押す（会話送り・再挑戦の確認・技選択を兼ねる）"""
        move_button = getattr(Button, self.cfg['move_button'])
        self.hold(Button.ZL)

        # 会話送り or 技選択(A)
        self.press(Button.A, duration=0.1)
        self.wait(0.2)

        # 技選択（設定の技ボタン。A を選んだときは A を 2 回押す）
        self.press(move_button, duration=0.1)
        self.wait(0.1)

        self.holdEnd(Button.ZL)
        self.wait(0.2)

    # ===================================================================
    # メインループ
    # ===================================================================
    def do(self):
        if self.cfg is None:
            # 実行リストなど、start() を通らずに呼ばれたとき
            self.cfg = normalize_config(load_config_file())
        cfg = self.cfg
        mode = MODES[cfg['mode']]

        print(f"=== ZA 周回バトル v{VERSION}: {mode['label']} ===")
        print(f"技ボタン: {cfg['move_button']}")
        if cfg['skip_move']:
            print("移動: スキップ（すでにバトル相手の前にいる設定）")
        else:
            getattr(self, mode['fly'])()
            getattr(self, mode['enter'])()

        max_loop = cfg['max_loop']
        print("--- ループ開始 ({}。停止するには Stop ボタン) ---".format(
            '無限' if max_loop == 0 else f'{max_loop} 回'))

        count = 0
        while max_loop == 0 or count < max_loop:
            self.battle_step()
            count += 1
            if cfg['debug_log'] and count % 100 == 0:
                print(f"[Debug] ループ {count} 回")

        print(f"=== 終了: ループ {count} 回 ===")
        self.finish()

    # ===================================================================
    # 開始前の設定画面
    # ===================================================================
    def _tk_root(self):
        """設定画面の親にする Tk のウィンドウ（Tk の画面が無いときは None）"""
        gui = getattr(self, 'gui', None)
        if gui is None:
            return None
        try:
            import tkinter as tk
            if not isinstance(gui, tk.Misc):
                return None
            return gui.winfo_toplevel()
        except Exception:
            return None

    def _later(self, fn):
        """画面のスレッドで、今の処理が終わった後に fn を呼ぶ（キャンセル時の postProcess 用）"""
        if fn is None:
            return
        root = self._tk_root()
        try:
            if root is not None:
                root.after_idle(fn)
                return
        except Exception:
            pass
        fn()

    def start(self, ser, postProcess):
        """Start ボタンで呼ばれる（画面のスレッド）。設定画面を出して、選んだ設定で開始する"""
        try:
            ok = self._prepare_settings()
        except Exception:
            import traceback
            traceback.print_exc()
            print("[Error] 設定画面でエラーが出たため、開始しませんでした。")
            ok = False
        if not ok:
            print("[System] 開始をキャンセルしました。")
            self._later(postProcess)
            return None
        return super().start(ser, postProcess)

    def _prepare_settings(self):
        """設定を決めて self.cfg に入れる。開始してよければ True、キャンセルなら False"""
        cfg = normalize_config(load_config_file())
        root = self._tk_root()
        if not cfg['show_settings_ui'] or root is None or not _is_main_thread():
            if cfg['show_settings_ui'] and root is None:
                print("[System] 設定画面を出せない画面なので、config.json の値で開始します。")
            self.cfg = cfg
            return True

        result = _SettingsDialog(root, cfg).show()
        if result is None:
            return False
        new_cfg, save = result
        if save:
            try:
                save_config_file(new_cfg)
                print(f"[System] 設定を保存しました: {CONFIG_FILE_ABS}")
            except Exception as e:
                print(f"[Warning] config.json に保存できませんでした（この回は画面の値で動きます）: {e}")
        self.cfg = normalize_config(new_cfg)
        return True


# =============================================================================
# 設定画面
# =============================================================================
class _SettingsDialog:
    """
    開始前に設定を選ぶ画面（Tk の Toplevel。Start を押した画面のスレッドで開き、閉じるまで待つ）。
    show() の戻り値: (設定の辞書, config.json に保存するか)。キャンセルなら None
    """

    def __init__(self, root, cfg):
        import tkinter as tk
        from tkinter import ttk, messagebox
        self.tk, self.ttk, self.messagebox = tk, ttk, messagebox
        self.root = root
        self.cfg = normalize_config(cfg)
        self.result = None
        self._countdown = None
        self._after_id = None
        self.muted = '#707070'

    def _row(self, parent, label):
        f = self.ttk.Frame(parent)
        f.pack(fill='x', pady=2)
        self.ttk.Label(f, text=label, width=26).pack(side='left')
        return f

    def _spin(self, parent, label, var, from_, to, inc, note):
        f = self._row(parent, label)
        sb = self.ttk.Spinbox(f, from_=from_, to=to, increment=inc, textvariable=var, width=8)
        sb.pack(side='left')
        self.ttk.Label(f, text=note, foreground=self.muted).pack(side='left', padx=6)
        return f

    def show(self):
        tk, ttk = self.tk, self.ttk
        c = self.cfg
        win = tk.Toplevel(self.root)
        self.win = win
        win.title(f"ZA 周回バトル v{VERSION}: 設定")
        win.transient(self.root)
        win.resizable(False, False)

        body = ttk.Frame(win, padding=12)
        body.pack(fill='both', expand=True)

        self.v_mode = tk.StringVar(value=c['mode'])
        self.v_skip = tk.BooleanVar(value=c['skip_move'])
        self.v_max_loop = tk.StringVar(value=str(c['max_loop']))
        self.v_move_button = tk.StringVar(value=c['move_button'])
        self.v_timing = {k: tk.StringVar(value=str(c[k])) for k, _, _, _ in TIMING_KEYS}
        self.v_debug = tk.BooleanVar(value=c['debug_log'])
        self.v_show_ui = tk.BooleanVar(value=c['show_settings_ui'])
        self.v_ui_timeout = tk.StringVar(value=str(c['settings_ui_timeout_seconds']))
        self.v_save = tk.BooleanVar(value=True)

        # --- 周回先
        box = ttk.LabelFrame(body, text='周回先', padding=8)
        box.pack(fill='x')
        for key, info in MODES.items():
            ttk.Radiobutton(box, text=info['label'], value=key, variable=self.v_mode,
                            command=self._update_mode).pack(anchor='w')
        ttk.Checkbutton(box, text='すでにバトル相手の前にいる（移動をスキップしてすぐループ）',
                        variable=self.v_skip, command=self._update_mode).pack(anchor='w', pady=(6, 0))

        # --- 待ち時間
        tbox = ttk.LabelFrame(body, text='待ち時間（ロードが遅い端末は長めに）', padding=8)
        tbox.pack(fill='x', pady=(8, 0))
        self.timing_rows = {}
        for key, label, note, _ in TIMING_KEYS:
            self.timing_rows[key] = self._spin(tbox, label, self.v_timing[key], 0.0, 60.0, 0.5, note)

        # --- ループ
        lbox = ttk.LabelFrame(body, text='ループ', padding=8)
        lbox.pack(fill='x', pady=(8, 0))
        f = self._row(lbox, '技ボタン（A の後に押す）')
        for b in MOVE_BUTTONS:
            ttk.Radiobutton(f, text=b, value=b, variable=self.v_move_button).pack(side='left', padx=(0, 12))
        self._spin(lbox, 'ループ回数', self.v_max_loop, 0, 9999999, 1, '回（0 = Stop を押すまで無限）')
        ttk.Checkbutton(lbox, text='デバッグログを出す（100 ループごとに回数を表示）',
                        variable=self.v_debug).pack(anchor='w')

        # --- この画面
        ubox = ttk.LabelFrame(body, text='この画面', padding=8)
        ubox.pack(fill='x', pady=(8, 0))
        ttk.Checkbutton(ubox, text='Start を押したときに、この画面を出す', variable=self.v_show_ui).pack(anchor='w')
        ttk.Label(ubox, text='外すと次から config.json の値ですぐ開始します（戻すには "show_settings_ui": true）。',
                  foreground=self.muted, wraplength=520).pack(anchor='w')
        self._spin(ubox, '何もしなければ自動で開始', self.v_ui_timeout, 0, 3600, 1, '秒（0 = 自動で開始しない）')

        # --- 下のボタン
        bottom = ttk.Frame(body)
        bottom.pack(fill='x', pady=(10, 0))
        ttk.Checkbutton(bottom, text='この設定を config.json に保存する', variable=self.v_save).pack(side='left')
        ttk.Button(bottom, text='キャンセル', command=self._cancel).pack(side='right', padx=3)
        ttk.Button(bottom, text='開始', command=self._ok).pack(side='right', padx=3)
        self.countdown_label = ttk.Label(body, text='', foreground=self.muted)
        self.countdown_label.pack(anchor='e', pady=(4, 0))

        win.protocol('WM_DELETE_WINDOW', self._cancel)
        win.bind('<Escape>', lambda e: self._cancel())
        for seq in ('<Button>', '<Key>', '<MouseWheel>'):
            win.bind(seq, self._stop_countdown, add='+')

        self._update_mode()
        self._start_countdown()

        win.update_idletasks()
        try:
            x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - win.winfo_width()) // 2)
            y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - win.winfo_height()) // 3)
            win.geometry(f'+{x}+{y}')
        except tk.TclError:
            pass
        try:
            win.grab_set()
        except tk.TclError:
            pass
        win.focus_set()
        self.root.wait_window(win)
        return self.result

    def _update_mode(self):
        """選んだモードで使わない待ち時間・移動をスキップするときの待ち時間を灰色にする"""
        mode = self.v_mode.get()
        skip = bool(self.v_skip.get())
        for key, _, _, only in TIMING_KEYS:
            enabled = not skip and (only is None or only == mode)
            for w in self.timing_rows[key].winfo_children():
                try:
                    w.state(['!disabled' if enabled else 'disabled'])
                except Exception:
                    pass

    # --- 自動で開始
    def _start_countdown(self):
        try:
            sec = int(float(self.v_ui_timeout.get()))
        except ValueError:
            sec = 0
        if sec <= 0:
            return
        self._countdown = sec
        self._tick()

    def _tick(self):
        if self._countdown is None:
            return
        if self._countdown <= 0:
            self.countdown_label.configure(text='')
            self._countdown = None
            self._ok(auto=True)
            return
        self.countdown_label.configure(text=f'あと {self._countdown} 秒操作がなければ、この設定で開始します（何か操作すると止まります）')
        self._countdown -= 1
        self._after_id = self.win.after(1000, self._tick)

    def _stop_countdown(self, event=None):
        if self._countdown is None:
            return
        self._countdown = None
        if self._after_id is not None:
            try:
                self.win.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self.countdown_label.configure(text='')

    # --- 決定
    @staticmethod
    def _num(var, label, cast, lo, hi):
        try:
            v = cast(float(str(var.get()).strip()))
        except ValueError:
            raise ValueError(f'{label}: 数字を入れてください')
        if not lo <= v <= hi:
            raise ValueError(f'{label}: {lo}〜{hi} の範囲で入れてください')
        return v

    def collect(self):
        """画面の値を config.json と同じ形の辞書にする（入力がおかしいときは ValueError）"""
        cfg = dict(self.cfg)
        cfg['mode'] = self.v_mode.get()
        cfg['skip_move'] = bool(self.v_skip.get())
        cfg['move_button'] = self.v_move_button.get()
        cfg['max_loop'] = self._num(self.v_max_loop, 'ループ回数', int, 0, 9999999)
        for key, label, _, _ in TIMING_KEYS:
            cfg[key] = round(self._num(self.v_timing[key], label, float, 0.0, 60.0), 2)
        cfg['debug_log'] = bool(self.v_debug.get())
        cfg['show_settings_ui'] = bool(self.v_show_ui.get())
        cfg['settings_ui_timeout_seconds'] = self._num(self.v_ui_timeout, '自動で開始するまでの秒数', int, 0, 3600)
        return cfg

    def _ok(self, auto=False):
        try:
            cfg = self.collect()
        except ValueError as e:
            if auto:
                print(f"[Warning] 設定画面: {e}（自動では開始しませんでした）")
            self.messagebox.showinfo('ZA 周回バトル', str(e), parent=self.win)
            return
        if auto:
            print('[System] 設定画面で操作がなかったので、表示していた設定で開始します。')
        self.result = (cfg, bool(self.v_save.get()))
        self._close()

    def _cancel(self):
        self.result = None
        self._close()

    def _close(self):
        self._stop_countdown()
        try:
            self.win.grab_release()
        except Exception:
            pass
        self.win.destroy()


# NAME（文字列リテラル）と VERSION の書き忘れに気づけるようにする
if ZA_Battle_Loop.NAME != f"ZA 周回バトル v{VERSION}":
    print(f"[Warning] NAME ({ZA_Battle_Loop.NAME}) と VERSION ({VERSION}) が合っていません。両方を同じ版に書き換えてください。")
