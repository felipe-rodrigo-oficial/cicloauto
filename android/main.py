# -*- coding: utf-8 -*-
"""CicloAuto: painel para bicicleta com o celular preso no guidão (Kivy).

Mapa + velocímetro, no estilo Android Auto. As setas e o freio são espelhados
na fita NeoPixel do micro:bit (ver microbit_link.py e ../microbit/).
"""
import time
from math import sin, cos, radians, hypot

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.utils import platform
from kivy.graphics import (Color, Line, Rectangle, RoundedRectangle, Ellipse, Triangle,
                           StencilPush, StencilUse, StencilUnUse, StencilPop)
from kivy.graphics.texture import Texture
from kivy.properties import (NumericProperty, StringProperty, BooleanProperty,
                             ListProperty, ObjectProperty, ColorProperty)
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior

from microbit_link import MicrobitLink

ANDROID = platform == 'android'
if ANDROID:
    from plyer import gps
    from android.permissions import request_permissions, Permission
    from android.runnable import run_on_ui_thread
    from jnius import autoclass

    @run_on_ui_thread
    def manter_tela_ligada():
        LayoutParams = autoclass('android.view.WindowManager$LayoutParams')
        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        activity.getWindow().addFlags(LayoutParams.FLAG_KEEP_SCREEN_ON)

MAX_SPEED = 50       # km/h no fim do arco
FREIO_LIGA = -3.5    # km/h por segundo: desaceleração que acende o freio
FREIO_DESLIGA = -1.5

GREEN = (0.24, 0.86, 0.52)
CYAN = (0.31, 0.82, 1.0)
BLUE = (0.18, 0.48, 1.0)
RED = (1.0, 0.26, 0.32)
AMBER = (1.0, 0.66, 0.1)


# ---------------------------------------------------------------- utilidades
def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


def lerp(c1, c2, t):
    t = clamp(t)
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


def br(v, d=1):
    """Número no formato brasileiro (vírgula)."""
    return f'{v:.{d}f}'.replace('.', ',')


def make_tex(w, h, fn):
    """Textura RGBA calculada pixel a pixel com fn(u, v) -> (r, g, b, a)."""
    buf = bytearray(w * h * 4)
    i = 0
    for y in range(h):
        v = y / (h - 1)
        for x in range(w):
            for c in fn(x / (w - 1), v):
                buf[i] = int(clamp(c) * 255)
                i += 1
    data = bytes(buf)
    tex = Texture.create(size=(w, h), colorfmt='rgba')
    tex.blit_buffer(data, colorfmt='rgba', bufferfmt='ubyte')
    # recarrega se o Android descartar o contexto OpenGL
    tex.add_reload_observer(lambda t: t.blit_buffer(data, colorfmt='rgba', bufferfmt='ubyte'))
    return tex


def bg_texture(bright):
    top, mid, low = (0.07, 0.22, 0.56), (0.03, 0.08, 0.27), (0.02, 0.035, 0.11)

    def fn(u, v):
        d = clamp(hypot((u - 0.82) * 1.1, (v - 1.05) * 1.6) / 1.35)
        c = lerp(top, mid, d / 0.45) if d < 0.45 else lerp(mid, low, (d - 0.45) / 0.55)
        return (c[0] * bright, c[1] * bright, c[2] * bright, 1)
    return make_tex(96, 48, fn)


def glow_texture():
    return make_tex(64, 64, lambda u, v: (1, 1, 1, (1 - clamp(hypot(u - 0.5, v - 0.5) * 2)) ** 2))


def gauge_color(t):
    return lerp(GREEN, CYAN, t / 0.6) if t < 0.6 else lerp(CYAN, RED, (t - 0.6) / 0.4)


# ---------------------------------------------------------------- widgets
class Card(BoxLayout):
    pass


class FloatCard(FloatLayout):
    pass


class RailBtn(ButtonBehavior, BoxLayout):
    """Botão quadrado da barra lateral (estilo Android Auto)."""
    text = StringProperty('')
    active = BooleanProperty(False)
    dot_on = ColorProperty([0.31, 0.82, 1, 1])


class Stat(BoxLayout):
    value = StringProperty('')
    label = StringProperty('')


class Gauge(Widget):
    """Velocímetro em arco com degradê verde, ciano e vermelho."""
    value = NumericProperty(0)
    dial_center = ListProperty([0, 0])
    dial_r = NumericProperty(10)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.redraw, size=self.redraw, value=self.redraw)

    def redraw(self, *_):
        r = max(10, min(self.width * 0.44, self.height / 1.62))
        cx = self.center_x
        cy = self.y + (self.height - 1.5 * r) / 2 + 0.5 * r
        self.dial_center = [cx, cy]
        self.dial_r = r
        w = r * 0.08
        v = clamp(self.value)
        glow = App.get_running_app().glow_tex
        self.canvas.clear()
        with self.canvas:
            Color(*BLUE, 0.35)
            Rectangle(texture=glow, pos=(cx - r * 1.15, cy - r * 0.95), size=(r * 2.3, r * 2.3))
            Color(1, 1, 1, 0.16)
            for i in range(11):
                a = radians(-120 + 24 * i)
                r1, r2 = r * 0.82, r * (0.70 if i % 5 == 0 else 0.76)
                Line(points=[cx + sin(a) * r1, cy + cos(a) * r1,
                             cx + sin(a) * r2, cy + cos(a) * r2], width=1.4)
            Color(1, 1, 1, 0.08)
            Line(circle=(cx, cy, r, -120, 120), width=w, cap='round')
            if v > 0.004:
                end = -120 + 240 * v
                Color(*CYAN, 0.12)
                Line(circle=(cx, cy, r, -120, end), width=w * 2.3, cap='round')
                a0 = radians(-120)
                Color(*GREEN, 1)
                Ellipse(pos=(cx + sin(a0) * r - w, cy + cos(a0) * r - w), size=(w * 2, w * 2))
                n, prev = 48, -120.0
                for i in range(1, n + 1):
                    if prev >= end:
                        break
                    seg = min(-120 + 240 * i / n, end)
                    Color(*gauge_color(i / n), 1)
                    Line(circle=(cx, cy, r, prev, seg + 0.8), width=w, cap='none')
                    prev = seg
                ta = radians(end)
                tx, ty = cx + sin(ta) * r, cy + cos(ta) * r
                Color(*gauge_color(v), 0.5)
                Rectangle(texture=glow, pos=(tx - w * 4, ty - w * 4), size=(w * 8, w * 8))
                Color(1, 1, 1, 1)
                Ellipse(pos=(tx - w * 1.15, ty - w * 1.15), size=(w * 2.3, w * 2.3))


class SignalBtn(ButtonBehavior, Widget):
    """Seta de conversão: pisca em âmbar quando ativa."""
    side = StringProperty('left')
    active = BooleanProperty(False)
    lit = BooleanProperty(False)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.redraw, size=self.redraw, active=self.redraw, lit=self.redraw)

    def redraw(self, *_):
        x, y, w, h = self.x, self.y, self.width, self.height
        rad = min(w, h) * 0.28
        on = self.active and self.lit
        glow = App.get_running_app().glow_tex
        self.canvas.clear()
        with self.canvas:
            if on:
                Color(*AMBER, 0.45)
                Rectangle(texture=glow, pos=(x - w * 0.35, y - h * 0.6), size=(w * 1.7, h * 2.2))
                Color(*AMBER, 1)
            elif self.active:
                Color(*AMBER, 0.2)
            else:
                Color(0.09, 0.17, 0.48, 0.45)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[rad])
            Color(*(AMBER if self.active else (0.47, 0.63, 1)), 0.9 if self.active else 0.25)
            Line(rounded_rectangle=(x, y, w, h, rad), width=1.2)

            # seta: cabeça triangular + corpo
            s = min(w, h) * 0.3
            cx, cy = self.center
            d = -1 if self.side == 'left' else 1
            tip = cx + d * s * 1.3
            base = cx + d * s * 0.1
            tail = cx - d * s * 1.3
            if on:
                Color(0.12, 0.07, 0, 1)
            elif self.active:
                Color(*AMBER, 1)
            else:
                Color(0.55, 0.62, 0.82, 0.8)
            Triangle(points=[tip, cy, base, cy + s, base, cy - s])
            Rectangle(pos=(min(base, tail), cy - s * 0.38), size=(abs(base - tail), s * 0.76))


def _bezier(p0, p1, p2, p3, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        m = 1 - t
        pts.append((m ** 3 * p0[0] + 3 * m * m * t * p1[0] + 3 * m * t * t * p2[0] + t ** 3 * p3[0],
                    m ** 3 * p0[1] + 3 * m * m * t * p1[1] + 3 * m * t * t * p2[1] + t ** 3 * p3[1]))
    return pts


# Coordenadas do mapa num espaço 300x420 (y para baixo, como num SVG)
ROUTE = [(150, 390), (150, 260)] + _bezier((150, 260), (150, 200), (215, 205), (215, 140))[1:] + [(215, 38)]
BLOCKS = [(8, 30, 44, 44), (74, 32, 62, 42), (164, 28, 38, 46), (230, 34, 62, 40),
          (10, 104, 42, 40), (76, 102, 60, 44), (166, 106, 36, 38), (228, 100, 64, 46)]


class MapView(Widget):
    """Mapa estilizado (provisório). Aqui entra o mapa real depois.
    As ruas rolam conforme a velocidade."""
    offset = NumericProperty(0)
    radius = NumericProperty(20)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.redraw, size=self.redraw, offset=self.redraw)

    def redraw(self, *_):
        w, h = self.size
        if w < 2 or h < 2:
            return
        s = max(h / 420, w / 900)
        ox, top = self.center_x - 180 * s, self.center_y + 210 * s

        def P(x, y):
            return ox + x * s, top - y * s

        glow = App.get_running_app().glow_tex
        self.canvas.clear()
        with self.canvas:
            StencilPush()
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            StencilUse()

            Color(0.025, 0.05, 0.17, 1)
            Rectangle(pos=self.pos, size=self.size)
            for k in range(-3, 5):
                b = 140 * k + self.offset
                for j, (bx, by, bw, bh) in enumerate(BLOCKS):
                    Color(*((0.05, 0.10, 0.30) if j % 3 else (0.04, 0.14, 0.24)), 1)
                    x0, y0 = P(bx, b + by + bh)
                    RoundedRectangle(pos=(x0, y0), size=(bw * s, bh * s), radius=[5 * s])
                    x0, y0 = P(bx + 300, b + by + bh)   # repete para os lados (tela larga)
                    RoundedRectangle(pos=(x0, y0), size=(bw * s, bh * s), radius=[5 * s])
                    x0, y0 = P(bx - 300, b + by + bh)
                    RoundedRectangle(pos=(x0, y0), size=(bw * s, bh * s), radius=[5 * s])
                Color(0.08, 0.14, 0.38, 1)
                Line(points=[*P(-320, b + 24), *P(620, b + 16)], width=3.2 * s)
                Color(0.11, 0.19, 0.50, 1)
                Line(points=[*P(-320, b + 96), *P(620, b + 86)], width=6.5 * s)
            for dx in (-300, 0, 300):
                Color(0.08, 0.14, 0.38, 1)
                Line(points=[*P(62 + dx, -200), *P(62 + dx, 600)], width=3.2 * s)
                Color(0.11, 0.19, 0.50, 1)
                Line(points=[*P(150 + dx, -200), *P(150 + dx, 600)], width=6.5 * s)
                Line(points=[*P(215 + dx, -200), *P(215 + dx, 600)], width=6.5 * s)

            # rota
            pts = [c for p in ROUTE for c in P(*p)]
            Color(*CYAN, 0.16)
            Line(points=pts, width=13 * s, joint='round', cap='round')
            n = len(ROUTE) - 1
            for i in range(n):
                Color(*lerp(BLUE, CYAN, i / n), 1)
                Line(points=[*P(*ROUTE[i]), *P(*ROUTE[i + 1])], width=5.5 * s, cap='round')

            # destino
            dx, dy = P(215, 30)
            Color(*GREEN, 0.5)
            Rectangle(texture=glow, pos=(dx - 22 * s, dy - 22 * s), size=(44 * s, 44 * s))
            Color(*GREEN, 1)
            Ellipse(pos=(dx - 8 * s, dy - 8 * s), size=(16 * s, 16 * s))

            # ciclista
            cx, cy = P(150, 368)
            Color(*BLUE, 0.55)
            Rectangle(texture=glow, pos=(cx - 40 * s, cy - 40 * s), size=(80 * s, 80 * s))
            Color(0.93, 0.96, 1, 1)
            Ellipse(pos=(cx - 17 * s, cy - 17 * s), size=(34 * s, 34 * s))
            Color(*BLUE, 1)
            Triangle(points=[cx, cy + 11 * s, cx + 9 * s, cy - 9 * s, cx, cy - 4 * s])
            Triangle(points=[cx, cy + 11 * s, cx, cy - 4 * s, cx - 9 * s, cy - 9 * s])

            StencilUnUse()
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            StencilPop()


ARROWS = {
    'right': ([(0.32, 0.1), (0.32, 0.55), (0.8, 0.55)], [(0.62, 0.74), (0.82, 0.55), (0.62, 0.36)]),
    'left': ([(0.68, 0.1), (0.68, 0.55), (0.2, 0.55)], [(0.38, 0.74), (0.18, 0.55), (0.38, 0.36)]),
    'straight': ([(0.5, 0.1), (0.5, 0.88)], [(0.28, 0.66), (0.5, 0.9), (0.72, 0.66)]),
    'uturn': ([(0.28, 0.1), (0.28, 0.55)] +
              [(0.5 - 0.22 * cos(radians(a)), 0.55 + 0.22 * sin(radians(a))) for a in range(0, 181, 15)] +
              [(0.72, 0.22)], [(0.54, 0.4), (0.72, 0.2), (0.9, 0.4)]),
}


class TurnArrow(Widget):
    kind = StringProperty('right')

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.redraw, size=self.redraw, kind=self.redraw)

    def redraw(self, *_):
        s = min(self.size)
        x0, y0 = self.center_x - s / 2, self.center_y - s / 2
        body, head = ARROWS.get(self.kind, ARROWS['right'])
        pad, inner = s * 0.16, s * 0.68
        f = lambda pts: [c for (u, v) in pts for c in (x0 + pad + u * inner, y0 + pad + v * inner)]
        self.canvas.clear()
        with self.canvas:
            Color(*BLUE, 0.95)
            RoundedRectangle(pos=(x0, y0), size=(s, s), radius=[s * 0.26])
            Color(1, 1, 1, 1)
            Line(points=f(body), width=s * 0.055, joint='round', cap='round')
            Line(points=f(head), width=s * 0.055, joint='round', cap='round')


# ---------------------------------------------------------------- layout
KV = '''
#:set TXT [0.93, 0.96, 1, 1]
#:set DIM [0.55, 0.62, 0.82, 1]
#:set CYAN [0.31, 0.82, 1, 1]
#:set GREEN [0.24, 0.86, 0.52, 1]
#:set RED [1, 0.26, 0.32, 1]

<Label>:
    color: TXT

<Card,FloatCard>:
    canvas.before:
        Color:
            rgba: 0.09, 0.17, 0.48, 0.34
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.u * 0.9]
        Color:
            rgba: 0.47, 0.63, 1, 0.22
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, app.u * 0.9)
            width: 1.1

<Glass@BoxLayout>:
    canvas.before:
        Color:
            rgba: 0.02, 0.04, 0.13, 0.8
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.u * 0.6]
        Color:
            rgba: 0.47, 0.63, 1, 0.18
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, app.u * 0.6)
            width: 1

<RailBtn>:
    orientation: 'vertical'
    size_hint_y: None
    height: self.width
    padding: app.u * 0.35
    canvas.before:
        Color:
            rgba: (0.31, 0.82, 1, 0.16) if self.active else (0.09, 0.17, 0.48, 0.5)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.u * 0.6]
        Color:
            rgba: (0.31, 0.82, 1, 0.9) if self.active else (0.47, 0.63, 1, 0.22)
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, app.u * 0.6)
            width: 1.2
        Color:
            rgba: (1, 1, 1, 0.1) if self.state == 'down' else (0, 0, 0, 0)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.u * 0.6]
    Widget:
        canvas:
            Color:
                rgba: root.dot_on if root.active else (0.55, 0.62, 0.82, 0.45)
            Ellipse:
                pos: self.center_x - app.u * 0.22, self.center_y - app.u * 0.22
                size: app.u * 0.44, app.u * 0.44
    Label:
        text: root.text
        bold: True
        font_size: app.u * 0.5
        color: CYAN if root.active else TXT
        size_hint_y: None
        height: self.texture_size[1] + app.u * 0.2

<Stat>:
    orientation: 'vertical'
    padding: [0, app.u * 0.2]
    canvas.before:
        Color:
            rgba: 0.02, 0.04, 0.13, 0.5
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.u * 0.55]
    Label:
        text: root.value
        bold: True
        font_size: app.u * 0.85
    Label:
        text: root.label
        color: DIM
        bold: True
        font_size: app.u * 0.36
        size_hint_y: None
        height: self.texture_size[1]

FloatLayout:
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        Rectangle:
            pos: self.pos
            size: self.size
            texture: app.bg_tex

    BoxLayout:
        padding: app.u * 0.55
        spacing: app.u * 0.5

        # ------------------------------------------------ barra lateral
        Card:
            orientation: 'vertical'
            size_hint_x: None
            width: app.u * 3.3
            padding: app.u * 0.4
            spacing: app.u * 0.4
            Label:
                text: app.clock_txt
                bold: True
                font_size: app.u * 0.85
                size_hint_y: None
                height: app.u * 1.6
            Widget:
            RailBtn:
                text: 'GPS'
                active: app.gps_on
                dot_on: GREEN
                on_release: app.toggle_gps()
            RailBtn:
                text: 'BIT'
                active: app.bit_on
                on_release: app.toggle_bit()
            RailBtn:
                text: 'NOITE'
                active: app.night
                on_release: app.toggle_night()
            Widget:

        # ------------------------------------------------ mapa
        FloatCard:
            size_hint_x: 1.9
            MapView:
                pos_hint: {'x': 0, 'y': 0}
                offset: app.map_off
                radius: app.u * 0.9
            Glass:
                pos_hint: {'x': 0.035, 'top': 0.955}
                size_hint: None, None
                size: app.u * 10.5, app.u * 3.6
                padding: app.u * 0.5
                spacing: app.u * 0.55
                TurnArrow:
                    size_hint_x: None
                    width: self.height
                    kind: app.turn_kind
                BoxLayout:
                    orientation: 'vertical'
                    Label:
                        text: app.turn_txt
                        color: DIM
                        bold: True
                        font_size: app.u * 0.42
                        text_size: self.size
                        halign: 'left'
                        valign: 'bottom'
                    Label:
                        text: app.turn_dist_txt
                        markup: True
                        bold: True
                        font_size: app.u * 1.35
                        text_size: self.size
                        halign: 'left'
                        valign: 'middle'
                        size_hint_y: 1.6
                    Label:
                        text: app.street_txt
                        color: CYAN
                        bold: True
                        font_size: app.u * 0.48
                        text_size: self.size
                        halign: 'left'
                        valign: 'top'
                        shorten: True
            Glass:
                pos_hint: {'right': 0.965, 'y': 0.045}
                size_hint: None, None
                size: app.u * 9.5, app.u * 1.5
                padding: [app.u * 0.6, 0]
                Label:
                    text: app.eta_txt
                    markup: True
                    color: DIM
                    font_size: app.u * 0.46
                    text_size: self.size
                    halign: 'left'
                    valign: 'middle'
                Label:
                    text: app.rem_txt
                    markup: True
                    color: DIM
                    font_size: app.u * 0.46
                    text_size: self.size
                    halign: 'right'
                    valign: 'middle'

        # ------------------------------------------------ velocímetro
        Card:
            orientation: 'vertical'
            padding: app.u * 0.55
            spacing: app.u * 0.45
            BoxLayout:
                size_hint_y: None
                height: app.u * 2.4
                spacing: app.u * 0.45
                SignalBtn:
                    side: 'left'
                    active: app.sig_left
                    lit: app.blink
                    on_release: app.toggle_signal('L')
                SignalBtn:
                    side: 'right'
                    active: app.sig_right
                    lit: app.blink
                    on_release: app.toggle_signal('R')
            FloatLayout:
                Gauge:
                    id: gauge
                    pos_hint: {'x': 0, 'y': 0}
                    value: app.gauge_val
                Label:
                    id: spd
                    text: str(int(round(app.speed)))
                    font_size: max(1, gauge.dial_r * 0.8)
                    bold: True
                    italic: True
                    size_hint: None, None
                    size: self.texture_size
                    center_x: gauge.dial_center[0]
                    center_y: gauge.dial_center[1] + gauge.dial_r * 0.16
                Label:
                    text: 'KM/H'
                    color: DIM
                    bold: True
                    font_size: max(1, gauge.dial_r * 0.13)
                    size_hint: None, None
                    size: self.texture_size
                    center_x: gauge.dial_center[0]
                    top: spd.y + gauge.dial_r * 0.06
                # indicador de freio
                Label:
                    text: 'FREIO'
                    bold: True
                    font_size: max(1, gauge.dial_r * 0.15)
                    color: TXT if app.brake else [1, 0.26, 0.32, 0.45]
                    size_hint: None, None
                    size: self.texture_size[0] + gauge.dial_r * 0.35, gauge.dial_r * 0.3
                    center_x: gauge.dial_center[0]
                    center_y: gauge.dial_center[1] - gauge.dial_r * 0.55
                    canvas.before:
                        Color:
                            rgba: [1, 0.26, 0.32, 0.4] if app.brake else [0, 0, 0, 0]
                        Rectangle:
                            texture: app.glow_tex
                            pos: self.x - self.width * 0.4, self.y - self.height * 1.2
                            size: self.width * 1.8, self.height * 3.4
                        Color:
                            rgba: RED if app.brake else [1, 0.26, 0.32, 0.12]
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [self.height / 2]
            BoxLayout:
                size_hint_y: None
                height: app.u * 2.1
                spacing: app.u * 0.35
                Stat:
                    value: app.dist_txt
                    label: 'KM'
                Stat:
                    value: app.time_txt
                    label: 'TEMPO'
                Stat:
                    value: app.avg_txt
                    label: 'MÉDIA'

    # aviso rápido
    Label:
        text: app.toast_txt
        opacity: app.toast_op
        bold: True
        color: 0.05, 0.05, 0.1, 1
        font_size: app.u * 0.6
        size_hint: None, None
        size: self.texture_size[0] + app.u * 1.6, app.u * 1.5
        pos_hint: {'center_x': 0.5, 'top': 0.95}
        canvas.before:
            Color:
                rgba: 1, 0.66, 0.1, 1
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [self.height / 2]
'''

TURNS = [
    ('VIRE À DIREITA', 'Av. das Palmeiras', 850, 'right'),
    ('VIRE À ESQUERDA', 'Rua das Acácias', 600, 'left'),
    ('SIGA EM FRENTE', 'Ciclovia Beira-Rio', 1200, 'straight'),
    ('RETORNO', 'Praça Central', 400, 'uturn'),
]
V = '[color=eef4ff][b]{}[/b][/color]'  # destaque de valor dentro de texto cinza


# ---------------------------------------------------------------- app
class CicloAutoApp(App):
    u = NumericProperty(20)
    bg_tex = ObjectProperty(None)
    glow_tex = ObjectProperty(None)

    speed = NumericProperty(0)
    gauge_val = NumericProperty(0)
    map_off = NumericProperty(0)

    night = BooleanProperty(False)
    gps_on = BooleanProperty(False)
    bit_on = BooleanProperty(False)
    sig_left = BooleanProperty(False)
    sig_right = BooleanProperty(False)
    blink = BooleanProperty(False)
    brake = BooleanProperty(False)

    clock_txt = StringProperty('--:--')
    turn_txt = StringProperty('')
    turn_kind = StringProperty('right')
    street_txt = StringProperty('')
    turn_dist_txt = StringProperty('')
    eta_txt = StringProperty('')
    rem_txt = StringProperty('')
    time_txt = StringProperty('00:00')
    avg_txt = StringProperty('0,0')
    dist_txt = StringProperty('0,00')
    toast_txt = StringProperty('')
    toast_op = NumericProperty(0)

    def build(self):
        self.title = 'CicloAuto'
        if not ANDROID:
            Window.size = (1100, 550)
        Window.clearcolor = (0.02, 0.03, 0.08, 1)
        self.bg_day, self.bg_night = bg_texture(1.0), bg_texture(0.5)
        self.bg_tex = self.bg_day
        self.glow_tex = glow_texture()
        Window.bind(size=self._on_resize)
        self._on_resize(Window, Window.size)

        # estado da pedalada
        self.t = 0.0
        self.dist = 0.0
        self.elapsed = 0.0
        self.trip_km = 9.1
        self.turn_i = 0
        self.turn_left = TURNS[0][2]
        self.accel = 0.0         # km/h por segundo (suavizado)
        self.brake_bit = False   # freio detectado pelo acelerômetro do micro:bit

        # GPS (preenchido por ao_atualizar_posicao)
        self.gps_kmh = 0
        self.gps_last = 0.0

        self.link = MicrobitLink(on_message=self.ao_receber_microbit)

        self._set_turn()
        root = Builder.load_string(KV)
        Clock.schedule_interval(self.tick, 1 / 30)
        Clock.schedule_interval(self.slow_tick, 1)
        Clock.schedule_interval(self._blink, 0.36)
        self.slow_tick(0)
        return root

    def on_start(self):
        if ANDROID:
            manter_tela_ligada()

    def on_pause(self):
        return True

    def on_stop(self):
        if ANDROID and self.gps_on:
            gps.stop()
        self.link.desconectar()

    def _on_resize(self, win, size):
        self.u = min(size[0] / 2, size[1]) / 19

    # ------------------------------------------------ GPS (lógica do plyer)
    def toggle_gps(self):
        if self.gps_on:
            if ANDROID:
                gps.stop()
            self.gps_on = False
            self.toast('GPS desligado, voltando para a simulação')
            return
        if not ANDROID:
            self.toast('O GPS só funciona no celular')
            return
        self.toast('Buscando GPS…')
        request_permissions([Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION],
                            self._perm_result)

    def _perm_result(self, perms, grants):
        if all(grants):
            self._start_gps()
        else:
            self._toast_main('Permissão de localização negada')

    @mainthread
    def _start_gps(self):
        gps.configure(on_location=self.ao_atualizar_posicao, on_status=self.ao_status_gps)
        gps.start(minTime=1000, minDistance=0)
        self.gps_on = True

    @mainthread
    def ao_atualizar_posicao(self, **kwargs):
        # O GPS do celular entrega a velocidade direto em m/s
        velocidade_ms = kwargs.get('speed', 0) or 0
        self.gps_kmh = int(velocidade_ms * 3.6)
        self.gps_last = time.time()

    @mainthread
    def ao_status_gps(self, stype, status):
        if stype == 'provider-disabled':
            self.toast('Ative a localização do celular')

    @mainthread
    def _toast_main(self, msg):
        self.toast(msg)

    # ------------------------------------------------ setas / freio / micro:bit
    def toggle_signal(self, lado):
        """Toque na seta da tela (os botões A/B do micro:bit fazem o mesmo)."""
        if lado == 'L':
            self.set_signal('L' if not self.sig_left else '0')
        else:
            self.set_signal('R' if not self.sig_right else '0')

    def set_signal(self, lado, enviar=True):
        self.sig_left, self.sig_right = lado == 'L', lado == 'R'
        self.blink = True
        Clock.unschedule(self._blink)
        Clock.schedule_interval(self._blink, 0.36)
        if enviar:
            self.link.enviar('S' + lado)

    def _blink(self, dt):
        self.blink = not self.blink

    def _set_brake(self, on):
        if on != self.brake:
            self.brake = on
            self.link.enviar('B1' if on else 'B0')

    @mainthread
    def ao_receber_microbit(self, msg):
        if msg in ('SL', 'SR', 'S0'):
            self.set_signal(msg[1], enviar=False)
        elif msg in ('B1', 'B0'):
            self.brake_bit = msg == 'B1'

    def toggle_bit(self):
        if self.link.conectado:
            self.link.desconectar()
        elif not self.link.conectar():
            self.toast('Conexão Bluetooth com o micro:bit: em breve')
        self.bit_on = self.link.conectado

    def toggle_night(self):
        self.night = not self.night
        self.bg_tex = self.bg_night if self.night else self.bg_day

    def toast(self, msg):
        self.toast_txt = msg
        Animation.cancel_all(self, 'toast_op')
        (Animation(toast_op=1, d=0.18) + Animation(d=1.6) + Animation(toast_op=0, d=0.35)).start(self)

    # ------------------------------------------------ atualização
    def _set_turn(self):
        txt, street, dist, kind = TURNS[self.turn_i]
        self.turn_txt, self.street_txt, self.turn_kind = txt, street, kind
        self.turn_left = dist

    def tick(self, dt):
        real_dt = min(dt, 5)   # tempo real: conta distância e tempo
        dt = min(dt, 0.25)     # passo limitado: só para suavizar
        if dt <= 0:
            return
        self.t += real_dt
        real = self.gps_on and time.time() - self.gps_last < 5
        target = self.gps_kmh if real else 24 + 8 * sin(self.t / 4) + 3 * sin(self.t * 1.3)
        prev = self.speed
        self.speed += (target - self.speed) * min(1, dt * (4 if real else 1.5))

        # freio: desaceleração forte (GPS) ou aviso do acelerômetro do micro:bit
        self.accel += ((self.speed - prev) / dt - self.accel) * min(1, dt * 3)
        if self.accel < FREIO_LIGA or self.brake_bit:
            self._set_brake(True)
        elif self.accel > FREIO_DESLIGA:
            self._set_brake(False)

        km = self.speed / 3600 * real_dt
        self.dist += km
        self.elapsed += real_dt
        self.turn_left -= km * 1000
        if self.turn_left <= 0:
            self.turn_i = (self.turn_i + 1) % len(TURNS)
            self._set_turn()
        self.map_off = (self.map_off + self.speed * dt * 2.2) % 140

        self.gauge_val = self.speed / MAX_SPEED
        m, s = divmod(int(self.elapsed), 60)
        self.time_txt = f'{m:02d}:{s:02d}'
        self.avg_txt = br(self.dist / (self.elapsed / 3600) if self.elapsed > 2 else 0)
        self.dist_txt = br(self.dist, 2)
        d = max(0, int(round(self.turn_left / 10) * 10))
        self.turn_dist_txt = f'{d} [size={int(self.u * 0.65)}][color=8c9ed1]m[/color][/size]'
        self.rem_txt = 'RESTAM  ' + V.format(br(max(0, self.trip_km - self.dist)) + ' km')

    def slow_tick(self, dt):
        self.clock_txt = time.strftime('%H:%M')
        rem = max(0, self.trip_km - self.dist)
        eta_min = rem / max(self.speed, 12) * 60 if self.speed > 3 else 0
        self.eta_txt = 'CHEGADA  ' + V.format(time.strftime('%H:%M', time.localtime(time.time() + eta_min * 60)))
        self.bit_on = self.link.conectado


if __name__ == '__main__':
    CicloAutoApp().run()
