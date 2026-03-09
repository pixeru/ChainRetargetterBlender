# Chain Retargetter Blender

Chain Retargetter Blender is a Blender add-on focused on animation retargeting through bone chains.

The goal of the project is to make retargeting easier and more controllable by letting animators map and transfer motion chain by chain instead of forcing a full-rig solve or a tedious bone-by-bone workflow.

## Core Idea

Most retargeting workflows sit at one of two extremes:

- transfer everything at once and hope the rigs are similar enough
- manually adjust individual bones when they are not

This project is built around a middle-ground approach.

Instead of treating the rig as a single black box, the add-on should allow animation to be mapped and transferred one bone chain at a time, such as:

- spine
- neck and head
- arms
- hands
- legs
- feet

This chain-based workflow should provide much more control over how motion is interpreted between source and target rigs, especially when they do not share the same:

- proportions
- hierarchy
- naming conventions
- rest pose assumptions

## Project Vision

The add-on is intended to help bridge the gap between automation and manual control.

With a chain-focused retargeting workflow, the user should be able to:

- define corresponding source and target chains
- tune how translation and rotation are transferred per chain
- handle rigs with different proportions more predictably
- isolate and fix problem areas without reworking the entire retarget
- build a retarget setup that is easier to understand and debug

## Why Chain Retargeting

Animation problems usually do not affect every part of a character equally. A spine may need one strategy, arms another, and legs another again. Treating retargeting as a set of chain-level problems makes that complexity manageable.

This approach should make it easier to preserve intent in the original motion while adapting it to rigs that differ structurally from the source.

## Planned Direction

While the implementation is still being defined, the add-on is expected to focus on:

- chain mapping tools
- retarget transfer controls per chain
- workflows for rigs with non-matching proportions or hierarchy
- practical usability inside Blender for iterative animation work

## Status

Early project setup.