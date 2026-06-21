#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RiskGuard Pro - Generateur de presentation PDF (vectoriel, sans dependance).

Produit un PDF 16:9 de 19 diapositives en utilisant uniquement la librairie
standard de Python (aucun paquet externe, aucun navigateur requis).

Usage:
    python3 build_pdf.py
Sortie:
    RiskGuard_Pro_Presentation.pdf
"""

import math
import zlib
import os

# ----------------------------------------------------------------------------
# Page geometry (points). 16:9
# ----------------------------------------------------------------------------
PW, PH = 960.0, 540.0

# ----------------------------------------------------------------------------
# Palette
# ----------------------------------------------------------------------------
def rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)

NAVY900 = rgb("0a1238")
NAVY800 = rgb("0f1a4a")
NAVY700 = rgb("1a237e")
CARD    = rgb("141d44")
CARD2   = rgb("18224f")
GOLD    = rgb("ffd700")
GOLDSOFT= rgb("ffe566")
GOLDDEEP= rgb("e6b800")
WHITE   = (1, 1, 1)
INK     = rgb("eaf0ff")
MUTED   = rgb("aab4e0")
GREEN   = rgb("2ecc71")
YELLOW  = rgb("f1c40f")
ORANGE  = rgb("e67e22")
RED     = rgb("e74c3c")
BLUE    = rgb("3949ab")
BLUEL   = rgb("5c6bc0")
GRID    = rgb("2a3566")

# ----------------------------------------------------------------------------
# Helvetica / Helvetica-Bold AFM widths (units / 1000)
# ----------------------------------------------------------------------------
HELV = {
 ' ':278,'!':278,'"':355,'#':556,'$':556,'%':889,'&':667,"'":191,'(':333,')':333,
 '*':389,'+':584,',':278,'-':333,'.':278,'/':278,'0':556,'1':556,'2':556,'3':556,
 '4':556,'5':556,'6':556,'7':556,'8':556,'9':556,':':278,';':278,'<':584,'=':584,
 '>':584,'?':556,'@':1015,'A':667,'B':667,'C':722,'D':722,'E':667,'F':611,'G':778,
 'H':722,'I':278,'J':500,'K':667,'L':556,'M':833,'N':722,'O':778,'P':667,'Q':778,
 'R':722,'S':667,'T':611,'U':722,'V':667,'W':944,'X':667,'Y':667,'Z':611,'[':278,
 '\\':278,']':278,'^':469,'_':556,'`':333,'a':556,'b':556,'c':500,'d':556,'e':556,
 'f':278,'g':556,'h':556,'i':222,'j':222,'k':500,'l':222,'m':833,'n':556,'o':556,
 'p':556,'q':556,'r':333,'s':500,'t':278,'u':556,'v':500,'w':722,'x':500,'y':500,
 'z':500,'{':334,'|':260,'}':334,'~':584,'\u00b7':278,
}
HELVB = {
 ' ':278,'!':333,'"':474,'#':556,'$':556,'%':889,'&':722,"'":238,'(':333,')':333,
 '*':389,'+':584,',':278,'-':333,'.':278,'/':278,'0':556,'1':556,'2':556,'3':556,
 '4':556,'5':556,'6':556,'7':556,'8':556,'9':556,':':333,';':333,'<':584,'=':584,
 '>':584,'?':611,'@':975,'A':722,'B':722,'C':722,'D':722,'E':667,'F':611,'G':778,
 'H':722,'I':278,'J':556,'K':722,'L':611,'M':833,'N':722,'O':778,'P':667,'Q':778,
 'R':722,'S':667,'T':611,'U':722,'V':667,'W':944,'X':667,'Y':667,'Z':611,'[':333,
 '\\':278,']':333,'^':584,'_':556,'`':333,'a':556,'b':611,'c':556,'d':611,'e':556,
 'f':333,'g':611,'h':611,'i':278,'j':278,'k':556,'l':278,'m':889,'n':611,'o':611,
 'p':611,'q':611,'r':389,'s':556,'t':333,'u':611,'v':556,'w':778,'x':556,'y':556,
 'z':500,'{':389,'|':280,'}':389,'~':584,'\u00b7':333,
}

def char_w(c, bold):
    t = HELVB if bold else HELV
    if c in t:
        return t[c]
    o = ord(c)
    if 0xC0 <= o <= 0xFF:          # accented letters
        return 700 if c.isupper() else 556
    return 556

def text_width(s, size, bold=False):
    return sum(char_w(c, bold) for c in s) * size / 1000.0

# ----------------------------------------------------------------------------
# Content stream builder (top-left coordinate system; we flip to PDF space)
# ----------------------------------------------------------------------------
class Canvas:
    def __init__(self):
        self.ops = []

    def _y(self, y):
        return PH - y

    # --- raw ---
    def raw(self, s):
        self.ops.append(s)

    # --- colors ---
    def fill_color(self, c):
        self.ops.append("%.4f %.4f %.4f rg" % c)
    def stroke_color(self, c):
        self.ops.append("%.4f %.4f %.4f RG" % c)
    def line_width(self, w):
        self.ops.append("%.3f w" % w)

    # --- rectangles ---
    def rect(self, x, y, w, h, color, fill=True):
        self.ops.append("%.2f %.2f %.2f %.2f re" % (x, self._y(y + h), w, h))
        if fill:
            self.fill_color(color); self.ops.append("f")
        else:
            self.stroke_color(color); self.ops.append("S")

    def round_rect(self, x, y, w, h, r, fill=None, stroke=None, lw=1.0):
        Y = self._y
        x0, x1 = x, x + w
        y0, y1 = y + h, y           # y0 bottom (larger y), y1 top
        b0, b1 = Y(y0), Y(y1)       # pdf y bottom, top
        k = 0.5523 * r
        p = []
        p.append("%.2f %.2f m" % (x0 + r, b0))
        p.append("%.2f %.2f l" % (x1 - r, b0))
        p.append("%.2f %.2f %.2f %.2f %.2f %.2f c" % (x1 - r + k, b0, x1, b0 + r - k, x1, b0 + r))
        p.append("%.2f %.2f l" % (x1, b1 - r))
        p.append("%.2f %.2f %.2f %.2f %.2f %.2f c" % (x1, b1 - r + k, x1 - r + k, b1, x1 - r, b1))
        p.append("%.2f %.2f l" % (x0 + r, b1))
        p.append("%.2f %.2f %.2f %.2f %.2f %.2f c" % (x0 + r - k, b1, x0, b1 - r + k, x0, b1 - r))
        p.append("%.2f %.2f l" % (x0, b0 + r))
        p.append("%.2f %.2f %.2f %.2f %.2f %.2f c" % (x0, b0 + r - k, x0 + r - k, b0, x0 + r, b0))
        p.append("h")
        self.ops.append(" ".join(p))
        self._paint(fill, stroke, lw)

    def _paint(self, fill, stroke, lw):
        if fill and stroke:
            self.fill_color(fill); self.stroke_color(stroke); self.line_width(lw); self.ops.append("B")
        elif fill:
            self.fill_color(fill); self.ops.append("f")
        elif stroke:
            self.stroke_color(stroke); self.line_width(lw); self.ops.append("S")

    # --- lines / paths ---
    def line(self, x1, y1, x2, y2, color, lw=1.0, dash=None):
        if dash:
            self.ops.append("[%s] 0 d" % dash)
        self.stroke_color(color); self.line_width(lw)
        self.ops.append("%.2f %.2f m %.2f %.2f l S" % (x1, self._y(y1), x2, self._y(y2)))
        if dash:
            self.ops.append("[] 0 d")

    def polyline(self, pts, color, lw=2.0, close=False):
        self.stroke_color(color); self.line_width(lw)
        cmd = []
        for i, (x, y) in enumerate(pts):
            cmd.append("%.2f %.2f %s" % (x, self._y(y), "m" if i == 0 else "l"))
        if close:
            cmd.append("h")
        self.ops.append(" ".join(cmd) + " S")

    def polygon(self, pts, color):
        self.fill_color(color)
        cmd = []
        for i, (x, y) in enumerate(pts):
            cmd.append("%.2f %.2f %s" % (x, self._y(y), "m" if i == 0 else "l"))
        cmd.append("h f")
        self.ops.append(" ".join(cmd))

    def circle(self, cx, cy, r, fill=None, stroke=None, lw=1.0):
        cyp = self._y(cy)
        k = 0.5523 * r
        p = []
        p.append("%.2f %.2f m" % (cx + r, cyp))
        p.append("%.2f %.2f %.2f %.2f %.2f %.2f c" % (cx + r, cyp + k, cx + k, cyp + r, cx, cyp + r))
        p.append("%.2f %.2f %.2f %.2f %.2f %.2f c" % (cx - k, cyp + r, cx - r, cyp + k, cx - r, cyp))
        p.append("%.2f %.2f %.2f %.2f %.2f %.2f c" % (cx - r, cyp - k, cx - k, cyp - r, cx, cyp - r))
        p.append("%.2f %.2f %.2f %.2f %.2f %.2f c" % (cx + k, cyp - r, cx + r, cyp - k, cx + r, cyp))
        p.append("h")
        self.ops.append(" ".join(p))
        self._paint(fill, stroke, lw)

    # --- gradient simulation (vertical bands) ---
    def vgrad(self, x, y, w, h, c1, c2, bands=60):
        bh = h / bands
        for i in range(bands):
            t = i / (bands - 1)
            c = (c1[0] + (c2[0] - c1[0]) * t,
                 c1[1] + (c2[1] - c1[1]) * t,
                 c1[2] + (c2[2] - c1[2]) * t)
            self.rect(x, y + i * bh, w + 0.5, bh + 0.6, c, True)

    def hgrad(self, x, y, w, h, stops, bands=120):
        # stops = [(pos, color), ...]
        def col(t):
            for i in range(len(stops) - 1):
                p0, c0 = stops[i]; p1, c1 = stops[i + 1]
                if p0 <= t <= p1:
                    f = 0 if p1 == p0 else (t - p0) / (p1 - p0)
                    return (c0[0] + (c1[0] - c0[0]) * f,
                            c0[1] + (c1[1] - c0[1]) * f,
                            c0[2] + (c1[2] - c0[2]) * f)
            return stops[-1][1]
        bw = w / bands
        for i in range(bands):
            t = i / (bands - 1)
            self.rect(x + i * bw, y, bw + 0.6, h, col(t), True)

    # --- text ---
    def text(self, x, y, s, size, color=INK, bold=False, align="left", spacing=0.0):
        if s == "":
            return
        w = text_width(s, size, bold) + spacing * max(0, len(s) - 1)
        if align == "center":
            x -= w / 2.0
        elif align == "right":
            x -= w
        font = "F2" if bold else "F1"
        enc = self._encode(s)
        ts = ""
        if spacing:
            ts = " %.2f Tc" % spacing
        self.ops.append("BT /%s %.2f Tf%s %.4f %.4f %.4f rg %.2f %.2f Td (%s) Tj ET" %
                         (font, size, ts, color[0], color[1], color[2], x, self._y(y), enc))
        if spacing:
            self.ops.append("BT 0 Tc ET")
        return w

    @staticmethod
    def _encode(s):
        out = []
        for ch in s:
            try:
                b = ch.encode("cp1252")
            except UnicodeEncodeError:
                b = b"?"
            for byte in b:
                if byte in (0x28, 0x29, 0x5C):   # ( ) \
                    out.append("\\" + chr(byte))
                elif 32 <= byte <= 126:
                    out.append(chr(byte))
                else:
                    out.append("\\%03o" % byte)
        return "".join(out)

    def wrap(self, x, y, s, size, color, maxw, leading, bold=False):
        words = s.split(" ")
        line = ""
        ny = y
        for wd in words:
            test = wd if line == "" else line + " " + wd
            if text_width(test, size, bold) > maxw and line:
                self.text(x, ny, line, size, color, bold)
                line = wd
                ny += leading
            else:
                line = test
        if line:
            self.text(x, ny, line, size, color, bold)
            ny += leading
        return ny

    def stream(self):
        return "\n".join(self.ops)

# ----------------------------------------------------------------------------
# Shared slide chrome
# ----------------------------------------------------------------------------
TOTAL = 19

def background(c, decor=True):
    c.vgrad(0, 0, PW, PH, NAVY800, NAVY900)
    # corner glow accents
    c.fill_color(NAVY700)
    # subtle gold corner triangle top-right
    c.polygon([(PW, 0), (PW, 70), (PW - 130, 0)], rgb("121b48"))
    c.polygon([(0, PH), (0, PH - 70), (150, PH)], rgb("111a45"))

def footer(c, idx):
    # gold shield mark
    sx, sy = 26, PH - 22
    c.polygon([(sx, sy - 9), (sx + 9, sy - 6), (sx + 9, sy + 3),
               (sx + 4.5, sy + 9), (sx, sy + 3)], GOLD)
    c.text(42, PH - 18, "RiskGuard Pro", 9, INK, bold=True)
    c.text(PW - 26, PH - 18, "%d" % idx, 9, GOLD, bold=True, align="right")
    c.text(PW - 40, PH - 18, "/  %d   " % TOTAL, 9, MUTED, align="right")
    # progress line
    c.rect(0, 0, PW, 3, NAVY700, True)
    c.rect(0, 0, PW * idx / TOTAL, 3, GOLD, True)

def kicker(c, x, y, s):
    c.line(x, y - 3, x + 26, y - 3, GOLD, 2)
    c.text(x + 34, y, s.upper(), 10, GOLD, bold=True, spacing=1.6)

def heading(c, x, y, s, size=34):
    c.text(x, y, s, size, WHITE, bold=True)
    c.rect(x, y + 12, 64, 4, GOLD, True)

def badge(c, s):
    w = text_width(s, 9.5, False) + 24
    c.round_rect(PW - 60 - w, 30, w, 22, 11, fill=rgb("1c2654"), stroke=GOLDDEEP, lw=0.8)
    c.text(PW - 60 - w / 2, 45, s, 9.5, GOLD, align="center")

def bullet_marker(c, x, y, n=None, color=GOLD):
    if n is None:
        c.round_rect(x, y - 7, 9, 9, 2, fill=color)
    else:
        c.circle(x + 11, y - 3, 11, fill=rgb("2a2204"), stroke=GOLD, lw=1)
        c.text(x + 11, y + 1, str(n), 10, GOLD, bold=True, align="center")

def card(c, x, y, w, h, title=None):
    c.round_rect(x, y, w, h, 12, fill=CARD, stroke=rgb("3a3a66"), lw=0.8)
    if title:
        c.text(x + 18, y + 26, title, 12, GOLD, bold=True)

# ----------------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------------
def chart_ctx(c, x, y, w, h):
    pad = 30
    data = [22, 28, 26, 35, 41, 52, 63, 78]
    years = ["'18","'19","'20","'21","'22","'23","'24","'25"]
    mx = 90
    x0, y0 = x + pad, y + h - pad
    pw, ph = w - pad - 14, h - pad - 18
    for i in range(5):
        gy = y + 8 + ph * i / 4
        c.line(x0, gy, x + w - 14, gy, GRID, 0.6)
    def px(i): return x0 + pw * i / (len(data) - 1)
    def py(v): return y0 - ph * v / mx
    pts = [(px(i), py(v)) for i, v in enumerate(data)]
    # area
    c.polygon([(x0, y0)] + pts + [(px(len(data)-1), y0)], rgb("2c2a12"))
    c.polyline(pts, GOLD, 2.5)
    for i, (X, Y) in enumerate(pts):
        c.circle(X, Y, 3, fill=NAVY900, stroke=GOLD, lw=1.5)
        c.text(X, y0 + 14, years[i], 8, MUTED, align="center")

def chart_imbalance(c, x, y, w, h):
    base = y + h - 26
    top = y + 16
    bars = [("Sains (0)", 97, BLUE), ("Faillite (1)", 3, RED)]
    bw = 70
    gap = (w - 2 * bw) / 3
    for i, (lbl, v, col) in enumerate(bars):
        bx = x + gap + i * (bw + gap)
        bh = (base - top) * v / 100
        c.round_rect(bx, base - bh, bw, bh, 6, fill=col)
        c.text(bx + bw / 2, base - bh - 8, "%d%%" % v, 15, WHITE, bold=True, align="center")
        c.text(bx + bw / 2, base + 16, lbl, 10, MUTED, align="center")
    c.line(x + 14, base, x + w - 10, base, GRID, 0.8)

def chart_clean(c, x, y, w, h):
    base = y + h - 24
    top = y + 22
    data = [("Avant", 96, BLUEL), ("Apres", 65, GOLD)]
    bw = 64
    gap = (w - 2 * bw) / 3
    for i, (lbl, v, col) in enumerate(data):
        bx = x + gap + i * (bw + gap)
        bh = (base - top) * v / 100
        c.round_rect(bx, base - bh, bw, bh, 6, fill=col)
        c.text(bx + bw / 2, base - bh - 7, str(v), 14, WHITE, bold=True, align="center")
        c.text(bx + bw / 2, base + 15, lbl, 10, MUTED, align="center")
    # arrow
    midy = (base + top) / 2
    ax = x + gap + bw + gap / 2
    c.line(ax - 12, midy, ax + 12, midy, GOLD, 2)
    c.polygon([(ax + 12, midy - 4), (ax + 18, midy), (ax + 12, midy + 4)], GOLD)

def chart_confusion(c, x, y, w, h, m, labels, small=True):
    n = 2
    cell = min((w - 60) / n, (h - 36) / n)
    ox = x + 56
    oy = y + 10
    mx = max(max(row) for row in m)
    for r in range(n):
        for cc in range(n):
            v = m[r][cc]
            correct = (r == cc)
            inten = 0.22 + 0.62 * (v / mx if mx else 0)
            base = GREEN if correct else RED
            col = (base[0]*inten + NAVY900[0]*(1-inten),
                   base[1]*inten + NAVY900[1]*(1-inten),
                   base[2]*inten + NAVY900[2]*(1-inten))
            c.round_rect(ox + cc*cell, oy + r*cell, cell-4, cell-4, 5, fill=col)
            c.text(ox + cc*cell + cell/2 - 2, oy + r*cell + cell/2 + 4,
                   str(v), 13 if not small else 12, WHITE, bold=True, align="center")
    c.text(ox - 6, oy + cell/2, labels[0], 8, MUTED, align="right")
    c.text(ox - 6, oy + cell + cell/2, labels[1], 8, MUTED, align="right")
    c.text(ox + cell/2, oy + 2*cell + 12, "Pred " + labels[0], 8, MUTED, align="center")
    c.text(ox + cell + cell/2, oy + 2*cell + 12, "Pred " + labels[1], 8, MUTED, align="center")

def chart_smote(c, x, y, w, h):
    # map normalized coords into box
    def MX(v): return x + 20 + (w - 40) * v / 260.0
    def MY(v): return y + 10 + (h - 30) * v / 150.0
    pts = [(60,120),(110,60),(180,100),(230,50),(150,130)]
    P = [(MX(a), MY(b)) for a,b in pts]
    c.line(P[0][0],P[0][1],P[1][0],P[1][1], GOLD, 1.2, dash="3 3")
    c.line(P[1][0],P[1][1],P[3][0],P[3][1], GOLD, 1.2, dash="3 3")
    for a,b,t in [(0,1,.4),(0,1,.7),(1,3,.5)]:
        X = P[a][0] + (P[b][0]-P[a][0])*t
        Y = P[a][1] + (P[b][1]-P[a][1])*t
        c.circle(X, Y, 4.5, fill=GOLD)
    for X,Y in P:
        c.circle(X, Y, 5.5, fill=RED, stroke=WHITE, lw=1.2)
    c.circle(x+22, y+h-10, 4, fill=RED)
    c.text(x+30, y+h-7, "reels", 8.5, MUTED)
    c.circle(x+95, y+h-10, 4, fill=GOLD)
    c.text(x+103, y+h-7, "synthetiques (SMOTE)", 8.5, MUTED)

def chart_gauss(c, x, y, w, h):
    cx = x + w/2
    base = y + h - 18
    A = h - 34
    sig = w/7.0
    pts = []
    xx = x + 18
    while xx <= x + w - 18:
        v = base - A * math.exp(-((xx-cx)**2)/(2*sig*sig))
        pts.append((xx, v)); xx += 3
    c.line(x+18, base, x+w-18, base, GRID, 0.8)
    c.line(cx, y+8, cx, base, GRID, 0.8, dash="3 3")
    c.polyline(pts, GOLD, 2.2)
    c.text(cx, base + 13, "mean = 0", 9, MUTED, align="center")

def chart_gradientbar(c, x, y, w, h):
    c.hgrad(x, y, w, h, [(0,GREEN),(0.33,YELLOW),(0.66,ORANGE),(1.0,RED)])
    labs = [("Faible",0.0,0.25),("Modere",0.25,0.5),("Eleve",0.5,0.75),("Critique",0.75,1.0)]
    for name,a,b in labs:
        c.text(x + w*(a+b)/2, y + h/2 + 4, name, 11, NAVY900, bold=True, align="center")

def chart_bench(c, x, y, w, h):
    data = [("Reg.Log.",.72,False),("RF",.86,False),("SVM",.78,False),
            ("KNN",.75,False),("XGBoost",.93,True),("LightGBM",.91,False)]
    base = y + h - 26
    top = y + 14
    n = len(data)
    bw = (w - 30) / n * 0.62
    step = (w - 30) / n
    for i in range(5):
        gy = top + (base-top)*i/4
        c.line(x+18, gy, x+w-6, gy, GRID, 0.5)
    for i,(lbl,v,best) in enumerate(data):
        bx = x + 22 + i*step
        bh = (base-top)*v
        c.round_rect(bx, base-bh, bw, bh, 4, fill=GOLD if best else BLUEL)
        c.text(bx+bw/2, base-bh-6, "%.2f"%v, 9, GOLD if best else WHITE, bold=best, align="center")
        c.text(bx+bw/2, base+13, lbl, 7.5, MUTED, align="center")

def chart_boost(c, x, y, w, h):
    cy = y + 36
    for i in range(4):
        cx = x + 30 + i*((w-60)/3)
        c.circle(cx, cy, 15, fill=GOLD if i==3 else BLUEL)
        c.text(cx, cy+4, "T%d"%(i+1), 11, NAVY900, bold=True, align="center")
        c.text(cx, cy+32, "base" if i==0 else "+ erreur", 8, MUTED, align="center")
        if i < 3:
            nx = x + 30 + (i+1)*((w-60)/3)
            c.line(cx+17, cy, nx-17, cy, GOLD, 1.8)
            c.polygon([(nx-17,cy-3),(nx-11,cy),(nx-17,cy+3)], GOLD)

def chart_optuna(c, x, y, w, h):
    pad = 28
    raw = [.70,.66,.74,.71,.78,.76,.81,.79,.84,.80,.86,.85,.88,.87,.89,.88,
           .905,.90,.91,.905,.915,.91,.92,.918,.925,.92,.928,.925,.93,.929]
    best=[]; b=.6
    for v in raw:
        b=max(b,v); best.append(b)
    x0=x+pad; y0=y+h-pad; pw=w-pad-12; ph=h-pad-14
    def px(i): return x0+pw*i/(len(raw)-1)
    def py(v): return y0-ph*(v-.6)/.4
    for i in range(5):
        gy=y+8+ph*i/4
        c.line(x0,gy,x+w-12,gy,GRID,0.5)
    for i,v in enumerate(raw):
        c.circle(px(i),py(v),2,fill=BLUEL)
    c.polyline([(px(i),py(v)) for i,v in enumerate(best)], GOLD, 2.2)
    c.text(x0, y+6, "AUC-ROC", 8.5, MUTED)
    c.text(x+w-12, y0+13, "30 essais", 8.5, MUTED, align="right")
    c.text(px(29)-2, py(.93)-8, "0.93", 9, GOLD, bold=True, align="right")

def chart_roc(c, x, y, w, h):
    pad = 24
    sz = min(w, h) - pad - 14
    x0 = x + pad; y0 = y + h - pad
    c.rect(x0, y0 - sz, sz, sz, GRID, False)
    c.line(x0, y0, x0+sz, y0-sz, MUTED, 0.8, dash="3 3")
    pts=[(0,0),(.02,.55),(.04,.78),(.08,.88),(.15,.94),(.3,.97),(.6,.99),(1,1)]
    c.polyline([(x0+p*sz, y0-q*sz) for p,q in pts], GOLD, 2.4)
    c.text(x0+8, y0-sz+14, "AUC = 0.97", 10, GOLD, bold=True)

def chart_feat(c, x, y, w, h):
    data=[("Debt Ratio %",.39,True),("ROA (NI/Actifs)",.30,False),
          ("Current Ratio",.19,False),("Work.Cap/Actifs",.12,False),
          ("Retained E./Actifs",.10,False)]
    mx=.42; ox=x+138; bh=20; gap=10
    for i,(lbl,v,best) in enumerate(data):
        yy=y+16+i*(bh+gap)
        bw=(w-ox+x-12)*v/mx
        c.round_rect(ox, yy, bw, bh, 4, fill=GOLD if best else BLUEL)
        c.text(ox-6, yy+bh/2+4, lbl, 9, WHITE, align="right")
        c.text(ox+bw+5, yy+bh/2+4, "%.2f"%v, 8.5, MUTED)

def chart_qr(c, cx, cy, size):
    seed = [
      "1111111010111111","1000001110000010","1011101010111010","1011101110111010",
      "1011101010111010","1000001110000010","1111111010101110","0000000000000000",
      "1010110100110101","0110101010110100","1011010101011010","0101101110101100",
      "1111111010101010","1000001101010100","1011101011001100","1011101100110010"]
    n=16; cell=size/n
    x0=cx-size/2; y0=cy-size/2
    c.round_rect(x0-8, y0-8, size+16, size+16, 8, fill=WHITE)
    for r in range(n):
        row=seed[r]
        for cc in range(n):
            if cc < len(row) and row[cc]=="1":
                c.rect(x0+cc*cell, y0+r*cell, cell+0.4, cell+0.4, NAVY900, True)

# ----------------------------------------------------------------------------
# Bullet list helper
# ----------------------------------------------------------------------------
def bullets(c, x, y, items, size=12.5, gap=11, maxw=420, numbered=False, leading=15):
    yy = y
    for i, it in enumerate(items):
        if numbered:
            bullet_marker(c, x, yy, n=i+1)
            tx = x + 30
        else:
            bullet_marker(c, x, yy)
            tx = x + 20
        ny = c.wrap(tx, yy, it, size, INK, maxw, leading)
        yy = ny + gap
    return yy

# ----------------------------------------------------------------------------
# SLIDES
# ----------------------------------------------------------------------------
def slide_cover(c):
    background(c, decor=False)
    # shield
    cx, cy = PW/2, 132
    c.polygon([(cx,cy-46),(cx+42,cy-30),(cx+42,cy+12),(cx,cy+44),(cx-42,cy+12),(cx-42,cy-30)], GOLD)
    c.polyline([(cx-18,cy-2),(cx-4,cy+12),(cx+22,cy-16)], NAVY900, 6)
    kicker_centered(c, PW/2, 210, "PROJET DE FIN D'ANNEE  -  2025-2026")
    c.text(PW/2, 270, "RiskGuard Pro", 56, WHITE, bold=True, align="center")
    # gold accent on "Guard"? keep simple, underline
    c.rect(PW/2 - 70, 284, 140, 4, GOLD, True)
    c.wrap_center(PW/2, 312, "Plateforme Intelligente de Detection de Risque Bancaire pour Entreprises",
                  15, MUTED, 620)
    # meta row
    meta = [("Etudiant(s)","[ A completer ]"),("Encadrant","[ A completer ]"),("Universite","[ Logo / Nom ]")]
    bx = PW/2 - 300
    for i,(t,v) in enumerate(meta):
        x = PW/2 - 270 + i*270
        c.text(x, 388, t, 10, WHITE, bold=True, align="center")
        c.text(x, 406, v, 11, GOLDSOFT, align="center")
    # year pill
    yt = "Annee universitaire 2025 - 2026"
    yw = text_width(yt, 11, False) + 44
    c.round_rect(PW/2 - yw/2, 438, yw, 30, 15, stroke=GOLD, lw=1.2)
    c.text(PW/2, 458, yt, 11, GOLD, bold=True, align="center", spacing=1.0)
    footer(c, 1)

def kicker_centered(c, cx, y, s):
    w = text_width(s, 10, True) + 1.6*max(0,len(s)-1)
    c.text(cx, y, s, 10, GOLD, bold=True, align="center", spacing=1.6)

# add helpers to Canvas
def _wrap_center(self, cx, y, s, size, color, maxw, leading=20, bold=False):
    words = s.split(" "); line=""; lines=[]
    for wd in words:
        test = wd if not line else line+" "+wd
        if text_width(test,size,bold) > maxw and line:
            lines.append(line); line=wd
        else:
            line=test
    if line: lines.append(line)
    for i,ln in enumerate(lines):
        self.text(cx, y+i*leading, ln, size, color, bold=bold, align="center")
    return y + len(lines)*leading
Canvas.wrap_center = _wrap_center

def slide_toc(c):
    background(c)
    badge(c, "30 s")
    kicker(c, 60, 70, "Plan de la presentation")
    heading(c, 60, 110, "Sommaire")
    items = ["Contexte & Problematique","Objectifs du projet","Donnees & Pretraitement",
             "Donnees synthetiques (SMOTE + Bruit Gaussien)","Comparaison des modeles ML",
             "Pourquoi XGBoost ?","Architecture technique","Demonstration",
             "Resultats & Metriques","Conclusion & Perspectives"]
    colw = 410
    for i, it in enumerate(items):
        col = i // 5
        row = i % 5
        x = 70 + col * 430
        y = 175 + row * 62
        c.round_rect(x, y, colw, 48, 10, fill=CARD, stroke=rgb("3a3a66"), lw=0.8)
        c.circle(x + 26, y + 24, 15, fill=GOLD)
        c.text(x + 26, y + 29, str(i+1), 12, NAVY900, bold=True, align="center")
        c.text(x + 52, y + 29, it, 12.5, INK, bold=False)
    footer(c, 2)

def slide_context(c):
    background(c); badge(c, "1 min")
    kicker(c, 60, 70, "Pourquoi ce projet ?")
    heading(c, 60, 110, "Contexte & Problematique", 30)
    items = [
      "Le secteur bancaire marocain fait face a un risque croissant de defaillance d'entreprises.",
      "Les methodes traditionnelles (scoring manuel, ratios simples) sont limitees et subjectives.",
      "Besoin d'un outil automatise, fiable et rapide pour classifier le niveau de risque.",
    ]
    bullets(c, 60, 175, items, maxw=420)
    card(c, 60, 360, 460, 110, "Question centrale")
    c.wrap(78, 408, "Comment predire la probabilite de faillite d'une entreprise a partir de ses ratios financiers ?",
           13.5, INK, 424, 18)
    card(c, 560, 150, 340, 320, "Hausse des defaillances")
    chart_ctx(c, 575, 185, 312, 265)
    footer(c, 3)

def slide_objectives(c):
    background(c); badge(c, "1 min")
    kicker(c, 60, 70, "Ce que nous voulons livrer")
    heading(c, 60, 110, "Objectifs du projet")
    feats = [
      ("Pipeline ML complet","De la donnee brute a la prediction temps reel."),
      ("4 niveaux de risque","Faible - Modere - Eleve - Critique."),
      ("Interface web intuitive","Pensee pour les analystes bancaires."),
      ("Interpretabilite (SHAP)","Expliquer chaque decision du modele."),
      ("Analyse unitaire & batch","Saisie manuelle ou import CSV / Excel."),
      ("Reponse temps reel","Prediction en moins de 100 ms."),
    ]
    grid_features(c, feats, cols=2, x=60, y=170, w=840, ch=86, gx=24, gy=20)
    footer(c, 4)

def grid_features(c, feats, cols, x, y, w, ch, gx, gy, icon=True):
    cw = (w - (cols-1)*gx) / cols
    for i,(t,d) in enumerate(feats):
        col = i % cols; row = i // cols
        cx = x + col*(cw+gx); cy = y + row*(ch+gy)
        c.round_rect(cx, cy, cw, ch, 12, fill=CARD, stroke=rgb("33335f"), lw=0.8)
        if icon:
            c.round_rect(cx+16, cy+ch/2-16, 32, 32, 8, fill=rgb("2a2204"))
            c.round_rect(cx+24, cy+ch/2-8, 16, 16, 4, fill=GOLD)
            tx = cx + 64
        else:
            tx = cx + 18
        c.text(tx, cy+30, t, 13.5, WHITE, bold=True)
        c.wrap(tx, cy+50, d, 11, MUTED, cw - (tx-cx) - 16, 14)

def slide_dataset(c):
    background(c); badge(c, "1 min")
    kicker(c, 60, 70, "Le jeu de donnees")
    heading(c, 60, 110, "Donnees utilisees")
    items = [
      "Source : \"Company Bankruptcy Prediction\" (Taiwan Economic Journal).",
      "96 colonnes de ratios financiers : ROA, ROE, liquidite, endettement, tresorerie...",
      "Cible : Bankrupt?  -  0 = sain, 1 = defaillant.",
      "Environ 6 800 observations initiales.",
    ]
    bullets(c, 60, 172, items, maxw=420)
    c.round_rect(60, 372, 460, 96, 12, fill=rgb("2a1414"), stroke=rgb("7a2e2e"), lw=1)
    c.text(78, 400, "Probleme majeur", 12, rgb("ff8e7a"), bold=True)
    c.wrap(78, 422, "Desequilibre extreme des classes : ~3 % de faillites contre 97 % d'entreprises saines.",
           12.5, INK, 424, 17)
    card(c, 560, 150, 340, 320, "Desequilibre des classes")
    chart_imbalance(c, 575, 185, 312, 265)
    footer(c, 5)

def slide_cleaning(c):
    background(c); badge(c, "1 min 30")
    kicker(c, 60, 70, "Pretraitement")
    heading(c, 60, 110, "Data Cleaning")
    items = [
      "Detection & suppression des doublons.",
      "Valeurs manquantes : imputation par la mediane (robuste aux outliers).",
      "Detection des outliers via IQR  -  capping aux percentiles 1 % et 99 %.",
      "Suppression des features a variance quasi-nulle (>95 % de valeurs identiques).",
      "Correlation : suppression des features avec correlation > 0.95 (multicolinearite).",
      "Normalisation des noms de colonnes.",
    ]
    bullets(c, 60, 168, items, size=12, gap=9, maxw=430, numbered=True, leading=14)
    card(c, 560, 150, 340, 180, "Reduction des features")
    chart_clean(c, 575, 185, 312, 110)
    c.text(716, 312, "96 features  ->  ~65 pertinentes", 10.5, GOLDSOFT, align="center")
    card(c, 560, 348, 340, 122, "Pipeline de nettoyage")
    c.wrap(578, 392, "Doublons -> Imputation -> IQR capping -> Variance -> Correlation -> Normalisation.",
           11.5, MUTED, 306, 16)
    footer(c, 6)

def slide_why_synth(c):
    background(c); badge(c, "1 min")
    kicker(c, 60, 70, "Le piege du desequilibre")
    heading(c, 60, 110, "Pourquoi generer des donnees synthetiques ?", 26)
    items = [
      "Avec ~3 % de cas positifs, le modele apprend a toujours predire \"sain\".",
      "Accuracy trompeuse : 97 % en predisant toujours 0  ->  inutile !",
      "Le recall sur la classe \"faillite\" est quasi nul sans reequilibrage.",
      "Solution : augmenter la classe minoritaire avec des donnees synthetiques realistes.",
    ]
    bullets(c, 60, 180, items, maxw=400)
    card(c, 540, 150, 360, 320, "Matrice de confusion  -  avant / apres")
    c.text(620, 198, "Sans reequilibrage", 10, MUTED, align="center")
    c.text(820, 198, "Apres reequilibrage", 10, MUTED, align="center")
    chart_confusion(c, 545, 210, 175, 240, [[97,0],[3,0]], ["0","1"])
    chart_confusion(c, 720, 210, 175, 240, [[88,9],[1,12]], ["0","1"])
    footer(c, 7)

def slide_smote(c):
    background(c); badge(c, "2 min")
    kicker(c, 60, 70, "Generation de donnees synthetiques")
    heading(c, 60, 110, "SMOTE  +  Bruit Gaussien")
    card(c, 60, 160, 420, 145, "1.  SMOTE  -  Synthetic Minority Over-sampling")
    c.wrap(78, 200, "Cree de nouveaux exemples en interpolant entre voisins proches (k-NN). Pour chaque exemple minoritaire, un point est genere sur le segment vers un voisin.",
           11.5, INK, 388, 16)
    c.round_rect(78, 258, 384, 32, 6, fill=rgb("0a1230"), stroke=rgb("3a3a66"), lw=0.8)
    c.text(90, 279, "x_new = x_i + lambda * (x_voisin - x_i)", 12.5, GOLDSOFT, bold=False)
    c.text(330, 279, "lambda in [0,1]", 9, MUTED)
    card(c, 60, 320, 420, 150, "2.  Ajout de bruit gaussien")
    c.wrap(78, 360, "Un leger bruit normal est ajoute a chaque feature pour eviter des donnees trop \"lisses\" et introduire une variabilite realiste, limitant le sur-apprentissage.",
           11.5, INK, 388, 16)
    c.round_rect(78, 422, 384, 32, 6, fill=rgb("0a1230"), stroke=rgb("3a3a66"), lw=0.8)
    c.text(90, 443, "x_final = x_smote + e", 12.5, GOLDSOFT)
    c.text(250, 443, "e ~ N(0, sigma^2), sigma = 0.01 * ecart-type", 9, MUTED)
    card(c, 520, 160, 380, 175, "Interpolation SMOTE")
    chart_smote(c, 535, 195, 350, 135)
    card(c, 520, 350, 380, 120, "Bruit gaussien  N(0, sigma^2)")
    chart_gauss(c, 535, 380, 350, 80)
    footer(c, 8)

def slide_classes(c):
    background(c); badge(c, "30 s")
    kicker(c, 60, 70, "Multi-classification")
    heading(c, 60, 110, "4 classes de risque")
    c.wrap(60, 165, "Le probleme binaire devient une echelle de risque, plus utile aux analystes qu'un simple oui / non.",
           14, MUTED, 820, 20)
    steps = [
      ("Faible","0 - 25 %","Entreprise financierement saine.", GREEN, NAVY900),
      ("Modere","25 - 50 %","Vigilance requise.", YELLOW, NAVY900),
      ("Eleve","50 - 75 %","Risque significatif, surveillance active.", ORANGE, NAVY900),
      ("Critique","75 - 100 %","Risque imminent de defaillance.", RED, WHITE),
    ]
    cw = 200; gap = 24; x0 = 60; y0 = 235; ch = 150
    for i,(name,pct,desc,col,txtc) in enumerate(steps):
        x = x0 + i*(cw+gap)
        c.round_rect(x, y0, cw, ch, 14, fill=col)
        c.text(x+18, y0+30, pct, 11, txtc, bold=True)
        c.text(x+18, y0+62, name, 20, txtc, bold=True)
        c.wrap(x+18, y0+88, desc, 11.5, txtc, cw-32, 15)
    chart_gradientbar(c, 60, 410, 870, 30)
    footer(c, 9)

def slide_bench(c):
    background(c); badge(c, "2 min")
    kicker(c, 60, 70, "Comparaison des modeles ML")
    heading(c, 60, 110, "Benchmark des modeles testes")
    # table
    rows = [
      ("Modele","Accuracy","F1","AUC-ROC","Entrainement", "head"),
      ("Regression Logistique","78 %","0.72","0.81","Tres rapide",""),
      ("Random Forest","89 %","0.86","0.92","Moyen",""),
      ("SVM (RBF)","82 %","0.78","0.85","Lent",""),
      ("KNN","80 %","0.75","0.83","Rapide",""),
      ("XGBoost  *","94 %","0.93","0.97","Moyen","best"),
      ("LightGBM","93 %","0.91","0.96","Rapide",""),
    ]
    tx, ty, tw = 60, 165, 470
    colx = [tx+14, tx+210, tx+285, tx+340, tx+400]
    rh = 38
    for i,(a,b,d,e,f,kind) in enumerate(rows):
        yy = ty + i*rh
        if kind=="head":
            c.round_rect(tx, yy, tw, rh, 6, fill=rgb("1a224f"))
        elif kind=="best":
            c.round_rect(tx, yy, tw, rh, 4, fill=rgb("2e2a0c"))
            c.rect(tx, yy, 3, rh, GOLD, True)
        col_main = GOLD if kind=="head" else (WHITE if kind=="best" else INK)
        bold = kind in ("head","best")
        c.text(colx[0], yy+rh/2+4, a, 11, col_main, bold=bold)
        for j,val in enumerate((b,d,e,f)):
            cc = GOLD if kind=="best" and j<3 else (GOLD if kind=="head" else (MUTED if not bold else WHITE))
            c.text(colx[j+1], yy+rh/2+4, val, 10.5, cc, bold=bold)
        if kind not in ("head",):
            c.line(tx, yy+rh, tx+tw, yy+rh, rgb("242c55"), 0.5)
    card(c, 560, 165, 340, 270, "F1-Score par modele")
    chart_bench(c, 575, 195, 312, 235)
    c.text(60, 455, "*  XGBoost domine sur toutes les metriques.", 12.5, GOLD, bold=True)
    footer(c, 10)

def slide_why_xgb(c):
    background(c); badge(c, "1 min 30")
    kicker(c, 60, 70, "Justification du choix")
    heading(c, 60, 110, "Pourquoi XGBoost ?")
    feats = [
      ("Performance superieure","Meilleur F1 & AUC-ROC."),
      ("Gestion du desequilibre","scale_pos_weight."),
      ("Regularisation L1 + L2","Evite le sur-apprentissage."),
      ("Robuste aux outliers","Arbres de decision."),
      ("Feature importance","Interpretabilite native."),
      ("Compatible Optuna","Tuning bayesien (30 essais)."),
      ("Inference rapide","< 100 ms par requete."),
      ("Ecosysteme mature","Standard de la finance."),
    ]
    grid_features(c, feats, cols=2, x=60, y=160, w=470, ch=64, gx=16, gy=12)
    card(c, 560, 160, 340, 130, "Gradient Boosting  -  arbres sequentiels")
    chart_boost(c, 575, 196, 312, 90)
    c.text(716, 292, "Chaque arbre corrige les erreurs du precedent.", 9.5, MUTED, align="center")
    card(c, 560, 305, 340, 165, "Pourquoi pas les autres ?")
    nb = [
      "Reg. logistique : pas de non-linearites.",
      "SVM : lent, peu interpretable.",
      "Random Forest : sans boosting sequentiel.",
      "Deep Learning : trop complexe, boite noire.",
    ]
    yy = 348
    for it in nb:
        c.text(578, yy, "-", 11, GOLD, bold=True)
        c.text(590, yy, it, 10.5, INK)
        yy += 27
    footer(c, 11)

def slide_optuna(c):
    background(c); badge(c, "1 min")
    kicker(c, 60, 70, "Optimisation des hyperparametres")
    heading(c, 60, 110, "Tuning avec Optuna")
    items = [
      "Optimisation bayesienne  -  plus intelligente que Grid Search.",
      "30 essais d'optimisation automatique.",
      "Validation croisee stratifiee (5-fold) pour chaque configuration.",
    ]
    bullets(c, 60, 175, items, maxw=420)
    card(c, 60, 300, 460, 170, "Hyperparametres optimises")
    params = ["max_depth","learning_rate","n_estimators","subsample","colsample_bytree","reg_alpha","reg_lambda"]
    px = 80; py = 345
    for p in params:
        w = text_width(p, 10.5, False) + 24
        if px + w > 510:
            px = 80; py += 38
        c.round_rect(px, py, w, 28, 14, fill=rgb("11193f"), stroke=rgb("3a3a66"), lw=0.8)
        c.text(px + w/2, py+18, p, 10.5, INK, align="center")
        px += w + 12
    card(c, 560, 160, 340, 310, "Convergence des essais Optuna")
    chart_optuna(c, 575, 195, 312, 260)
    footer(c, 12)

def slide_architecture(c):
    background(c); badge(c, "1 min 30")
    kicker(c, 60, 70, "Architecture technique")
    heading(c, 60, 110, "Architecture de la plateforme")
    tiers = [
      ("Frontend","HTML / CSS / JS pur",
       ["Interface responsive","Dashboard KPIs & graphiques","Tableau d'historique","Mode demo (15 entreprises MA)"]),
      ("Backend","FastAPI - Python",
       ["API RESTful - 8 endpoints","Validation Pydantic","Generation de rapports PDF","Base SQLite (historique)"]),
      ("ML Pipeline","XGBoost - joblib",
       ["Preprocessing -> Feature selection","XGBoost -> SHAP","Modele serialise (joblib)","Prediction multi-classes + proba"]),
    ]
    y0 = 165; th = 86; gap_arrow = 22
    for i,(name,sub,tags) in enumerate(tiers):
        yy = y0 + i*(th+gap_arrow)
        c.round_rect(60, yy, 840, th, 12, fill=CARD, stroke=rgb("33335f"), lw=0.8)
        c.rect(60, yy, 4, th, GOLD, True)
        c.text(82, yy+34, name, 15, GOLD, bold=True)
        c.text(82, yy+56, sub, 10, MUTED)
        # tags
        tx = 280
        for t in tags:
            w = text_width(t, 10, False) + 22
            c.round_rect(tx, yy+th/2-14, w, 28, 14, fill=rgb("11193f"), stroke=rgb("33335f"), lw=0.7)
            c.text(tx + w/2, yy+th/2+4, t, 10, INK, align="center")
            tx += w + 12
            if tx > 860:
                tx = 280
        if i < 2:
            ay = yy + th + gap_arrow/2
            c.text(140, ay+4, "REST / JSON" if i==0 else "appel modele", 9, MUTED, align="center")
            c.polygon([(110,ay-2),(116,ay+4),(104,ay+4)], GOLD)
            c.polygon([(110,ay+6),(116,ay),(104,ay)], GOLD)
    footer(c, 13)

def slide_features(c):
    background(c); badge(c, "1 min")
    kicker(c, 60, 70, "Fonctionnalites cles")
    heading(c, 60, 110, "Fonctionnalites")
    feats = [
      ("Analyse unitaire","Saisie manuelle des ratios financiers."),
      ("Analyse batch","Upload CSV / Excel multi-entreprises."),
      ("Dashboard","Distribution des risques & tendances."),
      ("Historique","Analyses filtrables et paginees."),
      ("Export PDF","Rapport detaille + recommandations."),
      ("Interpretabilite","SHAP values par prediction."),
    ]
    grid_features(c, feats, cols=3, x=60, y=165, w=840, ch=96, gx=20, gy=18)
    c.round_rect(60, 400, 840, 64, 12, fill=rgb("2a2204"), stroke=GOLDDEEP, lw=0.8)
    c.text(PW/2, 438, "Temps reel  -  reponse en moins de 100 ms par requete.", 14, GOLDSOFT, bold=True, align="center")
    footer(c, 14)

def slide_demo(c):
    background(c)
    # centered
    c.circle(PW/2, 130, 34, fill=rgb("2a2204"), stroke=GOLD, lw=1.5)
    c.polyline([(PW/2-10,116),(PW/2-10,144),(PW/2+16,130)], GOLD, 4)
    kicker_centered(c, PW/2, 188, "DEMONSTRATION EN DIRECT")
    c.text(PW/2, 230, "Place a la demo", 34, WHITE, bold=True, align="center")
    feats = [
      ("Scenario 1","Entreprise a risque faible."),
      ("Scenario 2","Entreprise a risque critique."),
      ("Scenario 3","Upload batch d'un fichier CSV."),
      ("Rapport PDF","Generation & export du rapport."),
    ]
    grid_features(c, feats, cols=2, x=180, y=265, w=600, ch=64, gx=20, gy=16, icon=True)
    c.round_rect(180, 420, 600, 56, 10, fill=rgb("2a2204"), stroke=GOLDDEEP, lw=0.8)
    c.rect(180, 420, 4, 56, GOLD, True)
    c.wrap(200, 446, "Note au presentateur : preparer le backend lance (uvicorn main:app --port 8000) + le fichier test_batch.csv.",
           11, INK, 560, 16)
    footer(c, 15)

def slide_results(c):
    background(c); badge(c, "1 min")
    kicker(c, 60, 70, "Resultats du modele final")
    heading(c, 60, 110, "Resultats & Metriques")
    stats = [("94 %","Accuracy globale"),("0.93","F1-Score macro"),("0.97","AUC-ROC")]
    sw = 270; gap = 15
    for i,(num,lbl) in enumerate(stats):
        x = 60 + i*(sw+gap)
        c.round_rect(x, 158, sw, 78, 12, fill=rgb("1a1f3f"), stroke=GOLDDEEP, lw=0.8)
        c.text(x+sw/2, 200, num, 30, GOLD, bold=True, align="center")
        c.text(x+sw/2, 224, lbl, 10.5, MUTED, align="center")
    card(c, 60, 256, 270, 214, "Matrice de confusion")
    chart_confusion(c, 70, 292, 250, 175, [[1577,43],[33,311]], ["Sain","Faill."])
    card(c, 345, 256, 250, 214, "Courbe ROC")
    chart_roc(c, 360, 292, 220, 175)
    card(c, 610, 256, 290, 214, "Top 5 features importantes")
    chart_feat(c, 622, 292, 278, 175)
    footer(c, 16)

def slide_conclusion(c):
    background(c); badge(c, "30 s")
    kicker(c, 60, 70, "Bilan")
    heading(c, 60, 110, "Conclusion")
    items = [
      "Pipeline ML complet de bout en bout.",
      "Resolution du desequilibre via SMOTE + bruit gaussien.",
      "XGBoost : choix justifie par les performances et l'interpretabilite.",
      "Plateforme web fonctionnelle et intuitive.",
      "Applicable au contexte bancaire marocain.",
    ]
    yy = 185
    for it in items:
        # check mark
        c.circle(74, yy-4, 12, fill=rgb("0e3a22"), stroke=GREEN, lw=1.2)
        c.polyline([(68,yy-4),(72,yy),(80,yy-9)], GREEN, 2.5)
        c.text(98, yy, it, 15, INK)
        yy += 52
    footer(c, 17)

def slide_perspectives(c):
    background(c); badge(c, "30 s")
    kicker(c, 60, 70, "Et apres ?")
    heading(c, 60, 110, "Perspectives & Ameliorations")
    feats = [
      ("Donnees reelles marocaines","Bank Al-Maghrib, OMPIC."),
      ("Donnees textuelles (NLP)","Rapports d'audit analyses."),
      ("Deploiement cloud","AWS / Azure en production."),
      ("Monitoring du modele","Detection de drift."),
      ("Extension PME / TPE","Features adaptees."),
      ("API publique","Integration tierce (SaaS)."),
    ]
    grid_features(c, feats, cols=2, x=60, y=165, w=840, ch=90, gx=24, gy=18)
    footer(c, 18)

def slide_thanks(c):
    background(c, decor=False)
    cx, cy = PW/2, 150
    c.polygon([(cx,cy-40),(cx+36,cy-26),(cx+36,cy+10),(cx,cy+38),(cx-36,cy+10),(cx-36,cy-26)], GOLD)
    c.polyline([(cx-15,cy-2),(cx-3,cy+10),(cx+19,cy-14)], NAVY900, 5)
    c.text(PW/2, 230, "Merci pour votre attention", 38, WHITE, bold=True, align="center")
    c.text(PW/2, 272, "Questions ?", 22, GOLD, bold=True, align="center")
    meta = [("Etudiant(s)","[ A completer ]"),("Contact","[ email ]"),("GitHub","achrafbaaiz/riskguard-pro")]
    for i,(t,v) in enumerate(meta):
        x = PW/2 - 280 + i*280
        c.text(x, 318, t, 10, WHITE, bold=True, align="center")
        c.text(x, 336, v, 11, GOLDSOFT, align="center")
    chart_qr(c, PW/2, 420, 92)
    c.text(PW/2, 486, "QR -> depot GitHub du projet", 9, MUTED, align="center")
    footer(c, 19)

SLIDES = [
    slide_cover, slide_toc, slide_context, slide_objectives, slide_dataset,
    slide_cleaning, slide_why_synth, slide_smote, slide_classes, slide_bench,
    slide_why_xgb, slide_optuna, slide_architecture, slide_features, slide_demo,
    slide_results, slide_conclusion, slide_perspectives, slide_thanks,
]

# ----------------------------------------------------------------------------
# PDF assembly
# ----------------------------------------------------------------------------
def build(path):
    objects = []      # list of bytes (object body without "N 0 obj")
    def add(body):
        objects.append(body)
        return len(objects)   # 1-based object number

    # Reserve: 1=Catalog, 2=Pages ; fonts ; then pages+contents
    catalog_num = 1
    pages_num = 2
    objects.append(b"")  # placeholder 1
    objects.append(b"")  # placeholder 2

    # Fonts
    f1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    f2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    page_obj_nums = []
    for fn in SLIDES:
        c = Canvas()
        fn(c)
        content = c.stream().encode("latin-1", "replace")
        comp = zlib.compress(content, 9)
        stream_obj = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(comp) + comp + b"\nendstream")
        page_body = (b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] "
                     b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> "
                     b"/Contents %d 0 R >>" % (pages_num, int(PW), int(PH), f1, f2, stream_obj))
        pnum = add(page_body)
        page_obj_nums.append(pnum)

    kids = b" ".join(b"%d 0 R" % n for n in page_obj_nums)
    objects[pages_num-1] = (b"<< /Type /Pages /Count %d /Kids [%s] >>" % (len(page_obj_nums), kids))
    objects[catalog_num-1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_num

    # Serialize
    out = bytearray()
    out += b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]*(len(objects)+1)
    for i, body in enumerate(objects, start=1):
        offsets[i] = len(out)
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects)+1)
    out += b"0000000000 65535 f \n"
    for i in range(1, len(objects)+1):
        out += b"%010d 00000 n \n" % offsets[i]
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\n" % (len(objects)+1, catalog_num)
    out += b"startxref\n%d\n%%%%EOF\n" % xref_pos

    with open(path, "wb") as f:
        f.write(out)
    return len(out)

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "RiskGuard_Pro_Presentation.pdf")
    size = build(out)
    print("PDF genere: %s (%d octets, %d slides)" % (out, size, len(SLIDES)))
