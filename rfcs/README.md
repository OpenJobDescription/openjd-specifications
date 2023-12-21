# Open Job Description RFCs

This directory is the place to propose and track upcoming changes to the Open Job Description standard.
The RFC ("Request For Comment") process is how Open Job Description achieves consensus on proposed
changes to the formal specification. The process is intended to provide a consistent and controlled
path for changes to the specification. 

RFCs can be created by anyone in the community. If you have an idea, a kernel of an idea, or a
problem to solve then we encourage you to engage in this process.

**Jump to**: [RFC Process](#rfc-process) | [RFC Process Stages](#rfc-process-stages)

## RFC Process

This section describes each state of the RFC process.

### 1. Look for similar existing proposals or discussions

Before you start along the path of proposing your idea as an RFC, please take some time
to search through our [issues tracker] and [discussion forum] for similar or compatible
proposals. It is possible that your idea has previously been proposed, or it might fit
in nicely as an enhancement to an RFC that is in the works.

[issues tracker]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/issues
[discussion forum]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/discussions/categories/ideas

### 2. Post in GitHub Discussions

As an informal starting point, we suggest that you try our discussion forums to have
some preliminary discussions on your proposal. These discussions can help find like-minded members of
the community to collaborate with, and test the idea with the community before commiting
to filling out an RFC template with the details of your proposal.

Simply create a new discussion thread in the [Ideas category] of the discussion forum to
get started.

[Ideas category]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/discussions/categories/ideas

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

[tracking issue template]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/blob/master/.github/ISSUE_TEMPLATE/rfc.yml

### 4. RFC Document

The next step is to write the first revision of the RFC document itself.

1. First, [fork this repository]
2. Then, in your fork:
    1. Create a file under `rfcs/NNNN-name.md` based off of the [0000-template.md] file.
       `NNNN` in the filename is your tracking issue number, and `name` should be a one
       or two word summary of the proposal.
    2. Please follow the template; it includes useful guidance and tips on how to write a good RFC.

[fork this repository]: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo
[0000-template.md]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/blob/mainline/rfcs/0000-template.md

### 5. Feedback

Once you have an initial version of your RFC document (it is completely fine to
submit an unfinished RFC to get initial feedback), [submit it as a pull request]
against this repository to start collecting feedback.

This is the likely going to be the longest part of your RFC process, and where
most of the feedback is collected.

A few tips:

- If you decide to resolve a comment without addressing it, take the time to
  explain.
- Try to understand where people are coming from. If a comment seems off, ask
  folks to elaborate and describe their use case or provide concrete examples.
- Work with the team member assigned to your tracking issue: if there are disagreements,
  @mention them in a comment and ask them to provide their opinion.
- Be patient: it sometimes takes time for an RFC to converge. Some ideas need to "bake"
  and solutions oftentimes emerge via a healthy debate.
- Not everything must be resolved in the first revision. It is okay to leave
  some things to resolve later. Make sure to capture them clearly and have an
  agreement about that. An RFC document may be updated/modified as new information
  comes to light at any time before it it published in a revision of Open Job Description.

[submit it as a pull request]: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork

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
to the "Accepted-Future" state.

### 7. Accepted and Beyond

The pull request for your RFC will be merged in to this repository when your proposal
has been accepted. This requires an approval of the pull request by one of the core
members of the Open Job Description team.

After merging the pull request, it may take some time for the core team to identify
which draft of the specification to include the proposal in; it may not be the current/next
one. 

The team will contact you through your RFCs tracking issue when it is time to include
the proposal in the current draft specification. When that happens, we ask that you
prepare pull requests that modify the draft specification, user documentation, and
so on to include your proposed changes.

## RFC Process Stages

An RFC's tracking ticket is tagged to indicate what stage of the process it is in:

| Stage | Tracking Label | Description |
| ----- | -------------- | ----------- |
| [0 - Proposed](#Proposed) | [rfc/proposed] | A proposal for a change that is offered for community and team evaluation. |
| [1 - Exploring](#Exploring) | [rfc/exploring] | The author(s), team, and community are working together to refine and iterate on the proposal. |
| [2 - Final Comments](#LastCall) | [rfc/exploring] and [rfc/final-comments] | Consensus has been reached on the RFC. A "last call" has been announced for feedback. |
| [3 - Accepted-Future](#Future) | [rfc/accepted-future] | The proposal has been accepted for inclusion in a future revision of the Open Job Description specification. |
| [4 - Accepted-Draft](#Draft) | [rfc/accepted-draft] | The author has been given the green light to include the proposal in a draft of the Open Job Description specification. |
| [5 - Accepted-Staged](#Staged) | [rfc/accepted-staged] | The proposal has been accepted and included in a draft revision of the Open Job Description specification. |
| [6 - Released](#Released) | [rfc/released] | The proposal has been included in a published revision of the Open Job Description specification. |

There are two additional statuses for RFCs that will not move forward:
- **[Abandoned](#Abandoned)** (label: [rfc/abandoned]) - The RFC's author(s) have ceased to engage in the process, and the RFC's process is
  stalled. RFCs leave this state when the author(s) reengage, or a new champion from the community or team takes on
  advocating for the proposal.
- **[Closed](#Closed)** - The RFC was closed by the author, or the review process determined that the proposal will
  not be accepted. The tracking issue and pull request are closed in this stage.

[rfc/proposed]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/labels/rfc%2Fproposed
[rfc/exploring]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/labels/rfc%2Fexploring
[rfc/final-comments]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/labels/rfc%2Ffinal-comments
[rfc/accepted-future]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/labels/rfc%2Faccepted-future
[rfc/accepted-draft]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/labels/rfc%2Faccepted-draft
[rfc/accepted-staged]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/labels/rfc%2Faccepted-staged
[rfc/released]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/labels/rfc%2Freleased
[rfc/abandoned]: https://github.com/xxyggoqtpcmcofkc/openjd-specifications/labels/rfc%2Fabandoned

---

This RFC process is inspired by RFC processes in popular open source projects: [Yarn RFC process],
[Rust RFC process], [React RFC process], [Ember RFC process], [AWS CDK RFC process], and [Python PEP].

[yarn rfc process]: https://github.com/yarnpkg/rfcs
[rust rfc process]: https://github.com/rust-lang/rfcs
[react rfc process]: https://github.com/reactjs/rfcs
[ember rfc process]: https://github.com/emberjs/rfcs
[AWS CDK RFC process]: https://github.com/aws/aws-cdk-rfcs
[Python PEP]: https://peps.python.org/pep-0012/

