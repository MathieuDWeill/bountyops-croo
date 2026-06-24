# Why BountyOps Exists

## One-sentence pitch

BountyOps is an autonomous opportunity-to-submission agent: it finds paid builder opportunities, scores expected value, hires specialist agents, verifies deliverables, and produces a ready-to-submit package.

## The problem

Builders can earn money through hackathons, bounties, grants, RFPs, and startup programs.

But the opportunity market is fragmented.

A builder has to answer many questions manually:

- Is this opportunity worth my time?
- Is the prize large enough?
- Is the competition crowded?
- Do my skills fit the requirements?
- What should I build?
- What should I submit?
- Can I produce a strong demo before the deadline?

Most builders lose time either by missing good opportunities or by working on low-ROI ones.

## The simple idea

BountyOps helps a builder decide where to spend effort.

It does not only list opportunities. It turns an opportunity into an execution plan.

Given a paid opportunity, BountyOps:

1. extracts the key facts;
2. estimates expected value;
3. recommends whether to go or skip;
4. designs the strongest project angle;
5. hires specialist agents to prepare the submission;
6. verifies the final deliverable;
7. returns a proof hash and a CAP-style order ledger.

## Why this is a CROO-native idea

CROO is about agent commerce.

The core thesis is that agents should be able to discover, hire, pay, and verify other agents.

BountyOps demonstrates that thesis directly.

BountyOps acts as a buyer / procurement agent. It does not do all the work alone. It hires specialist agents:

- OpportunityScoutAgent
- ROIScorerAgent
- AgentDesignerAgent
- SubmissionWriterAgent
- VerifierAgent

Each agent performs a specific job. BountyOps pays them, collects their deliverables, verifies the output, and assembles the final package.

## The A2A workflow

Buyer Agent
→ BountyOps
→ OpportunityScoutAgent
→ ROIScorerAgent
→ AgentDesignerAgent
→ SubmissionWriterAgent
→ VerifierAgent
→ Final Submission Pack + Proof Hash

This is not just a chatbot workflow. It is an agent-commerce workflow.

## What BountyOps produces

For each opportunity, BountyOps returns:

- GO / MAYBE / NO_GO decision;
- expected value score;
- recommended project;
- recommended tracks;
- rationale;
- README outline;
- DoraHacks writeup draft;
- demo video script;
- submission checklist;
- specialist order ledger;
- proof hash.

## Mock mode vs live CROO mode

BountyOps has two modes.

CAP_MODE=mock is the deterministic local mode used for reproducible demos and tests.

CAP_MODE=live is the live integration path for CROO SDK, real agents, real orders, real wallets, and real deliverables.

The mock mode must not be presented as live settlement. It exists so judges and developers can reproduce the A2A workflow even without credentials.

## What is needed for full live CROO execution

To run BountyOps fully live on CROO, the project needs:

- CROO Agent Store listing;
- CROO SDK credentials;
- an agent wallet;
- at least one real buyer wallet;
- specialist counterparty agents;
- real or testnet orders;
- deliverable submission through CROO CAP.

The repository is designed so this live layer can be added without changing the core product logic.

## Why it can win

BountyOps matches the CROO judging criteria:

- Technical execution: working API, tests, CAP adapter, ledger, proof hash.
- A2A composability: multiple specialist agents are hired and paid.
- Innovation: it turns opportunity discovery into agent commerce.
- Usability: builders can use it to find and prepare money-making opportunities.
- Presentation: the CROO hackathon itself is used as a real demo case.

## Why it matters beyond this hackathon

Even if the CROO hackathon ends, the product remains useful.

BountyOps can be used for:

- Kaggle competitions;
- DoraHacks hackathons;
- Devpost hackathons;
- Gitcoin grants;
- web3 bounties;
- AI startup programs;
- research grants;
- RFPs;
- technical competitions.

The long-term product is simple:

Find where a builder can make money, then prepare the best possible submission.
