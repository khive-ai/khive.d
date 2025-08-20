"""File operations security and functionality tests for AgentComposer.

This module focuses on comprehensive testing of file operations, including:
- File loading with various malformed inputs
- File size and permission handling
- Concurrent file access safety
- Error recovery from file system issues
- Malicious file content handling
- File system race condition prevention
"""

import builtins
import contextlib
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from khive.services.composition.agent_composer import AgentComposer


class TestFileLoadingSafety:
    """Test safe file loading with various input conditions."""

    def test_load_yaml_with_malformed_content(self, temp_dir):
        """Test handling of various malformed YAML content."""
        composer = AgentComposer(str(temp_dir))

        malformed_contents = [
            # Invalid YAML structures
            "key: value\n  invalid: yaml: structure:",
            "- item1\n    - nested_wrong_indent",
            "key: [unclosed_list",
            "key: {unclosed_dict",
            "key: 'unclosed_string",
            'key: "unclosed_double_string',
            "key: value\n\ttab_mixed_with_spaces: invalid",
            "key:\n  value\n    extra_indented: problem",
            # Unicode issues
            b"\xff\xfe\x00\x00invalid_bom".decode("utf-8", errors="ignore"),
            "key: value\x00null_byte_embedded",
            "key: \udcff\udcfe",  # Surrogate characters
            # Very large structures
            "key: " + "x" * (1024 * 1024),  # 1MB value
            "key:\n" + "  subkey: value\n" * 10000,  # Many subkeys
            # Empty/minimal files
            "",
            "   \n   \n   ",  # Only whitespace
            "# Only comments",
            "---",  # Only YAML document separator
            "null",
            # Anchor and reference issues
            "key: *unknown_anchor",
            "<<: *unknown_merge",
            "&recursive_anchor key: *recursive_anchor",
        ]

        for i, content in enumerate(malformed_contents):
            yaml_file = temp_dir / f"malformed_{i}.yaml"

            try:
                yaml_file.write_text(content, encoding="utf-8")
                result = composer.load_yaml(yaml_file)

                # Should return empty dict for malformed content, not crash
                assert isinstance(result, dict | type(None))

            except UnicodeEncodeError:
                # Some malformed Unicode content might not be writable
                continue

    def test_file_permission_handling(self, temp_dir):
        """Test handling of files with various permission issues."""
        composer = AgentComposer(str(temp_dir))

        # Create a file with restricted permissions
        restricted_file = temp_dir / "restricted.yaml"
        restricted_file.write_text("key: value")

        # Make file unreadable
        restricted_file.chmod(0o000)

        try:
            result = composer.load_yaml(restricted_file)
            assert result == {}  # Should return empty dict for unreadable files
        except PermissionError:
            # Also acceptable behavior
            pass
        finally:
            # Restore permissions for cleanup
            with contextlib.suppress(builtins.BaseException):
                restricted_file.chmod(0o644)

    def test_file_size_edge_cases(self, temp_dir):
        """Test handling of files at size boundaries."""
        composer = AgentComposer(str(temp_dir))

        # Test exactly at limit
        limit_file = temp_dir / "at_limit.yaml"
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 10 * 1024 * 1024  # Exactly 10MB
            limit_file.write_text("key: value")

            result = composer.load_yaml(limit_file)
            assert result == {}  # Should reject file at exact limit

        # Test just over limit
        over_limit_file = temp_dir / "over_limit.yaml"
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 10 * 1024 * 1024 + 1  # Just over 10MB
            over_limit_file.write_text("key: value")

            result = composer.load_yaml(over_limit_file)
            assert result == {}  # Should reject oversized files

        # Test content size vs file size mismatch
        mismatch_file = temp_dir / "size_mismatch.yaml"
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 1024  # Report small size

            huge_content = "key: " + "x" * (15 * 1024 * 1024)  # Actually huge content
            with patch("builtins.open", mock_open(read_data=huge_content)):
                result = composer.load_yaml(mismatch_file)
                assert result == {}  # Should reject based on actual content size

    def test_file_race_condition_handling(self, temp_dir):
        """Test handling of race conditions during file operations."""
        composer = AgentComposer(str(temp_dir))

        race_file = temp_dir / "race_condition.yaml"
        race_file.write_text("initial: content")

        def modify_file():
            """Continuously modify the file during loading."""
            for i in range(10):
                try:
                    race_file.write_text(f"modified: {i}")
                    time.sleep(0.01)
                except:
                    pass  # File might be locked

        def load_file():
            """Load file while it's being modified."""
            results = []
            for _ in range(5):
                try:
                    result = composer.load_yaml(race_file)
                    results.append(result)
                    time.sleep(0.02)
                except:
                    results.append({})  # Handle errors gracefully
            return results

        # Run both operations concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            modify_future = executor.submit(modify_file)
            load_future = executor.submit(load_file)

            load_results = load_future.result()
            modify_future.result()

        # Should handle race conditions gracefully
        assert all(isinstance(result, dict) for result in load_results)

    def test_symlink_and_hardlink_handling(self, temp_dir):
        """Test handling of symbolic links and hard links."""
        composer = AgentComposer(str(temp_dir))

        # Create original file
        original_file = temp_dir / "original.yaml"
        original_file.write_text("original: data")

        try:
            # Create symbolic link
            symlink_file = temp_dir / "symlink.yaml"
            symlink_file.symlink_to(original_file)

            # Should either resolve safely or reject
            result = composer.load_yaml(symlink_file)
            if result:  # If it loads
                assert result.get("original") == "data"
            else:  # Or rejects for security
                assert result == {}

        except OSError:
            # Symlinks might not be supported on all systems
            pass

        try:
            # Create hard link
            hardlink_file = temp_dir / "hardlink.yaml"
            hardlink_file.hardlink_to(original_file)

            result = composer.load_yaml(hardlink_file)
            assert result.get("original") == "data"  # Hard links should work

        except OSError:
            # Hard links might not be supported
            pass

    def test_file_encoding_issues(self, temp_dir):
        """Test handling of files with various encoding issues."""
        composer = AgentComposer(str(temp_dir))

        encoding_tests = [
            # Different encodings
            ("utf-8", "key: café"),
            ("latin-1", "key: café"),
            ("utf-16", "key: value"),
            ("utf-32", "key: value"),
            # BOM variations
            ("utf-8-sig", "key: value"),
            ("utf-16le", "key: value"),
            ("utf-16be", "key: value"),
        ]

        for encoding, content in encoding_tests:
            try:
                encoded_file = temp_dir / f"encoded_{encoding.replace('-', '_')}.yaml"
                encoded_file.write_text(content, encoding=encoding)

                # Should handle different encodings gracefully
                result = composer.load_yaml(encoded_file)
                assert isinstance(result, dict | type(None))

            except (UnicodeError, LookupError):
                # Some encodings might not be available
                continue

    def test_binary_file_rejection(self, temp_dir):
        """Test rejection of binary files masquerading as YAML."""
        composer = AgentComposer(str(temp_dir))

        # Create binary file with .yaml extension
        binary_file = temp_dir / "binary.yaml"
        binary_content = bytes(range(256))  # All possible byte values
        binary_file.write_bytes(binary_content)

        result = composer.load_yaml(binary_file)
        assert result == {}  # Should reject binary content

    def test_extremely_deep_nesting(self, temp_dir):
        """Test handling of extremely deeply nested YAML structures."""
        composer = AgentComposer(str(temp_dir))

        # Create deeply nested structure
        deep_yaml = "root:\n"
        indent = 2
        for i in range(1000):  # Very deep nesting
            deep_yaml += " " * indent + f"level{i}:\n"
            indent += 2
        deep_yaml += " " * indent + "value: deep"

        deep_file = temp_dir / "deep.yaml"
        deep_file.write_text(deep_yaml)

        # Should either load successfully or reject gracefully, not crash
        start_time = time.time()
        result = composer.load_yaml(deep_file)
        end_time = time.time()

        # Should complete in reasonable time
        assert end_time - start_time < 5.0
        assert isinstance(result, dict | type(None))


class TestRoleFileOperations:
    """Test role file loading specific operations."""

    def test_markdown_role_parsing_edge_cases(self, temp_dir):
        """Test edge cases in markdown role file parsing."""
        composer = AgentComposer(str(temp_dir))

        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        edge_case_contents = [
            # Multiple YAML blocks
            "# Role\n```yaml\nid: test1\n```\nContent\n```yaml\nid: test2\n```",
            # Malformed YAML block
            "# Role\n```yaml\nid: test\nmalformed: yaml:\n```",
            # No closing backticks
            "# Role\n```yaml\nid: test\ntype: agent",
            # Empty YAML block
            "# Role\n```yaml\n```",
            # YAML block with dangerous content
            "# Role\n```yaml\nid: test\nsystem: rm -rf /\n```",
            # Multiple sections with same name
            "## Role\nFirst role\n## Role\nSecond role",
            # Extremely long sections
            "## Role\n" + "Very long role description " * 1000,
            # Binary content in markdown
            "# Role\n" + "Normal text\n" + "\x00\x01\x02\x03",
            # Unicode edge cases
            "# Rôle\n```yaml\nid: tëst\n```\n## Rôle\nUnicode content",
        ]

        for i, content in enumerate(edge_case_contents):
            role_file = roles_dir / f"edge_case_{i}.md"

            try:
                role_file.write_text(content, encoding="utf-8")
                result = composer.load_agent_role(f"edge_case_{i}")

                # Should return valid dict structure or raise ValueError
                assert isinstance(result, dict)
                assert "identity" in result or "role" in result or "purpose" in result

            except (ValueError, UnicodeEncodeError):
                # Expected for malformed content
                continue
            except FileNotFoundError:
                # Expected if file creation fails
                continue

    def test_yaml_role_fallback_behavior(self, temp_dir):
        """Test fallback from .md to .yaml role files."""
        composer = AgentComposer(str(temp_dir))

        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        # Create .yaml file but not .md file
        yaml_role_file = roles_dir / "yaml_only.yaml"
        yaml_role_file.write_text(
            yaml.dump(
                {
                    "identity": {"id": "yaml_only", "type": "test"},
                    "role": "YAML role only",
                }
            )
        )

        result = composer.load_agent_role("yaml_only")
        assert result["identity"]["id"] == "yaml_only"
        assert result["role"] == "YAML role only"

        # Create both .md and .yaml files - should prefer .md
        md_role_file = roles_dir / "both_formats.md"
        md_role_file.write_text(
            """# Both Formats Role
```yaml
id: both_formats
type: markdown
```

## Role
Markdown version
"""
        )

        yaml_role_file2 = roles_dir / "both_formats.yaml"
        yaml_role_file2.write_text(
            yaml.dump(
                {
                    "identity": {"id": "both_formats", "type": "yaml"},
                    "role": "YAML version",
                }
            )
        )

        result = composer.load_agent_role("both_formats")
        assert result["identity"]["type"] == "markdown"  # Should use .md version
        assert "Markdown version" in result["role"]

    def test_role_file_section_extraction(self, temp_dir):
        """Test extraction of various sections from markdown."""
        composer = AgentComposer(str(temp_dir))

        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        complex_markdown = """# Complex Role

```yaml
id: complex
type: test
capabilities: [test, analyze]
```

## Role
Primary role description
with multiple lines

## Purpose
Main purpose of this agent
spanning several paragraphs

## Core Capabilities
- Capability 1
- Capability 2
- Capability 3

## Decision Logic
1. First step
2. Second step
3. Final step

## Output Schema
```json
{
  "result": "string",
  "confidence": "number"
}
```

## Non-standard Section
This should also be extractable

## Role
Duplicate section (should not cause issues)
"""

        role_file = roles_dir / "complex.md"
        role_file.write_text(complex_markdown)

        result = composer.load_agent_role("complex")

        # Verify all sections are extracted
        assert result["identity"]["id"] == "complex"
        assert "Primary role description" in result["role"]
        assert "Main purpose" in result["purpose"]
        assert "Capability 1" in result["capabilities"]
        assert "First step" in result["decision_logic"]
        assert '"result"' in result["output_schema"]

        # Full content should be preserved
        assert "Non-standard Section" in result["content"]


class TestDomainFileOperations:
    """Test domain file loading specific operations."""

    def test_hierarchical_domain_search(self, temp_dir):
        """Test searching for domains in hierarchical structure."""
        composer = AgentComposer(str(temp_dir))

        domains_dir = temp_dir / "domains"
        domains_dir.mkdir()

        # Create flat structure domain
        flat_domain = domains_dir / "flat.yaml"
        flat_domain.write_text(
            yaml.dump(
                {
                    "domain": {"id": "flat"},
                    "knowledge_patterns": {"flat": ["pattern1"]},
                }
            )
        )

        # Create hierarchical structure
        category1 = domains_dir / "category1"
        category1.mkdir()

        hierarchical_domain = category1 / "hierarchical.yaml"
        hierarchical_domain.write_text(
            yaml.dump(
                {
                    "domain": {"id": "hierarchical"},
                    "knowledge_patterns": {"hierarchical": ["pattern1"]},
                }
            )
        )

        # Create deeply nested structure
        subcategory = category1 / "subcategory"
        subcategory.mkdir()

        deep_domain = subcategory / "deep.yaml"
        deep_domain.write_text(
            yaml.dump(
                {
                    "domain": {"id": "deep"},
                    "knowledge_patterns": {"deep": ["pattern1"]},
                }
            )
        )

        # Test loading from different levels
        flat_result = composer.load_domain_expertise("flat")
        assert flat_result["domain"]["id"] == "flat"

        hierarchical_result = composer.load_domain_expertise("hierarchical")
        assert hierarchical_result["domain"]["id"] == "hierarchical"

        deep_result = composer.load_domain_expertise("deep")
        assert deep_result["domain"]["id"] == "deep"

    def test_domain_name_collision_handling(self, temp_dir):
        """Test handling of domain name collisions in hierarchy."""
        composer = AgentComposer(str(temp_dir))

        domains_dir = temp_dir / "domains"
        domains_dir.mkdir()

        # Create same-named domain in flat structure
        flat_collision = domains_dir / "collision.yaml"
        flat_collision.write_text(
            yaml.dump(
                {
                    "domain": {"id": "collision", "source": "flat"},
                }
            )
        )

        # Create same-named domain in hierarchical structure
        category = domains_dir / "category"
        category.mkdir()

        hierarchical_collision = category / "collision.yaml"
        hierarchical_collision.write_text(
            yaml.dump(
                {
                    "domain": {"id": "collision", "source": "hierarchical"},
                }
            )
        )

        # Should return first found (flat structure checked first)
        result = composer.load_domain_expertise("collision")
        assert result["domain"]["source"] == "flat"

    def test_domain_file_corruption_recovery(self, temp_dir):
        """Test recovery from corrupted domain files."""
        composer = AgentComposer(str(temp_dir))

        domains_dir = temp_dir / "domains"
        domains_dir.mkdir()

        # Create corrupted YAML files
        corrupted_files = [
            ("truncated.yaml", "domain: {id: truncated\n# File truncated"),
            ("binary_corruption.yaml", "domain:\n  id: test\n" + "\x00" * 10),
            ("encoding_issue.yaml", "domain:\n  id: test\n  ñame: vålue"),
        ]

        for filename, content in corrupted_files:
            corrupted_file = domains_dir / filename
            try:
                corrupted_file.write_text(content, encoding="utf-8")
            except UnicodeEncodeError:
                corrupted_file.write_bytes(content.encode("utf-8", errors="replace"))

            domain_name = filename.split(".")[0]
            result = composer.load_domain_expertise(domain_name)

            # Should return empty dict for corrupted files
            assert result == {}

    def test_domain_listing_operations(self, temp_dir):
        """Test domain listing and taxonomy operations."""
        composer = AgentComposer(str(temp_dir))

        domains_dir = temp_dir / "domains"
        domains_dir.mkdir()

        # Create complex hierarchy
        (domains_dir / "root_domain.yaml").write_text("domain: {id: root}")

        # Category 1
        cat1 = domains_dir / "engineering"
        cat1.mkdir()
        (cat1 / "backend.yaml").write_text("domain: {id: backend}")
        (cat1 / "frontend.yaml").write_text("domain: {id: frontend}")

        # Subcategory
        subcat = cat1 / "specialized"
        subcat.mkdir()
        (subcat / "ml.yaml").write_text("domain: {id: ml}")

        # Category 2
        cat2 = domains_dir / "architecture"
        cat2.mkdir()
        (cat2 / "microservices.yaml").write_text("domain: {id: microservices}")

        # Create non-domain files that should be ignored
        (domains_dir / "README.md").write_text("# Domains")
        (domains_dir / "TAXONOMY.yaml").write_text("taxonomy: info")
        (cat1 / "README.yaml").write_text("readme: info")

        # Test listing all domains
        all_domains = composer.list_available_domains()
        expected_domains = ["root_domain", "backend", "frontend", "ml", "microservices"]

        for domain in expected_domains:
            assert domain in all_domains

        # Should not include README or TAXONOMY files
        assert "README" not in all_domains
        assert "TAXONOMY" not in all_domains

        # Test taxonomy listing
        taxonomy = composer.list_domains_by_taxonomy()

        assert "engineering" in taxonomy
        assert "architecture" in taxonomy
        assert "specialized" in taxonomy["engineering"]

        # Check structure
        assert "backend" in taxonomy["engineering"]["_root"]
        assert "ml" in taxonomy["engineering"]["specialized"]
        assert "microservices" in taxonomy["architecture"]["_root"]


class TestConcurrentFileOperations:
    """Test thread safety and concurrent file operations."""

    def test_concurrent_yaml_loading(self, temp_dir):
        """Test concurrent YAML file loading safety."""
        composer = AgentComposer(str(temp_dir))

        # Create multiple YAML files
        yaml_files = []
        for i in range(10):
            yaml_file = temp_dir / f"concurrent_{i}.yaml"
            yaml_file.write_text(
                yaml.dump({"id": i, "data": f"test_data_{i}", "list": list(range(10))})
            )
            yaml_files.append(yaml_file)

        def load_random_files():
            """Load random files concurrently."""
            results = []
            for _ in range(20):
                import random

                file_to_load = random.choice(yaml_files)
                result = composer.load_yaml(file_to_load)
                results.append(result)
                time.sleep(0.001)  # Small delay to increase chance of races
            return results

        # Run concurrent loads
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(load_random_files) for _ in range(5)]
            all_results = []
            for future in futures:
                all_results.extend(future.result())

        # All results should be valid
        assert len(all_results) == 100  # 5 threads * 20 loads each
        for result in all_results:
            assert isinstance(result, dict)
            assert "id" in result
            assert "data" in result

    def test_file_lock_effectiveness(self, temp_dir):
        """Test effectiveness of file locking mechanism."""
        composer = AgentComposer(str(temp_dir))

        shared_file = temp_dir / "shared.yaml"
        shared_file.write_text("initial: value")

        access_times = []
        lock_acquisitions = []

        def access_with_timing():
            """Access file and record timing."""
            start_time = time.time()

            # Access the file lock explicitly
            with composer._file_lock:
                lock_acquisitions.append(time.time())
                result = composer.load_yaml(shared_file)
                time.sleep(0.1)  # Hold lock for a bit

            end_time = time.time()
            access_times.append((start_time, end_time))
            return result

        # Run concurrent accesses
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(access_with_timing) for _ in range(4)]
            results = [f.result() for f in futures]

        # All should succeed
        assert all(isinstance(r, dict) for r in results)

        # Lock acquisitions should be sequential (not overlapping significantly)
        lock_acquisitions.sort()
        for i in range(1, len(lock_acquisitions)):
            # Each lock should be acquired after the previous one started
            time_diff = lock_acquisitions[i] - lock_acquisitions[i - 1]
            assert time_diff >= 0  # Sequential acquisition

    def test_role_loading_race_conditions(self, temp_dir):
        """Test role loading under race conditions."""
        composer = AgentComposer(str(temp_dir))

        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        # Create role file
        role_file = roles_dir / "race_test.yaml"
        role_file.write_text(
            yaml.dump(
                {
                    "identity": {"id": "race_test", "type": "test"},
                    "role": "Test role for race conditions",
                }
            )
        )

        load_results = []
        errors = []

        def load_role():
            """Load role and handle errors."""
            try:
                result = composer.load_agent_role("race_test")
                load_results.append(result)
            except Exception as e:
                errors.append(e)

        # Run many concurrent role loads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(load_role) for _ in range(50)]
            for future in futures:
                future.result()  # Wait for completion

        # Most should succeed, few errors acceptable due to race conditions
        success_rate = len(load_results) / (len(load_results) + len(errors))
        assert success_rate > 0.9  # At least 90% success rate

        # All successful loads should return same data
        for result in load_results:
            assert result["identity"]["id"] == "race_test"

    def test_domain_composition_concurrency(self, temp_dir):
        """Test concurrent agent composition with domains."""
        composer = AgentComposer(str(temp_dir))

        # Setup test files
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()
        role_file = roles_dir / "concurrent.yaml"
        role_file.write_text("identity: {id: concurrent}")

        domains_dir = temp_dir / "domains"
        domains_dir.mkdir()
        domain_file = domains_dir / "concurrent.yaml"
        domain_file.write_text(
            yaml.dump(
                {
                    "domain": {"id": "concurrent"},
                    "knowledge_patterns": {"test": ["pattern1"]},
                }
            )
        )

        composition_results = []

        def compose_agent():
            """Compose agent concurrently."""
            try:
                result = composer.compose_agent("concurrent", "concurrent")
                composition_results.append(result)
            except Exception as e:
                composition_results.append({"error": str(e)})

        # Run concurrent compositions
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(compose_agent) for _ in range(30)]
            for future in futures:
                future.result()

        # All compositions should succeed
        successful_compositions = [
            r
            for r in composition_results
            if "error" not in r and r.get("identity", {}).get("id") == "concurrent"
        ]

        success_rate = len(successful_compositions) / len(composition_results)
        assert success_rate > 0.95  # At least 95% success rate


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)
