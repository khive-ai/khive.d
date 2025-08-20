"""Core composition fixtures for AgentComposer testing.

Provides standard test data, mock environments, and helper utilities
for testing agent composition functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from khive.services.composition.agent_composer import AgentComposer


@pytest.fixture
def temp_composition_env():
    """Create a complete temporary composition environment with roles and domains."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_path = Path(tmp_dir)

        # Create directory structure
        roles_dir = base_path / "roles"
        roles_dir.mkdir()
        domains_dir = base_path / "domains"
        domains_dir.mkdir()

        # Create standard roles
        create_test_roles(roles_dir)

        # Create standard domains
        create_test_domains(domains_dir)

        # Create configuration files
        create_config_files(base_path)

        yield base_path


@pytest.fixture
def composer_with_test_data(temp_composition_env):
    """Create an AgentComposer instance with comprehensive test data."""
    return AgentComposer(str(temp_composition_env))


@pytest.fixture
def mock_file_system():
    """Create a mock file system for testing without actual file I/O."""
    mock_files = {}

    def mock_read_text(self, encoding="utf-8"):
        path_str = str(self)
        if path_str in mock_files:
            return mock_files[path_str]
        raise FileNotFoundError(f"Mock file not found: {path_str}")

    def mock_write_text(self, content, encoding="utf-8"):
        mock_files[str(self)] = content

    def mock_exists(self):
        return str(self) in mock_files

    def mock_stat(self):
        mock_stat_result = MagicMock()
        content = mock_files.get(str(self), "")
        mock_stat_result.st_size = len(content.encode("utf-8"))
        return mock_stat_result

    with (
        patch.object(Path, "read_text", mock_read_text),
        patch.object(Path, "write_text", mock_write_text),
        patch.object(Path, "exists", mock_exists),
        patch.object(Path, "stat", mock_stat),
    ):
        yield mock_files


def create_test_roles(roles_dir: Path):
    """Create standard test roles for composition testing."""

    # Researcher role (markdown format)
    researcher_md = """# Researcher Role

```yaml
id: researcher
type: investigation
capabilities: [research, analyze, synthesize]
tools: [Read, WebSearch, Grep]
```

## Role
Research specialist focused on gathering and analyzing information from multiple sources.

## Purpose
Conduct thorough research and provide comprehensive analysis on assigned topics.

## Core Capabilities
- Information gathering from various sources
- Data analysis and pattern recognition
- Synthesis of complex information
- Critical evaluation of sources

## Decision Logic
1. Define research scope and objectives
2. Identify and evaluate information sources
3. Gather relevant data systematically
4. Analyze findings for patterns and insights
5. Synthesize results into actionable conclusions
"""
    (roles_dir / "researcher.md").write_text(researcher_md)

    # Analyst role (YAML format)
    analyst_data = {
        "identity": {
            "id": "analyst",
            "type": "analysis",
            "capabilities": ["analyze", "evaluate", "recommend"],
            "tools": ["Read", "Write", "Bash"],
        },
        "role": "Data analyst specializing in quantitative and qualitative analysis",
        "purpose": "Analyze complex datasets and provide actionable insights",
        "capabilities": "Statistical analysis, data visualization, pattern recognition",
        "decision_logic": "Apply analytical frameworks to evaluate data and generate insights",
    }
    (roles_dir / "analyst.yaml").write_text(yaml.dump(analyst_data))

    # Implementer role (markdown format)
    implementer_md = """# Implementer Role

```yaml
id: implementer
type: execution
capabilities: [implement, build, deploy]
tools: [Write, Edit, Bash, MultiEdit]
```

## Role
Software implementation specialist responsible for building and deploying solutions.

## Purpose
Transform designs and specifications into working software implementations.

## Core Capabilities
- Code development and implementation
- System architecture implementation
- Testing and quality assurance
- Deployment and maintenance

## Decision Logic
1. Review requirements and specifications
2. Design implementation approach
3. Develop code following best practices
4. Test implementation thoroughly
5. Deploy and monitor solution
"""
    (roles_dir / "implementer.md").write_text(implementer_md)

    # Tester role (YAML format)
    tester_data = {
        "identity": {
            "id": "tester",
            "type": "validation",
            "capabilities": ["test", "validate", "verify"],
            "tools": ["Bash", "Read", "Write"],
        },
        "role": "Quality assurance specialist focused on comprehensive testing",
        "purpose": "Ensure software quality through systematic testing approaches",
        "capabilities": "Test design, execution, automation, and quality metrics",
        "decision_logic": "Create comprehensive test strategies and validate system behavior",
    }
    (roles_dir / "tester.yaml").write_text(yaml.dump(tester_data))

    # Critic role (markdown with complex structure)
    critic_md = """# Critic Role

```yaml
id: critic
type: evaluation
capabilities: [critique, evaluate, assess]
tools: [Read, Grep, WebSearch]
quality_thresholds:
  accuracy: 0.95
  completeness: 0.90
  relevance: 0.85
```

## Role
Critical evaluation specialist providing objective assessment and improvement recommendations.

## Purpose
Evaluate work quality, identify issues, and provide constructive feedback for improvement.

## Core Capabilities
- Critical analysis and evaluation
- Quality assessment frameworks
- Risk identification and mitigation
- Improvement recommendation generation

## Decision Logic
1. Establish evaluation criteria and standards
2. Systematically assess work against criteria
3. Identify strengths, weaknesses, and risks
4. Provide specific, actionable recommendations
5. Verify improvements meet quality standards

## Output Schema
```json
{
  "overall_rating": "number",
  "strengths": ["string"],
  "weaknesses": ["string"],
  "recommendations": ["string"],
  "risk_level": "string"
}
```
"""
    (roles_dir / "critic.md").write_text(critic_md)


def create_test_domains(domains_dir: Path):
    """Create standard test domains for composition testing."""

    # Flat structure domains
    software_arch_data = {
        "domain": {
            "id": "software-architecture",
            "name": "Software Architecture",
            "description": "System design and architectural patterns",
        },
        "knowledge_patterns": {
            "design_patterns": [
                "Microservices",
                "Event-Driven",
                "Layered Architecture",
                "Hexagonal Architecture",
                "CQRS",
                "Event Sourcing",
            ],
            "quality_attributes": [
                "Scalability",
                "Reliability",
                "Performance",
                "Security",
                "Maintainability",
                "Usability",
            ],
            "architectural_styles": [
                "Monolithic",
                "Distributed",
                "Service-Oriented",
                "Component-Based",
                "Pipe-and-Filter",
            ],
        },
        "decision_rules": {
            "design_principles": [
                "Single Responsibility Principle",
                "Open-Closed Principle",
                "Dependency Inversion",
                "Interface Segregation",
            ],
            "trade_offs": {
                "consistency_vs_availability": "Evaluate CAP theorem implications",
                "performance_vs_maintainability": "Balance optimization with code clarity",
                "security_vs_usability": "Implement security without compromising UX",
            },
            "confidence_thresholds": {
                "architecture_review": 0.90,
                "design_approval": 0.85,
                "risk_assessment": 0.95,
            },
        },
        "specialized_tools": {
            "modeling": ["C4 Model", "UML", "ArchiMate"],
            "analysis": ["ATAM", "SAAM", "Architecture Trade-off Analysis"],
            "documentation": ["ADRs", "Architecture Diagrams", "API Specs"],
        },
    }
    (domains_dir / "software-architecture.yaml").write_text(
        yaml.dump(software_arch_data)
    )

    # Code quality domain
    code_quality_data = {
        "domain": {
            "id": "code-quality",
            "name": "Code Quality Assurance",
            "description": "Software quality metrics and improvement practices",
        },
        "knowledge_patterns": {
            "quality_metrics": [
                "Cyclomatic Complexity",
                "Code Coverage",
                "Technical Debt",
                "Maintainability Index",
                "Code Duplication",
            ],
            "testing_strategies": [
                "Unit Testing",
                "Integration Testing",
                "E2E Testing",
                "Performance Testing",
                "Security Testing",
                "Mutation Testing",
            ],
            "code_smells": [
                "Long Method",
                "Large Class",
                "Duplicate Code",
                "Dead Code",
                "Complex Conditional",
                "Feature Envy",
            ],
        },
        "decision_rules": {
            "quality_gates": [
                {
                    "condition": "new_code",
                    "requirements": ["coverage_80", "no_blocker_issues"],
                },
                {
                    "condition": "release",
                    "requirements": ["coverage_90", "security_scan_pass"],
                },
                {
                    "condition": "hotfix",
                    "requirements": ["critical_tests_pass", "code_review"],
                },
            ],
            "refactoring_triggers": [
                "complexity_threshold_exceeded",
                "duplication_above_5_percent",
                "technical_debt_ratio_high",
            ],
            "confidence_thresholds": {
                "code_review_approval": 0.90,
                "automated_test_pass": 0.95,
                "security_scan_clean": 0.99,
            },
        },
        "specialized_tools": {
            "static_analysis": ["SonarQube", "CodeClimate", "ESLint", "Pylint"],
            "testing": ["pytest", "Jest", "JUnit", "Cypress"],
            "coverage": ["coverage.py", "Istanbul", "JaCoCo"],
            "security": ["SAST", "DAST", "Dependency Check"],
        },
    }
    (domains_dir / "code-quality.yaml").write_text(yaml.dump(code_quality_data))

    # Create hierarchical domain structure
    create_hierarchical_domains(domains_dir)


def create_hierarchical_domains(domains_dir: Path):
    """Create hierarchical domain taxonomy structure."""

    # Engineering category
    engineering_dir = domains_dir / "engineering"
    engineering_dir.mkdir()

    # Backend development domain
    backend_data = {
        "domain": {
            "id": "backend-development",
            "name": "Backend Development",
            "description": "Server-side application development",
        },
        "knowledge_patterns": {
            "frameworks": ["FastAPI", "Django", "Spring Boot", "Express.js"],
            "databases": ["PostgreSQL", "MongoDB", "Redis", "Elasticsearch"],
            "messaging": ["RabbitMQ", "Apache Kafka", "Redis Pub/Sub"],
            "deployment": ["Docker", "Kubernetes", "AWS", "CI/CD"],
        },
        "decision_rules": {
            "technology_selection": [
                "Consider scalability requirements",
                "Evaluate team expertise",
                "Assess ecosystem maturity",
                "Review licensing and costs",
            ],
            "confidence_thresholds": {
                "api_design": 0.85,
                "database_schema": 0.90,
                "deployment_strategy": 0.88,
            },
        },
        "specialized_tools": {
            "development": ["IDE", "API Client", "Database Client"],
            "testing": ["Postman", "pytest", "Locust"],
            "monitoring": ["Prometheus", "Grafana", "ELK Stack"],
        },
    }
    (engineering_dir / "backend-development.yaml").write_text(yaml.dump(backend_data))

    # Operations category
    operations_dir = domains_dir / "operations"
    operations_dir.mkdir()

    # DevOps automation domain
    devops_data = {
        "domain": {
            "id": "devops-automation",
            "name": "DevOps Automation",
            "description": "Automated deployment and operations",
        },
        "knowledge_patterns": {
            "ci_cd_patterns": ["GitFlow", "Trunk-based", "Feature Branching"],
            "infrastructure": ["Infrastructure as Code", "Container Orchestration"],
            "monitoring": ["Observability", "Alerting", "Log Aggregation"],
            "security": ["DevSecOps", "Compliance", "Vulnerability Management"],
        },
        "decision_rules": {
            "automation_priorities": [
                "Build and test automation first",
                "Deployment automation second",
                "Infrastructure automation third",
                "Monitoring automation throughout",
            ],
            "confidence_thresholds": {
                "pipeline_reliability": 0.95,
                "deployment_success": 0.98,
                "rollback_capability": 0.99,
            },
        },
        "specialized_tools": {
            "ci_cd": ["Jenkins", "GitHub Actions", "GitLab CI"],
            "infrastructure": ["Terraform", "Ansible", "CloudFormation"],
            "containers": ["Docker", "Kubernetes", "Helm"],
            "monitoring": ["Datadog", "New Relic", "Splunk"],
        },
    }
    (operations_dir / "devops-automation.yaml").write_text(yaml.dump(devops_data))


def create_config_files(base_path: Path):
    """Create configuration files for the test environment."""

    # Agent prompts configuration
    agent_prompts = {
        "system_prompts": {
            "researcher": "You are a thorough research specialist...",
            "analyst": "You are an analytical expert...",
            "implementer": "You are a skilled software developer...",
            "tester": "You are a quality assurance specialist...",
            "critic": "You are a critical evaluator...",
        },
        "templates": {
            "task_context": "TASK CONTEXT: {context}",
            "domain_expertise": "DOMAIN EXPERTISE: {domains}",
            "coordination": "COORDINATION PROTOCOL: {protocol}",
        },
    }
    (base_path / "agent_prompts.yaml").write_text(yaml.dump(agent_prompts))

    # Domain name mapper
    name_mapper = {
        "synonyms": {
            "software_architecture": "software-architecture",
            "code_quality": "code-quality",
            "backend": "backend-development",
            "devops": "devops-automation",
            "testing": "code-quality",
            "qa": "code-quality",
            "architecture": "software-architecture",
        },
        "canonical_domains": [
            "software-architecture",
            "code-quality",
            "backend-development",
            "devops-automation",
        ],
    }
    (base_path / "name_mapper.yaml").write_text(yaml.dump(name_mapper))


@pytest.fixture
def sample_agent_compositions():
    """Provide sample agent composition results for testing."""
    return {
        "researcher_only": {
            "identity": {"id": "researcher", "type": "investigation"},
            "role": "Research specialist",
            "purpose": "Conduct thorough research",
            "capabilities": "Information gathering and analysis",
        },
        "analyst_with_domain": {
            "identity": {"id": "analyst", "type": "analysis"},
            "role": "Data analyst",
            "purpose": "Analyze complex datasets",
            "domains": [{"id": "code-quality"}],
            "domain_patterns": {
                "quality_metrics": ["Cyclomatic Complexity", "Code Coverage"]
            },
            "domain_rules": {"quality_gates": [{"condition": "new_code"}]},
            "domain_tools": {"static_analysis": ["SonarQube", "ESLint"]},
        },
        "implementer_multi_domain": {
            "identity": {"id": "implementer", "type": "execution"},
            "role": "Software implementation specialist",
            "domains": [{"id": "software-architecture"}, {"id": "backend-development"}],
            "domain_patterns": {
                "design_patterns": ["Microservices", "Event-Driven"],
                "frameworks": ["FastAPI", "Django"],
            },
            "domain_thresholds": {"architecture_review": 0.90, "api_design": 0.85},
        },
    }


@pytest.fixture
def composition_test_scenarios():
    """Provide test scenarios for agent composition."""
    return [
        {
            "name": "simple_role_only",
            "role": "researcher",
            "domains": None,
            "context": None,
            "expected_keys": ["identity", "role", "purpose"],
        },
        {
            "name": "role_with_single_domain",
            "role": "analyst",
            "domains": "code-quality",
            "context": None,
            "expected_keys": ["identity", "domains", "domain_patterns"],
        },
        {
            "name": "role_with_multiple_domains",
            "role": "implementer",
            "domains": "software-architecture,backend-development",
            "context": None,
            "expected_keys": ["domains", "domain_thresholds"],
        },
        {
            "name": "full_composition",
            "role": "critic",
            "domains": "code-quality,software-architecture",
            "context": "Evaluate the new authentication system",
            "expected_keys": ["task_context", "domains", "domain_patterns"],
        },
    ]


@pytest.fixture
def thread_safety_setup():
    """Setup for thread safety testing."""
    return {
        "thread_count": 8,
        "operations_per_thread": 25,
        "test_duration": 10.0,  # seconds
        "expected_success_rate": 0.95,
    }


def create_mock_composer(base_path: str | None = None):
    """Create a mock AgentComposer for testing."""
    mock_composer = MagicMock(spec=AgentComposer)

    # Mock basic attributes
    mock_composer.base_path = Path(base_path or "/tmp/test")
    mock_composer.roles_path = mock_composer.base_path / "roles"
    mock_composer.domains_path = mock_composer.base_path / "domains"
    mock_composer._seen_pairs = set()
    mock_composer._agent_prompts = {}
    mock_composer._domain_mapper = {"synonyms": {}, "canonical_domains": []}

    # Mock methods with realistic behavior
    mock_composer._sanitize_input.side_effect = lambda x: x.replace("../", "").replace(
        "/", "_"
    )[:255]
    mock_composer._sanitize_context.side_effect = lambda x: x.replace(
        "system:", "[FILTERED]"
    )
    mock_composer._sanitize_cache_key.side_effect = lambda x: x.replace("/", "_")[:100]
    mock_composer._is_safe_path.return_value = True

    return mock_composer
