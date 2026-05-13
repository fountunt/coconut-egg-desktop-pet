# -*- coding: utf-8 -*-
"""
Coconut Egg Desktop Pet v3.0
Full-featured desktop companion that walks, chases mouse, eats food, and has emotions!
"""

import tkinter as tk
from tkinter import messagebox
import random
import math
import json
import os
import sys
from datetime import datetime

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pet_config.json")
DEFAULT_CONFIG = {"x": 400, "y": 400, "opacity": 0.95, "walk_freq": 50}

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


class Particle:
    def __init__(self, canvas, x, y, kind="heart"):
        self.canvas = canvas
        self.x, self.y = x, y
        self.kind = kind
        self.age, self.max_age = 0, random.randint(30, 50)
        self.speed = random.uniform(1.0, 2.5)
        self.dx = random.uniform(-1.5, 1.5)
        self.id = None
        emojis = {"heart": ["\u2764\ufe0f", "\U0001f495", "\U0001f497"],
                  "star": ["\u2728", "\u2b50", "\U0001f31f"],
                  "note": ["\u266a", "\u266b", "\U0001f3b5"]}
        syms = emojis.get(kind, ["\u2728"])
        self.char = random.choice(syms)
        self.size = random.choice([9, 11, 13, 15])

    def update(self):
        self.age += 1
        self.life = max(0, 1.0 - self.age / self.max_age)
        if self.life <= 0: return False
        self.y -= self.speed
        self.x += self.dx * 0.5
        self.dx *= 0.98
        alpha = int(self.life * 255)
        color = f"#{alpha:02x}{alpha:02x}{alpha:02x}"
        self.canvas.delete(self.id)
        self.id = self.canvas.create_text(self.x, self.y, text=self.char,
            font=("Segoe UI Emoji", self.size), fill=color, tags="particle")
        return True


class Food:
    def __init__(self, canvas, x, y, kind=None):
        self.canvas = canvas
        self.x, self.y = x, y
        self.kind = kind or random.choice(["cake", "cookie", "milk", "fruit", "candy"])
        self.eaten = False
        self.id = None
        icons = {"cake": "\U0001f9c1", "cookie": "\U0001f36a", "milk": "\U0001f95b",
                 "fruit": "\U0001f34e", "candy": "\U0001f36c"}
        icon = icons.get(self.kind, "\U0001f36a")
        self.id = self.canvas.create_text(x, y, text=icon, font=("Segoe UI Emoji", 20), tags="food")

    def remove(self):
        self.canvas.delete(self.id)
        self.eaten = True


class CoconutPet:
    W, H = 160, 180
    WALK_SPEED = 2.5
    SCREEN_MARGIN = 50

    C = {"shell": "#5D4037", "shell_l": "#795548", "shell_d": "#3E2723",
         "yolk": "#FFD54F", "yolk_l": "#FFE082",
         "eye_w": "#FFFFFF", "eye_p": "#212121",
         "blush": "#FF8A80", "mouth": "#BF360C", "shadow": "#E0E0E0"}

    def __init__(self):
        self.cfg = load_config()
        self.win = tk.Tk()
        self.win.title("CoconutPet")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True, "-transparentcolor", "#000001")
        self.win.config(bg="#000001")
        self.win.wm_attributes("-alpha", self.cfg["opacity"])
        self.win.update_idletasks()
        self.sw = self.win.winfo_screenwidth()
        self.sh = self.win.winfo_screenheight()
        sx = min(self.cfg["x"], self.sw - self.W)
        sy = min(self.cfg["y"], self.sh - self.H)
        self.win.geometry(f"{self.W}x{self.H}+{sx}+{sy}")
        self.canvas = tk.Canvas(self.win, width=self.W, height=self.H,
                                bg="#000001", highlightthickness=0)
        self.canvas.pack()

        # State
        self.frame = 0
        self.state = "idle"       # idle | blink | walk | chase | eat | sleep | stretch | happy
        self.st = 0               # state timer
        self.bt = 0               # blink timer
        self.mood = "happy"
        self.wtx, self.wty = sx, sy
        self.wp = 0               # walk pause
        self.happiness = 50
        self.bubble = ""
        self.bubble_id = None
        self.chase_on = False
        self.cur_speed = 0.0       # current movement speed (for easing)
        self.target_dist = 0.0     # distance to target when started
        self.food = None
        self.particles = []
        self.drag = {"x": 0, "y": 0, "active": False}
        self.after_id = None

        # Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.show_menu)

        # Menu
        m = self.menu = tk.Menu(self.win, tearoff=0, bg="#FFF3E0", fg="#3E2723",
                               activebackground="#FFCC80", activeforeground="#3E2723")
        m.add_command(label="\U0001f60a 换心情", command=self.cycle_mood)
        m.add_command(label="\U0001f4ac 说句话", command=self.say_something)
        m.add_command(label="\U0001f36a 喂食", command=self.spawn_food)
        m.add_command(label="\U0001f43e 追鼠标模式", command=self.toggle_chase)
        m.add_command(label="\U0001f43e 追一次", command=self.chase_once)
        m.add_separator()
        m.add_command(label="\U0001f4cc 置顶", command=self.toggle_top)
        m.add_command(label="\U0001f39a 透明度", command=self.adjust_opacity)
        m.add_command(label="\U0001f6b6 走动频率", command=self.adjust_walk)
        m.add_separator()
        m.add_command(label="\U0001f60a 心情状态", command=self.show_status)
        m.add_separator()
        m.add_command(label="\u274c 退出", command=self.on_exit)

        self._greet()
        self._tick()

    def _greet(self):
        h = datetime.now().hour
        if h < 6: self.say("半夜了还没睡呀 \U0001f319")
        elif h < 9: self.say("早安主人！\U0001f965\u2600\ufe0f")
        elif h < 12: self.say("上午好~ 摸鱼吗？\U0001f41f")
        elif h < 14: self.say("中午啦，吃了吗？\U0001f35a")
        elif h < 18: self.say("下午好~ 有点困 \U0001f971")
        elif h < 22: self.say("晚上好！\U0001f965\U0001f306")
        else: self.say("夜深了，早点休息哦 \U0001f634")

    # ── Main Loop ──

    def _tick(self):
        self.frame += 1
        self.st += 1
        self.bt += 1

        if self.frame % 60 == 0 and self.happiness > 0:
            self.happiness = max(0, self.happiness - 0.3)

        # Blink
        if self.bt > random.randint(80, 200) and self.state not in ("sleep", "blink"):
            self.state = "blink"
            self.st = 0
            self.bt = 0
        if self.state == "blink" and self.st >= 4:
            self.state = "idle"

        # Idle actions
        if self.state in ("idle",) and self.st > 20:
            r = random.random()
            wc = 0.008 * (self.cfg.get("walk_freq", 50) / 50.0)
            if self.happiness > 70: wc *= 1.5
            elif self.happiness < 20: wc *= 0.5

            # Chase: 纯随机触发，不管鼠标在哪
            if r < 0.02:
                self._start_chase()
            # 追鼠标模式：频率更高
            elif self.chase_on and r < 0.04:
                self._start_chase()
            elif r < wc:
                self._start_walk()
            elif r < 0.012:
                self.state = "stretch"; self.st = 0
            elif r < 0.015:
                self.state = "sit"; self.st = 0
                self.mood = "sleepy" if self.happiness < 30 else random.choice(["happy", "sleepy", "derp"])

            if self.happiness < 15 and self.st > 50 and random.random() < 0.003:
                self.say(random.choice(["好无聊...", "没人理我 \U0001f622", "饿饿了...", "好孤单..."]))
                self._particles(2, "star")

        if self.state == "sleep" and self.st > random.randint(150, 300):
            self.state = "stretch"; self.st = 0

        if self.state in ("stretch", "sit") and self.st > 40:
            self.state = "idle"; self.mood = "happy" if self.happiness > 30 else "sleepy"

        if self.state == "walk": self._do_walk()
        if self.state == "chase": self._do_chase()
        if self.state == "eat": self._do_eat()

        self.particles = [p for p in self.particles if p.update()]
        self._draw()
        self.after_id = self.win.after(30, self._tick)

    # ── Particles ──

    def _particles(self, n=5, kind="heart"):
        cx, cy = self.W // 2, self.H // 2
        for _ in range(n):
            self.particles.append(Particle(self.canvas,
                cx + random.randint(-20, 20), cy + random.randint(-30, 10), kind))

    # ── Chase Mouse ──

    def toggle_chase(self):
        self.chase_on = not self.chase_on
        self.say("追鼠标模式 " + ("\U0001f7e2" if self.chase_on else "\U0001f534"))
        if self.chase_on: self._particles(3, "heart")

    def chase_once(self):
        """菜单触发：立刻追一次鼠标"""
        if self.state in ("walk", "chase", "eat"):
            self.say("等一下嘛...")
            return
        mx, my = self.win.winfo_pointerxy()
        cx = self.win.winfo_x() + self.W // 2
        cy = self.win.winfo_y() + self.H // 2
        dist = math.hypot(mx - cx, my - cy)
        if dist < 30:
            self.say("就在你旁边啦！\U0001f965")
            return
        self._start_chase()

    def _start_chase(self):
        """开始追逐 — 持续追踪直到抓到或鼠标不动太久"""
        if self.state in ("walk", "chase", "eat"): return
        self.state = "chase"; self.mood = "happy"; self.st = 0
        self.last_mx, self.last_my = self.win.winfo_pointerxy()
        self.mouse_still_frames = 0  # 鼠标静止了多少帧
        self._particles(3, "star")
        self.say("来追你啦！\U0001f3c3")

    def _do_chase(self):
        """连续追逐 — 不超时，鼠标不动太久才放弃"""
        cx = self.win.winfo_x() + self.W // 2
        cy = self.win.winfo_y() + self.H // 2
        mx, my = self.win.winfo_pointerxy()
        dx, dy = mx - cx, my - cy
        dist = math.hypot(dx, dy)

        # 检测鼠标是否在移动
        mouse_dx = mx - self.last_mx
        mouse_dy = my - self.last_my
        mouse_moved = math.hypot(mouse_dx, mouse_dy) > 3
        if mouse_moved:
            self.mouse_still_frames = 0
        else:
            self.mouse_still_frames += 1
        self.last_mx, self.last_my = mx, my

        # 抓到光标
        if dist < 35:
            self.state = "happy"; self.st = 0; self.cur_speed = 0.0
            self.mood = "love"
            self.happiness = min(100, self.happiness + 3)
            self._particles(5, "heart")
            if random.random() < 0.3:
                self.say(random.choice(["抓到啦！", "嘿嘿 \U0001f965", "找到你啦 \u2764\ufe0f"]))
            return

        # 鼠标一直没动超过 3 秒 — 放弃
        if self.mouse_still_frames > 100:
            self.state = "idle"; self.cur_speed = 0.0
            self.say("不跟我玩 😢")
            return

        # 鼠标跑太远 — 放弃
        if dist > 1000:
            self.state = "idle"; self.cur_speed = 0.0
            self.say("跑太远了追不上...")
            return

        # 加减速移动
        max_speed = self.WALK_SPEED * 1.3
        if self.cur_speed < max_speed:
            self.cur_speed = min(max_speed, self.cur_speed + 0.5)
        if dist < 50 and self.cur_speed > 0.5:
            self.cur_speed = max(0.5, self.cur_speed * (dist / 50))

        if dist > self.cur_speed:
            nx = (cx - self.W//2) + (dx / dist) * self.cur_speed
            ny = (cy - self.H//2) + (dy / dist) * self.cur_speed
            self.win.geometry(f"+{int(nx)}+{int(ny)}")
            self.mood = "happy"
        else:
            self.win.geometry(f"+{mx - self.W//2}+{my - self.H//2}")

    # ── Food ──

    def spawn_food(self):
        if self.food and not self.food.eaten:
            self.say("还没吃完呢 \U0001f36a"); return
        fx = self.W // 2 + random.randint(10, 40) * random.choice([-1, 1])
        fy = self.H // 2 + random.randint(20, 50)
        self.food = Food(self.canvas, fx, fy)
        self.state = "walk"
        self.wtx, self.wty = fx - 20, fy + 10
        self.wp = 5
        self._food_xy = (fx, fy)

    def _do_eat(self):
        self.st += 1
        if self.st == 1:
            self.mood = "love"
            self._particles(8, "heart")
            self.say(random.choice(["好吃！\U0001f970", "yummy~ \U0001f36a", "好香！", "再来一个！"]))
            self.happiness = min(100, self.happiness + 15)
        if self.st > 30:
            if self.food and not self.food.eaten:
                self.food.remove(); self.food = None
            self.state = "happy"; self.st = 0; self.mood = "love"

    # ── Walk ──

    def _start_walk(self):
        if self.state == "walk": return
        self.cur_speed = 0.5  # start slow for smooth acceleration
        m = self.SCREEN_MARGIN
        self.wtx = random.randint(m, self.sw - m - self.W)
        self.wty = random.randint(m, self.sh - m - self.H)
        self.state = "walk"; self.st = 0
        self.mood = random.choice(["happy", "happy", "derp", "happy"])
        self.wp = random.randint(30, 100)

    def _do_walk(self):
        cx, cy = self.win.winfo_x(), self.win.winfo_y()
        dx, dy = self.wtx - cx, self.wty - cy
        dist = math.hypot(dx, dy)
        speed = self.WALK_SPEED * (1.8 if self.mood == "derp" else 1.0)

        if dist > speed:
            self.win.geometry(f"+{int(cx+(dx/dist)*speed)}+{int(cy+(dy/dist)*speed)}")
            if random.random() < 0.01: self._particles(1, "note")
        else:
            self.win.geometry(f"+{self.wtx}+{self.wty}")
            # Check if reached food
            if hasattr(self, '_food_xy') and self.food and not self.food.eaten:
                fx, fy = self._food_xy
                if math.hypot(self.wtx-(self.win.winfo_x()+fx-20), self.wty-(self.win.winfo_y()+fy+10)) < 40:
                    self.state = "eat"; self.st = 0; return
            if self.wp > 0:
                self.wp -= 1
                if self.wp == 90 and random.random() < 0.3:
                    self.say(random.choice(["到啦！", "这里不错~", "歇会儿 \U0001f965",
                               "呼呼~", "风景挺好 \U0001f334", "就这儿了！"]))
                return
            self.state = "idle"; self.mood = "happy"; self.st = 0
            self.cfg["x"], self.cfg["y"] = self.wtx, self.wty
            save_config(self.cfg)
            if random.random() < 0.2: self._particles(2, "heart")

    # ── Draw ──

    def _draw(self):
        self.canvas.delete("all")
        cx, cy = self.W // 2, self.H // 2 + 5
        C = self.C

        b = 1.0
        if self.state in ("walk", "chase"): b = 1.0 + 0.04 * math.sin(self.frame * 0.6)
        elif self.state == "sleep": b = 1.0 + 0.015 * math.sin(self.frame * 0.12)
        elif self.state == "stretch": b = 1.0 + 0.06 * math.sin(self.frame * 0.5)
        elif self.state == "sit": b = 0.98
        elif self.state == "eat": b = 1.0 + 0.03 * math.sin(self.frame * 0.4)
        elif self.state == "happy": b = 1.0 + 0.04 * math.sin(self.frame * 0.5)
        else: b = 1.0 + 0.02 * math.sin(self.frame * 0.15)

        if self.happiness > 70: b += 0.01 * math.sin(self.frame * 0.3)
        elif self.happiness < 20: b -= 0.01

        yolk_c = C["yolk"] if self.happiness < 80 else "#FFE57F"
        shell_c = C["shell"] if self.happiness >= 20 else "#6D4C41"

        # Shadow
        self.canvas.create_oval(cx-35, cy+48*b+4-6, cx+35, cy+48*b+4+6, fill=C["shadow"], outline="")

        # Shell
        st = cy - 4 * b
        self.canvas.create_oval(cx-32*b, st-28*b, cx+32*b, st+28*b, fill=shell_c, outline=C["shell_d"], width=2)
        self.canvas.create_oval(cx-27*b, st-23*b, cx+27*b, st+23*b, fill=C["shell_l"], outline="")
        for i in range(3):
            a = i * 0.8 - 0.8
            self.canvas.create_line(cx+20*math.cos(a)*b, st+8+15*math.sin(a)*b,
                                    cx+28*math.cos(a+0.3)*b, st-2+12*math.sin(a+0.3)*b, fill=C["shell_d"], width=1.5)

        # Yolk
        yc = st - 12 * b
        self.canvas.create_oval(cx-22*b, yc-22*b, cx+22*b, yc+27*b, fill=yolk_c, outline="#F9A825", width=2)
        self.canvas.create_oval(cx-18*b, yc-18*b, cx+18*b, yc+22*b, fill=C["yolk_l"], outline="")
        self.canvas.create_oval(cx-10, yc-22*b+2, cx, yc-22*b+10, fill="white", outline="", stipple="gray25")

        # Eyes
        ey = yc + 2; esp = 12
        blink = self.state in ("blink", "sleep")
        for s in [-1, 1]:
            ex = cx + s * esp
            if self.state == "eat":
                self.canvas.create_arc(ex-7, ey-5, ex+7, ey+5, start=0, extent=180, fill=C["eye_w"], outline=C["shell_d"], width=1)
            elif self.mood == "surprised":
                self.canvas.create_oval(ex-7, ey-7, ex+7, ey+7, fill=C["eye_w"], outline=C["shell_d"], width=1)
                if not blink: self.canvas.create_oval(ex-4, ey-4, ex+4, ey+4, fill=C["eye_p"])
            elif self.mood == "derp":
                self.canvas.create_oval(ex-6, ey-6, ex+6, ey+6, fill=C["eye_w"], outline=C["shell_d"], width=1)
                if not blink: self.canvas.create_oval(cx+(2 if s==-1 else -2)-2, ey-2, cx+(2 if s==-1 else -2)+2, ey+2, fill=C["eye_p"])
            elif self.mood == "love":
                self.canvas.create_text(ex, ey, text="\u2764\ufe0f", font=("Segoe UI Emoji", 11))
            elif blink:
                self.canvas.create_line(ex-7, ey, ex+7, ey, fill=C["shell_d"], width=2.5)
            else:
                self.canvas.create_oval(ex-6, ey-6, ex+6, ey+6, fill=C["eye_w"], outline=C["shell_d"], width=1)
                self.canvas.create_oval(ex-3, ey-3, ex+3, ey+3, fill=C["eye_p"])

        # Mouth
        my = ey + 14
        if self.state == "sleep":
            self.canvas.create_arc(cx-6, my-2, cx+6, my+4, start=0, extent=180, fill="", outline=C["mouth"], width=1.5)
            self.canvas.create_text(cx+20, ey-14, text="\U0001f4a4", font=("Segoe UI Emoji", 10))
        elif self.state == "eat":
            self.canvas.create_oval(cx-5, my-2, cx+5, my+6, fill=C["mouth"], outline=C["shell_d"], width=1)
        elif self.mood == "surprised":
            self.canvas.create_oval(cx-4, my-3, cx+4, my+3, fill=C["mouth"], outline=C["shell_d"], width=1)
        elif self.mood == "derp":
            self.canvas.create_arc(cx-5, my-1, cx+5, my+4, start=0, extent=180, fill="", outline=C["mouth"], width=1.5)
            self.canvas.create_oval(cx-3, my+2, cx+3, my+8, fill="#FF8A80", outline=C["mouth"], width=1)
        else:
            ext = 200 if self.state in ("happy", "chase") else (200 if self.happiness > 70 else 150 if self.happiness < 20 else 180)
            self.canvas.create_arc(cx-6, my-2, cx+6, my+4, start=0, extent=ext, fill="", outline=C["mouth"], width=1.5)

        # Blush
        if self.mood in ("happy", "surprised", "derp", "love") or self.state == "eat":
            for s in [-1, 1]:
                bx, by = cx + s * 22, ey + 6
                self.canvas.create_oval(bx-5, by-3, bx+5, by+3, fill=C["blush"], outline="", stipple="gray25")

        # Bubble
        if self.bubble: self._bubble(cx, cy, b)

    def _bubble(self, cx, cy, b):
        txt, n = self.bubble, 14
        lines, cur = [], ""
        for ch in txt:
            if len(cur) >= n: lines.append(cur); cur = ch
            else: cur += ch
        if cur: lines.append(cur)
        if not lines: lines = [""]
        ml = max(len(l) for l in lines)
        bw, bh = ml * 8 + 20, len(lines) * 18 + 16
        bx, by = cx - bw // 2, cy - 62 * b - bh
        self.canvas.create_oval(bx-4, by-4, bx+bw+4, by+bh+4, fill="#FFFDE7", outline="#FFB74D", width=2)
        self.canvas.create_polygon(cx-8, by+bh, cx, by+bh+12, cx+8, by+bh, fill="#FFFDE7", outline="#FFB74D", width=2)
        for i, line in enumerate(lines):
            self.canvas.create_text(cx, by+14+i*18, text=line, fill="#3E2723", font=("Microsoft YaHei", 9))

    # ── Interactions ──

    def on_click(self, ev):
        self.drag["x"], self.drag["y"] = ev.x, ev.y
        self.drag["active"] = False
        self.state = "happy"; self.st = 0; self.mood = random.choice(["happy", "surprised", "love", "derp"])
        self.happiness = min(100, self.happiness + 5)
        self._particles(3, "heart")
        reacts = ["哎哟！", "别戳我 \U0001f965", "干嘛~", "嘿嘿嘿", "痒啦！",
                   "再戳要生气了！", "mua~ \u2764\ufe0f", "咕噜咕噜~", "主人好！", "嘻嘻 \U0001f60a"]
        if self.happiness > 80: reacts += ["好开心！\U0001f970", "最喜欢你了 \u2764\ufe0f", "嘿嘿嘿超开心！"]
        elif self.happiness < 20: reacts += ["别碰我 \U0001f622", "走开啦...", "心情不好..."]
        self.say(random.choice(reacts))

    def on_drag(self, ev):
        if abs(ev.x - self.drag["x"]) > 3 or abs(ev.y - self.drag["y"]) > 3:
            self.drag["active"] = True
        if self.drag["active"]:
            x = self.win.winfo_x() + ev.x - self.drag["x"]
            y = self.win.winfo_y() + ev.y - self.drag["y"]
            self.win.geometry(f"+{int(x)}+{int(y)}")

    def on_release(self, ev):
        if not self.drag["active"]: return
        self.drag["active"] = False
        self.cfg["x"], self.cfg["y"] = self.win.winfo_x(), self.win.winfo_y()
        save_config(self.cfg)
        self.state = "idle"; self.mood = "happy"
        self.say("放这里啦 \U0001f965")

    def show_menu(self, ev): self.menu.tk_popup(ev.x_root, ev.y_root)

    def toggle_top(self):
        self.win.attributes("-topmost", not self.win.attributes("-topmost"))
        self.say("\U0001f4cc \u2705" if self.win.attributes("-topmost") else "\U0001f4cc \u274c")

    def adjust_opacity(self):
        top = tk.Toplevel(self.win)
        top.title("\u900f\u660e\u5ea6")
        top.geometry(f"250x100+{self.win.winfo_x()+20}+{self.win.winfo_y()+20}")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        tk.Label(top, text="\U0001f39a \u900f\u660e\u5ea6", font=("Microsoft YaHei", 10)).pack(pady=3)
        v = tk.DoubleVar(value=self.cfg["opacity"])
        tk.Scale(top, from_=0.3, to=1.0, resolution=0.05, orient=tk.HORIZONTAL,
                 variable=v, command=lambda x: self.win.wm_attributes("-alpha", float(x)), length=200).pack()
        tk.Button(top, text="\u786e\u5b9a", command=lambda: [self.cfg.update(opacity=float(v.get())), save_config(self.cfg), top.destroy()],
                  bg="#FFCC80", fg="#3E2723").pack(pady=3)

    def adjust_walk(self):
        top = tk.Toplevel(self.win)
        top.title("\u8d70\u52a8\u9891\u7387")
        top.geometry(f"250x140+{self.win.winfo_x()+30}+{self.win.winfo_y()+30}")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        tk.Label(top, text="\U0001f6b6 \u8d70\u52a8\u9891\u7387", font=("Microsoft YaHei", 10)).pack(pady=3)
        v = tk.IntVar(value=self.cfg.get("walk_freq", 50))
        l = tk.Label(top, text="", font=("Microsoft YaHei", 9), fg="#795548")
        l.pack()
        def slide(x):
            val = int(float(x))
            labels = {0: "\U0001faa8 \u9759\u6b62\u4e0d\u52a8", 25: "\U0001f422 \u5076\u5c14\u8d70\u8d70",
                      50: "\U0001f6b6 \u6b63\u5e38", 75: "\U0001f3c3 \u6d3b\u6cfc", 100: "\U0001f4a8 \u6839\u672c\u505c\u4e0d\u4e0b\u6765"}
            l.config(text=next(v for k, v in sorted(labels.items(), reverse=True) if val >= k))
        tk.Scale(top, from_=0, to=100, resolution=10, orient=tk.HORIZONTAL, variable=v, command=slide, length=200).pack(pady=5)
        slide(self.cfg.get("walk_freq", 50))
        tk.Button(top, text="\u786e\u5b9a", command=lambda: [self.cfg.update(walk_freq=int(v.get())), save_config(self.cfg), top.destroy()],
                  bg="#FFCC80", fg="#3E2723").pack(pady=5)

    def cycle_mood(self):
        moods = ["happy", "sleepy", "surprised", "love", "derp"]
        idx = moods.index(self.mood) if self.mood in moods else 0
        self.mood = moods[(idx + 1) % len(moods)]
        names = {"happy": "\u5f00\u5fc3", "sleepy": "\u56f0\u56f0", "surprised": "\u60ca\u8bb6",
                 "love": "\u7231\u5fc3", "derp": "\u641e\u602a"}
        self.say(f"\U0001f965 {names.get(self.mood, '?')}\u6a21\u5f0f\uff01")
        self._particles(3, "heart")

    def show_status(self):
        if self.happiness >= 80: d = "\U0001f970 \u8d85\u5f00\u5fc3\uff01"
        elif self.happiness >= 60: d = "\U0001f60a \u633a\u5f00\u5fc3\u7684"
        elif self.happiness >= 40: d = "\U0001f610 \u8fd8\u884c"
        elif self.happiness >= 20: d = "\U0001f622 \u6709\u70b9\u4f4e\u843d"
        else: d = "\U0001f62d \u597d\u96be\u8fc7..."
        bar = "\u2588" * int(self.happiness // 5) + "\u2591" * (20 - int(self.happiness // 5))
        messagebox.showinfo("\U0001f965 \u6930\u5b50\u86cb\u72b6\u6001", f"\u60c5\u7eea: {d}\n[{bar}] {int(self.happiness)}/100")

    def say_something(self):
        texts = ["\U0001f965\u6930\u5b50\u86cb\u6765\u5566", "\u65e0\u804a~", "\u4eca\u5929\u5403\u4ec0\u4e48\uff1f",
                 "\u6478\u9c7c\u4e2d \U0001f41f", "\u4e3b\u4eba\u597d\uff01", "\u597d\u60f3\u51fa\u53bb\u73a9 \U0001f334",
                 "\u5495\u565c\u5495\u565c~", "\U0001f965 \u6930\uff01", "\u4ee3\u7801\u5199\u5b8c\u4e86\u5417\uff1f",
                 "\u56f0\u4e86 Zzz...", "\u563b\u563b\u563b~", "\U0001f965\u6930\u6930\u6930\uff01"]
        if self.happiness > 70: texts += ["\u597d\u5f00\u5fc3\u5440\uff01\U0001f970", "\u4eca\u5929\u8d85\u68d2\uff01\U0001f389"]
        elif self.happiness < 20: texts += ["\u597d\u65e0\u804a...", "\u6ca1\u4eba\u966a\u6211 \U0001f622"]
        self.say(random.choice(texts))
        self._particles(2, "note")

    def say(self, t):
        self.bubble = t
        if self.bubble_id: self.win.after_cancel(self.bubble_id)
        self.bubble_id = self.win.after(2500, lambda: setattr(self, "bubble", ""))

    def on_exit(self):
        if messagebox.askokcancel("\U0001f965 \u6930\u5b50\u86cb", f"\u771f\u7684\u8981\u8d70\u5417\uff1f\uff08\u5fc3\u60c5\u503c {int(self.happiness)}\uff09\U0001f622"):
            if self.after_id: self.win.after_cancel(self.after_id)
            save_config(self.cfg)
            self.win.destroy()
            sys.exit(0)

    def run(self):
        self._tick()
        self.win.mainloop()


if __name__ == "__main__":
    CoconutPet().run()
