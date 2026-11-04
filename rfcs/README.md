# Open Job Description RFCs

This directory is the place to propose upcoming changes to the Open Job Description standard.
The RFC ("Request For Comment") process is how Open Job Description achieves consensus on proposed
changes to the formal specification. The process is intended to provide a consistent and controlled
path for changes to the specification.

RFCs can be created by anyone in the community, and is the process that the Open Job Description team
uses to propose changes. If you have an idea, a kernel of an idea, a problem to solve, or want to
provide your point of view on proposals then we encourage you to engage in this process.

**Jump to**: [RFC Process](#rfc-process) | [RFC Process Stages](#rfc-process-stages)

## RFC Process

This section describes each state of the RFC process.

### 1. Look for similar existing proposals or discussions

Before you start along the path of proposing your idea as an RFC, please take some time
to search through our [issues tracker] and [discussion forum] for similar or compatible
proposals. It is possible that your idea has previously been proposed, or it might fit
in nicely as an enhancement to an RFC that is in the works.

[issues tracker]: https://github.com/OpenJobDescription/openjd-specifications/issues
[discussion forum]: https://github.com/OpenJobDescription/openjd-specifications/discussions/categories/ideas

### 2. Post in GitHub Discussions

As an informal starting point, we suggest that you try our discussion forums to have
some preliminary discussions on your proposal. These discussions can help find like-minded members of
the community to collaborate with, and test the idea with the community before commiting
to filling out an RFC template with the details of your proposal.

Simply create a new discussion thread in the [Ideas category] of the discussion forum to
get started.

[Ideas category]: https://github.com/OpenJobDescription/openjd-specifications/discussions/categories/ideas

### 3. Tracking Issue

Each RFC has a GitHub issue which tracks it from start to finish. The issue is
the hub for conversations, community signal (+1s) and the issue number is used
as the unique identifier of this RFC.

Before creating a tracking issue, please search for similar or related ideas
in the issue list and discussion forum of this repo. If there is a relevant
RFC, collaborate on that existing RFC, based on its current stage.

Our [tracking issue template] includes a checklist of all the steps an RFC goes
through and it's the driver's responsibility to update the checklist and assign
the correct label to on the RFC throughout the process.

[tracking issue template]: https://github.com/OpenJobDescription/openjd-specifications/blob/master/.github/ISSUE_TEMPLATE/rfc.md

### 4. RFC Document

The next step is to write the first revision of the RFC document itself.

1. We suggest reading our [design tenets] before you start.
2. [Fork this repository]
3. Then, in your fork:
    1. Create a file under `rfcs/NNNN-name.md` based off of the [0000-template.md] file.
       `NNNN` in the filename is your tracking issue number, and `name` should be a one
       or two word summary of the proposal.
    2. Please follow the template; it includes useful guidance and tips on how to write a good RFC.
    3. Alongside the RFC document, edit the specification in the [`wiki/`] directory to make your proposed
       changes: the formal text in `wiki/2023-09-Template-Schemas.md` and
       `wiki/2026-02-Expression-Language.md`, and the more approachable explanation in narrative pages
       such as `wiki/How-Jobs-Are-Run.md`. These wiki edits are the normative text of your proposal.
       The RFC describes each change in short prose, focused on why it is made, and links to the wiki
       sections it edits. Where the RFC and the wiki differ, the wiki governs.
4. We recommend that you develop a prototype implementation in [openjd-rs] in parallel with the RFC,
   on a branch in your fork of that repository. Practical experience with the prototype should guide
   the RFC directly: writing templates against it, running them, and implementing the validation
   rules will show where the proposal is unclear, hard to use, or hard to implement. Link the
   prototype branch from the RFC, and say what it taught you.

[design tenets]: https://github.com/OpenJobDescription/openjd-specifications/wiki/Design-Tenets
[Fork this repository]: https://help.github.com/articles/fork-a-repo/
[0000-template.md]: https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0000-template.md
[`wiki/`]: https://github.com/OpenJobDescription/openjd-specifications/tree/mainline/wiki
[openjd-rs]: https://github.com/OpenJobDescription/openjd-rs

### 5. Feedback

Once you have an initial version of your RFC document (it is completely fine to
submit an unfinished RFC to get initial feedback), [submit it as a pull request]
against this repository to start collecting feedback. The pull request includes
both the RFC document and its wiki edits.

This is the likely going to be the longest part of your RFC process, and where
most of the feedback is collected.

A few tips:

- If you decide to resolve a comment without addressing it, take the time to
  explain.
- Try to understand where people are coming from. If a comment seems off, ask
  folks to elaborate and describe their use case or provide concrete examples.
- Work with the team member assigned to your tracking issue: if there are disagreements,
  @mention them in a comment and ask them to provide their opinion.
- As the proposal changes, update the wiki edits, the RFC, and the prototype together, so that they
  continue to agree.
- Be patient: it sometimes takes time for an RFC to converge. Some ideas need to "bake"
  and solutions oftentimes emerge via a healthy debate.
- Not everything must be resolved in the first revision. It is okay to leave
  some things to resolve later. Make sure to capture them clearly and have an
  agreement about that. An RFC document may be updated/modified as new information
  comes to light at any time before it it published in a revision of Open Job Description.

[submit it as a pull request]: https://help.github.com/articles/creating-a-pull-request/

### 6. Final Comments Period

At some point, you've reached consensus about most issues that were brought up
during the review period, and you are ready to merge. To allow "last call" on
feedback, the author can announce that the RFC enters "final comments period",
which means that within about a week or two, if no major concerns are raised, the
RFC will be approved and merged.

Add a comment on the RFC pull request, tracking issue, and discussion forum thread
if relevant that the RFC has entered this stage so that all relevant stakeholders
will be notified.

Once the final comments period is over, seek an approval of one of the core team
members, and you can merge your PR to the main branch. This will move your RFC
to the "Released" state.

### 7. Accepted and Beyond

The pull request for your RFC will be merged in to this repository when your proposal
has been accepted. This requires an approval of the pull request by one of the core
members of the Open Job Description team.

Because the pull request includes the wiki edits, merging it publishes your proposed changes in the
specification. This moves your RFC to the "Released" state.

## RFC Process Stages

An RFC's tracking ticket is tagged to indicate what stage of the process it is in:

| Stage | Tracking Label | Description |
| ----- | -------------- | ----------- |
| [0 - Proposed](#Proposed) | [rfc/proposed] | A proposal for a change that is offered for community and team evaluation. |
| [1 - Exploring](#Exploring) | [rfc/exploring] | The author(s), team, and community are working together to refine and iterate on the proposal, its wiki edits, and its prototype. |
| [2 - Final Comments](#LastCall) | [rfc/exploring] and [rfc/final-comments] | Consensus has been reached on the RFC. A "last call" has been announced for feedback. |
| [3 - Accepted-Future](#Future) | [rfc/accepted-future] | The proposal has been accepted for inclusion in a future revision of the Open Job Description specification. |
| [4 - Accepted-Draft](#Draft) | [rfc/accepted-draft] | The author has been given the green light to include the proposal in a draft of the Open Job Description specification. |
| [5 - Accepted-Staged](#Staged) | [rfc/accepted-staged] | The proposal has been accepted and included in a draft revision of the Open Job Description specification. |
| [6 - Released](#Released) | [rfc/released] | The proposal has been included in a published revision of the Open Job Description specification. |

Because an RFC's pull request includes its wiki edits, the RFC moves from Final Comments to Released when the pull
request is merged. The Accepted-Future, Accepted-Draft, and Accepted-Staged stages are for RFCs accepted before the wiki
edits were part of the RFC's pull request, under an earlier process that made the specification changes in later
pull requests.

There are two additional statuses for RFCs that will not move forward:
- **[Abandoned](#Abandoned)** (label: [rfc/abandoned]) - The RFC's author(s) have ceased to engage in the process, and the RFC's process is
  stalled. RFCs leave this state when the author(s) reengage, or a new champion from the community or team takes on
  advocating for the proposal.
- **[Closed](#Closed)** - The RFC was closed by the author, or the review process determined that the proposal will
  not be accepted. The tracking issue and pull request are closed in this stage.

[rfc/proposed]: https://github.com/OpenJobDescription/openjd-specifications/labels/rfc%2Fproposed
[rfc/exploring]: https://github.com/OpenJobDescription/openjd-specifications/labels/rfc%2Fexploring
[rfc/final-comments]: https://github.com/OpenJobDescription/openjd-specifications/labels/rfc%2Ffinal-comments
[rfc/accepted-future]: https://github.com/OpenJobDescription/openjd-specifications/labels/rfc%2Faccepted-future
[rfc/accepted-draft]: https://github.com/OpenJobDescription/openjd-specifications/labels/rfc%2Faccepted-draft
[rfc/accepted-staged]: https://github.com/OpenJobDescription/openjd-specifications/labels/rfc%2Faccepted-staged
[rfc/released]: https://github.com/OpenJobDescription/openjd-specifications/labels/rfc%2Freleased
[rfc/abandoned]: https://github.com/OpenJobDescription/openjd-specifications/labels/rfc%2Fabandoned

---

This RFC process is inspired by RFC processes in popular open source projects: [Yarn RFC process],
[Rust RFC process], [React RFC process], [Ember RFC process], [AWS CDK RFC process], and [Python PEP].

[yarn rfc process]: https://github.com/yarnpkg/rfcs
[rust rfc process]: https://github.com/rust-lang/rfcs
[react rfc process]: https://github.com/reactjs/rfcs
[ember rfc process]: https://github.com/emberjs/rfcs
[AWS CDK RFC process]: https://github.com/aws/aws-cdk-rfcs
[Python PEP]: https://peps.python.org/pep-0012/

