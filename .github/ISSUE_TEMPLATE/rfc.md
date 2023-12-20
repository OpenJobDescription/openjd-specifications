---
name: "Request for Comment (RFC)"
description: "Create a tracking issue for an RFC."
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
       add URLs to those here. Otherwise, remove this bullet point.)

## Description

A short description of the proposal.

## Roles

| Role | User
| ---- | ----
| Proposed By | @alias
| Author(s)   | @alias

## Workflow

- [x] Tracking issue created (label: `rfc/proposed`)
- [ ] RFC pull request submitted and ready for discussion (label: `rfc/exploring`)
- [ ] Last call for comments (labels: `rfc/exploring` and `rfc/final-comments`)
- [ ] Accepted and merged RFC pull request (label: `rfc/accepted-future`)
- [ ] Green-light for inclusion in a draft specification, and the author is creating and iterating on pull requests (label: `rfc/accepted-draft`)
- [ ] Pull requests are merged in to a draft specification (label: `rfc/accepted-staged`)
- [ ] Officially published in a non-draft revision of the specification (label: `rfc/released`)

Please close this tracking issue when the proposal enters the `Released` stage of the process.

## Open Points

For easier discovery, especially if there is a lot of discussion on this issue, then please keep this section updated
with brief summaries and pointers to the main points of discussion.

---

> The author is responsible to progress the RFC according to this checklist, and
apply the relevant labels to this issue.