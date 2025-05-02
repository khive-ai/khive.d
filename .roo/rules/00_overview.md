# project: khive.d

- _GitHub Owner:_ **khive-ai**
- _Repository:_ **khive.d**

## 0. Project Team

- _Orchestrator:_ **@khive-orchestrator**
- _Architect:_ **@khive-architect**
- _Researcher:_ **@khive-researcher**
- _Implementer:_ **@khive-implementer**
- _Quality Reviewer:_ **@khive-quality-reviewer**
- _Documenter:_ **@khive-documenter**

## 1. Response Format

> **Every response must begin with a structured reasoning format**

```
To increase our reasoning context, Let us think through with 5 random perspectives in random order:
[^...] Reason / Action / Reflection / Expected Outcome
[^...] Reason / Action / Reflection / Expected Outcome
...
---
Then move onto answering the prompt.
```

### 1.1 Best Practices

- always starts with reading dev_style
- check which local branch you are working at and which one you should be
  working on
- use command line to manipulate local working branch
- must clear commit tree before calling completion
- if already working on a PR or issue, you can commit to the same branch if
  appropriate, or you can add a patch branch to that particular branch. You need
  to merge the patch branch to the "feature" branch before merging to the main
  branch.
- when using command line, pay attention to the directory you are in, for
  example if you have already done

  ```
  cd frontend
  npm install
  ```

  and now you want to build the frontend, the correct command is
  `npm run build`, and the wrong answer is `cd frontend && npm run build`.
- since you are in a vscode environment, you should always use local env to make
  changes to repo. use local cli when making changes to current working
  directory
- always checkout the branch to read files locally if you can, since sometimes
  Github MCP tool gives base64 response.
- must clear commit trees among handoffs.

- **Search first, code second.**
- Follow Conventional Commits.
- Run `khive ci` locally before pushing.
- Keep templates up to date; replace all `{{PLACEHOLDER:…}}`.
- Security, performance, and readability are non-negotiable.
- Be kind - leave code better than you found it. 🚀

### 1.. Citation

- All information from external searches must be properly cited
- Use `...` format for citations
- Cite specific claims rather than general knowledge
- Provide sufficient context around citations
- Never reproduce copyrighted content in entirety, Limit direct quotes to less
  than 25 words
- Do not reproduce song lyrics under any circumstances
- Summarize content in own words when possible

### 1.3 Thinking Methodologies

- **Creative Thinking** [^Creative]: Generate innovative ideas and
  unconventional solutions beyond traditional boundaries.

- **Critical Thinking** [^Critical]: Analyze problems from multiple
  perspectives, question assumptions, and evaluate evidence using logical
  reasoning.

- **Systems Thinking** [^System]: Consider problems as part of larger systems,
  identifying underlying causes, feedback loops, and interdependencies.

- **Reflective Thinking** [^Reflect]: Step back to examine personal biases,
  assumptions, and mental models, learning from past experiences.

- **Risk Analysis** [^Risk]: Evaluate potential risks, uncertainties, and
  trade-offs associated with different solutions.

- **Stakeholder Analysis** [^Stakeholder]: Consider human behavior aspects,
  affected individuals, perspectives, needs, and required resources.

- **Problem Specification** [^Specification]: Identify technical requirements,
  expertise needed, and success metrics.

- **Alternative Solutions** [^New]: Challenge existing solutions and propose
  entirely new approaches.

- **Solution Modification** [^Edit]: Analyze the problem type and recommend
  appropriate modifications to current solutions.

- **Problem Decomposition** [^Breakdown]: Break down complex problems into
  smaller, more manageable components.

- **Simplification** [^Simplify]: Review previous approaches and simplify
  problems to make them more tractable.

- **Analogy** [^Analogy]: Use analogies to draw parallels between different
  domains, facilitating understanding and generating new ideas.

- **Brainstorming** [^Brainstorm]: Generate a wide range of ideas and
  possibilities without immediate judgment or evaluation.

- **Mind Mapping** [^Map]: Visualize relationships between concepts, ideas, and
  information, aiding in organization and exploration of complex topics.

- **Scenario Planning** [^Scenario]: Explore potential future scenarios and
  their implications, helping to anticipate challenges and opportunities.

- **SWOT Analysis** [^SWOT]: Assess strengths, weaknesses, opportunities, and
  threats related to a project or idea, providing a structured framework for
  evaluation.

- **Design Thinking** [^Design]: Empathize with users, define problems, ideate
  solutions, prototype, and test, focusing on user-centered design principles.

- **Lean Thinking** [^Lean]: Emphasize efficiency, waste reduction, and
  continuous improvement in processes, products, and services.

- **Agile Thinking** [^Agile]: Embrace flexibility, adaptability, and iterative
  development, allowing for rapid response to changing requirements and
  feedback.

## 2. Core Principles

1. **Autonomy & Specialisation** - each agent sticks to its stage of the golden
   path.
2. **Search-Driven Development (MANDATORY)** - run `khive search` **before**
   design/impl _Cite result IDs / links in specs, plans, PRs, commits._
3. **TDD & Quality** - >80 pct combined coverage (`khive ci --threshold 80` in
   CI).
4. **Clear Interfaces** - `shared-protocol` defines Rust ↔ TS contracts; Tauri
   commands/events are the API.
5. **GitHub Orchestration** - Issues & PRs are the single source of truth.
6. **Use local read/edit** - use native roo tools for reading and editing files
7. **Local CLI First** - prefer plain `git`, `gh`, `pnpm`, `cargo`, plus helper
   scripts (`khive-*`).
8. **Standardised Templates** - Create via CLI (`khive new-doc`) and should be
   **filled** and put under `reports/...`
9. **Quality Gates** - CI + reviewer approval before merge.
10. **Know your issue** - always check the issue you are working on, use github
    intelligently, correct others mistakes and get everyone on the same page.

| code | template         | description           | folder         |
| ---- | ---------------- | --------------------- | -------------- |
| RR   | `RR-<issue>.md`  | Research Report       | `reports/rr/`  |
| TDS  | `TDS-<issue>.md` | Technical Design Spec | `reports/tds/` |
| IP   | `IP-<issue>.md`  | Implementation Plan   | `reports/ip/`  |
| TI   | `TI-<issue>.md`  | Test Implementation   | `reports/ti/`  |
| CRR  | `CRR-<pr>.md`    | Code Review Report    | `reports/crr/` |

if it's an issue needing zero or one pr, don't need to add suffix

**Example**

> khive new-doc RR 123 # RR = Research Report, this ->
> docs/reports/research/RR-123.md

if you are doing multiple pr's for the same issue, you need to add suffix

> _issue 150_ khive new-doc ID 150-pr1 # ID = Implementation plans, this ->
> docs/reports/plans/ID-150-pr1.md

> khive new-doc TDS 150-pr2

11. **Docs Mirror Reality** - update docs **after** Quality Review passes.

---

## 3. Golden Path & Roles

| Stage          | Role                     | Primary Artifacts (template)                 | Search citation |
| -------------- | ------------------------ | -------------------------------------------- | --------------- |
| Research       | `khive-researcher`       | `RR-<issue>.md`                              | ✅              |
| Design         | `khive-architect`        | `TDS-<issue>.md`                             | ✅              |
| Implement      | `khive-implementer`      | `IP-<issue>.md`, `TI-<issue>.md`, code+tests | ✅              |
| Quality Review | `khive-quality-reviewer` | `CRR-<pr>.md` (optional) + GH review         | verifies        |
| Document       | `khive-documenter`       | Updated READMEs / guides                     | N/A             |

Each artifact must be committed before hand-off to the next stage.

### 3.1 Team Roles

researcher · architect · implementer · quality-reviewer · documenter ·
orchestrator

### 3.2 Golden Path

1. Research → 2. Design → 3. Implement → 4. Quality-Review → 5. Document → Merge

## 4. Tooling Matrix

## Core Philosophy

- **Single entry-point** → `khive <command>`
- **Convention over config** → sensible defaults, TOML for the rest
- **CI/local parity** → the CLI and the GH workflow run the _same_ code
- **Idempotent helpers** → safe to run repeatedly; exit 0 on "nothing to do"
- **No lock-in** → wraps existing ecosystem tools instead of reinventing them

---

## Quick Start

```bash
# 1 · clone & install
$ git clone https://github.com/khive-dev/khive.git
$ cd khive
$ uv pip install -e .        # editable install - puts `khive` on your PATH

# 2 · bootstrap repo (node deps, rust fmt, git hooks, …)
$ khive init -v

# 3 · hack happily
$ khive fmt --check           # smoke-test formatting
$ khive ci --check            # quick pre-commit gate
```

---

## Command Catalogue

| Command         | What it does (TL;DR)                                                                       |
| --------------- | ------------------------------------------------------------------------------------------ |
| `khive init`    | Verifies toolchain, installs JS & Python deps, runs `cargo check`, wires Husky hooks.      |
| `khive fmt`     | Opinionated multi-stack formatter (`ruff` + `black`, `cargo fmt`, `deno fmt`, `markdown`). |
| `khive commit`  | Stages → (optional patch-select) → conventional commit → (optional) push.                  |
| `khive pr`      | Pushes branch & opens/creates GitHub PR (uses `gh`).                                       |
| `khive ci`      | Local CI gate - lints, tests, coverage, template checks. Mirrors GH Actions.               |
| `khive clean`   | Deletes a finished branch locally & remotely - never nukes default branch.                 |
| `khive new-doc` | Scaffolds markdown docs (ADR, RFC, IP…) from templates with front-matter placeholders.     |
| `khive reader`  | Opens/reads arbitrary docs via `docling`; returns JSON over stdout.                        |
| `khive search`  | Validates & (optionally) executes Exa/Perplexity searches.                                 |

Run `khive <command> --help` for full flag reference.

---

## Usage Examples

```bash
# format *everything*, fixing files in-place
khive fmt

# format only Rust & docs, check-only
khive fmt --stack rust,docs --check

# staged patch commit, no push (good for WIP)
khive commit "feat(ui): dark-mode toggle" --patch --no-push

# open PR in browser as draft
khive pr --draft --web

# run the same CI suite GH will run
khive ci

# delete old feature branch safely
khive clean feature/old-experiment --dry-run

# spin up a new RFC doc: docs/rfcs/RFC-001-streaming-api.md
khive new-doc RFC 001-streaming-api

# open a PDF & read slice 0-500 chars
DOC=$(khive reader open --source paper.pdf | jq -r .doc_id)
khive reader read --doc "$DOC" --end 500
```

| purpose                   | local CLI                                 | GitHub MCP                                                                |
| ------------------------- | ----------------------------------------- | ------------------------------------------------------------------------- |
| clone / checkout / rebase | `git`                                     | —                                                                         |
| multi-file commit         | `git add -A && git commit`                | `mcp: github.push_files` (edge cases)                                     |
| open PR                   | `gh pr create` _or_ `create_pull_request` | `mcp: github.create_pull_request`                                         |
| comment / review          | `gh pr comment` _or_ `add_issue_comment`  | `mcp: github.add_issue_comment`, `mcp: github.create_pull_request_review` |
| CI status                 | `gh pr checks`                            | `mcp: github.get_pull_request_status`                                     |

_(CLI encouraged; MCP always available)_

## 5. Validation Gates

- spec committed → CI green
- PR → Quality-Reviewer approves in coomments
- Orchestrator merges & tags

---

### 5.1 Quality Gates (CI + Reviewer)

1. **Design approved** - TDS committed, search cited.
2. **Implementation ready** - IP & TI committed, PR opened, local tests pass.
3. **Quality review** - Reviewer approves, coverage ≥ 80 pct, citations
   verified.
4. **Docs updated** - Documenter syncs docs.
5. **Merge & clean** - PR merged, issue closed, branch deleted.

---
