# Toolchain Setup

To replicate the steps taken in this guide you will need to have the Open Job Description CLI,
[Blender](https://www.blender.org/), and [FFmpeg](https://www.ffmpeg.org/) installed.
Open Job Description's CLI provides easy to use subcommands for validating the syntax of a Job Template,
running Tasks defined by a Job Template locally on your workstation, and more. There are two CLI implementations
available — choose whichever fits your environment:

## Option A: Python CLI

The [Python CLI](https://pypi.org/project/openjd-cli/) requires Python 3.9 or higher; for information on how to
install Python, please see the official [Python.org website](https://www.python.org/).

We suggest installing the tooling into a Python virtual environment based on [venv](https://docs.python.org/3/library/venv.html)
or [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html#term-Miniforge).

```bash
pip install openjd-cli
```

## Option B: Rust CLI

The [Rust CLI](https://crates.io/crates/openjd-cli) is a standalone binary.
Install it with [Cargo](https://doc.rust-lang.org/cargo/getting-started/installation.html):

```bash
cargo install openjd-cli
```

Both CLIs provide the same `check`, `summary`, and `run` subcommands used throughout this guide.

For writing Job Templates by hand we also recommend using [Visual Studio Code](https://code.visualstudio.com/)
and configuring it so that it can auto-complete the syntax of your Job Templates. To configure auto-complete, you
will first need to generate schema files for Open Job Description using the CLI:

```bash
mkdir ~/openjd-schemas
cd ~/openjd-schemas
openjd schema --version jobtemplate-2023-09 > openjobdescription-jobtemplate-2023-09.json
openjd schema --version environment-2023-09 > openjobdescription-environment-2023-09.json
```

Then install the official [Red Hat YAML](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) extension, and
modify your [Visual Studio Code settings](https://code.visualstudio.com/docs/languages/json#_json-schemas-and-settings)
to apply the Open Job Description schemas to your Job and Environment Templates. The following is an example of settings to
automatically apply the schemas to all JSON and YAML files on a workstation:

```json
    "json.schemas": [
        {"fileMatch": ["/**/*.json"], "url": "/Users/<username>/openjd-schemas/openjobdescription-jobtemplate-2023-09.json"},
        {"fileMatch": ["/**/*.json"], "url": "/Users/<username>/openjd-schemas/openjobdescription-environment-2023-09.json"}
    ],
    "yaml.schemas": {
        "/Users/<username>/json-schemas/openjobdescription-jobtemplate-2023-09.json": [
            "/**/*.yaml"
        ],
        "/Users/myusername/json-schemas/openjobdescription-environment-2023-09.json": [
            "/**/*.yaml"
        ]
    }
```

To use auto-complete, simply use Control-Space and select a schema entity to automatically populate all of the entities required
fields, or select a field to auto-complete it:

| Menu | Selecting "JobTemplate" Entity | Selecting "specificationVersion" field |
| ---  | --- | ---- |
| ![Autocomplete menu](images/template_autocomplete_menu.png) | ![Autocomplete template](images/template_autocomplete_entity.png) | ![Autocomplete field](images/template_autocomplete_field.png) |

Note that if you prefer to programmatically generate Open Job Description templates, in a pipeline for instance,
then the [openjd-model](https://pypi.org/project/openjd-model/) Python package
[supports that use case](https://github.com/OpenJobDescription/openjd-model-for-python?tab=readme-ov-file#converting-a-template-model-to-a-dictionary).

Continue the walkthrough in [Starting with shell scripts](Job-Intro-02-Starting-With-Shell-Scripts).