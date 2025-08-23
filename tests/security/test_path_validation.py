"""Path Validation Security Tests

Comprehensive testing of directory traversal attack prevention and path sanitization
effectiveness across all Pydantic models that handle file paths or path-like data.

Focus areas:
1. Directory traversal prevention (../, ..\\ patterns)
2. Absolute path injection prevention
3. Special file access prevention (/etc/passwd, /proc/*, etc.)
4. Path encoding bypass attempts
5. Mixed path separator handling
6. Long path attack prevention
"""

import pytest
from pydantic import ValidationError

from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.parts import AgentRequest


class TestDirectoryTraversalPrevention:
    """Test prevention of directory traversal attacks through various input vectors."""

    @pytest.fixture
    def directory_traversal_patterns(self) -> list[str]:
        """Comprehensive list of directory traversal attack patterns."""
        return [
            # Basic traversal patterns
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../../../home/user/.ssh/id_rsa",
            "../../../proc/self/environ",
            "..\\..\\..\\..\\..\\windows\\win.ini",
            # URL-encoded traversal
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "%2e%2e%5c%2e%2e%5c%2e%2e%5cwindows%5csystem32",
            # Double URL-encoded
            "%252e%252e%252f%252e%252e%252f%252e%252e%252fetc%252fpasswd",
            # Unicode normalization bypasses
            "\u002e\u002e\u002f\u002e\u002e\u002f\u002e\u002e\u002fetc\u002fpasswd",
            "\uff0e\uff0e\u002f\uff0e\uff0e\u002f\uff0e\uff0e\u002fetc\u002fpasswd",
            # Mixed separators
            "../..\\../etc/passwd",
            "..\\..//..\\windows/system32",
            # Null byte injection (historical)
            "../../../etc/passwd\x00.txt",
            "..\\..\\..\\windows\\system32\\config\\sam\x00.conf",
            # Long path traversal
            ("../" * 50) + "etc/passwd",
            ("..\\" * 50) + "windows\\system32\\config\\sam",
            # Absolute path with traversal
            "/etc/passwd/../../../etc/shadow",
            "C:\\Windows\\..\\..\\..\\Windows\\System32\\config\\SAM",
            # Case variations (for case-insensitive systems)
            "../../../ETC/PASSWD",
            "..\\..\\..\\WINDOWS\\SYSTEM32\\CONFIG\\SAM",
            # Path with embedded commands
            "../../../etc/passwd; cat /etc/shadow",
            "..\\..\\..\\windows\\system32\\config\\sam && dir",
            # Symlink-style attacks
            "/proc/self/cwd/../../../etc/passwd",
            "/proc/1/root/etc/passwd",
            # Network path injection
            "\\\\?\\C:\\Windows\\System32\\config\\SAM",
            "\\\\127.0.0.1\\c$\\Windows\\System32\\config\\SAM",
        ]

    def test_composer_request_context_path_validation(
        self, directory_traversal_patterns
    ):
        """Test ComposerRequest context field blocks directory traversal."""

        for malicious_path in directory_traversal_patterns:
            context_variations = [
                f"Read file: {malicious_path}",
                f"Process data from {malicious_path}",
                f"Load configuration: {malicious_path}",
                f"Import template: {malicious_path}",
                malicious_path,  # Direct path injection
            ]

            for context in context_variations:
                try:
                    request = ComposerRequest(
                        role="researcher", context=context, domains="file-operations"
                    )

                    # If we reach here, the malicious path was accepted
                    # Check if dangerous patterns remain
                    dangerous_patterns = [
                        "../",
                        "..\\/",
                        "/etc/",
                        "C:\\Windows",
                        "\\\\?\\",
                    ]
                    context_lower = request.context.lower()

                    for pattern in dangerous_patterns:
                        if pattern.lower() in context_lower:
                            pytest.fail(
                                f"Directory traversal pattern accepted in context: {pattern} in '{malicious_path}'"
                            )

                except ValidationError:
                    # Expected - validation should block malicious paths
                    pass

    def test_composer_request_domains_path_validation(
        self, directory_traversal_patterns
    ):
        """Test ComposerRequest domains field blocks directory traversal."""

        for malicious_path in directory_traversal_patterns:
            domain_variations = [
                malicious_path,
                f"file-operations,{malicious_path}",
                f"data-processing,path:{malicious_path}",
                f"{malicious_path},backend-development",
            ]

            for domain_spec in domain_variations:
                try:
                    request = ComposerRequest(
                        role="researcher",
                        context="Legitimate context",
                        domains=domain_spec,
                    )

                    # Check if dangerous path patterns remain in domains
                    if request.domains and isinstance(request.domains, str):
                        dangerous_patterns = ["../", "..\\/", "/etc/", "C:\\Windows"]
                        domains_lower = request.domains.lower()

                        for pattern in dangerous_patterns:
                            if pattern.lower() in domains_lower:
                                pytest.fail(
                                    f"Directory traversal in domains: {pattern} in '{malicious_path}'"
                                )

                except ValidationError:
                    # Expected - validation should block malicious domains
                    pass

    def test_agent_request_instruction_path_validation(
        self, directory_traversal_patterns
    ):
        """Test AgentRequest instruction field blocks directory traversal."""

        for malicious_path in directory_traversal_patterns:
            instruction_variations = [
                {
                    "instruction": f"Read file at {malicious_path}",
                    "context": "File reading task",
                },
                {
                    "instruction": "Process data",
                    "context": f"Load from {malicious_path}",
                },
                {
                    "instruction": "Analysis task",
                    "guidance": f"Use template: {malicious_path}",
                },
            ]

            for instruct_data in instruction_variations:
                try:
                    request = AgentRequest(
                        instruct=instruct_data, compose_request={"role": "researcher"}
                    )

                    # Check instruction content for dangerous patterns
                    instruct_str = str(
                        request.instruct.__dict__
                        if hasattr(request.instruct, "__dict__")
                        else request.instruct
                    )
                    dangerous_patterns = ["../", "..\\/", "/etc/", "C:\\Windows"]

                    for pattern in dangerous_patterns:
                        if pattern in instruct_str:
                            pytest.fail(
                                f"Directory traversal in instruction: {pattern} in '{malicious_path}'"
                            )

                except ValidationError:
                    # Expected - validation should block malicious instructions
                    pass


class TestAbsolutePathInjection:
    """Test prevention of absolute path injection attacks."""

    @pytest.fixture
    def absolute_path_attacks(self) -> list[str]:
        """List of absolute path injection attempts."""
        return [
            # Unix absolute paths
            "/etc/passwd",
            "/etc/shadow",
            "/proc/self/environ",
            "/proc/1/cmdline",
            "/dev/null",
            "/tmp/../etc/passwd",
            "/home/user/.ssh/id_rsa",
            "/root/.bashrc",
            # Windows absolute paths
            "C:\\Windows\\System32\\config\\SAM",
            "C:\\Users\\Administrator\\Documents\\secrets.txt",
            "D:\\sensitive\\data.db",
            "\\\\?\\C:\\Windows\\System32\\drivers\\etc\\hosts",
            # Network paths
            "\\\\localhost\\c$\\Windows\\System32",
            "\\\\127.0.0.1\\admin$\\system32\\config",
            "//etc/passwd",
            # Device files (Unix)
            "/dev/kmem",
            "/dev/mem",
            "/dev/random",
            "/proc/version",
            "/sys/class/dmi/id/product_name",
        ]

    def test_absolute_path_blocking(self, absolute_path_attacks):
        """Test that absolute paths are properly blocked or sanitized."""

        for absolute_path in absolute_path_attacks:
            test_contexts = [
                f"Access file: {absolute_path}",
                f"Load data from {absolute_path}",
                absolute_path,  # Direct injection
            ]

            for context in test_contexts:
                try:
                    request = ComposerRequest(
                        role="researcher", context=context, domains="file-access"
                    )

                    # If accepted, verify dangerous paths are sanitized
                    if any(
                        abs_pattern in request.context
                        for abs_pattern in ["/etc/", "C:\\Windows", "/proc/", "/dev/"]
                    ):
                        pytest.fail(
                            f"Absolute path injection accepted: {absolute_path}"
                        )

                except ValidationError:
                    # Expected - should block absolute paths
                    pass


class TestSpecialFileAccess:
    """Test prevention of access to special system files."""

    @pytest.fixture
    def special_system_files(self) -> list[str]:
        """List of special system files that should be protected."""
        return [
            # Linux/Unix special files
            "/etc/passwd",
            "/etc/shadow",
            "/etc/hosts",
            "/etc/sudoers",
            "/proc/self/maps",
            "/proc/self/environ",
            "/proc/version",
            "/sys/devices/system/memory/meminfo",
            # Windows special files
            "C:\\Windows\\System32\\config\\SAM",
            "C:\\Windows\\System32\\config\\SECURITY",
            "C:\\Windows\\System32\\config\\SYSTEM",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "C:\\pagefile.sys",
            "C:\\hiberfil.sys",
            # Application-specific sensitive files
            ".env",
            "config.ini",
            "database.sqlite",
            "private.key",
            "secrets.json",
            ".htpasswd",
        ]

    def test_special_file_access_prevention(self, special_system_files):
        """Test that access to special system files is prevented."""

        for special_file in special_system_files:
            access_attempts = [
                f"Read {special_file}",
                f"Load configuration from {special_file}",
                f"Process {special_file} contents",
                f"../../../{special_file}",  # Traversal to special file
                special_file,  # Direct access
            ]

            for attempt in access_attempts:
                try:
                    request = ComposerRequest(
                        role="researcher", context=attempt, domains="file-analysis"
                    )

                    # Check if special file references remain
                    context_lower = request.context.lower()
                    file_lower = special_file.lower()

                    if file_lower in context_lower:
                        pytest.fail(
                            f"Special file access attempt accepted: {special_file}"
                        )

                except ValidationError:
                    # Expected - should block special file access
                    pass


class TestPathEncodingBypass:
    """Test prevention of path encoding bypass attempts."""

    def test_url_encoding_bypass_prevention(self):
        """Test prevention of URL encoding bypasses."""

        encoded_payloads = [
            # URL encoded traversal
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "%2e%2e%5c%2e%2e%5c%2e%2e%5cwindows%5csystem32",
            # Double URL encoded
            "%252e%252e%252f%252e%252e%252f%252e%252e%252fetc%252fpasswd",
            # HTML entity encoding
            "&lt;script&gt;alert('path')&lt;/script&gt;",
            "&#46;&#46;&#47;&#46;&#46;&#47;etc&#47;passwd",
            # Unicode encoding
            "\u002e\u002e\u002f\u002e\u002e\u002f\u002e\u002e\u002fetc\u002fpasswd",
        ]

        for encoded_payload in encoded_payloads:
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Process file: {encoded_payload}",
                    domains="data-processing",
                )

                # Verify encoding didn't bypass validation
                if "../" in request.context or "\\" in request.context:
                    pytest.fail(f"Encoding bypass successful: {encoded_payload}")

            except ValidationError:
                # Expected - encoding bypass should be blocked
                pass

    def test_mixed_encoding_prevention(self):
        """Test prevention of mixed encoding attacks."""

        mixed_attacks = [
            "../%2e%2e/etc/passwd",  # Mixed normal and URL encoded
            "..\\%2e%2e\\windows\\system32",  # Mixed separators and encoding
            "%2e%2e/../etc/passwd",  # Mixed URL and normal
            "\u002e.\u002f../etc/passwd",  # Mixed unicode and normal
        ]

        for attack in mixed_attacks:
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Access: {attack}",
                    domains="file-system",
                )

                # Check if attack pattern bypassed validation
                dangerous_patterns = ["../", "..\\", "/etc/", "system32"]
                context_str = request.context

                for pattern in dangerous_patterns:
                    if pattern.lower() in context_str.lower():
                        pytest.fail(f"Mixed encoding bypass: {attack}")

            except ValidationError:
                # Expected - mixed encoding should be blocked
                pass


class TestLongPathAttacks:
    """Test prevention of long path attacks and buffer overflow attempts."""

    def test_long_path_dos_prevention(self):
        """Test prevention of DoS through extremely long paths."""

        # Generate very long path traversal attempts
        long_paths = [
            ("../" * 1000) + "etc/passwd",  # Very deep traversal
            ("../" * 5000) + "etc/passwd",  # Extremely deep
            "A" * 10000 + "/etc/passwd",  # Long directory name
            ("longdirectoryname/" * 100) + "../" * 100 + "etc/passwd",  # Mixed long
        ]

        for long_path in long_paths:
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Process: {long_path}",
                    domains="file-operations",
                )

                # Check if excessively long paths were accepted
                if len(request.context) > 1000:  # Reasonable limit
                    pytest.fail(
                        f"Long path attack accepted: {len(long_path)} characters"
                    )

            except (ValidationError, MemoryError):
                # Expected - long paths should be rejected
                pass

    def test_path_component_limits(self):
        """Test limits on individual path components."""

        # Test individual component limits
        long_component_paths = [
            f"{'A' * 500}/etc/passwd",  # Long single component
            f"dir1/{'B' * 1000}/etc/passwd",  # Long middle component
            f"../../../{'C' * 2000}",  # Long final component
        ]

        for path in long_component_paths:
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Navigate to: {path}",
                    domains="navigation",
                )

                # Individual components shouldn't be excessively long
                path_parts = request.context.split("/")
                for part in path_parts:
                    if len(part) > 255:  # Typical filesystem limit
                        pytest.fail(f"Long path component accepted: {len(part)} chars")

            except ValidationError:
                # Expected - long components should be rejected
                pass


class TestPathSanitizationEffectiveness:
    """Test the effectiveness of path sanitization functions."""

    def test_sanitization_consistency(self):
        """Test that path sanitization is consistently applied."""

        # Test various malicious patterns to see if sanitization is consistent
        test_patterns = [
            ("../../../etc/passwd", "should remove traversal patterns"),
            ("C:\\Windows\\System32\\config\\SAM", "should block Windows paths"),
            ("/etc/shadow", "should block absolute Unix paths"),
            ("file:///etc/passwd", "should block URI schemes"),
            ("\\\\network\\share\\file", "should block UNC paths"),
        ]

        for pattern, description in test_patterns:
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Test: {pattern}",
                    domains="security-testing",
                )

                # Verify sanitization occurred (pattern should be removed/modified)
                if pattern in request.context:
                    pytest.fail(f"Sanitization failed - {description}: {pattern}")

            except ValidationError:
                # Also acceptable - validation rejection instead of sanitization
                pass

    def test_sanitization_doesnt_break_legitimate_paths(self):
        """Test that sanitization doesn't break legitimate relative paths."""

        legitimate_paths = [
            "data/input.txt",
            "templates/report.html",
            "config/settings.json",
            "logs/application.log",
            "uploads/document.pdf",
        ]

        for legit_path in legitimate_paths:
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Process file: {legit_path}",
                    domains="file-operations",
                )

                # Legitimate paths should be preserved
                assert (
                    legit_path in request.context
                ), f"Legitimate path was over-sanitized: {legit_path}"

            except ValidationError as e:
                pytest.fail(f"Legitimate path incorrectly rejected: {legit_path} - {e}")
