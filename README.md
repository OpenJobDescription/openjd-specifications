# Open Job Description Specifications

This repository provides the specification for Open Job Description, a flexible
open specification for portable batch processing jobs. This repository serves
as a point of reference and to drive updates from the community via
a Request For Comment (RFC) process.

Jump to:

* [Wiki Home](https://github.com/OpenJobDescription/openjd-specifications/wiki)
* [Sample Templates](samples/README.md)
* [RFC Readme](rfcs/README.md)

## Getting Started

The fastest way to understand the bones of Open Job Description is to understand both
[How Jobs Are Constructed](https://github.com/OpenJobDescription/openjd-specifications/wiki/How-Jobs-Are-Constructed)
and [How Jobs Are Run](https://github.com/OpenJobDescription/openjd-specifications/wiki/How-Jobs-Are-Run).
You may also find it beneficial to look through the provided
[sample templates](https://github.com/OpenJobDescription/openjd-specifications/tree/mainline/samples) in this GitHub
repository.

## What is Open Job Description?

Open Job Description is a flexible open specification for defining batch processing
jobs that are portable between different scheduling system deployments. The specification
was developed in the context of render farms and visual compute use cases, but applies
more broadly. A set of libraries and CLI tooling complement the specification, and
can be used to integrate Open Job Description support into your scheduling system
of choice.

By creating and using tools that produce and/or consume portable jobs in
Open Job Description form, you can develop a flexible production pipeline that
directs these jobs to different scheduling system, or stores the jobs
outside of any scheduling system for later processing.

For deeper insight into our thought process and goals, we recommend
[this Academy Software Foundation talk](https://www.youtube.com/watch?v=2umfqGX844Y)
by Pauline Koh, Senior Product Manager - Technical at Amazon Web Services, titled
*Portable and Open Render Job Specifications*.

## Open Job Description Projects

*If you have an Open Job Description project that you would like to advertise here then please
submit a pull request.*

### Tools

* [openjd-cli](https://github.com/OpenJobDescription/openjd-cli) - A command-line
  interface for running and working with Open Job Description templates.

### Libraries

* [openjd-model](https://github.com/OpenJobDescription/openjd-model-for-python) - A Python
  implementation of the data model for Open Job Description's template schemas.
* [openjd-sessions](https://github.com/OpenJobDescription/openjd-sessions-for-python) - A Python
  library that can be used to build a runtime that is able to run Jobs in a Session as defined
  by Open Job Description.
* [openjd-adaptor-runtime](https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python) - A Python library
  for creating a command-line Adaptor to assist with integrating an existing application, such as a rendering
  application, into batch computing systems that run Jobs in a way that is compatible with Open Job Description Sessions.

## Contributing

Open Job Description is under active development. We want your feedback and participation
as we move forward, together, in defining and implementing a specification that solves
the problems in the space. Open Job Description needs to grow to be able to express all the
jobs and workflows we'd love to support.

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for a more detailed description of how to
contribute, and the [RFC Readme](rfcs/README.md) for how to contribute an RFC.

We look forward to your input.

* [Discussions](https://github.com/OpenJobDescription/openjd-specifications/discussions):
  We encourage you to post about what you would like to see in future revisions
  of the specification, share, and brag about how you are using Open Job
  Description, and engage with us and the community.
* [Request for Comment](rfcs/README.md):
  This repository exists because we want your comments on the specification.
  Please consider submitting an RFC if you have thoughts on how the
  specification could be improved.
* [Issues](https://github.com/OpenJobDescription/openjd-specifications/issues):
  We encourage you to use the GitHub issue tracker to report bugs.
* [Pull Requests](https://github.com/OpenJobDescription/openjd-specifications/pulls):
  We welcome pull requests to improve this wiki documentation. Simply make your
  changes in our [GitHub Repository](https://github.com/OpenJobDescription/openjd-specifications/tree/mainline/wiki)
  and post a pull request.

## Getting Help

* [Discussions](https://github.com/OpenJobDescription/openjd-specifications/discussions):
  Seek help via our GitHub Discussions forum.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more
information.

## License

See the [LICENSE](LICENSE) file for our project's licensing. We will also ask
you to confirm the licensing of your contribution.

