# Documentation Index — VoteChain V3

This folder contains project documentation for VoteChain V3. Use this index to quickly find reference docs, diagrams, and operational guides.

## How to use

- Open files in VS Code and use the Markdown preview (`Ctrl+Shift+V`) to see rendered diagrams (Mermaid support recommended).
- Files marked **(Mermaid)** contain embedded Mermaid diagrams that render in supported viewers.

## Contents

- `ARCHITECTURE.md` — System-level architecture and diagrams (Deployment, Logical/class diagram, Runtime). **(Mermaid)**
- `DATAFLOW_DIAGRAM.md` — Dataflow description and flowchart showing interactions between Kiosk, Backend, Supabase, Ethereum, and Frontend. **(Mermaid)**
- `ENTITY_RELATIONSHIP_DIAGRAM.md` — ER / data model overview; includes a renderable Mermaid `classDiagram` representing Voter, Candidate, Vote, Admin, and Config entities. **(Mermaid)**
- `SOFTWARE_REQUIREMENTS_SPECIFICATION.md` — Software requirements specification (SRS) describing functional and non-functional software requirements.
- `SYSTEM_REQUIREMENTS_SPECIFICATION.md` — System/Hardware requirements (SyRS) for kiosks and backend deployment.

## Operational & Reference Docs (recommended)

These files may exist or be useful additions; check the repository root or `docs/` for similar names.

- `SERVICE_DISCOVERY.md` — How the frontend discovers the backend URL via Supabase and Cloudflare Tunnel integration.
- `DEPLOYMENT.md` — Deployment instructions for backend, kiosk, and smart contract (Hardhat) steps.
- `HARDWARE.md` — Kiosk wiring, fingerprint scanner integration, pin mappings, and hardware troubleshooting.
- `SECURITY.md` — Secrets management, Supabase RLS, and private-key handling guidance.
- `TESTING.md` / `TEST_CASES.md` — How to run tests and the test cases to validate enrollment, voting, and results flows.
- `OPERATIONAL_RUNBOOK.md` — Runbook for starting/stopping services, monitoring, and recovery steps.

## Contributing to docs

- Follow the repository's Markdown conventions and run markdownlint if available.
- Prefer Mermaid diagrams embedded in Markdown for portability and easy previews.
- Keep documentation up to date when changing APIs, database schemas, or deployment flows.

## Contact

For questions about documentation content or to request new docs, open an issue or create a PR with the proposed document.
