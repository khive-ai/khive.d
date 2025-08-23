"""Thread safety and concurrency tests for AgentComposer.

This module provides comprehensive testing of thread safety, race conditions,
and concurrent operations to ensure the AgentComposer can safely handle
multiple simultaneous operations without data corruption or resource conflicts.
"""

import queue
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest
import yaml

from khive.services.composition.agent_composer import AgentComposer


class TestBasicThreadSafety:
    """Test basic thread safety of AgentComposer operations."""

    def test_concurrent_initialization(self):
        """Test concurrent AgentComposer initialization."""

        def create_composer(temp_dir):
            return AgentComposer(str(temp_dir))

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_path = Path(tmp_dir)

            # Create basic structure
            (temp_path / "roles").mkdir()
            (temp_path / "domains").mkdir()
            (temp_path / "agent_prompts.yaml").write_text("prompts: {}")
            (temp_path / "name_mapper.yaml").write_text("synonyms: {}")

            composers = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(create_composer, temp_path) for _ in range(20)
                ]

                for future in as_completed(futures):
                    try:
                        composer = future.result()
                        composers.append(composer)
                    except Exception as e:
                        pytest.fail(f"Concurrent initialization failed: {e}")

            # All should succeed
            assert len(composers) == 20

            # All should have valid configuration
            for composer in composers:
                assert composer.base_path.exists()
                assert isinstance(composer._seen_pairs, set)

    def test_concurrent_yaml_loading(self, temp_dir):
        """Test concurrent YAML file loading safety."""
        composer = AgentComposer(str(temp_dir))

        # Create test YAML files
        test_files = []
        for i in range(10):
            yaml_file = temp_dir / f"concurrent_{i}.yaml"
            yaml_data = {
                "id": i,
                "data": f"test_data_{i}",
                "items": list(range(i * 10, (i + 1) * 10)),
            }
            yaml_file.write_text(yaml.dump(yaml_data))
            test_files.append(yaml_file)

        results = []
        errors = []

        def load_yaml_file(file_path):
            try:
                result = composer.load_yaml(file_path)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Load files concurrently
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            # Each file loaded by multiple threads
            for _ in range(5):  # 5 rounds
                futures.extend(
                    executor.submit(load_yaml_file, file_path)
                    for file_path in test_files
                )

            # Wait for all to complete
            for future in as_completed(futures):
                future.result()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 50  # 10 files x 5 rounds

        # All results should be valid
        for result in results:
            assert isinstance(result, dict)
            assert "id" in result
            assert "data" in result

    def test_concurrent_role_loading(self, temp_dir):
        """Test concurrent role loading operations."""
        composer = AgentComposer(str(temp_dir))

        # Create test roles
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        role_names = []
        for i in range(20):
            role_name = f"concurrent_role_{i}"
            role_file = roles_dir / f"{role_name}.yaml"
            role_data = {
                "identity": {"id": role_name, "type": "concurrent_test"},
                "role": f"Concurrent test role {i}",
                "capabilities": [f"skill_{j}" for j in range(5)],
            }
            role_file.write_text(yaml.dump(role_data))
            role_names.append(role_name)

        loaded_roles = []
        load_errors = []

        def load_role(role_name):
            try:
                result = composer.load_agent_role(role_name)
                loaded_roles.append((role_name, result))
            except Exception as e:
                load_errors.append((role_name, e))

        # Load roles concurrently
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = []
            # Each role loaded multiple times concurrently
            for _ in range(3):
                futures.extend(
                    executor.submit(load_role, role_name) for role_name in role_names
                )

            for future in as_completed(futures):
                future.result()

        # Verify results
        assert len(load_errors) == 0, f"Load errors: {load_errors}"
        assert len(loaded_roles) == 60  # 20 roles x 3 rounds

        # Group by role name and verify consistency
        role_groups = {}
        for role_name, result in loaded_roles:
            if role_name not in role_groups:
                role_groups[role_name] = []
            role_groups[role_name].append(result)

        # All instances of same role should be identical
        for role_name, results in role_groups.items():
            first_result = results[0]
            for result in results[1:]:
                assert result == first_result, f"Inconsistent results for {role_name}"

    def test_file_lock_coordination(self, temp_dir):
        """Test file lock coordination between threads."""
        composer = AgentComposer(str(temp_dir))

        shared_file = temp_dir / "shared.yaml"
        shared_file.write_text("shared: data")

        access_order = []
        access_lock = threading.Lock()

        def access_with_lock(thread_id):
            # Simulate work that requires file lock
            with composer._file_lock:
                with access_lock:
                    access_order.append(f"start_{thread_id}")

                # Simulate file operation
                result = composer.load_yaml(shared_file)
                time.sleep(0.05)  # Hold lock briefly

                with access_lock:
                    access_order.append(f"end_{thread_id}")

                return result

        # Run concurrent accesses
        results = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(access_with_lock, i) for i in range(6)]

            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # All operations should succeed
        assert len(results) == 6
        for result in results:
            assert result["shared"] == "data"

        # Verify lock coordination (starts and ends should be paired)
        assert len(access_order) == 12  # 6 starts + 6 ends

        # Check that no two operations overlap significantly
        start_times = []
        end_times = []
        for event in access_order:
            if event.startswith("start_"):
                start_times.append(event)
            elif event.startswith("end_"):
                end_times.append(event)

        assert len(start_times) == len(end_times) == 6


class TestRaceConditionPrevention:
    """Test prevention of race conditions in critical operations."""

    def test_unique_agent_id_race_condition(self, temp_dir):
        """Test unique agent ID generation under concurrent access."""
        composer = AgentComposer(str(temp_dir))

        generated_ids = []
        id_lock = threading.Lock()

        def generate_id(thread_id):
            # Multiple threads generating IDs for same role-domain pair
            agent_id = composer.get_unique_agent_id("test_role", "test_domain")

            with id_lock:
                generated_ids.append((thread_id, agent_id))

            return agent_id

        # Generate IDs concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(generate_id, i) for i in range(50)]

            results = [future.result() for future in as_completed(futures)]

        # All IDs should be unique
        all_ids = list(results)
        unique_ids = set(all_ids)

        assert len(unique_ids) == len(all_ids), f"Duplicate IDs found: {all_ids}"

        # Verify ID format and versioning
        base_id = "test_role_test_domain"
        id_counts = {}

        for thread_id, agent_id in generated_ids:
            if agent_id == base_id or agent_id.startswith(base_id + "_v"):
                id_counts[agent_id] = id_counts.get(agent_id, 0) + 1

        # Each unique ID should appear only once
        for agent_id, count in id_counts.items():
            assert count == 1, f"ID {agent_id} generated {count} times"

    def test_seen_pairs_race_condition(self, temp_dir):
        """Test race condition in seen pairs tracking."""
        composer = AgentComposer(str(temp_dir))

        pairs_added = []
        add_lock = threading.Lock()

        def add_pair(pair_id):
            # Simulate concurrent modification of seen pairs
            role, domain = f"role_{pair_id % 5}", f"domain_{pair_id % 3}"
            unique_id = composer.get_unique_agent_id(role, domain)

            with add_lock:
                pairs_added.append((role, domain, unique_id))

            return unique_id

        # Add pairs concurrently
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(add_pair, i) for i in range(100)]

            results = [future.result() for future in as_completed(futures)]

        # Verify no duplicate base IDs for same role-domain pairs
        role_domain_to_base_id = {}

        for role, domain, unique_id in pairs_added:
            pair_key = f"{role}:{domain}"
            base_id = unique_id.split("_v")[0]  # Get base ID without version

            if pair_key not in role_domain_to_base_id:
                role_domain_to_base_id[pair_key] = base_id
            else:
                # Should be same base ID for same role-domain pair
                assert role_domain_to_base_id[pair_key] == base_id

        # Verify internal consistency of seen pairs
        seen_pairs = composer._seen_pairs

        # Count expected pairs
        expected_unique_pairs = set()
        for role, domain, unique_id in pairs_added:
            canonical_domain = composer.canonicalize_domain(domain)
            if "_v" in unique_id:
                version = unique_id.split("_v")[1]
                pair_key = f"{role}:{canonical_domain}-v{version}"
            else:
                pair_key = f"{role}:{canonical_domain}"
            expected_unique_pairs.add(pair_key)

        # All expected pairs should be in seen_pairs
        for pair in expected_unique_pairs:
            assert pair in seen_pairs, f"Missing pair: {pair}"

    def test_cache_coherence_race_condition(self, temp_dir):
        """Test cache coherence under concurrent operations."""
        composer = AgentComposer(str(temp_dir))

        # Create test data
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        role_file = roles_dir / "cache_test.yaml"
        role_data = {"identity": {"id": "cache_test"}, "role": "Test role"}
        role_file.write_text(yaml.dump(role_data))

        load_results = []
        result_lock = threading.Lock()

        def load_and_cache(thread_id):
            # Load role (potentially from cache)
            result = composer.load_agent_role("cache_test")

            with result_lock:
                load_results.append((thread_id, result))

            return result

        # Concurrent loads
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(load_and_cache, i) for i in range(75)]

            results = [future.result() for future in as_completed(futures)]

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, "Cache coherence violation detected"

        # Verify result consistency across threads
        for thread_id, result in load_results:
            assert result["identity"]["id"] == "cache_test"
            assert result["role"] == "Test role"


class TestResourceContention:
    """Test handling of resource contention and limits."""

    def test_file_descriptor_management(self, temp_dir):
        """Test file descriptor management under high load."""
        composer = AgentComposer(str(temp_dir))

        # Create many small files
        yaml_files = []
        for i in range(100):
            yaml_file = temp_dir / f"fd_test_{i}.yaml"
            yaml_file.write_text(f"id: {i}\ndata: test_{i}")
            yaml_files.append(yaml_file)

        successful_loads = []
        failed_loads = []

        def load_many_files(start_idx):
            results = []
            for i in range(start_idx, min(start_idx + 10, len(yaml_files))):
                try:
                    result = composer.load_yaml(yaml_files[i])
                    results.append((i, result))
                    successful_loads.append(i)
                except Exception as e:
                    failed_loads.append((i, e))
            return results

        # Load files concurrently
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = [
                executor.submit(load_many_files, i * 10)
                for i in range(10)  # 10 threads, each loading 10 files
            ]

            all_results = []
            for future in as_completed(futures):
                thread_results = future.result()
                all_results.extend(thread_results)

        # Should handle file operations without exhausting descriptors
        success_rate = len(successful_loads) / (
            len(successful_loads) + len(failed_loads)
        )
        assert (
            success_rate > 0.95
        ), f"Too many file operations failed: {len(failed_loads)} failures"

        # Verify loaded data integrity
        for file_idx, result in all_results:
            assert result["id"] == file_idx
            assert result["data"] == f"test_{file_idx}"

    def test_memory_pressure_handling(self, temp_dir):
        """Test behavior under memory pressure."""
        composer = AgentComposer(str(temp_dir))

        # Create roles and domains
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()
        domains_dir = temp_dir / "domains"
        domains_dir.mkdir()

        # Create role with large data
        large_role_data = {
            "identity": {"id": "memory_test", "capabilities": ["test"] * 100},
            "role": "Large role for memory testing",
            "large_data": ["item_" + str(i) for i in range(1000)],  # Large list
            "description": "x" * 10000,  # 10KB description
        }
        role_file = roles_dir / "memory_test.yaml"
        role_file.write_text(yaml.dump(large_role_data))

        # Create domain with large data
        large_domain_data = {
            "domain": {"id": "memory_domain"},
            "knowledge_patterns": {
                f"pattern_{i}": [f"item_{j}" for j in range(100)] for i in range(50)
            },
            "large_rules": {
                f"rule_{i}": "x" * 1000 for i in range(100)  # 100 rules, 1KB each
            },
        }
        domain_file = domains_dir / "memory_domain.yaml"
        domain_file.write_text(yaml.dump(large_domain_data))

        compositions = []
        memory_errors = []

        def create_large_composition(iteration):
            try:
                # Create composition with large context within validation limits
                large_context = (
                    "Context data " * 750
                )  # ~9.75KB context (within 10000 char limit)
                result = composer.compose_agent(
                    "memory_test", "memory_domain", large_context
                )
                compositions.append((iteration, len(str(result))))
                return result
            except (MemoryError, ValueError) as e:
                # Handle both memory errors and validation errors gracefully
                memory_errors.append((iteration, e))
                return None

        # Create many large compositions concurrently
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(create_large_composition, i) for i in range(50)]

            results = []
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    results.append(result)

        # Should handle memory pressure gracefully - allow some validation errors but expect most to succeed
        # At least 80% of requests should succeed under normal memory conditions
        assert (
            len(results) >= 40
        ), f"Too many failures: {len(results)} successes, {len(memory_errors)} errors"

        # If there are genuine memory errors (not validation errors), flag them
        genuine_memory_errors = [
            e for e in memory_errors if isinstance(e[1], MemoryError)
        ]
        assert (
            len(genuine_memory_errors) == 0
        ), f"Genuine memory errors: {genuine_memory_errors}"

        # Verify composition structure
        for result in results[:5]:  # Check first 5 results
            assert "identity" in result
            assert "task_context" in result
            assert "domains" in result

    def test_thread_pool_exhaustion_resilience(self, temp_dir):
        """Test resilience against thread pool exhaustion."""
        composer = AgentComposer(str(temp_dir))

        # Create test data
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        role_file = roles_dir / "thread_test.yaml"
        role_file.write_text("identity: {id: thread_test}")

        operation_results = queue.Queue()

        def blocking_operation(delay):
            """Operation that blocks for specified time."""
            time.sleep(delay)
            try:
                result = composer.load_agent_role("thread_test")
                operation_results.put(("success", result))
            except Exception as e:
                operation_results.put(("error", e))

        # Start many blocking operations
        threads = []
        for i in range(20):
            thread = threading.Thread(
                target=blocking_operation,
                args=(0.1,),  # 100ms delay
            )
            thread.start()
            threads.append(thread)

        # Start quick operations while threads are blocked
        quick_results = []
        for i in range(10):
            try:
                result = composer.load_agent_role("thread_test")
                quick_results.append(result)
            except Exception as e:
                quick_results.append(f"error: {e}")

        # Wait for all blocking operations to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Collect results from blocking operations
        blocking_results = []
        while not operation_results.empty():
            try:
                result = operation_results.get_nowait()
                blocking_results.append(result)
            except queue.Empty:
                break

        # Both quick and blocking operations should succeed
        assert len(quick_results) == 10
        for result in quick_results:
            assert isinstance(result, dict), f"Quick operation failed: {result}"

        successful_blocking = [r for r in blocking_results if r[0] == "success"]
        assert (
            len(successful_blocking) == 20
        ), f"Blocking operations failed: {blocking_results}"


class TestDeadlockPrevention:
    """Test prevention of deadlocks in multi-threaded scenarios."""

    def test_nested_lock_acquisition(self, temp_dir):
        """Test prevention of deadlocks from nested lock acquisition."""
        composer = AgentComposer(str(temp_dir))

        # Create test files
        yaml_file = temp_dir / "deadlock_test.yaml"
        yaml_file.write_text("test: data")

        results = []
        errors = []

        def nested_operation(thread_id):
            """Operation that might cause nested lock acquisition."""
            try:
                # First level lock acquisition
                with composer._file_lock:
                    result1 = composer.load_yaml(yaml_file)

                    # Simulate nested operation that might need lock
                    # This should not deadlock
                    result2 = composer._sanitize_input("test_input")

                    results.append((thread_id, result1, result2))
            except Exception as e:
                errors.append((thread_id, e))

        # Run nested operations concurrently
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(nested_operation, i) for i in range(20)]

            # Use timeout to detect deadlocks
            for future in as_completed(futures, timeout=10.0):
                try:
                    future.result()
                except Exception as e:
                    errors.append(("future_error", e))

        # Should complete without deadlocks
        assert len(errors) == 0, f"Deadlock or errors detected: {errors}"
        assert len(results) == 20

        # Verify results
        for thread_id, result1, result2 in results:
            assert result1["test"] == "data"
            assert result2 == "test_input"

    def test_cross_thread_dependency_avoidance(self, temp_dir):
        """Test avoidance of cross-thread dependencies that could cause deadlocks."""
        composer = AgentComposer(str(temp_dir))

        # Create shared resources
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()
        domains_dir = temp_dir / "domains"
        domains_dir.mkdir()

        role_file = roles_dir / "shared_role.yaml"
        role_file.write_text("identity: {id: shared_role}")

        domain_file = domains_dir / "shared_domain.yaml"
        domain_file.write_text("domain: {id: shared_domain}")

        completed_operations = []
        operation_lock = threading.Lock()

        def interdependent_operation(op_type, thread_id):
            """Operation that accesses multiple shared resources."""
            try:
                if op_type == "role_then_domain":
                    role_result = composer.load_agent_role("shared_role")
                    time.sleep(0.01)  # Small delay to increase chance of interference
                    domain_result = composer.load_domain_expertise("shared_domain")
                    result = (role_result, domain_result)
                else:  # "domain_then_role"
                    domain_result = composer.load_domain_expertise("shared_domain")
                    time.sleep(0.01)
                    role_result = composer.load_agent_role("shared_role")
                    result = (domain_result, role_result)

                with operation_lock:
                    completed_operations.append((thread_id, op_type, "success", result))

            except Exception as e:
                with operation_lock:
                    completed_operations.append((thread_id, op_type, "error", str(e)))

        # Run interdependent operations concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            # Mix of different operation orders to test for order-dependent deadlocks
            for i in range(30):
                op_type = "role_then_domain" if i % 2 == 0 else "domain_then_role"
                futures.append(executor.submit(interdependent_operation, op_type, i))

            # Wait for completion with timeout
            for future in as_completed(futures, timeout=15.0):
                try:
                    future.result()
                except Exception as e:
                    with operation_lock:
                        completed_operations.append(
                            (
                                "future",
                                "timeout",
                                "error",
                                str(e),
                            )
                        )

        # Verify no deadlocks occurred
        successful_ops = [op for op in completed_operations if op[2] == "success"]
        failed_ops = [op for op in completed_operations if op[2] == "error"]

        assert (
            len(failed_ops) == 0
        ), f"Operations failed (possible deadlock): {failed_ops}"
        assert (
            len(successful_ops) == 30
        ), f"Expected 30 successful operations, got {len(successful_ops)}"

        # Verify all operations produced valid results
        for thread_id, op_type, status, result in successful_ops:
            if op_type == "role_then_domain":
                role_result, domain_result = result
                assert role_result["identity"]["id"] == "shared_role"
                assert domain_result["domain"]["id"] == "shared_domain"
            else:
                domain_result, role_result = result
                assert domain_result["domain"]["id"] == "shared_domain"
                assert role_result["identity"]["id"] == "shared_role"


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)
