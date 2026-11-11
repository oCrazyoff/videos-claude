#!/usr/bin/env python3
"""Gera os grafismos do estilo CLIPSTATION (vinheta, tela final, flash) como .mp4 com áudio.

Uso: grafismos.py {stinger|outro|flash} SAIDA.mp4 [--dur S] [--w 1920] [--h 1080] [--fps 30] [--marca CLIPSTATION]
"""
import argparse, math, random, subprocess
from PIL import Image, ImageDraw, ImageFont

BG = (11, 18, 32)
LARANJA, AMARELO = (255, 140, 20), (255, 200, 40)
FONTE = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"


def fonte(px):
    return ImageFont.truetype(FONTE, int(px))


def texto_inclinado(txt, px, skew=0.22, cor=(255, 255, 255)):
    """Texto em caixa-alta com itálico 'falso' (shear), como a fonte display do original."""
    f = fonte(px)
    l, t, r, b = f.getbbox(txt)
    w, h = r - l + int(px * skew) + 10, b - t + 10
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((5 - l + int(px * skew), 5 - t), txt, font=f, fill=cor)
    return im.transform(im.size, Image.AFFINE, (1, skew, -skew * h * 0.0, 0, 1, 0), Image.BICUBIC)


class Poeira:
    """Partículas de poeira + riscos verticais de filme velho sobre o fundo azul-marinho."""

    def __init__(self, W, H, seed=7):
        r = random.Random(seed)
        self.W, self.H, self.r = W, H, r
        self.p = [(r.random() * W, r.random() * H, r.uniform(0.5, 2.2), r.uniform(-8, 8), r.uniform(4, 25))
                  for _ in range(int(W * H / 9000))]

    def frame(self, t, n):
        im = Image.new("RGB", (self.W, self.H), BG)
        d = ImageDraw.Draw(im)
        s = self.W / 1920
        for x, y, rad, vx, vy in self.p:
            px, py = (x + vx * t * 10) % self.W, (y + vy * t * 10) % self.H
            a = 120 + int(100 * math.sin(n * 0.7 + x))
            d.ellipse([px - rad * s, py - rad * s, px + rad * s, py + rad * s], fill=(a, a, a + 10))
        r = random.Random(n // 3)  # riscos mudam a cada 3 quadros
        for _ in range(r.choice([0, 0, 1, 1, 2])):
            x = r.random() * self.W
            y0 = r.random() * self.H * 0.5
            d.line([(x, y0), (x + r.uniform(-6, 6), y0 + r.uniform(0.3, 1) * self.H)], fill=(170, 175, 185), width=max(1, int(2 * s)))
        return im


def ease_out(x):
    x = min(max(x, 0), 1)
    return 1 - (1 - x) ** 3


def rastros(d, x0, y, comp, esp, n=4, ang=-6):
    """Linhas paralelas de velocidade (speed lines) atrás de um elemento que entra."""
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    for i in range(n):
        yy = y + i * esp * 2.2
        d.line([(x0, yy), (x0 + comp * c, yy + comp * s)], fill=(255, 255, 255), width=int(esp))


def stinger(W, H, fps, dur, marca):
    po = Poeira(W, H)
    base = texto_inclinado(marca, H * 0.15)
    base = base.rotate(6, resample=Image.BICUBIC, expand=True)  # sobe para a direita, como no original
    tot = int(dur * fps)
    for n in range(tot):
        t = n / fps
        if n < 2:  # quadro preto antes de entrar
            yield Image.new("RGB", (W, H), (0, 0, 0)); continue
        im = po.frame(t, n)
        d = ImageDraw.Draw(im)
        k = ease_out((t - 0.07) / 0.7)
        cx = int(W * 0.08 + (1 - k) * W * 0.9)
        cy = int(H * 0.42 - base.height / 2)
        # revelação da esquerda para a direita + rastros na borda que entra
        vis = int(base.width * min(1, k * 1.15))
        if vis > 0:
            im.paste(base.crop((0, 0, vis, base.height)), (cx, cy), base.crop((0, 0, vis, base.height)))
        if k < 0.98:
            rastros(d, cx + vis - 10, cy + base.height * 0.35, W * 0.55 * (1 - k) + 40, H * 0.012, n=3, ang=-6)
        # leve "respiração" depois de parado
        if t > dur - 4 / fps:  # flash branco de saída (estrobo de 4 quadros)
            im = Image.blend(im, Image.new("RGB", (W, H), (255, 255, 255)), [0.95, 0.6, 0.95, 0.65][(tot - n - 1) % 4])
        yield im


def mascote(W, H, t):
    """Mascote original: robozinho laranja com visor e antena, acenando."""
    s = H / 1080
    im = Image.new("RGBA", (int(420 * s), int(460 * s)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bob = math.sin(t * 4) * 8 * s
    cx = im.width / 2
    # antena
    d.line([(cx, 70 * s + bob), (cx + 10 * s, 20 * s + bob)], fill=(230, 230, 240), width=int(8 * s))
    d.ellipse([cx - 5 * s, 5 * s + bob, cx + 25 * s, 35 * s + bob], fill=AMARELO)
    # corpo (cápsula)
    d.rounded_rectangle([cx - 120 * s, 70 * s + bob, cx + 120 * s, 440 * s], radius=int(115 * s), fill=LARANJA, outline=(30, 20, 10), width=int(8 * s))
    # visor
    d.rounded_rectangle([cx - 90 * s, 130 * s + bob, cx + 90 * s, 230 * s + bob], radius=int(45 * s), fill=(20, 28, 45))
    blink = (t % 2.6) < 0.12
    for ex in (-40, 40):
        if blink:
            d.line([(cx + (ex - 18) * s, 180 * s + bob), (cx + (ex + 18) * s, 180 * s + bob)], fill=(90, 240, 255), width=int(7 * s))
        else:
            d.ellipse([cx + (ex - 18) * s, 160 * s + bob, cx + (ex + 18) * s, 200 * s + bob], fill=(90, 240, 255))
    # sorriso
    d.arc([cx - 50 * s, 250 * s + bob, cx + 50 * s, 320 * s + bob], 20, 160, fill=(30, 20, 10), width=int(9 * s))
    # braço acenando
    ang = math.radians(-60 + 25 * math.sin(t * 7))
    ox, oy = cx + 110 * s, 280 * s + bob
    d.line([(ox, oy), (ox + math.cos(ang) * 110 * s, oy + math.sin(ang) * 110 * s)], fill=(30, 20, 10), width=int(30 * s))
    d.line([(ox, oy), (ox + math.cos(ang) * 110 * s, oy + math.sin(ang) * 110 * s)], fill=LARANJA, width=int(20 * s))
    return im


def anel_texto(raio, txt, ang0, px):
    f = fonte(px)
    lado = int(raio * 2 + px * 3)
    im = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    passo = 360 / len(txt)
    for i, ch in enumerate(txt):
        a = ang0 + i * passo
        l = Image.new("RGBA", (px * 2, px * 2), (0, 0, 0, 0))
        ImageDraw.Draw(l).text((px, px), ch, font=f, fill="white", anchor="mm")
        l = l.rotate(-a, resample=Image.BICUBIC)
        x = lado / 2 + raio * math.sin(math.radians(a)) - px
        y = lado / 2 - raio * math.cos(math.radians(a)) - px
        im.alpha_composite(l, (int(x), int(y)))
    return im


def outro(W, H, fps, dur, marca):
    po = Poeira(W, H, seed=3)
    titulo = texto_inclinado("MAIS VÍDEOS", H * 0.065)
    for n in range(int(dur * fps)):
        t = n / fps
        im = po.frame(t, n).convert("RGBA")
        d = ImageDraw.Draw(im)
        # "MAIS VÍDEOS" entra com wipe + rastros
        k = ease_out(t / 0.6)
        tx, ty = int(W * 0.66), int(H * 0.08)
        vis = int(titulo.width * k)
        if vis:
            im.alpha_composite(titulo.crop((0, 0, vis, titulo.height)), (tx, ty))
        if k < 0.98:
            rastros(d, tx + vis, ty + titulo.height * 0.3, W * 0.25 * (1 - k) + 20, H * 0.008, n=3, ang=0)
        # anel giratório "SE INSCREVA"
        anel = anel_texto(H * 0.11, "SE INSCREVA • SE INSCREVA • ", t * 40, int(H * 0.032))
        esc = ease_out((t - 0.2) / 0.5)
        if esc > 0:
            a2 = anel.resize((max(1, int(anel.width * esc)), max(1, int(anel.height * esc))))
            im.alpha_composite(a2, (int(W * 0.17 - a2.width / 2), int(H * 0.42 - a2.height / 2)))
        # mascote sobe do canto inferior esquerdo
        m = mascote(W, H, t)
        sobe = ease_out((t - 0.3) / 0.6)
        im.alpha_composite(m, (int(W * 0.02), int(H - m.height * 0.82 * sobe + m.height * 0.0)) if sobe > 0 else (0, H))
        # barra de progresso laranja->amarelo no rodapé
        bh = int(H * 0.018)
        prog = int(W * t / dur)
        if prog:
            barra = Image.linear_gradient("L").rotate(90).resize((max(prog, 1), bh))
            cor = Image.composite(Image.new("RGBA", barra.size, AMARELO + (255,)), Image.new("RGBA", barra.size, LARANJA + (255,)), barra)
            im.alpha_composite(cor, (0, H - bh))
        yield im.convert("RGB")


def flash(W, H, fps, dur, marca):
    for v in [255, 175, 255, 190]:
        yield Image.new("RGB", (W, H), (v, v, v))


def audio(tipo, dur):
    """Efeitos sintéticos: whoosh + impacto na vinheta, estalo no flash, silêncio no outro."""
    if tipo == "stinger":
        return (["-f", "lavfi", "-i", f"anoisesrc=d={dur}:c=pink:a=0.6,highpass=f=300,lowpass=f=5000,"
                 "afade=t=in:d=0.25,afade=t=out:st=0.3:d=0.6,volume=0.8[a];"
                 f"sine=f=55:d={dur},afade=t=in:st=0.55:d=0.02,afade=t=out:st=0.6:d=0.8,adelay=0|0,volume=1.5[b];"
                 "[a][b]amix=inputs=2:normalize=0,aformat=channel_layouts=stereo"])
    if tipo == "flash":
        return ["-f", "lavfi", "-i", f"anoisesrc=d={dur}:c=white:a=0.5,highpass=f=2000,afade=t=out:d={dur},aformat=channel_layouts=stereo"]
    return ["-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo:d={dur}"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tipo", choices=["stinger", "outro", "flash"])
    ap.add_argument("saida")
    ap.add_argument("--dur", type=float)
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--marca", default="CLIPSTATION")
    a = ap.parse_args()
    dur = a.dur or {"stinger": 5.1, "outro": 13.0, "flash": 4 / a.fps}[a.tipo]
    if a.tipo == "flash":
        dur = 4 / a.fps
    gen = {"stinger": stinger, "outro": outro, "flash": flash}[a.tipo](a.w, a.h, a.fps, dur, a.marca)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{a.w}x{a.h}", "-r", str(a.fps), "-i", "-",
           *audio(a.tipo, dur), "-t", f"{dur:.4f}", "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", a.saida]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fr in gen:
        p.stdin.write(fr.tobytes())
    p.stdin.close()
    if p.wait():
        raise SystemExit("ffmpeg falhou")


if __name__ == "__main__":
    main()
