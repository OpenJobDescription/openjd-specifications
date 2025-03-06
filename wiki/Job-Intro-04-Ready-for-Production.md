# Ready for Production

After following the walkthrough step [Creating a Job Template](Job-Intro-03-Creating-a-Job-Template), you have
a complete template to render in Blender and then encode a video. You've been reducing the resolution and quality
of the resulting frames to make the development iterations quicker. To use the template in production you'll need
to remove that testing code. You may also want to control which worker hosts in your cluster run the Steps of the Job.
We'll go over both in this section.

## 1. Conditional Testing Using Environments

To use the template in production you'd either need to remove the testing code from the `render.sh`
embedded file so that it becomes:

```bash
#!/bin/bash

# Return an error code if any command in the script fails.
set -euo pipefail

SCENE="$1"
OUTDIR="$2"
FRAME="$3"

blender --background "$SCENE" \
  --render-output "$OUTDIR"/frame-### \
  --render-format PNG --use-extension 1 \
  --render-frame "${FRAME}"
```

or you need to modify the template so that it has both a testing and production mode. We'll do the latter in this guide to demonstrate
using [Environments](2023-09-Template-Schemas#4-environment) in a Job Template. Think of Environments as encapsulating commands that you
can run to set up the context that Tasks run on in a session, then tear it down after no more Tasks will run (whether successfully or not).
See the [How Jobs Are Run](How-Jobs-Are-Run#sessions) wiki topic for more details.
Since Environmnets run arbitrary commands of your choosing they can do anything that you would like, but one of their use cases is to
set up or modify the environment where your Tasks will be running.

For this case, modify the `render.sh` embedded file so that the testing code is only run if the environment variable
`TESTING_TEMPLATE` has the value `true`:

```bash
#!/bin/bash

# Return an error code if any command in the script fails.
set -euo pipefail

# Use Blender's scripting interface to reduce the scene resolution and sampling rate to speed up testing.
# See https://www.gnu.org/savannah-checkouts/gnu/bash/manual/bash.html#Here-Documents
TMPFILE=$(mktemp)
if test "${TESTING_TEMPLATE:-false}" == "true"; then
    cat > "$TMPFILE" << EOF
import bpy
for s in bpy.data.scenes:
s.render.resolution_x = 480
s.render.resolution_y = 270
bpy.context.scene.cycles.samples = 100
EOF
fi

# Exit handler to clean up the temporary python script
function cleanup {
    rm -f $TMPFILE
}
trap cleanup EXIT

SCENE="$1"
OUTDIR="$2"
FRAME="$3"

blender --background "$SCENE" \
  --python "$TMPFILE" \
  --render-output "$OUTDIR"/frame-### \
  --render-format PNG --use-extension 1 \
  --render-frame "${FRAME}"
```

Then you can add a Step Environment to the `BlenderRender` Step that sets that environment variable to `true` or `false`
based on the value of a `TestingMode` Job Parameter:

```yaml
...
parameterDefinitions:
...
  - name: TestingMode
    type: STRING
    allowedValues: ["true", "false"]
    default: "false"
...
  - name: BlenderRender
    stepEnvironments:
      - name: ToggleTesting
        variables:
          TESTING_TEMPLATE: "{{Param.TestingMode}}"
      # - name: ToggleTesting
      #   description: "An alternative form that uses the openjd_env stdout message"
      #   script:
      #     actions:
      #       onEnter:
      #         command: "{{Env.File.SetEnv}}"
      #     embeddedFiles:
      #       - name: SetEnv
      #         type: TEXT
      #         runnable: true
      #         filename: set_testing_env.sh
      #         data: |
      #           #!/bin/bash
      #           echo "openjd_env: TESTING_TEMPLATE={{Param.TestingMode}}"
...
```

When you run this template, notice that the log now shows that the Session is entering the `ToggleTesting` environment
before running the Task:

```bash
Mon Jul  8 14:23:44 2024
Mon Jul  8 14:23:44 2024	==============================================
Mon Jul  8 14:23:44 2024	--------- Entering Environment: ToggleTesting
Mon Jul  8 14:23:44 2024	==============================================
Mon Jul  8 14:23:44 2024	Setting: TESTING_TEMPLATE=true
Mon Jul  8 14:23:44 2024
Mon Jul  8 14:23:44 2024	==============================================
Mon Jul  8 14:23:44 2024	--------- Running Task
Mon Jul  8 14:23:44 2024	==============================================
Mon Jul  8 14:23:44 2024	Parameter values:
Mon Jul  8 14:23:44 2024	RangeStart(INT) = 1
Mon Jul  8 14:23:44 2024	RangeEnd(INT) = 11
...
```

## 2. Adding Host Requirements

The definition of each Step in a Job Template can include a
[`hostRequirements` property](https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas#33-hostrequirements)
that, if supported by your job scheduler, will constrain the Step's Tasks to only run on certain hardware. For instance, you can say that
the Tasks must run on a Linux host, requires at least 16 GiB of memory, and requires at least 8 CPU cores.

Add host requirements to the `BlenderRender` Step to constrain which hosts in your compute cluster can run its Tasks:

```yaml
...
steps:
  - name: BlenderRender
...
    hostRequirements:
      amounts:
      - name: amount.worker.vcpu
        min: 4
      - name: amount.worker.memory
        min: 4096 # MiB. = 4 GiB
      attributes:
      - name: attr.worker.os.family
        anyOf: [ "linux" ]
      - name: attr.worker.cpu.arch
        anyOf: [ "x86_64" ]
    script:
...
```

The Open Job Description CLI does not currently support enforcing the constraints defined by host requirements, so you can
validate the template syntax using the CLI but you will have to test the constraints on your compute cluster.

## 3. The Final Result

The completed template now looks like:

```yaml
specificationVersion: jobtemplate-2023-09
name: "{{Param.JobName}}"
parameterDefinitions:
  - name: SceneFile
    type: PATH
    dataFlow: IN
    objectType: FILE
  - name: FramesDirectory
    type: PATH
    dataFlow: OUT
    objectType: DIRECTORY
  - name: AnimationFile
    type: PATH
    dataFlow: OUT
    objectType: FILE
  - name: FrameStart
    type: INT
    minValue: 1
    default: 1
  - name: FrameEnd
    type: INT
    minValue: 1
    default: 2
  - name: FrameEndMinusOne
    description: "Must be one less than the FrameEnd value"
    type: INT
  - name: FramesPerTask
    description: "Number of frames to render in each task. Note: The math breaks if FrameEnd is an integer multiple of FramesPerTask."
    type: INT
    default: 11
  - name: JobName
    type: STRING
    minLength: 1
    default: "DemoJob"
  - name: TestingMode
    type: STRING
    allowedValues: ["true", "false"]
    default: "false"
steps:
  - name: BlenderRender
    stepEnvironments:
      - name: ToggleTesting
        variables:
          TESTING_TEMPLATE: "{{Param.TestingMode}}"
      # - name: ToggleTesting
      #   description: "An alternative form that uses the openjd_env stdout message"
      #   script:
      #     actions:
      #       onEnter:
      #         command: "{{Env.File.SetEnv}}"
      #     embeddedFiles:
      #       - name: SetEnv
      #         type: TEXT
      #         runnable: true
      #         filename: set_testing_env.sh
      #         data: |
      #           #!/bin/bash
      #           echo "openjd_env: TESTING_TEMPLATE={{Param.TestingMode}}"
    parameterSpace:
      taskParameterDefinitions:
        - name: RangeStart
          type: INT
          range: "{{Param.FrameStart}}-{{Param.FrameEnd}}:{{Param.FramesPerTask}}"
        - name: RangeEnd
          type: INT
          range: "{{Param.FramesPerTask}}-{{Param.FrameEndMinusOne}}:{{Param.FramesPerTask}},{{Param.FrameEnd}}"
      combination: "(RangeStart,RangeEnd)"
    hostRequirements:
      amounts:
      - name: amount.worker.vcpu
        min: 4
      - name: amount.worker.memory
        min: 4096 # MiB. = 4 GiB
      attributes:
      - name: attr.worker.os.family
        anyOf: [ "linux" ]
      - name: attr.worker.cpu.arch
        anyOf: [ "x86_64" ]
    script:
      actions:
        onRun:
          command: "{{Task.File.Render}}"
          args:
            - "{{Param.SceneFile}}"
            - "{{Param.FramesDirectory}}"
            - "{{Task.Param.RangeStart}}..{{Task.Param.RangeEnd}}"
          timeout: 2400
      embeddedFiles:
        - name: Render
          type: TEXT
          filename: render.sh
          runnable: true
          data: |
            #!/bin/bash

            # Return an error code if any command in the script fails.
            set -euo pipefail

            # Use Blender's scripting interface to reduce the scene resolution and sampling rate to speed up testing.
            # See https://www.gnu.org/savannah-checkouts/gnu/bash/manual/bash.html#Here-Documents
            TMPFILE=$(mktemp)
            if test "${TESTING_TEMPLATE:-false}" == "true"; then
                cat > "$TMPFILE" << EOF
            import bpy
            for s in bpy.data.scenes:
            s.render.resolution_x = 480
            s.render.resolution_y = 270
            bpy.context.scene.cycles.samples = 100
            EOF
            fi

            SCENE="$1"
            OUTDIR="$2"
            FRAME="$3"

            blender --background "$SCENE" \
              --python "$TMPFILE" \
              --render-output "$OUTDIR"/frame-### \
              --render-format PNG --use-extension 1 \
              --render-frame "${FRAME}"

            rm -f $TMPFILE

  - name: EncodeVideo
    dependencies:
      - dependsOn: BlenderRender
    script:
      actions:
        onRun:
          command: "{{Task.File.Encode}}"
          args:
            - "{{Param.FramesDirectory}}"
            - "{{Param.AnimationFile}}"
            - "{{Param.FrameStart}}"
          timeout: 60
      embeddedFiles:
        - name: Encode
          type: TEXT
          runnable: true
          filename: encode.sh
          data: |
            #!/bin/bash

            set -euo pipefail

            INPUT_DIR="$1"
            OUTPUT_FILENAME="$2"
            START_FRAME="$3"

            ffmpeg -y -r 10 -start_number "$START_FRAME" -i "$INPUT_DIR"/frame-%03d.png -pix_fmt yuv420p \
                -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" \
                -frames:v 300 -c:v libx264 -preset fast \
                -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
                -movflags faststart "$OUTPUT_FILENAME"
```