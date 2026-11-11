#!/usr/bin/env bash
# Monta um vídeo no estilo "CLIPSTATION" (ver analise/DESMONTE_EDICAO.md) a partir de um roteiro.
#
# Uso: scripts/montar_clipstation.sh roteiro.txt saida.mp4
#
# Formato do roteiro (uma linha por segmento, campos separados por "|", "#" = comentário):
#   clip    | arquivo | inicio | fim | nome=NOME            -> gameplay em tela cheia (+ tag de nome opcional)
#   cam     | arquivo | inicio | fim | crop=w:h:x:y         -> webcam em tela cheia com zoom 100%->120%
#   stinger |         |        |     |                      -> vinheta "CLIPSTATION" (0,8 s)
#   outro   |         |        |     | dur=13               -> tela final "MAIS VÍDEOS / SE INSCREVA"
# O crop do "cam" é em pixels do vídeo ORIGINAL (ex.: cam 480x270 no canto sup. dir. de um 1080p
# = crop=480:270:1440:0).
#
# Variáveis opcionais: MARCA (texto da marca d'água, padrão "CLIP STATION"), FONTE (arquivo .ttf/.otf).
set -euo pipefail

ROTEIRO=${1:?roteiro}
SAIDA=${2:?saida.mp4}
MARCA=${MARCA:-CLIP STATION}
FONTE=${FONTE:-/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf}
W=1920; H=1080; FPS=30
BG=0x0b1220
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

# Codificação comum a todos os segmentos (precisa ser idêntica para o concat sem recodificar)
ENC=(-c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -r $FPS
     -c:a aac -b:a 192k -ar 48000 -ac 2)
SILENCIO=(-f lavfi -i "anullsrc=r=48000:cl=stereo")

# Fundo animado do stinger/outro: azul-marinho + poeira + riscos verticais de filme velho
fundo() { # $1 = duração
  echo "color=c=$BG:s=${W}x${H}:r=$FPS:d=$1,noise=alls=12:allf=t,
drawbox=x='mod(t*4110,${W})':y=0:w=2:h=ih:color=white@0.35:t=fill:enable='lt(mod(n,7),2)'"
}

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
    stinger)
      ffmpeg -v error -y -f lavfi -i "$(fundo 0.8)" "${SILENCIO[@]}" -t 0.8 \
        -vf "drawtext=fontfile=$FONTE:text='CLIPSTATION':fontsize=170:fontcolor=white:x=(w-tw)/2:y=(h-th)/2,rotate=-3*PI/180:c=$BG" \
        "${ENC[@]}" -shortest "$seg" ;;
    outro)
      d=13; [[ "$extra" == dur=* ]] && d=${extra#dur=}
      ffmpeg -v error -y -f lavfi -i "$(fundo "$d")" "${SILENCIO[@]}" -t "$d" -vf "
drawtext=fontfile=$FONTE:text='MAIS VÍDEOS':fontsize=72:fontcolor=white:x='w-tw-160':y=120:alpha='min(1,t*3)',
drawtext=fontfile=$FONTE:text='SE INSCREVA':fontsize=48:fontcolor=white:x=360-tw/2:y=520:alpha='min(1,t*3)',
drawbox=x=0:y=ih-24:w='iw*t/$d':h=24:color=0xff9a1f:t=fill" \
        "${ENC[@]}" -shortest "$seg" ;;
    *) echo "tipo desconhecido: $tipo" >&2; exit 1 ;;
  esac
  echo "file '$seg'" >> "$LISTA"
done 3< "$ROTEIRO"

# Junta tudo, aplica marca d'água fixa (sup. dir., 50%) e normaliza o áudio em -14 LUFS
ffmpeg -v error -y -f concat -safe 0 -i "$LISTA" \
  -vf "drawtext=fontfile=$FONTE:text='$MARCA':fontsize=54:fontcolor=white@0.5:borderw=3:bordercolor=black@0.4:x=w-tw-40:y=40" \
  -af "loudnorm=I=-14:TP=-1:LRA=11" "${ENC[@]}" -movflags +faststart "$SAIDA"
echo "OK -> $SAIDA"
