# BountyOps — DoraHacks Writeup Draft

## One-liner

BountyOps is an autonomous bounty intelligence and submission procurement agent: it scouts paid builder opportunities, scores expected value, then hires specialist CAP agents to prepare a complete submission pack.

## Problem

Builders are surrounded by hackathons, grants, bounties, and RFPs, but most opportunities are hard to compare. Prize size, competition density, deadline, fit, and submission effort are scattered across platforms. Builders either miss profitable opportunities or spend time on low-ROI ones.

## Solution

BountyOps turns opportunity discovery into a paid A2A workflow. A buyer agent sends a builder profile and opportunity. BountyOps evaluates the opportunity, creates specialist orders, pays/calls multiple agents, verifies the deliverables, and returns a submission-ready package.

## A2A composability

BountyOps hires five specialist agents:

1. OpportunityScoutAgent — extracts facts, requirements, deadlines, and competition density.
2. ROIScorerAgent — calculates expected value and go/no-go.
3. AgentDesignerAgent — selects the best project angle and tracks.
4. SubmissionWriterAgent — drafts README, writeup, and demo script.
5. VerifierAgent — checks compliance and creates a proof hash.

This demonstrates agent commerce: discovery, hiring, priced work, delivery verification, and final composition.

## CROO demo

The demo uses the CROO Agent Hackathon as the first opportunity. BountyOps determines that the expected value is strong because the prize pool is meaningful, visible competition is low, and the judging criteria reward A2A composability. It recommends building BountyOps itself and generates the submission pack.

## Why it matters beyond the hackathon

BountyOps can be used by any builder or agent that wants to find monetizable opportunities and prepare submissions. It can support hackathons, grants, bounties, startup programs, and developer RFPs.

## Tracks

Primary: Open – Any A2A Agents
Secondary: Developer Tooling Agents
