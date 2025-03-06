# Introduction to Creating a Job

This page guides you through developing an example job using Open Job Description, after setting up
and configuring the [Visual Studio Code](https://code.visualstudio.com/) editor to help you write
Open Job Description templates.

The job generates frames of an animation using [Blender](https://www.blender.org/), then encodes those rendered frames
into an mp4 video using [FFmpeg](https://ffmpeg.org/). We illustrate a fast development loop using
the Open Job Description CLI to iteratively test the Job on your workstation. The steps make
small incremental changes to more easily narrow in on the root causes of errors. This process
has faster iterations than repeatedly submitting the Job to your scheduling system, and can be done
in a cafe or airplane without an internet connection before later running it on a deployed compute cluster.

If you have not already read through [How Jobs Are Constructed](How-Jobs-Are-Constructed) and [How Jobs Are Run](How-Jobs-Are-Run)
then we recommend starting with those first. Those pages provide context that will help you
understand the remainder of this guide.

1. [Toolchain Setup](Job-Intro-01-Toolchain-Setup)
2. [Starting with shell scripts](Job-Intro-02-Starting-With-Shell-Scripts)
    1. [Creating a shell script to render with Blender](Job-Intro-02-Starting-With-Shell-Scripts#1-creating-a-shell-script-to-render-with-blender)
    2. [Creating a shell script to encode a video with FFmpeg](Job-Intro-02-Starting-With-Shell-Scripts#2-creating-a-shell-script-to-encode-a-video-with-ffmpeg)
3. [Creating a Job Template](Job-Intro-03-Creating-a-Job-Template)
    1. [Embed the scripts into a Job Template](Job-Intro-03-Creating-a-Job-Template#1-embed-the-scripts-into-a-job-template)
    2. [Parameterizing the template](Job-Intro-03-Creating-a-Job-Template#2-parameterizing-the-template)
    3. [Path Mapping](Job-Intro-03-Creating-a-Job-Template#3-path-mapping)
    4. [Adding Task Parallelism](Job-Intro-03-Creating-a-Job-Template#4-adding-task-parallelism)
4. [Ready for Production](Job-Intro-04-Ready-for-Production)
    1. [Condition testing using environments](Job-Intro-04-Ready-for-Production#1-conditional-testing-using-environments)
    2. [Adding host requirements](Job-Intro-04-Ready-for-Production#2-adding-host-requirements)
    3. [The final result](Job-Intro-04-Ready-for-Production#3-the-final-result)

We've just scratched the surface of what you can do with a Open Job Description Job Templates. To learn more we recommend:

1. Taking a look through [the samples](https://github.com/OpenJobDescription/openjd-specifications/tree/mainline/samples) to
   get some more ideas;
2. Creating your own templates for the kinds of Jobs that you are interested in; and
3. Ask questions in our [Discussion Forums](https://github.com/OpenJobDescription/openjd-specifications/discussions).

