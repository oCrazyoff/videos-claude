#!/usr/bin/env python3
"""Seleção de momentos do VOD 2924195555 ("duas live seguidas?") e geração do roteiro.

Uso: selecao.py PASTA_DOS_TRECHOS   -> baixa os trechos (1080p60) e escreve roteiro.txt
Tempos em segundos do VOD, escolhidos a partir de picos de áudio + transcrição (Whisper small).
"""
import os, subprocess, sys

VOD = "https://www.twitch.tv/videos/2924195555"
CAM = "440:282:25:63"  # janela da webcam no layout 1080p da live

# Cada bloco é uma lista de clipes: (inicio, fim, [zooms na cam (ini, fim)], nome_da_tag)
BLOCOS = [
    # cold open: a reação do PvP (tem ação na tela; a lava fica de fora porque a tela estava pausada)
    [(12462, 12478, [(12463, 12468)], None)],
    "stinger",
    # abertura da live
    [(226, 243, [], "oCRAZYOFF")],
    "flash",
    # negócios de elitra
    [(5176, 5230, [], None),
     (9497, 9537, [(9528, 9536)], None),
     (10700, 10732, [], None),
     (13060, 13102, [], None)],
    "flash",
    # perigos
    [(10565, 10628, [], None),
     (11770, 11792, [(11773, 11777)], None)],
    "flash",
    # o inglês
    [(7945, 7988, [(7958, 7963)], None),
     (9626, 9656, [], None),
     (10266, 10290, [], None)],
    "flash",
    # pvp
    [(12282, 12320, [], None),
     (12440, 12510, [(12463, 12469), (12485, 12490)], None),
     (12862, 12896, [], None)],
    "flash",
    # aleatoriedades
    [(12125, 12150, [], None),
     (14648, 14710, [(14680, 14685)], None)],
    "outro",
]


def main():
    pasta = sys.argv[1]
    os.makedirs(pasta, exist_ok=True)
    aqui = os.path.dirname(os.path.abspath(__file__))
    baixar = os.path.join(aqui, "..", "..", "scripts", "baixar_trecho.py")
    linhas = ["# gerado por selecao.py — tipo | arquivo | inicio | fim | extra"]
    for b in BLOCOS:
        if isinstance(b, str):
            linhas.append({"stinger": "stinger | | | | dur=4", "flash": "flash | | | |", "outro": "outro | | | | dur=12"}[b])
            continue
        for ini, fim, zooms, nome in b:
            arq = os.path.join(pasta, f"vod_{ini}_{fim}.mp4")
            if not os.path.exists(arq):
                subprocess.run([sys.executable, baixar, VOD, str(ini), str(fim), arq,
                                "--cache", os.path.join(pasta, "cache")], check=True)
            # quebra o clipe em gameplay / cam / gameplay (tempos relativos ao arquivo baixado)
            t = ini
            primeiro = True
            for zi, zf in zooms:
                if zi > t:
                    linhas.append(f"clip | {arq} | {t - ini} | {zi - ini} |" + (f" nome={nome}" if nome and primeiro else ""))
                    primeiro = False
                linhas.append(f"cam | {arq} | {zi - ini} | {zf - ini} | crop={CAM}")
                t = zf
            if fim > t:
                linhas.append(f"clip | {arq} | {t - ini} | {fim - ini} |" + (f" nome={nome}" if nome and primeiro else ""))
    open(os.path.join(pasta, "roteiro.txt"), "w").write("\n".join(linhas) + "\n")
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
