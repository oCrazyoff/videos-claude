#!/usr/bin/env python3
"""Baixa só um trecho de um VOD da Twitch, na qualidade escolhida, sem baixar a live inteira.

Uso: baixar_trecho.py URL_DO_VOD INICIO FIM SAIDA.mp4 [--qualidade 1080p60] [--cache DIR]
     INICIO/FIM em segundos ou h:mm:ss.

Pega a playlist m3u8 com yt-dlp, baixa (com curl, que respeita o proxy) apenas os pedaços .ts
que cobrem o trecho, junta e corta no quadro exato com ffmpeg.
"""
import argparse, os, subprocess, tempfile, urllib.parse


def seg(s):
    t = 0.0
    for p in str(s).split(":"):
        t = t * 60 + float(p)
    return t


def playlist(url, q, cache):
    os.makedirs(cache, exist_ok=True)
    pl = os.path.join(cache, f"{q}.m3u8")
    if not os.path.exists(pl):
        u = subprocess.run(["yt-dlp", "-f", q, "-g", url], capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run(["curl", "-sSf", "-o", pl, u], check=True)
        open(pl + ".base", "w").write(u.rsplit("/", 1)[0] + "/")
    base = open(pl + ".base").read()
    pedacos, t, dur = [], 0.0, None
    for linha in open(pl):
        linha = linha.strip()
        if linha.startswith("#EXTINF:"):
            dur = float(linha[8:].split(",")[0])
        elif linha and not linha.startswith("#"):
            pedacos.append((t, dur, urllib.parse.urljoin(base, linha)))
            t += dur
    return pedacos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("inicio"); ap.add_argument("fim"); ap.add_argument("saida")
    ap.add_argument("--qualidade", default="1080p60")
    ap.add_argument("--cache", default=os.path.expanduser("~/.cache/baixar_trecho"))
    a = ap.parse_args()
    ini, fim = seg(a.inicio), seg(a.fim)
    cache = os.path.join(a.cache, a.url.rstrip("/").split("/")[-1])
    sel = [p for p in playlist(a.url, a.qualidade, cache) if p[0] + p[1] > ini and p[0] < fim]
    if not sel:
        raise SystemExit("trecho fora do VOD")
    with tempfile.TemporaryDirectory() as tmp:
        arqs = []
        for i, (t, d, u) in enumerate(sel):
            f = os.path.join(tmp, f"{i:05d}.ts")
            for tentativa in range(4):
                if subprocess.run(["curl", "-sSf", "--retry", "3", "-o", f, u]).returncode == 0:
                    break
            else:
                raise SystemExit(f"falha ao baixar {u}")
            arqs.append(f)
        juntos = os.path.join(tmp, "juntos.ts")
        with open(juntos, "wb") as out:
            for f in arqs:
                out.write(open(f, "rb").read())
        off = ini - sel[0][0]
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{off:.3f}", "-i", juntos, "-t", f"{fim - ini:.3f}",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k", a.saida], check=True)


if __name__ == "__main__":
    main()
