---
name: openjd-rfc-review
description: Review Open Job Description RFC proposals for completeness, clarity, and alignment with design tenets. Use when reviewing RFC documents, providing feedback on RFC pull requests, or evaluating proposed OpenJD specification changes.
tags: [openjd, rfc, review, specification]
---

# OpenJD RFC Review

## Overview
Guide for reviewing Open Job Description RFC proposals to ensure quality, completeness,
alignment with project tenets, and compatibility with existing specifications.

## Usage
Use this skill when:
- Reviewing an Open Job Description RFC document for the `openjd-specifications` project in its `rfcs/` directory.
- Providing feedback on an RFC pull request
- Evaluating whether an RFC is ready for final comments period
- Checking RFC compliance with template requirements

## Core Concepts

### Design Tenets
Every RFC **MUST** align with these tenets (unless you know better ones):

1. **Portable** - Features should work across different operating systems, queuing implementations, and technology stacks
2. **Expressive** - Features should be general, not narrowly tailored to specific use cases
3. **Human readable and writable** - Artifacts should be easily understood and authored with a text editor
4. **Tooling parseable** - Artifacts should be parseable by automated tooling

### RFC Template Sections
Required sections per `0000-template.md`:
- **Summary** - One paragraph overview
- **Basic Examples** - Usage demonstrations for schema/syntax changes
- **Motivation** - Use cases, workflows enabled, how common they are
- **Specification** - Specific changes in formal specification style
- **Design Choice Rationale** - Reasoning for each significant decision
- **Prior Art** - Similar features in other systems
- **Rejected Ideas** - Ideas considered but not pursued
- **Copyright** - Public domain or CC0-1.0-Universal

### RFC Metadata
Required header fields:
- Feature Name (unique identifier)
- RFC Tracking Issue URL
- Start Date (YYYY-MM-DD)
- Specification Version (e.g., `2023-09 extension EXTENSION_NAME`)
- Accepted On (filled when accepted)

### Compatibility with Open Job Description Specifications
Every RFC proposed change must fit into the formal template specification in the `openjd-specifications` repo
in wiki/2023-09-Template-Schemas, or downloadable at https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas.

* If the RFC adds sections similar to existing sections, are they consistent with the existing sections in context?
* Does the proposed new language fit naturally into the specification?
* Do the high level ideas fit well with the existing concepts in the specification?
* Do they apply orthogonally, as general features should, or do they have special cases that limit applicability?
* Does the combined system feel consistent and whole, not disparate pieces bolted together?

## Review Checklist

### Completeness
- [ ] All template sections present and substantive
- [ ] Metadata fields filled correctly
- [ ] Tracking issue exists and linked
- [ ] Examples are runnable and demonstrate the feature

### Clarity
- [ ] Summary captures the essence in one paragraph
- [ ] Motivation explains WHY, not just WHAT
- [ ] Examples succinctly demonstrate the proposal in practice
- [ ] Specification is precise enough to implement
- [ ] Design rationale explains key decisions

### Tenet Alignment
- [ ] **Portable**: Does this work across systems? Does it make any assumptions that won't apply on a different OS, data management system, etc.?
- [ ] **Expressive**: Is this general or too narrowly tailored?
- [ ] **Human readable**: Can users understand this from reading the template?
- [ ] **Human writeable**: Can users write templates with this, and not get lost in boilerplate or complicated details?
- [ ] **Tooling parseable**: Can automated tools process a template with the feature and unambiguously determine author intent?

### Specification Compatibility
- [ ] Proposed language fits naturally into the specification
- [ ] High level ideas fit well with existing concepts
- [ ] New concepts apply orthogonally with existing features
- [ ] Combined work is consistent and whole

### Technical Quality
- [ ] Specification diff is syntactically correct
- [ ] Examples validate against proposed schema
- [ ] Edge cases addressed
- [ ] Backward compatibility considered
- [ ] Extension naming follows conventions

### Process
- [ ] Prior art section shows research was done
- [ ] Rejected ideas explain why alternatives weren't chosen
- [ ] No unresolved open questions blocking acceptance

## Common Issues

### Weak Motivation
**Problem**: "Users want this feature" without explaining workflows enabled.
**Fix**: Describe concrete use cases and how common they are.

### Vague Specification
**Problem**: Prose description instead of formal specification language.
**Fix**: Write as if it could be dropped into the spec document directly.

### Missing Rationale
**Problem**: Design choices made without explaining alternatives considered.
**Fix**: For each significant choice, explain why this option over others.

### Tenet Violations
**Problem**: Feature is too specific to one workflow or system.
**Fix**: Generalize the feature or justify why specificity is necessary.

## Quick Reference

| Review Aspect | Key Question |
|---------------|--------------|
| Summary | Does one paragraph capture the proposal? |
| Motivation | Are use cases concrete and common? |
| Specification | Could this be copy-pasted into the spec? |
| Rationale | Are design choices explained? |
| Portability | Does this work everywhere? |
| Expressiveness | Is this general enough? |
| Readability | Can humans understand templates using this? |
| Parseability | Can tools process this? |

## Providing Feedback

When reviewing, structure feedback as:
1. **Summary assessment** - Overall readiness for acceptance
2. **Strengths** - What the RFC does well
3. **Tenet alignment** - How well the RFC exemplifies each tenet
4. **Specification compatibility** - How well the RFC fits with existing specification
5. **Required changes** - Blocking issues that must be addressed
6. **Suggestions** - Non-blocking improvements
7. **Questions** - Clarifications needed

Reference specific sections and line numbers. Cite design tenets when relevant.
