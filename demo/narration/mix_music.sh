#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Mix narration with music bed using sidechain ducking.
#
# - Music plays at MUSIC_GAIN
# - When narration is present, music auto-ducks via sidechaincompress
# - Narration sits on top at NARRATION_GAIN
# - Fade in/out on music
#
# Usage:  cd demo && bash narration/mix_music.sh
# ─────────────────────────────────────────────────────────────────────────────

FFMPEG="C:/fieldpack-ai/ffmpeg/bin/ffmpeg.exe"
FFPROBE="C:/fieldpack-ai/ffmpeg/bin/ffprobe.exe"
DIR="C:/fieldpack-ai/demo/narration"

NARRATION="$DIR/narration_final.mp3"
MUSIC="$DIR/music.mp3"
OUT="$DIR/narration_with_music.mp3"

TOTAL=175           # output duration (seconds, matches build_audio.sh)
FADE_IN=2           # music fade-in (seconds)
FADE_OUT=3          # music fade-out (seconds)
MUSIC_GAIN=0.07     # base music volume (7% — very faint bed, voice fully dominant)
NARRATION_GAIN=1.3  # narration boosted so it sits clearly on top

# Music is 90s but last 2s are silence → trim to 88s, then loop with crossfade
MUSIC_TRIM=88       # seconds to keep from source music
LOOP_XFADE=2        # crossfade duration at loop seam (seconds)

# Sidechain compressor: music ducks when narration is present
# threshold=0.05 → trigger easily on any voice
# ratio=8        → aggressive duck (music drops ~12dB under voice)
# attack=5ms     → fast clamp at word start
# release=600ms  → smooth recovery after phrase ends
SIDECHAIN="sidechaincompress=threshold=0.05:ratio=8:attack=5:release=600"

FADE_OUT_START=$((TOTAL - FADE_OUT))

if [ ! -f "$MUSIC" ]; then
  echo "ERROR: $MUSIC not found."
  exit 1
fi

if [ ! -f "$NARRATION" ]; then
  echo "ERROR: $NARRATION not found. Run build_audio.sh first."
  exit 1
fi

echo "Mixing:"
echo "  narration: $NARRATION"
echo "  music:     $MUSIC"
echo "  output:    $OUT"
echo "  music gain: $MUSIC_GAIN   narration gain: $NARRATION_GAIN"
echo "  fade in: ${FADE_IN}s   fade out: ${FADE_OUT}s (starts at ${FADE_OUT_START}s)"
echo ""

# Music pipeline:
#  1. Load twice (as inputs 1 and 2), trim each to MUSIC_TRIM seconds
#  2. acrossfade them → one continuous track (MUSIC_TRIM*2 - LOOP_XFADE seconds long)
#  3. Apply gain, fade-in, fade-out
#  4. Sidechain-duck against narration
#  5. Mix narration on top

"$FFMPEG" -y \
  -i "$NARRATION" \
  -i "$MUSIC" \
  -i "$MUSIC" \
  -i "$MUSIC" \
  -filter_complex "
    [0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=${NARRATION_GAIN}[narr];
    [1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,atrim=0:${MUSIC_TRIM},asetpts=PTS-STARTPTS[m1];
    [2:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,atrim=0:${MUSIC_TRIM},asetpts=PTS-STARTPTS[m2];
    [3:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,atrim=0:${MUSIC_TRIM},asetpts=PTS-STARTPTS[m3];
    [m1][m2]acrossfade=d=${LOOP_XFADE}:c1=tri:c2=tri[l12];
    [l12][m3]acrossfade=d=${LOOP_XFADE}:c1=tri:c2=tri[looped];
    [looped]volume=${MUSIC_GAIN},
            afade=t=in:st=0:d=${FADE_IN},
            afade=t=out:st=${FADE_OUT_START}:d=${FADE_OUT}[mus];
    [mus][narr]${SIDECHAIN}[ducked];
    [ducked][narr]amix=inputs=2:duration=longest:normalize=0[out]
  " \
  -map "[out]" -t $TOTAL -q:a 2 "$OUT" 2>&1 | tail -3

echo ""
DUR=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$OUT" 2>/dev/null)
echo "Output duration: ${DUR}s"
echo ""
echo "Listen → if music too loud, lower MUSIC_GAIN (try 0.22)"
echo "         if ducking too aggressive, lower ratio in SIDECHAIN (try ratio=4)"
echo "         if narration unclear, raise NARRATION_GAIN (try 1.25)"
