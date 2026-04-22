
* Feature Name: range_based_capability_matching
* Author(s): Johannes Oehmen `[oehmends](https://github.com/oehmends)`
* RFC Tracking Issue: https://github.com/OpenJobDescription/openjd-specifications/issues/134
* Start Date: 2026-04-22
* Specification Version: 2023-09
* Accepted On: (pending)

## Summary

This RFC proposes adding normative language to the Open Job Description specification that
defines how scheduling systems should match Step amount requirements against hosts or fleets
that advertise a **range** of capabilities (e.g., vCPU min–max). The current specification
defines the data model for requirements and capabilities but does not specify matching
semantics for range-based capability advertisements. This gap has led to implementations
that match only against the lower bound of a capability range, forcing users to maintain
separate fleets for each resource tier — defeating the purpose of flexible fleet sizing.

## Basic Examples

### Current behavior (problematic)

A fleet is configured with a vCPU range of 64–128, meaning it can provision instances
anywhere in that range. A job step requires 96 vCPUs:

```yaml
steps:
- name: HeavyRender
  hostRequirements:
    amounts:
    - name: amount.worker.vcpu
      min: 96
  script:
    actions:
      onRun:
        command: bash
        args: ["render.sh"]
```

**Expected**: The fleet is compatible — it can provision a 96-vCPU instance.
**Actual**: The fleet is rejected because the compatibility check compares the step's
requirement (96) against the fleet's minimum capability (64), not its maximum (128).

### Workaround required today

Users must either:

1. Set the fleet's minimum vCPU to 128 (wasting resources on smaller jobs), or
2. Create separate fleets for each vCPU tier (64-vCPU fleet, 96-vCPU fleet, 128-vCPU fleet),
   each requiring its own service quotas and adding operational overhead.

### Expected behavior with this proposal

A fleet advertising capability range [64, 128] for `amount.worker.vcpu` should be
considered compatible with any step requiring an amount within that range. A step
requiring 96 vCPUs matches because 96 ≤ 128 (the fleet's maximum).

## Motivation

### The problem

The Open Job Description specification defines `<AmountRequirement>` with `min` and `max`
fields for step requirements, and the worker agent reports single-valued capabilities
(e.g., `amount.worker.vcpu = 96`). However, the specification does not define how a
scheduling system should evaluate compatibility when a fleet or host pool advertises a
**range** of capabilities rather than a single value.

This gap matters because modern cloud-based render farms use auto-scaling fleets that
can provision instances across a range of configurations. A fleet configured with
vCPU range 64–128 is telling the scheduler: "I can provide workers with anywhere from
64 to 128 vCPUs." The scheduler should treat the fleet's **maximum** as the upper bound
of what it can deliver when evaluating whether a step's requirements can be met.

### Real-world impact

Without defined matching semantics, implementations have defaulted to matching against
the fleet's minimum capability. This creates significant operational burden:

1. **Fleet proliferation**: Users must create separate fleets for each resource tier
   (e.g., one fleet for 64-vCPU jobs, another for 96-vCPU jobs, another for 128-vCPU
   jobs). Each fleet requires its own service quotas, monitoring, and configuration.

2. **Wasted resources**: Alternatively, users set the fleet minimum to the highest value
   any job might need, which means smaller jobs get over-provisioned instances, increasing
   cost with no benefit.

3. **Reduced scheduling flexibility**: The entire point of defining a capability range is
   to allow the scheduler to right-size instances for each job. Matching only against the
   minimum eliminates this flexibility.

4. **Quota pressure**: Each additional fleet consumes service quotas. Users who need
   multiple vCPU/memory tiers must request quota increases for each fleet, adding
   administrative overhead.

This issue affects both `amount.worker.vcpu` and `amount.worker.memory` — users face
the same problem for memory-based requirements, compounding the fleet proliferation issue.

### Use cases supported

1. **Flexible fleet sizing**: A single fleet with vCPU range 64–128 serves jobs requiring
   64, 96, or 128 vCPUs. The scheduler provisions the right-sized instance for each job.

2. **Cost optimization**: Smaller jobs get smaller instances; larger jobs get larger
   instances. No over-provisioning.

3. **Simplified operations**: One fleet to manage instead of N fleets per resource tier.
   Fewer quotas to request, fewer configurations to maintain.

## Specification

### Capability advertisements

A scheduling system may advertise host or fleet capabilities as either:

1. **Single value**: A specific amount of a capability (e.g., `amount.worker.vcpu = 96`).
   This is the existing behavior for individual workers.

2. **Range**: A minimum and maximum amount of a capability
   (e.g., `amount.worker.vcpu = [64, 128]`). This represents a pool of hosts or a fleet
   that can provision workers anywhere within the range.

### Matching semantics for amount requirements

When evaluating whether a capability advertisement satisfies an `<AmountRequirement>`:

#### Single-value capability

Given a step requirement with `min` = R_min and `max` = R_max, and a host capability
value C:

- The capability satisfies the requirement if and only if:
  - R_min is not defined, or C ≥ R_min
  - R_max is not defined, or C ≤ R_max

This is the existing behavior for individual worker-to-step matching.

#### Range-valued capability

Given a step requirement with `min` = R_min and `max` = R_max, and a capability range
[C_min, C_max]:

- The capability range satisfies the requirement if and only if:
  - R_min is not defined, or C_max ≥ R_min (the fleet **can** provide at least R_min)
  - R_max is not defined, or C_min ≤ R_max (the fleet has instances small enough to
    not exceed R_max)

In plain language: a fleet is compatible with a step if there exists at least one
value in the fleet's range that satisfies the step's requirement. The fleet's maximum
determines whether it can meet the step's minimum requirement, and the fleet's minimum
determines whether it can stay within the step's maximum constraint.

#### Examples

| Fleet range | Step requires min | Step requires max | Compatible? | Reason |
|-------------|-------------------|-------------------|-------------|--------|
| [64, 128]   | 96                | —                 | Yes         | Fleet max (128) ≥ 96 |
| [64, 128]   | 256               | —                 | No          | Fleet max (128) < 256 |
| [64, 128]   | —                 | 48                | No          | Fleet min (64) > 48 |
| [64, 128]   | 64                | 96                | Yes         | 128 ≥ 64 and 64 ≤ 96 |
| [64, 128]   | 96                | 96                | Yes         | 128 ≥ 96 and 64 ≤ 96 |
| [128, 128]  | 96                | —                 | Yes         | Equivalent to single-value 128 |

### Instance selection

When a fleet's capability range satisfies a step's requirement, the scheduling system
SHOULD provision a worker with a capability value that:

1. Is ≥ R_min (if defined)
2. Is ≤ R_max (if defined)
3. Is within [C_min, C_max]

The specific value chosen within these constraints is an implementation detail of the
scheduling system (e.g., it may optimize for cost, availability, or bin-packing).

## Design Choice Rationale

### Why match against the fleet maximum, not minimum

The fleet's minimum represents the smallest instance the fleet might provision. The
fleet's maximum represents the largest. When a step says "I need at least 96 vCPUs,"
the relevant question is "can this fleet provide a worker with 96 vCPUs?" — which is
answered by the fleet's maximum, not its minimum.

Matching against the minimum is overly conservative: it assumes the fleet will always
provision the smallest possible instance, which is not how auto-scaling fleets work.
The scheduler controls instance selection and can provision an appropriately sized
instance for each job.

### Why use range overlap rather than containment

We define compatibility as "there exists a valid value in the intersection of the
fleet's range and the step's requirement range." This is more permissive than requiring
the fleet's range to fully contain the step's range, and correctly handles the common
case where a step specifies only a minimum requirement.

### Why this belongs in the specification

Without normative matching semantics, each implementation makes its own choice, leading
to inconsistent behavior across scheduling systems. Users writing portable job templates
cannot predict whether their fleet configurations will work. Defining the matching
semantics in the specification ensures consistent, predictable behavior.

## Prior Art

- **Kubernetes resource requests/limits**: Kubernetes matches pod resource requests
  against node capacity (the node's total, analogous to our fleet maximum), not against
  any minimum. A pod requesting 4 CPUs can be scheduled on any node with ≥ 4 CPUs
  available.

- **AWS EC2 Fleet**: EC2 Fleet allows specifying instance type ranges (e.g., vCPU range)
  and selects instances that meet the requirements. The fleet's capability is defined by
  what it *can* provision, not by its minimum configuration.

- **HTCondor ClassAds**: HTCondor's matchmaking evaluates boolean expressions over
  machine and job attributes. A machine advertising `Cpus = 96` matches a job requiring
  `Cpus >= 64`. Range-based matching is naturally supported through the expression
  language.

## Rejected Ideas

### Require users to create separate fleets per tier

This is the current workaround and is explicitly what this RFC aims to eliminate. It
creates operational overhead, quota pressure, and defeats the purpose of flexible fleet
sizing.

### Match against the arithmetic mean of the range

Matching against the midpoint of the range would be arbitrary and would still reject
valid configurations. There is no principled reason to use the mean.

### Leave matching semantics undefined

The current state of affairs. This has led to implementations that match against the
minimum, causing the problems described in the Motivation section. Explicit semantics
prevent this class of issues.

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal license, whichever is more permissive.
