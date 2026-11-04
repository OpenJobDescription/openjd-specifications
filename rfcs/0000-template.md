
* Feature Name: (fill in with a unique one or two word identifier. e.g. my_feature)
* Author(s): (fill in all the authors as Author Name `[<github-user>](https://github.com/<github-user>)`)
* RFC Tracking Issue: (fill in with the URL for the tracking issue in this repository)
* Start Date: (fill in with today's date: YYYY-MM-DD)
* Specification Version: 2023-09 extension (fill in with a chosen extension name as per RFC 0002)
* Accepted On: (fill in with the date that the proposal was accepted: YYYY-MM-DD)

## Summary

A one paragraph summary of the proposed feature.

## Basic Examples

If the proposal involves a new or changed schema or syntax, then include some basic examples
that demonstrate how an end-user would use it.

## Motivation

Why are we doing this? What use cases does it support? Focus on what sorts of workflows your
feature would enable for users. How common are those use cases: Are they specific to one
company's way of working, or more generally adopted?

If this is inspired by the capabilities of existing systems, then think about *why* the feature
is available in terms of what users accomplish with it. Our vision for Open Job Description is a
general and expressive specification rather than one that is a simply superset of features/syntax
available in existing distributed batch computing systems and pipeline tools.

## Specification

What are the specific changes that are being proposed?

The pull request for this RFC also edits the specification in the `wiki/` directory, and those edits are the
normative text of the proposal: formal in [Template Schemas] and [Expression Language], and more
approachable in narrative pages such as [How Jobs Are Run]. Please do not reproduce them here.
Instead, describe every change the pull request makes to the wiki, in particular to Template Schemas and
the Expression Language, in short prose focused on why the change is made, and link to the wiki section
that holds its text. Where this RFC and the wiki differ, the wiki governs.

We suggest keeping our [design tenets] in mind while writing this part.

[Template Schemas]: https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas
[Expression Language]: https://github.com/OpenJobDescription/openjd-specifications/wiki/2026-02-Expression-Language
[How Jobs Are Run]: https://github.com/OpenJobDescription/openjd-specifications/wiki/How-Jobs-Are-Run

[design tenets]: https://github.com/OpenJobDescription/openjd-specifications/wiki/Design-Tenets

## Design Choice Rationale

### Title of Design Choice

For each choice you made between specific options, such as including or postponing some functionality,
briefly provide the rationale you used for the choice.

## Prior Art

Discuss prior art, both the good and the bad, in relation to the proposal. Does a feature
like this exist in other systems? How is it expressed in those system(s)?

## Prototype

Link the branch of the prototype implementation in [openjd-rs] that was developed in parallel with this
RFC, and say what the prototype taught you. Which parts of the proposal changed because of it? What
turned out to be unclear, hard to use, or hard to implement?

[openjd-rs]: https://github.com/OpenJobDescription/openjd-rs

## Implementation Impact

Describe the expected implementation complexity for known OpenJD implementations:

- **Python (openjd-model)**: [impact description]
- **Rust (openjd-rs)**: [impact description]

Are there features of this RFC that may be significantly harder to implement in one language
vs another? Are there performance implications?

## Rejected Ideas

Why certain ideas that were brought while discussing this RFC were not ultimately pursued.

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal license, whichever is more permissive.