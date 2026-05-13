# -*- coding: utf-8 -*-
"""
🥥 椰子蛋桌面宠物 v2.0
会在桌面上自由走动的可爱椰子蛋！
"""

import tkinter as tk
from tkinter import messagebox
import random
import math
import json
import os
import sys
import time

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pet_config.json")
DEFAULT_CONFIG = {
    "x": 400, "y": 400,
    "opacity": 0.95,
    "walk_freq": 50,   # 走动频率 0~100
}

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except:
        return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except:
        pass


class CoconutPet:
    """🥥 椰子蛋 — 会满屏溜达的桌面宠物"""

    SIZE = 130          # 绘制大小
    W = 160             # 窗口宽
    H = 180             # 窗口高
    WALK_SPEED = 2.5    # 行走速度（像素/帧）
    SCREEN_MARGIN = 50  # 不贴边

    COLORS = {
        "shell": "#5D4037", "shell_light": "#795548", "shell_dark": "#3E2723",
        "yolk": "#FFD54F", "yolk_light": "#FFE082",
        "eye_w": "#FFFFFF", "eye_p": "#212121",
        "blush": "#FF8A80", "mouth": "#BF360C", "shadow": "#E0E0E0"
    }

    def __init__(self):
        self.config = load_config()
        self.screen_w = 0
        self.screen_h = 0

        # ── 窗口 ──
        self.win = tk.Tk()
        self.win.title("CoconutPet")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-transparentcolor", "#000001")
        self.win.config(bg="#000001")
        self.win.wm_attributes("-alpha", self.config["opacity"])

        # 获取屏幕尺寸
        self.win.update_idletasks()
        self.screen_w = self.win.winfo_screenwidth()
        self.screen_h = self.win.winfo_screenheight()
        sx = min(self.config["x"], self.screen_w - self.W)
        sy = min(self.config["y"], self.screen_h - self.H)
        self.win.geometry(f"{self.W}x{self.H}+{sx}+{sy}")

        self.canvas = tk.Canvas(self.win, width=self.W, height=self.H,
                                bg="#000001", highlightthickness=0)
        self.canvas.pack()

        # ── 动画状态 ──
        self.frame = 0
        self.state = "idle"          # idle | blink | walk | sleep | stretch | happy | wave | sit
        self.state_timer = 0
        self.state_max = 60
        self.blink_timer = 0
        self.mood = "happy"          # happy | sleepy | surprised | love | derp

        # 绘制偏移（在画布内做小范围上下微动）
        self.draw_x = self.W // 2
        self.draw_y = self.H // 2 + 5

        # ── 屏幕行走 ──
        self.walk_target_x = sx
        self.walk_target_y = sy
        self.walk_pause = 0          # 走到目标后停多久

        # ── 交互 ──
        self.drag_data = {"x": 0, "y": 0, "dragging": False}
        self.is_topmost = True
        self.bubble_text = ""
        self.clear_bubble_id = None

        # ── 绑定 ──
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.show_menu)
        self.win.protocol("WM_DELETE_WINDOW", self.on_exit)

        # ── 菜单 ──
        self.menu = tk.Menu(self.win, tearoff=0, bg="#FFF3E0", fg="#3E2723",
                           activebackground="#FFCC80", activeforeground="#3E2723")
        self.menu.add_command(label="😊 换心情", command=self.cycle_mood)
        self.menu.add_command(label="💬 说句话", command=self.say_something)
        self.menu.add_separator()
        self.menu.add_command(label="📌 置顶" , command=self.toggle_topmost)
        self.menu.add_command(label="🎚 透明度", command=self.adjust_opacity)
        self.menu.add_command(label="🚶 走动频率", command=self.adjust_walk_freq)
        self.menu.add_separator()
        self.menu.add_command(label="❌ 退出", command=self.on_exit)

        self.after_id = None
        self.say("嗨！我是椰子蛋 🥥")
        self._schedule_next()

    # ════════════════════════════════════════════════
    #  主循环
    # ════════════════════════════════════════════════

    def tick(self):
        self.frame += 1
        self.state_timer += 1
        self.blink_timer += 1

        # ── 眨眼 ──
        if self.blink_timer > random.randint(80, 200) and self.state not in ("sleep", "blink"):
            self.state = "blink"
            self.state_timer = 0
            self.blink_timer = 0

        if self.state == "blink" and self.state_timer >= 4:
            self.state = "idle"

        # ── 空闲时随机行动 ──
        if self.state in ("idle",) and self.state_timer > 20:
            r = random.random()
            # walk_freq: 0=静止 50=正常 100=超活跃
            walk_chance = 0.008 * (self.config.get("walk_freq", 50) / 50.0)
            if r < walk_chance:
                self.start_walk()
            elif r < 0.012:
                self.state = "stretch"
                self.state_timer = 0
                self.state_max = 30
            elif r < 0.015:
                self.state = "sit"
                self.mood = random.choice(["happy", "sleepy", "derp"])
                self.state_timer = 0
                self.state_max = 40

        # ── 睡觉会持续 ──
        if self.state == "sleep":
            if self.state_timer > random.randint(150, 300):
                self.state = "stretch"
                self.state_timer = 0
                self.state_max = 20

        # ── 状态到期复位 ──
        if self.state in ("stretch", "sit", "wave") and self.state_timer >= self.state_max:
            self.state = "idle"
            self.mood = "happy"

        # ── 行走 ──
        if self.state == "walk":
            self.do_walk()

        # ── 绘制 ──
        self.draw()
        self._schedule_next()

    def _schedule_next(self):
        if self.after_id:
            self.win.after_cancel(self.after_id)
        self.after_id = self.win.after(30, self.tick)

    # ════════════════════════════════════════════════
    #  屏幕行走
    # ════════════════════════════════════════════════

    def start_walk(self):
        """选择一个随机桌面位置并走过去"""
        if self.state == "walk":
            return
        margin = self.SCREEN_MARGIN
        tx = random.randint(margin, self.screen_w - margin - self.W)
        ty = random.randint(margin, self.screen_h - margin - self.H)
        self.walk_target_x = tx
        self.walk_target_y = ty
        self.state = "walk"
        self.state_timer = 0
        self.mood = random.choice(["happy", "happy", "derp", "happy"])
        self.walk_pause = random.randint(30, 100)

    def do_walk(self):
        """移动窗口朝目标行走"""
        cx = self.win.winfo_x()
        cy = self.win.winfo_y()
        dx = self.walk_target_x - cx
        dy = self.walk_target_y - cy
        dist = math.hypot(dx, dy)

        speed = self.WALK_SPEED
        if self.mood == "derp":
            speed *= 1.8

        if dist > speed:
            nx = cx + (dx / dist) * speed
            ny = cy + (dy / dist) * speed
            self.win.geometry(f"+{int(nx)}+{int(ny)}")
        else:
            self.win.geometry(f"+{self.walk_target_x}+{self.walk_target_y}")
            # 到达后停一会
            if self.walk_pause > 0:
                self.walk_pause -= 1
                # 到达时切换表情和说话
                if self.walk_pause == 90:
                    arrival = [
                        "到啦！", "这里不错~", "歇会儿 🥥",
                        "呼呼~", "风景挺好 🌴", "就这儿了！"
                    ]
                    self.mood = random.choice(["happy", "happy", "sleepy", "derp"])
                    if random.random() < 0.4:
                        self.say(random.choice(arrival))
                return
            self.state = "idle"
            self.mood = "happy"
            self.state_timer = 0

            # 自动存档位置
            self.config["x"] = self.walk_target_x
            self.config["y"] = self.walk_target_y
            save_config(self.config)

    # ════════════════════════════════════════════════
    #  绘制
    # ════════════════════════════════════════════════

    def draw(self):
        self.canvas.delete("all")
        cx, cy = self.W // 2, self.H // 2 + 5
        C = self.COLORS
        s = 1.0

        # ── 随状态变化弹跳系数 ──
        bounce = 1.0
        if self.state == "walk":
            bounce = 1.0 + 0.04 * math.sin(self.frame * 0.6)
        elif self.state == "sleep":
            bounce = 1.0 + 0.015 * math.sin(self.frame * 0.12)
        elif self.state == "stretch":
            bounce = 1.0 + 0.06 * math.sin(self.frame * 0.5)
        elif self.state == "sit":
            bounce = 0.98
        else:
            bounce = 1.0 + 0.02 * math.sin(self.frame * 0.15)

        # ── 阴影 ──
        sh_y = cy + 48 * bounce + 4
        self.canvas.create_oval(cx-35, sh_y-6, cx+35, sh_y+6,
                                fill=C["shadow"], outline="")

        # ── 椰子壳 ──
        sr_x = 32 * bounce
        sr_y = 28 * bounce
        st = cy - 4 * bounce
        self.canvas.create_oval(cx - sr_x, st - sr_y, cx + sr_x, st + sr_y,
                                fill=C["shell"], outline=C["shell_dark"], width=2)
        self.canvas.create_oval(cx - sr_x + 5, st - sr_y + 5,
                                cx + sr_x - 5, st + sr_y - 5,
                                fill=C["shell_light"], outline="")
        # 壳纹
        for i in range(3):
            a = i * 0.8 - 0.8
            self.canvas.create_line(
                cx + 20*math.cos(a)*bounce, (st+8) + 15*math.sin(a)*bounce,
                cx + 28*math.cos(a+0.3)*bounce, (st-2) + 12*math.sin(a+0.3)*bounce,
                fill=C["shell_dark"], width=1.5)

        # ── 蛋黄 ──
        yk_cy = st - 12 * bounce
        yk_r = 22 * bounce
        self.canvas.create_oval(cx - yk_r, yk_cy - yk_r,
                                cx + yk_r, yk_cy + yk_r + 5,
                                fill=C["yolk"], outline="#F9A825", width=2)
        self.canvas.create_oval(cx - yk_r + 4, yk_cy - yk_r + 4,
                                cx + yk_r - 4, yk_cy + yk_r + 3,
                                fill=C["yolk_light"], outline="")
        # 高光
        self.canvas.create_oval(cx - 10, yk_cy - yk_r + 2,
                                cx, yk_cy - yk_r + 10,
                                fill="white", outline="", stipple="gray25")

        # ── 眼睛 ──
        eye_y = yk_cy + 2
        esp = 12
        blink = self.state in ("blink", "sleep")

        if self.mood == "surprised":
            for s in [-1, 1]:
                ex = cx + s * esp
                self.canvas.create_oval(ex-7, eye_y-7, ex+7, eye_y+7,
                                        fill=C["eye_w"], outline=C["shell_dark"], width=1)
                if not blink:
                    self.canvas.create_oval(ex-4, eye_y-4, ex+4, eye_y+4, fill=C["eye_p"])
        elif self.mood == "derp":
            for s in [-1, 1]:
                ex = cx + s * esp
                self.canvas.create_oval(ex-6, eye_y-6, ex+6, eye_y+6,
                                        fill=C["eye_w"], outline=C["shell_dark"], width=1)
                if not blink:
                    ix = cx + (2 if s == -1 else -2)
                    self.canvas.create_oval(ix-2, eye_y-2, ix+2, eye_y+2, fill=C["eye_p"])
        elif self.mood == "love":
            for s in [-1, 1]:
                ex = cx + s * esp
                self.canvas.create_text(ex, eye_y, text="❤️",
                                        font=("Segoe UI Emoji", 11), tags="hearts")
        else:
            for s in [-1, 1]:
                ex = cx + s * esp
                if blink:
                    self.canvas.create_line(ex-7, eye_y, ex+7, eye_y,
                                            fill=C["shell_dark"], width=2.5)
                else:
                    self.canvas.create_oval(ex-6, eye_y-6, ex+6, eye_y+6,
                                            fill=C["eye_w"], outline=C["shell_dark"], width=1)
                    self.canvas.create_oval(ex-3, eye_y-3, ex+3, eye_y+3, fill=C["eye_p"])

        # ── 嘴巴 ──
        my = eye_y + 14
        if self.state == "sleep":
            self.canvas.create_arc(cx-6, my-2, cx+6, my+4, start=0, extent=180,
                                   fill="", outline=C["mouth"], width=1.5)
            self.canvas.create_text(cx+20, eye_y-14, text="💤",
                                    font=("Segoe UI Emoji", 10))
        elif self.mood == "surprised":
            self.canvas.create_oval(cx-4, my-3, cx+4, my+3,
                                    fill=C["mouth"], outline=C["shell_dark"], width=1)
        elif self.mood == "derp":
            self.canvas.create_arc(cx-5, my-1, cx+5, my+4, start=0, extent=180,
                                   fill="", outline=C["mouth"], width=1.5)
            self.canvas.create_oval(cx-3, my+2, cx+3, my+8,
                                    fill="#FF8A80", outline=C["mouth"], width=1)
        else:
            ext = 200 if self.state in ("happy", "wave") else 180
            self.canvas.create_arc(cx-6, my-2, cx+6, my+4, start=0,
                                   extent=ext, fill="", outline=C["mouth"], width=1.5)

        # ── 腮红 ──
        if self.mood in ("happy", "surprised", "derp", "love"):
            for s in [-1, 1]:
                bx = cx + s * 22
                by = eye_y + 6
                self.canvas.create_oval(bx-5, by-3, bx+5, by+3,
                                        fill=C["blush"], outline="", stipple="gray25")

        # ── 气泡 ──
        if self.bubble_text:
            self._draw_bubble(cx, cy, bounce)

    def _draw_bubble(self, cx, cy, bounce):
        txt = self.bubble_text
        lines = self._wrap_text(txt, 14)
        max_l = max(len(l) for l in lines) if lines else 1
        bw = max_l * 8 + 20
        bh = len(lines) * 18 + 16
        bx = cx - bw // 2
        by = cy - 62 * bounce - bh

        self.canvas.create_oval(bx-4, by-4, bx+bw+4, by+bh+4,
                                fill="#FFFDE7", outline="#FFB74D", width=2)
        tx = cx
        ty = by + bh
        self.canvas.create_polygon(tx-8, ty, tx, ty+12, tx+8, ty,
                                   fill="#FFFDE7", outline="#FFB74D", width=2)
        for i, line in enumerate(lines):
            self.canvas.create_text(cx, by + 14 + i * 18, text=line,
                                    fill="#3E2723", font=("Microsoft YaHei", 9))

    def _wrap_text(self, text, n):
        lines, cur = [], ""
        for ch in text:
            if len(cur) >= n:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        if cur: lines.append(cur)
        return lines or [""]

    # ════════════════════════════════════════════════
    #  交互
    # ════════════════════════════════════════════════

    def on_click(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.drag_data["dragging"] = False

        self.state = "happy"
        self.state_timer = 0
        self.state_max = 15
        self.mood = random.choice(["happy", "surprised", "love", "derp"])

        reacts = [
            "哎哟！", "别戳我 🥥", "干嘛~", "嘿嘿嘿",
            "痒啦！", "再戳要生气了！", "mua~ ❤️",
            "(○｀3′○)", "咕噜咕噜~", "主人好！"
        ]
        self.say(random.choice(reacts))

    def on_drag(self, event):
        if abs(event.x - self.drag_data["x"]) > 3 or abs(event.y - self.drag_data["y"]) > 3:
            self.drag_data["dragging"] = True
        if self.drag_data["dragging"]:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            x = self.win.winfo_x() + dx
            y = self.win.winfo_y() + dy
            self.win.geometry(f"+{int(x)}+{int(y)}")

    def on_release(self, event):
        if not self.drag_data["dragging"]:
            return
        self.drag_data["dragging"] = False
        self.config["x"] = self.win.winfo_x()
        self.config["y"] = self.win.winfo_y()
        save_config(self.config)
        self.state = "idle"
        self.mood = "happy"
        self.say("放这里啦 🥥")

    def show_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def toggle_topmost(self):
        self.is_topmost = not self.is_topmost
        self.win.attributes("-topmost", self.is_topmost)
        self.say("置顶 " + ("✅" if self.is_topmost else "❌"))

    def adjust_opacity(self):
        top = tk.Toplevel(self.win)
        top.title("透明度")
        top.geometry(f"250x100+{self.win.winfo_x()+20}+{self.win.winfo_y()+20}")
        top.resizable(False, False)
        top.attributes("-topmost", True)

        tk.Label(top, text="🎚 透明度", font=("Microsoft YaHei", 10)).pack(pady=3)
        var = tk.DoubleVar(value=self.config["opacity"])

        def slide(v):
            self.win.wm_attributes("-alpha", float(v))

        tk.Scale(top, from_=0.3, to=1.0, resolution=0.05,
                 orient=tk.HORIZONTAL, variable=var, command=slide, length=200).pack()

        def save():
            self.config["opacity"] = float(var.get())
            save_config(self.config)
            top.destroy()

        tk.Button(top, text="确定", command=save,
                  bg="#FFCC80", fg="#3E2723").pack(pady=3)

    def adjust_walk_freq(self):
        top = tk.Toplevel(self.win)
        top.title("走动频率")
        top.geometry(f"250x140+{self.win.winfo_x()+30}+{self.win.winfo_y()+30}")
        top.resizable(False, False)
        top.attributes("-topmost", True)

        tk.Label(top, text="🚶 走动频率", font=("Microsoft YaHei", 10)).pack(pady=3)
        var = tk.IntVar(value=self.config.get("walk_freq", 50))

        # 标签提示
        lbl = tk.Label(top, text="", font=("Microsoft YaHei", 9), fg="#795548")
        lbl.pack()

        def slide(v):
            val = int(float(v))
            labels = {0: "🪨 静止不动", 25: "🐢 偶尔走走", 50: "🚶 正常", 75: "🏃 活泼", 100: "💨 根本停不下来"}
            label = next(v for k, v in sorted(labels.items(), reverse=True) if val >= k)
            lbl.config(text=label)

        s = tk.Scale(top, from_=0, to=100, resolution=10,
                     orient=tk.HORIZONTAL, variable=var, command=slide, length=200)
        s.pack(pady=5)
        slide(self.config.get("walk_freq", 50))

        def save():
            self.config["walk_freq"] = int(var.get())
            save_config(self.config)
            top.destroy()

        btn_frame = tk.Frame(top, bg="#000001")
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="确定", command=save,
                  bg="#FFCC80", fg="#3E2723", width=8).pack(side=tk.LEFT, padx=5)

        def random_walk():
            """立刻触发一次随机走动"""
            top.destroy()
            self.start_walk()
            self.say("走咯~ 🚶️")

        tk.Button(btn_frame, text="立刻走走", command=random_walk,
                  bg="#A5D6A7", fg="#1B5E20", width=8).pack(side=tk.LEFT, padx=5)

    def cycle_mood(self):
        moods = ["happy", "sleepy", "surprised", "love", "derp"]
        idx = moods.index(self.mood) if self.mood in moods else 0
        self.mood = moods[(idx + 1) % len(moods)]
        names = {"happy": "开心", "sleepy": "困困", "surprised": "惊讶",
                 "love": "爱心", "derp": "搞怪"}
        self.say(f"🥥 {names.get(self.mood, '?')}模式！")

    def say_something(self):
        texts = [
            "椰子蛋来啦 🥥", "无聊~", "今天吃什么？",
            "摸鱼中 🐟", "主人好！", "好想出去玩 🌴",
            "咕噜咕噜~", "🥥 椰！", "代码写完了吗？",
            "困了 Zzz...", "嘿嘿嘿~", "今天心情不错 😊",
            "🥥 椰椰椰！"
        ]
        self.say(random.choice(texts))

    def say(self, text):
        self.bubble_text = text
        if self.clear_bubble_id:
            self.win.after_cancel(self.clear_bubble_id)
        self.clear_bubble_id = self.win.after(2500, lambda: setattr(self, "bubble_text", ""))

    def on_exit(self):
        if messagebox.askokcancel("🥥 椰子蛋", "真的要走吗？😢"):
            if self.after_id:
                self.win.after_cancel(self.after_id)
            save_config(self.config)
            self.win.destroy()
            sys.exit(0)

    # ════════════════════════════════════════════════
    #  启动
    # ════════════════════════════════════════════════

    def run(self):
        self.tick()
        self.win.mainloop()


if __name__ == "__main__":
    pet = CoconutPet()
    pet.run()
