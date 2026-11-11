#!/usr/bin/env bash
# Monta um vídeo no estilo "CLIPSTATION" (ver analise/DESMONTE_EDICAO.md) a partir de um roteiro.
#
# Uso: scripts/montar_clipstation.sh roteiro.txt saida.mp4
#
# Formato do roteiro (uma linha por segmento, campos separados por "|", "#" = comentário):
#   clip    | arquivo | inicio | fim | nome=NOME            -> gameplay em tela cheia (+ tag de nome opcional)
#   cam     | arquivo | inicio | fim | crop=w:h:x:y         -> webcam em tela cheia com zoom 100%->120%
#   stinger |         |        |     | dur=5.1              -> vinheta animada "CLIPSTATION" (gerada por grafismos.py)
#   flash   |         |        |     |                      -> estrobo branco de 4 quadros (transição entre blocos)
#   outro   |         |        |     | dur=13               -> tela final "MAIS VÍDEOS / SE INSCREVA" com mascote
# O crop do "cam" é em pixels do vídeo ORIGINAL (ex.: cam 480x270 no canto sup. dir. de um 1080p
# = crop=480:270:1440:0).
#
# Variáveis opcionais: MARCA (texto da marca d'água, padrão "CLIP STATION"; MARCA="" desliga),
#                      TEXTO_VINHETA (padrão "CLIPSTATION"), FONTE (.ttf/.otf), W/H/FPS (padrão 1920x1080 @ 30).
set -euo pipefail

ROTEIRO=${1:?roteiro}
SAIDA=${2:?saida.mp4}
MARCA=${MARCA-CLIP STATION}
FONTE=${FONTE:-/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf}
W=${W:-1920}; H=${H:-1080}; FPS=${FPS:-30}
DIR=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

# Codificação comum a todos os segmentos (precisa ser idêntica para o concat sem recodificar)
ENC=(-c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -r $FPS
     -c:a aac -b:a 192k -ar 48000 -ac 2)

# Tag de nome: pílula preta no canto inf. esq., entra deslizando em ~0,2 s, fica 3 s
tag_nome() { # $1 = nome
  local n=$1
  echo "drawbox=x='if(lt(t,0.2),-500+2500*t,0)+40':y=ih-150:w=$(( ${#n} * 42 + 60 )):h=90:color=black@0.85:t=fill:enable='lt(t,3.2)',
drawtext=fontfile=$FONTE:text='$n':fontsize=64:fontcolor=white:x='if(lt(t,0.2),-500+2500*t,0)+70':y=h-135:enable='lt(t,3.2)'"
}

# "1:05", "0:01:05" ou "65" -> segundos
segundos() { awk -F: '{t=0; for(i=1;i<=NF;i++) t=t*60+$i; print t}' <<< "$1"; }

i=0; LISTA="$TMP/lista.txt"; : > "$LISTA"
while IFS="|" read -r -u 3 tipo arq ini fim extra; do
  tipo=$(echo "$tipo" | xargs); [[ -z "$tipo" || "$tipo" == \#* ]] && continue
  arq=$(echo "$arq" | xargs); ini=$(echo "$ini" | xargs); fim=$(echo "$fim" | xargs); extra=$(echo "$extra" | xargs)
  seg="$TMP/seg_$(printf %04d $i).mp4"; i=$((i+1))
  base="scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=$FPS"
  case "$tipo" in
    clip)
      vf="$base"
      [[ "$extra" == nome=* ]] && vf="$vf,$(tag_nome "${extra#nome=}")"
      ffmpeg -v error -y -ss "$ini" -to "$fim" -i "$arq" -vf "$vf" "${ENC[@]}" "$seg" ;;
    cam)
      crop=${extra#crop=}
      quadros=$(awk -v f="$(segundos "$fim")" -v s="$(segundos "$ini")" -v r=$FPS 'BEGIN{print int((f-s)*r)}')
      # crop da webcam -> tela cheia -> zoom contínuo de 100% a 120% centralizado
      vf="crop=$crop,scale=${W}:${H},setsar=1,fps=$FPS,zoompan=z='1+0.2*on/$quadros':d=1:s=${W}x${H}:fps=$FPS:x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"
      ffmpeg -v error -y -ss "$ini" -to "$fim" -i "$arq" -vf "$vf" "${ENC[@]}" "$seg" ;;
    stinger|outro|flash)
      args=(--w $W --h $H --fps $FPS --marca "${TEXTO_VINHETA:-CLIPSTATION}")
      [[ "$extra" == dur=* ]] && args+=(--dur "${extra#dur=}")
      python3 "$DIR/grafismos.py" "$tipo" "$seg" "${args[@]}" ;;
    *) echo "tipo desconhecido: $tipo" >&2; exit 1 ;;
  esac
  echo "file '$seg'" >> "$LISTA"
done 3< "$ROTEIRO"

# Junta tudo, aplica marca d'água fixa (sup. dir., 50%) e normaliza o áudio em -14 LUFS
VF_MARCA="null"
[[ -n "$MARCA" ]] && VF_MARCA="drawtext=fontfile=$FONTE:text='$MARCA':fontsize=$((H/20)):fontcolor=white@0.5:borderw=3:bordercolor=black@0.4:x=w-tw-$((W/48)):y=$((H/27))"
ffmpeg -v error -y -f concat -safe 0 -i "$LISTA" \
  -vf "$VF_MARCA" \
  -af "loudnorm=I=-14:TP=-1:LRA=11" "${ENC[@]}" -movflags +faststart "$SAIDA"
echo "OK -> $SAIDA"
