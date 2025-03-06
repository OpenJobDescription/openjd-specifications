# Starting with shell scripts

Once you've completed your [Toolchain Setup](Job-Intro-01-Toolchain-Setup), a good starting point is to work out what
commands you'll run in your job. We will do that by writing some shell scripts.

An Open Job Description Job is, essentially, describing a set of command-line instructions to run, the inputs to those commands,
and the order in which they need to be run. We encourage you to think of authoring a Job as writing a series of shell
scripts that accomplish the objective of the Job when they are run in the correct order with the correct inputs.

In this guide, you are creating a Job that generates a sequence of frames of a Blender animation and then encodes the frames into
a movie file using FFmpeg. You'll break this Job down into two steps:

1. Generate the animation frames with Blender's command-line interface; and then
2. Encode the generated frames into an mp4 video file with FFmpeg.

Note that this walkthrough is written for a bash-compatible shell such as those available on typical Linux or
MacOS workstations. If you are using Windows, you will need to modify the commands for PowerShell or batch; though you may also
run bash scripts on Windows if you install an application such as [Git BASH](https://gitforwindows.org/).

## 1. Creating a shell script to render with Blender

First, you'll create a shell script that calls the Blender command-line interface to render a part of the animation.
Looking up the [documentation for the Blender command line](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html)
we create the following as a starting point for our Blender script:

```bash
#!/bin/bash

# Return an error code if any command in the script fails.
set -euo pipefail

# Use Blender's scripting interface to reduce the scene resolution and sampling rate to speed up testing.
# See https://www.gnu.org/savannah-checkouts/gnu/bash/manual/bash.html#Here-Documents
TMPFILE=$(mktemp)
cat > "$TMPFILE" << EOF
import bpy
for s in bpy.data.scenes:
  s.render.resolution_x = 480
  s.render.resolution_y = 270
bpy.context.scene.cycles.samples = 100
EOF

# Exit handler to clean up the temporary python script
function cleanup {
    rm -f $TMPFILE
}
trap cleanup EXIT

# Run blender to generate the image frames.
blender --background 3d/pavillon_barcelone_v1.2.blend \
  --python "$TMPFILE" \
  --render-output "$(pwd)"/output_frames/frame-### \
  --render-format PNG --use-extension 1 \
  --render-frame "1..2"
```

This script makes some assumptions, such as being run from a directory that contains our input and output, that we'll modify next,
but this is a good start. It uses Blender to render two frames of the 380 frame animation created by
the ["Barcelona Pavillion" demo scene](https://www.blender.org/download/demo-files/#cycles) by eMirage, distributed under CC-BY
(accessed July 2024). Save this to a file called `render.sh`, set its execute bit (`chmod +x render.sh`), and then test it to verify
that it runs as expected:

```bash
% ./render.sh
Blender 4.1.1 (hash e1743a0317bc built 2024-04-16 00:06:22)
...
Fra:1 Mem:130.47M (Peak 206.18M) | Time:00:07.56 | Compositing | De-initializing execution
Saved: 'output_frames/frame-001.png'
...
Fra:2 Mem:130.48M (Peak 272.58M) | Time:00:07.64 | Compositing | De-initializing execution
Saved: 'output_frames/frame-002.png'
Time: 00:07.71 (Saving: 00:00.07)
```

Next, you'll want to be able to create a Job that can render any scene rather than just this one demo scene. So, parameterize the
script such that the scene file, output directory, and frames to render can all be passed in as command-line arguments to the script:

```bash
#!/bin/bash

# Return an error code if any command in the script fails.
set -euo pipefail

# Use Blender's scripting interface to reduce the scene resolution and sampling rate to speed up testing.
# See https://www.gnu.org/savannah-checkouts/gnu/bash/manual/bash.html#Here-Documents
TMPFILE=$(mktemp)
cat > "$TMPFILE" << EOF
import bpy
for s in bpy.data.scenes:
  s.render.resolution_x = 480
  s.render.resolution_y = 270
bpy.context.scene.cycles.samples = 100
EOF

# Exit handler to clean up the temporary python script
function cleanup {
    rm -f $TMPFILE
}
trap cleanup EXIT

# Note: $1, $2, etc are the arguments passed to the shell script in order.
# See https://www.gnu.org/savannah-checkouts/gnu/bash/manual/bash.html#Positional-Parameters
SCENE="$(realpath $1)"
OUTDIR="$(realpath $2)"
START_FRAME="$3"
END_FRAME="$4"

blender --background "$SCENE" \
  --python "$TMPFILE" \
  --render-output "$OUTDIR"/frame-### \
  --render-format PNG --use-extension 1 \
  --render-frame "${START_FRAME}..${END_FRAME}"
```

Then test the script again:

```bash
% ./render.sh 3d/pavillon_barcelone_v1.2.blend output_frames 1 2
Blender 4.1.1 (hash e1743a0317bc built 2024-04-16 00:06:22)
...
Fra:2 Mem:130.48M (Peak 272.58M) | Time:00:08.09 | Compositing | De-initializing execution
Saved: 'output_frames/frame-002.png'
Time: 00:08.17 (Saving: 00:00.07)
```

## 2. Creating a shell script to encode a video with FFmpeg

To create the script for FFmpeg encoding consult the [Academy Software Foundation's encoding guidelines](https://academysoftwarefoundation.github.io/EncodingGuidelines/)
on how to run FFmpeg:

```bash
#!/bin/bash

set -euo pipefail

ffmpeg -y -r 10 -start_number 1 -i output_frames/frame-%03d.png -pix_fmt yuv420p \
    -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" \
    -frames:v 300 -c:v libx264 -preset fast \
    -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
    -movflags faststart "animation.mp4"
```

Then, as with the Blender script, save it to a file (`encode.sh`), set its execute bit, and then test it:

```bash
% ./encode.sh
ffmpeg version 6.1.1-tessus  https://evermeet.cx/ffmpeg/  Copyright (c) 2000-2023 the FFmpeg developers
...
```

Then modify it so that it accepts arguments from the command line:

```bash
#!/bin/bash

set -euo pipefail

INPUT_DIR="$(realpath $1)"
OUTPUT_FILENAME="$(realpath $2)"
START_FRAME="$3"

ffmpeg -y -r 10 -start_number "$START_FRAME" -i "$INPUT_DIR"/frame-%03d.png -pix_fmt yuv420p \
    -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" \
    -frames:v 300 -c:v libx264 -preset fast \
    -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
    -movflags faststart "$OUTPUT_FILENAME"
```

and then test it again:

```bash
% ./encode.sh output_frames animation.mp4 1
ffmpeg version 6.1.1-tessus  https://evermeet.cx/ffmpeg/  Copyright (c) 2000-2023 the FFmpeg developers
...
```

Continue the walkthrough in [Creating a Job Template](Job-Intro-03-Creating-a-Job-Template).