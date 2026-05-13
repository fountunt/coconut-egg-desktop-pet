# -*- coding: utf-8 -*-
"""
🥥 椰子蛋桌面宠物 v3.0 — 功能完整版
会追鼠标、吃东西、冒爱心、有心情的桌面小可爱！
"""

import tkinter as tk
from tkinter import messagebox
import random
import math
import json
import os
import sys
import time
from datetime import datetime

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pet_config.json")
DEFAULT_CONFIG = {
    "x": 400, "y": 400,
    "opacity": 0.95,
    "walk_freq": 50,
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


class Particle:
    """粒子特效：爱心 / 星星 / 音符"""
    def __init__(self, canvas, x, y, kind="heart"):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.kind = kind
        self.life = 1.0
        self.speed = random.uniform(1.0, 2.5)
        self.dx = random.uniform(-1.5, 1.5)
        self.age = 0
        self.max_age = random.randint(30, 50)
        self.id = None

        emojis = {"heart": ["❤️", "💕", "💗"],
                  "star": ["✨", "⭐", "🌟"],
                  "note": ["♪", "♫", "🎵"]}
        syms = emojis.get(kind, ["✨"])
        self.char = random.choice(syms)
        self.size = random.choice([9, 11, 13, 15])

    def update(self):
        self.age += 1
        self.life = 1.0 - (self.age / self.max_age)
        if self.life <= 0:
            return False

        self.y -= self.speed
        self.x += self.dx * 0.5
        self.dx *= 0.98

        alpha = max(0, int(self.life * 255))
        color = f"#{alpha:02x}{alpha:02x}{alpha:02x}"
        self.canvas.delete(self.id)
        self.id = self.canvas.create_text(
            self.x, self.y, text=self.char,
            font=("Segoe UI Emoji", self.size),
            fill=color, tags="particle")
        return True


class Food:
    """食物实体：出现在屏幕上，宠物会走过去吃"""
    def __init__(self, canvas, x, y, kind=None):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.kind = kind or random.choice(["cake", "cookie", "milk", "fruit"])
        self.eaten = False
        self.id = None
        self.draw()

    def draw(self):
        icons = {"cake": "🧁", "cookie": "🍪", "milk": "🥛", "fruit": "🍎", "candy": "🍬"}
        icon = icons.get(self.kind, "🍪")
        self.id = self.canvas.create_text(
            self.x, self.y, text=icon,
            font=("Segoe UI Emoji", 20), tags="food")

    def remove(self):
        self.canvas.delete(self.id)
        self.eaten = True


class CoconutPet:
    """🥥 椰子蛋 v3 — 满屏溜达、追鼠标、吃东西的桌面宠物"""

    SIZE = 130
    W = 160
    H = 180
    WALK_SPEED = 2.5
    SCREEN_MARGIN = 50

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
        self.state = "idle"
        self.state_timer = 0
        self.state_max = 60
        self.blink_timer = 0
        self.mood = "happy"

        self.draw_x = self.W // 2
        self.draw_y = self.H // 2 + 5

        # ── 行走 ──
        self.walk_target_x = sx
        self.walk_target_y = sy
        self.walk_pause = 0

        # ── 交互 ──
        self.drag_data = {"x": 0, "y": 0, "dragging": False}
        self.is_topmost = True
        self.bubble_text = ""
        self.clear_bubble_id = None
        self.happiness = 50          # 0~100 心情值

        # ── 粒子系统 ──
        self.particles = []

        # ── 食物系统 ──
        self.food = None

        # ── 鼠标跟随 ──
        self.chase_mouse = False
        self.mouse_timer = 0
        self.mouse_target_x = 0
        self.mouse_target_y = 0

        # ── 绑定事件 ──
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.show_menu)
        self.canvas.bind("<Enter>", self.on_mouse_enter)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.win.protocol("WM_DELETE_WINDOW", self.on_exit)

        # ── 菜单 ──
        self.menu = tk.Menu(self.win, tearoff=0, bg="#FFF3E0", fg="#3E2723",
                           activebackground="#FFCC80", activeforeground="#3E2723")
        self.menu.add_command(label="😊 换心情", command=self.cycle_mood)
        self.menu.add_command(label="💬 说句话", command=self.say_something)
        self.menu.add_command(label="🍪 喂食", command=self.spawn_food)
        self.menu.add_command(label="🐾 追鼠标", command=self.toggle_chase_mouse)
        self.menu.add_separator()
        self.menu.add_command(label="📌 置顶", command=self.toggle_topmost)
        self.menu.add_command(label="🎚 透明度", command=self.adjust_opacity)
        self.menu.add_command(label="🚶 走动频率", command=self.adjust_walk_freq)
        self.menu.add_separator()
        self.menu.add_command(label="😊 心情状态", command=self.show_status)
        self.menu.add_separator()
        self.menu.add_command(label="❌ 退出", command=self.on_exit)

        # ── 问候 ──
        self.after_id = None
        self._greet_on_start()
        self._schedule_next()

    def _greet_on_start(self):
        hour = datetime.now().hour
        if hour < 6:
            self.say("半夜了还没睡呀 🌙")
        elif hour < 9:
            self.say("早安主人！🥥☀️")
        elif hour < 12:
            self.say("上午好~ 摸鱼吗？🐟")
        elif hour < 14:
            self.say("中午啦，吃了吗？🍚")
        elif hour < 18:
            self.say("下午好~ 有点困 🥱")
        elif hour < 22:
            self.say("晚上好！🥥🌆")
        else:
            self.say("夜深了，早点休息哦 😴")

    # ════════════════════════════════════════════════
    #  主循环
    # ════════════════════════════════════════════════

    def tick(self):
        self.frame += 1
        self.state_timer += 1
        self.blink_timer += 1

        # 心情自然衰减
        if self.frame % 60 == 0 and self.happiness > 0:
            self.happiness = max(0, self.happiness - 0.3)

        # ── 眨眼 ──
        if self.blink_timer > random.randint(80, 200) and self.state not in ("sleep", "blink"):
            self.state = "blink"
            self.state_timer = 0
            self.blink_timer = 0

        if self.state == "blink" and self.state_timer >= 4:
            self.state = "idle"

        # ── 空闲随机行为 ──
        if self.state in ("idle",) and self.state_timer > 20:
            r = random.random()
            walk_chance = 0.008 * (self.config.get("walk_freq", 50) / 50.0)

            # 心情好时更活跃
            if self.happiness > 70:
                walk_chance *= 1.5
            elif self.happiness < 20:
                walk_chance *= 0.5

            if self.chase_mouse and r < 0.01:
                self.start_chase_mouse()
            elif r < walk_chance:
                self.start_walk()
            elif r < 0.012:
                self.state = "stretch"
                self.state_timer = 0
                self.state_max = 30
            elif r < 0.015:
                self.state = "sit"
                self.mood = "sleepy" if self.happiness < 30 else random.choice(["happy", "sleepy", "derp"])
                self.state_timer = 0
                self.state_max = 40

            # 心情值过低时自动说消极话
            if self.happiness < 15 and self.state_timer > 50 and random.random() < 0.003:
                sad_msgs = ["好无聊...", "没人理我 😢", "饿饿了...", "好孤单..."]
                self.say(random.choice(sad_msgs))
                self.spawn_particles("sad", count=2)

        # ── 睡觉 ──
        if self.state == "sleep":
            if self.state_timer > random.randint(150, 300):
                self.state = "stretch"
                self.state_timer = 0
                self.state_max = 20
            elif self.blink_timer % 30 == 0 and random.random() < 0.05:
                self.spawn_particles("sleep", count=1)

        # ── 状态到期 ──
        if self.state in ("stretch", "sit", "wave") and self.state_timer >= self.state_max:
            self.state = "idle"
            self.mood = "happy" if self.happiness > 30 else "sleepy"

        # ── 进食 ──
        if self.state == "eating":
            self.do_eat()

        # ── 行走 ──
        if self.state == "walk":
            self.do_walk()

        # ── 追鼠标 ──
        if self.state == "chase":
            self.do_chase_mouse()

        # ── 粒子系统 ──
        self.particles = [p for p in self.particles if p.update()]

        # ── 绘制 ──
        self.draw()
        self._schedule_next()

    def _schedule_next(self):
        if self.after_id:
            self.win.after_cancel(self.after_id)
        self.after_id = self.win.after(30, self.tick)

    # ════════════════════════════════════════════════
    #  粒子系统
    # ════════════════════════════════════════════════

    def spawn_particles(self, kind="heart", count=5):
        cx, cy = self.W // 2, self.H // 2
        for _ in range(count):
            ox = cx + random.randint(-20, 20)
            oy = cy + random.randint(-30, 10)
            self.particles.append(Particle(self.canvas, ox, oy, kind))

    # ════════════════════════════════════════════════
    #  鼠标跟随
    # ════════════════════════════════════════════════

    def toggle_chase_mouse(self):
        self.chase_mouse = not self.chase_mouse
        self.say("追鼠标 " + ("🟢" if self.chase_mouse else "🔴"))
        if self.chase_mouse:
            self.spawn_particles("heart", 3)

    def on_mouse_enter(self, event):
        if self.chase_mouse and self.state not in ("walk", "chase", "eating"):
            self.mouse_target_x = self.win.winfo_x() + event.x
            self.mouse_target_y = self.win.winfo_y() + event.y

    def on_mouse_move(self, event):
        if self.chase_mouse and self.state not in ("chase", "eating"):
            self.mouse_target_x = self.win.winfo_x() + event.x
            self.mouse_target_y = self.win.winfo_y() + event.y

    def start_chase_mouse(self):
        if self.state in ("walk", "chase", "eating"):
            return
        self.state = "chase"
        self.mood = "happy"
        self.state_timer = 0

    def do_chase_mouse(self):
        """追鼠标：持续朝着鼠标位置移动"""
        cx = self.win.winfo_x()
        cy = self.win.winfo_y()
        mx = self.mouse_target_x
        my = self.mouse_target_y

        dx = mx - cx
        dy = my - cy
        dist = math.hypot(dx, dy)

        # 如果离鼠标很近，停下来开心
        if dist < 15:
            self.state = "happy"
            self.state_timer = 0
            self.state_max = 10
            self.mood = "love"
            self.happiness = min(100, self.happiness + 3)
            self.spawn_particles("heart", 5)
            if random.random() < 0.3:
                self.say(random.choice(["抓到啦！", "嘿嘿 🥥", "找到你啦 ❤️"]))
            self.chase_mouse_timer = 0
            return

        speed = self.WALK_SPEED * 1.2
        if dist > speed:
            nx = cx + (dx / dist) * speed
            ny = cy + (dy / dist) * speed
            self.win.geometry(f"+{int(nx)}+{int(ny)}")
        else:
            self.win.geometry(f"+{mx}+{my}")

        self.mood = "happy"

        # 超时停止追
        self.state_timer += 1
        if self.state_timer > 300:  # ~9秒
            self.state = "idle"
            self.say("追不到啦 😮‍💨")

    # ════════════════════════════════════════════════
    #  食物 / 喂食
    # ════════════════════════════════════════════════

    def spawn_food(self):
        """在宠物旁边生成食物"""
        if self.food and not self.food.eaten:
            self.say("还没吃完呢 🍪")
            return

        cx = self.win.winfo_x() + self.W // 2
        cy = self.win.winfo_y() + self.H // 2
        fx = self.W // 2 + random.randint(10, 40) * random.choice([-1, 1])
        fy = self.H // 2 + random.randint(20, 50)

        foods = ["cake", "cookie", "milk", "fruit", "candy"]
        kinds = {"cake": "🧁", "cookie": "🍪", "milk": "🥛", "fruit": "🍎", "candy": "🍬"}
        self.food = Food(self.canvas, fx, fy, random.choice(foods))
        self.state = "walk_to_food"
        self.walk_target_x = fx - 20
        self.walk_target_y = fy + 10
        self.state = "walk"
        self.walk_pause = 5
        self._food_target = (fx, fy)

    def do_eat(self):
        """吃东西动画"""
        self.state_timer += 1
        if self.state_timer == 1:
            self.mood = "love"
            self.spawn_particles("heart", 8)
            self.say(random.choice(["好吃！🥰", "yummy~ 🍪", "好香！", "再来一个！"]))
            self.happiness = min(100, self.happiness + 15)

        if self.state_timer > 30:
            if self.food and not self.food.eaten:
                self.food.remove()
                self.food = None
            self.state = "happy"
            self.state_timer = 0
            self.state_max = 15
            self.mood = "love"

    # ════════════════════════════════════════════════
    #  屏幕行走
    # ════════════════════════════════════════════════

    def start_walk(self):
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
            if random.random() < 0.01:
                self.spawn_particles("note", 1)
        else:
            self.win.geometry(f"+{self.walk_target_x}+{self.walk_target_y}")

            # 检查是否走到了食物
            if hasattr(self, '_food_target') and self.food and not self.food.eaten:
                fx, fy = self._food_target
                fdx = self.walk_target_x - (self.win.winfo_x() + fx - 20)
                fdy = self.walk_target_y - (self.win.winfo_y() + fy + 10)
                if math.hypot(fdx, fdy) < 40:
                    self.state = "eating"
                    self.state_timer = 0
                    return

            if self.walk_pause > 0:
                self.walk_pause -= 1
                if self.walk_pause == 90:
                    arrival = ["到啦！", "这里不错~", "歇会儿 🥥",
                               "呼呼~", "风景挺好 🌴", "就这儿了！"]
                    self.mood = random.choice(["happy", "happy", "sleepy", "derp"])
                    if random.random() < 0.3:
                        self.say(random.choice(arrival))
                return

            self.state = "idle"
            self.mood = "happy"
            self.state_timer = 0
            self.config["x"] = self.walk_target_x
            self.config["y"] = self.walk_target_y
            save_config(self.config)
            # 走路后随机开心粒子
            if random.random() < 0.2:
                self.spawn_particles("heart", 2)

    # ════════════════════════════════════════════════
    #  绘制
    # ════════════════════════════════════════════════

    def draw(self):
        self.canvas.delete("all")
        cx, cy = self.W // 2, self.H // 2 + 5
        C = self.COLORS

        bounce = 1.0
        if self.state == "walk" or self.state == "chase":
            bounce = 1.0 + 0.04 * math.sin(self.frame * 0.6)
        elif self.state == "sleep":
            bounce = 1.0 + 0.015 * math.sin(self.frame * 0.12)
        elif self.state == "stretch":
            bounce = 1.0 + 0.06 * math.sin(self.frame * 0.5)
        elif self.state == "sit":
            bounce = 0.98
        elif self.state == "eating":
            bounce = 1.0 + 0.03 * math.sin(self.frame * 0.4)
        elif self.state == "happy":
            bounce = 1.0 + 0.04 * math.sin(self.frame * 0.5)
        else:
            bounce = 1.0 + 0.02 * math.sin(self.frame * 0.15)

        # 心情好时更弹
        if self.happiness > 70:
            bounce += 0.01 * math.sin(self.frame * 0.3)
        elif self.happiness < 20:
            bounce -= 0.01

        # ── 心情变色 ──
        shell_c = C["shell"]
        yolk_c = C["yolk"]
        if self.happiness > 80:
            yolk_c = "#FFE57F"  # 心情好蛋黄更亮
        elif self.happiness < 20:
            shell_c = "#6D4C41"  # 心情差壳变暗
            yolk_c = "#FFC107"

        # ── 阴影 ──
        sh_y = cy + 48 * bounce + 4
        self.canvas.create_oval(cx-35, sh_y-6, cx+35, sh_y+6,
                                fill=C["shadow"], outline="")

        # ── 椰子壳 ──
        sr_x = 32 * bounce
        sr_y = 28 * bounce
        st = cy - 4 * bounce
        self.canvas.create_oval(cx - sr_x, st - sr_y, cx + sr_x, st + sr_y,
                                fill=shell_c, outline=C["shell_dark"], width=2)
        self.canvas.create_oval(cx - sr_x + 5, st - sr_y + 5,
                                cx + sr_x - 5, st + sr_y - 5,
                                fill=C["shell_light"], outline="")
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
                                fill=yolk_c, outline="#F9A825", width=2)
        self.canvas.create_oval(cx - yk_r + 4, yk_cy - yk_r + 4,
                                cx + yk_r - 4, yk_cy + yk_r + 3,
                                fill=C["yolk_light"], outline="")
        self.canvas.create_oval(cx - 10, yk_cy - yk_r + 2,
                                cx, yk_cy - yk_r + 10,
                                fill="white", outline="", stipple="gray25")

        # ── 眼睛 ──
        eye_y = yk_cy + 2
        esp = 12
        blink = self.state in ("blink", "sleep")

        if self.state == "eating":
            # 眯眼享受
            for s in [-1, 1]:
                ex = cx + s * esp
                self.canvas.create_arc(ex-7, eye_y-5, ex+7, eye_y+5,
                                       start=0, extent=180,
                                       fill=C["eye_w"], outline=C["shell_dark"], width=1)

        elif self.mood == "surprised":
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
        elif self.state == "eating":
            # 吃东西嘴张着
            self.canvas.create_oval(cx-5, my-2, cx+5, my+6,
                                    fill=C["mouth"], outline=C["shell_dark"], width=1)
        elif self.mood == "surprised":
            self.canvas.create_oval(cx-4, my-3, cx+4, my+3,
                                    fill=C["mouth"], outline=C["shell_dark"], width=1)
        elif self.mood == "derp":
            self.canvas.create_arc(cx-5, my-1, cx+5, my+4, start=0, extent=180,
                                   fill="", outline=C["mouth"], width=1.5)
            self.canvas.create_oval(cx-3, my+2, cx+3, my+8,
                                    fill="#FF8A80", outline=C["mouth"], width=1)
        else:
            ext = 200 if self.state in ("happy", "wave", "chase") else 180
            if self.happiness > 70:
                ext = 200
            elif self.happiness < 20:
                ext = 150
            self.canvas.create_arc(cx-6, my-2, cx+6, my+4, start=0,
                                   extent=ext, fill="", outline=C["mouth"], width=1.5)

        # ── 腮红 ──
        if self.mood in ("happy", "surprised", "derp", "love") or self.state == "eating":
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

        # 摸头加心情
        self.happiness = min(100, self.happiness + 5)
        self.spawn_particles("heart", 3)

        reacts = [
            "哎哟！", "别戳我 🥥", "干嘛~", "嘿嘿嘿",
            "痒啦！", "再戳要生气了！", "mua~ ❤️",
            "(○｀3′○)", "咕噜咕噜~", "主人好！", "嘻嘻 😊"
        ]
        if self.happiness > 80:
            reacts += ["好开心！🥰", "最喜欢你了 ❤️", "嘿嘿嘿超开心！"]
        elif self.happiness < 20:
            reacts += ["别碰我 😢", "走开啦...", "心情不好..."]

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
            top.destroy()
            self.start_walk()
            self.say("走咯~ 🚶")

        tk.Button(btn_frame, text="立刻走走", command=random_walk,
                  bg="#A5D6A7", fg="#1B5E20", width=8).pack(side=tk.LEFT, padx=5)

    def cycle_mood(self):
        moods = ["happy", "sleepy", "surprised", "love", "derp"]
        idx = moods.index(self.mood) if self.mood in moods else 0
        self.mood = moods[(idx + 1) % len(moods)]
        names = {"happy": "开心", "sleepy": "困困", "surprised": "惊讶",
                 "love": "爱心", "derp": "搞怪"}
        self.say(f"🥥 {names.get(self.mood, '?')}模式！")
        self.spawn_particles("heart", 3)

    def show_status(self):
        """显示心情状态"""
        if self.happiness >= 80:
            desc = "🥰 超开心！"
        elif self.happiness >= 60:
            desc = "😊 挺开心的"
        elif self.happiness >= 40:
            desc = "😐 还行"
        elif self.happiness >= 20:
            desc = "😢 有点低落"
        else:
            desc = "😭 好难过..."

        # 显示心情值条
        bar = "█" * int(self.happiness // 5) + "░" * (20 - int(self.happiness // 5))
        msg = f"心情: {desc}\n[{bar}] {int(self.happiness)}/100"
        messagebox.showinfo("🥥 椰子蛋状态", msg)

    def say_something(self):
        texts = [
            "椰子蛋来啦 🥥", "无聊~", "今天吃什么？",
            "摸鱼中 🐟", "主人好！", "好想出去玩 🌴",
            "咕噜咕噜~", "🥥 椰！", "代码写完了吗？",
            "困了 Zzz...", "嘿嘿嘿~", "今天心情不错 😊",
            "🥥 椰椰椰！", "好闲啊~", "喵？不对我是椰子 🥥"
        ]
        if self.happiness > 70:
            texts += ["好开心呀！🥰", "今天超棒！🎉"]
        elif self.happiness < 20:
            texts += ["好无聊...", "没人陪我 😢"]
        self.say(random.choice(texts))
        self.spawn_particles("note", 2)

    def say(self, text):
        self.bubble_text = text
        if self.clear_bubble_id:
            self.win.after_cancel(self.clear_bubble_id)
        self.clear_bubble_id = self.win.after(2500, lambda: setattr(self, "bubble_text", ""))

    def on_exit(self):
        if messagebox.askokcancel("🥥 椰子蛋", f"真的要走吗？（心情值 {int(self.happiness)}）😢"):
            if self.after_id:
                self.win.after_cancel(self.after_id)
            save_config(self.config)
            self.win.destroy()
            sys.exit(0)

    def run(self):
        self.tick()
        self.win.mainloop()


if __name__ == "__main__":
    pet = CoconutPet()
    pet.run()
