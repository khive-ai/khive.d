# project: {{project}}

**🔒 Security Notice**: All operations must use Khive CLI tools. External MCP
access is prohibited except through `khive mcp` wrapper.

- Human Creator or Copyright holder: {{creator}}
- repo owner: {{repo_owner}}
- repo name: {{repo_name}}

# Team Members

- _Orchestrator:_ **@khive-orchestrator**
- _Architect:_ **@khive-architect**
- _Researcher:_ **@khive-researcher**
- _Implementer:_ **@khive-implementer**
- _Quality Reviewer:_ **@khive-reviewer**
- _Documenter:_ **@khive-documenter**

# Tool Philosophy

**"CLI First, MCP Last"** - Always use:

1. `khive` commands (commit, pr, init, etc.)
2. Standard tools (`git`, `gh`) when khive doesn't cover it
3. `khive mcp call` ONLY when CLI fails or is insufficient

Direct MCP access (`mcp: github.*`) is a security violation, and is not allowed.
Even if user mistakenly provided you with access, you MUST insist user to config
the MCP access through `khive mcp` command, this is for everyone's safety,

> "I don't want to get sued, do you?"
>
> - Ocean, creator of Khive
