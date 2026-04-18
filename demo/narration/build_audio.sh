#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Build synced narration audio track from timestamps.json + MP3 clips
#
# Reads actual scene start times from demo/timestamps.json (produced by
# Playwright recording) and places each narration clip at the correct time.
#
# Usage:  cd demo && bash narration/build_audio.sh
# ─────────────────────────────────────────────────────────────────────────────

FFMPEG="C:/fieldpack-ai/ffmpeg/bin/ffmpeg.exe"
FFPROBE="C:/fieldpack-ai/ffmpeg/bin/ffprobe.exe"
DIR="C:/fieldpack-ai/demo/narration"
TIMESTAMPS="C:/fieldpack-ai/demo/timestamps.json"
OUT="$DIR/narration_final.mp3"

TOTAL=175  # pad a few seconds beyond 2:50

# ─── Read scene timestamps from JSON ─────────────────────────────────────────

if [ ! -f "$TIMESTAMPS" ]; then
  echo "ERROR: $TIMESTAMPS not found. Run the demo recording first."
  exit 1
fi

# Extract elapsedMs for each scene using python (available in venv)
PYTHON="C:/fieldpack-ai/venv/Scripts/python.exe"

# Python script outputs: SCENE_NAME ELAPSED_MS (one per line)
SCENE_TIMES=$("$PYTHON" -c "
import json, sys
with open('$TIMESTAMPS') as f:
    data = json.load(f)
for entry in data:
    print(f\"{entry['scene']} {int(entry['elapsedMs'])}\")
" | tr -d '\r')

# Parse into bash associative array
declare -A SCENE_MS
while IFS=' ' read -r scene ms; do
  SCENE_MS["$scene"]=$ms
done <<< "$SCENE_TIMES"

echo "Scene timestamps from recording:"
for scene in title-card persona map stats architecture mission-chat agent-progress transition field-session hero-shot grounded platform closing; do
  ms=${SCENE_MS[$scene]:-"MISSING"}
  if [ "$ms" != "MISSING" ]; then
    secs=$((ms / 1000))
    printf "  %-20s %6d ms  (%d:%02d)\n" "$scene" "$ms" $((secs/60)) $((secs%60))
  fi
done
echo ""

# ─── Clip-to-scene mapping ───────────────────────────────────────────────────
# Each clip maps to a scene + an offset (ms within that scene).
# Clips 1.mp3 and 2.mp3 are SKIPPED (cold open redesign — music only).
#
# Format: "clip_file scene_name offset_ms"
# offset_ms = how many ms AFTER the scene starts before this clip plays

CLIP_MAP=(
  "3_slow.mp3 persona       0"
  "4.mp3    map             0"
  "5.mp3    stats           0"
  "6.mp3    architecture    0"
  "7.mp3    mission-chat    0"
  "8.mp3    agent-progress  0"
  "9a.mp3   transition      0"
  "9b.mp3   transition      2500"
  "9c.mp3   transition      4000"
  "9d.mp3   transition      5500"
  "10.mp3   transition      7000"
  "11.mp3   field-session   0"
  "12.mp3   field-session   10000"
  "13.mp3   hero-shot       0"
  "14.mp3   hero-shot       12000"
  "15.mp3   hero-shot       30000"
  "16.mp3   grounded        0"
  "17.mp3   platform        0"
  "18.mp3   closing         0"
)

# ─── Calculate delays and check for overlaps ─────────────────────────────────

echo "Clip placement plan:"
echo "─────────────────────────────────────────────────────────"

INPUTS=""
FILTER=""
MIXINPUTS=""
IDX=0
PREV_END=0
GAP_MS=200  # minimum gap between clips to avoid clipping tails/heads

for entry in "${CLIP_MAP[@]}"; do
  read -r FILE SCENE OFFSET <<< "$entry"

  SCENE_START=${SCENE_MS[$SCENE]}
  if [ -z "$SCENE_START" ]; then
    echo "  WARNING: Scene '$SCENE' not found in timestamps.json — skipping $FILE"
    continue
  fi

  SCHEDULED_MS=$((SCENE_START + OFFSET))

  # Get clip duration
  DUR=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$DIR/$FILE" 2>/dev/null | tr -d '\r')
  DUR_MS=$(echo "$DUR" | "$PYTHON" -c "import sys; print(int(float(sys.stdin.read().strip()) * 1000))" | tr -d '\r')

  # Anti-overlap: push clip forward if previous one is still playing
  MIN_START=$((PREV_END + GAP_MS))
  PUSHED=""
  if [ "$SCHEDULED_MS" -lt "$MIN_START" ]; then
    PUSH_AMT=$(( (MIN_START - SCHEDULED_MS) ))
    DELAY_MS=$MIN_START
    PUSHED="  ↪ pushed +${PUSH_AMT}ms to avoid overlap"
  else
    DELAY_MS=$SCHEDULED_MS
  fi

  END_MS=$((DELAY_MS + DUR_MS))
  SECS=$((DELAY_MS / 1000))
  printf "  %-12s → %6d ms  (%d:%02d)  dur=%ss%s\n" "$FILE" "$DELAY_MS" $((SECS/60)) $((SECS%60)) "$DUR" "$PUSHED"

  INPUTS="$INPUTS -i $DIR/$FILE"
  FILTER="${FILTER}[${IDX}]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,adelay=${DELAY_MS}|${DELAY_MS}[d${IDX}];"
  MIXINPUTS="${MIXINPUTS}[d${IDX}]"
  IDX=$((IDX + 1))

  PREV_END=$END_MS
done

COUNT=$IDX
FILTER="${FILTER}${MIXINPUTS}amix=inputs=${COUNT}:duration=longest:normalize=0[out]"

echo ""
echo "Merging ${COUNT} clips..."
"$FFMPEG" -y $INPUTS -filter_complex "$FILTER" -map "[out]" -t $TOTAL -q:a 2 "$OUT" 2>&1 | tail -3

echo ""
echo "Output: $OUT"
DUR=$("$FFPROBE" -v error -show_entries format=duration -of csv=p=0 "$OUT" 2>/dev/null)
echo "Duration: ${DUR}s"
echo ""
echo "Next: record the demo, then re-run this script to sync to actual timestamps."
echo "Final merge: ffmpeg -i recording.mp4 -i narration_final.mp3 -c:v copy -c:a aac -shortest final.mp4"
