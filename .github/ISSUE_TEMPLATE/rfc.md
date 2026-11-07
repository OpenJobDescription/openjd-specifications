---
name: "Request for Comment (RFC)"
about: "Create a tracking issue for an RFC."
title: "RFC: (short description)"
labels:
- rfc/proposed
assignees:
- ddneilson
- mwiebe
---

* **Pull Request**: (Add the URL to the pull request here.)
* **Discussion Thread(s)**:
    * (If there are discussion forum threads where this RFC has been discussed, then
       please add URLs to those here. You can remove this bullet point otherwise.)

## Description

A short description of the proposal.

## Roles

| Role | User
| ---- | ----
| Proposed By | @alias
| Author(s)   | @alias

## Workflow

- [x] Tracking issue created (label: `rfc/proposed`)
- [ ] RFC pull request, with its wiki edits, submitted and ready for discussion (label: `rfc/exploring`)
- [ ] Prototype in openjd-rs linked from the RFC
- [ ] Last call for comments (labels: `rfc/exploring` and `rfc/final-comments`)
- [ ] RFC pull request, with its wiki edits, merged (label: `rfc/released`)

Please close this tracking issue when the RFC pull request is merged.

## Open Points

For easier discovery, especially if there is a lot of discussion on this issue, then please keep this section updated
with brief summaries and pointers to the main points of discussion.

---

> The author is responsible to progress the RFC according to this checklist, and
apply the relevant labels to this issue.