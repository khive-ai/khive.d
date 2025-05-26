# TDS-unittest-redo: Strategic Plan for Khive Unittest Overhaul

## 1. Overview

This document outlines the strategic plan for a comprehensive overhaul of the
unittests for the Khive system. The Khive system has undergone significant
updates, and the existing tests in the [`tests/`](tests/) directory require
review, refactoring, and expansion to ensure comprehensive coverage, robustness,
and alignment with the current system architecture. This plan prioritizes
critical areas, addresses coverage gaps, and defines strategies for refactoring,
integration testing, and adherence to best practices using `pytest`.

## 2. Prioritization Strategy

Given the significant updates to the Khive system, the following prioritization
strategy will be adopted:

### Phase 1: Critical Core Components & High-Change Areas

Based on the likely impact of system updates and criticality, the following
modules/components within [`src/khive/`](src/khive/) will be prioritized for
immediate test review, enhancement, and creation:

1. **CLI Layer ([`src/khive/cli/`](src/khive/cli/)):**
   - **Reasoning:** The primary user interaction point. Changes here have a
     direct impact on usability and functionality.
   - **Focus:** Verify all commands, subcommands, arguments, options, and their
     interactions. Ensure robust parsing and error handling. Test output
     formatting.
   - Files like [`src/khive/cli/khive_cli.py`](src/khive/cli/khive_cli.py) and
     individual command modules (e.g.,
     [`src/khive/cli/khive_ci.py`](src/khive/cli/khive_ci.py),
     [`src/khive/cli/khive_info.py`](src/khive/cli/khive_info.py),
     [`src/khive/cli/khive_git.py`](src/khive/commands/git.py) (assuming
     `khive_git.py` is now in `src/khive/commands/` but invoked by CLI)).
2. **Core Services ([`src/khive/services/`](src/khive/services/)):**
   - **Reasoning:** These likely encapsulate the core business logic of the new
     Khive system.
   - **Focus:** Test the public API of each service (e.g.,
     [`src/khive/services/info/info_service.py`](src/khive/services/info/info_service.py),
     [`src/khive/services/git/git_service.py`](src/khive/services/git/git_service.py),
     [`src/khive/services/dev/dev_service.py`](src/khive/services/dev/dev_service.py)).
     Ensure they behave correctly with various inputs and mocked dependencies.
3. **Client Logic ([`src/khive/clients/`](src/khive/clients/)):**
   - **Reasoning:** Handles interactions with external systems/APIs, which are
     often sources of change and potential failure.
   - **Focus:** Test
     [`src/khive/clients/api_client.py`](src/khive/clients/api_client.py),
     [`src/khive/clients/executor.py`](src/khive/clients/executor.py),
     resilience mechanisms
     ([`src/khive/clients/resilience.py`](src/khive/clients/resilience.py)), and
     rate limiting
     ([`src/khive/clients/rate_limiter.py`](src/khive/clients/rate_limiter.py)).
     Heavy use of mocking will be required.
4. **Connection Management
   ([`src/khive/connections/`](src/khive/connections/)):**
   - **Reasoning:** Fundamental for client logic and service interactions.
   - **Focus:** Test endpoint configuration
     ([`src/khive/connections/endpoint_config.py`](src/khive/connections/endpoint_config.py)),
     endpoint matching
     ([`src/khive/connections/match_endpoint.py`](src/khive/connections/match_endpoint.py)),
     and provider-specific logic
     ([`src/khive/connections/providers/`](src/khive/connections/providers/)).
5. **Configuration ([`src/khive/config.py`](src/khive/config.py)):**
   - **Reasoning:** Changes in configuration loading or structure can affect the
     entire system.
   - **Focus:** Test loading from different sources, default values, and
     validation.

### Phase 2: Internal Libraries and Remaining Components

1. **Internal Libraries ([`src/khive/_libs/`](src/khive/_libs/)):**
   - **Focus:** This includes
     [`src/khive/_libs/schema.py`](src/khive/_libs/schema.py) and any other
     utilities. These are lower priority unless identified as high-risk during
     Phase 1.
2. **Utilities ([`src/khive/utils.py`](src/khive/utils.py)):**
   - **Focus:** General utility functions.
3. **Remaining Untested or Low-Coverage Areas:** Identified via coverage reports
   after Phase 1.

## 3. Addressing Coverage Gaps

1. **[`src/khive/_libs/`](src/khive/_libs/) Modules (especially
   [`src/khive/_libs/schema.py`](src/khive/_libs/schema.py)):**
   - **Plan:**
     - Analyze [`src/khive/_libs/schema.py`](src/khive/_libs/schema.py) to
       understand its purpose (likely data validation,
       serialization/deserialization).
     - Create dedicated tests in a new file, e.g.,
       [`tests/libs/test_schema.py`](tests/libs/test_schema.py).
     - Test schema validation with valid and invalid data.
     - Test any transformation or utility functions within the module.
     - For other modules in [`src/khive/_libs/`](src/khive/_libs/), follow a
       similar pattern: understand functionality, create dedicated test files,
       and cover core logic.
2. **Identifying and Covering New Features:**
   - **Strategy:**
     - **Collaboration:** Work with developers or consult design
       documents/changelogs for the "updated khive system" to identify new
       functionalities.
     - **Exploratory Testing & Code Review:** Review new or significantly
       modified modules in [`src/khive/`](src/khive/) to understand their
       behavior.
     - **Coverage Analysis:** After initial test development, use `pytest-cov`
       to generate coverage reports. Identify untested new code paths.
     - **Test Case Design:** For each new feature, design test cases that cover
       its primary use cases, edge cases, and error conditions.

## 4. Refactoring and Enhancement of Existing Tests

Guidelines for reviewing existing tests in [`tests/cli/`](tests/cli/),
[`tests/clients/`](tests/clients/), [`tests/connections/`](tests/connections/),
[`tests/services/`](tests/services/), etc.:

1. **Robustness & Reliability:**
   - Eliminate flaky tests. Identify and fix sources of non-determinism.
   - Ensure tests clean up after themselves (e.g., temporary files, mocked
     states).
2. **Maintainability:**
   - **Clarity:** Tests should be easy to read and understand. Use descriptive
     names for test functions and variables.
   - **DRY Principle:** Avoid code duplication by using helper functions or
     `pytest` fixtures for common setup or assertions.
   - **Focused Tests:** Each test should verify a single piece of functionality
     or behavior.
3. **Accuracy with Current Functionality:**
   - Verify that each test accurately reflects the current behavior of the code
     it targets.
   - Update or remove tests for deprecated or changed features.
4. **Mocking Strategies (Leveraging `khive info` insights):**
   - **Targeted Mocking:** Use `unittest.mock` (`pytest-mock` provides a
     `mocker` fixture) to mock external dependencies (filesystem, network,
     external APIs, other services not under test).
   - Mock at the appropriate boundary. Avoid over-mocking, which can make tests
     brittle or hide integration issues.
   - Ensure mocks verify that the correct calls were made with the expected
     arguments.
5. **Test Data Management:**
   - Use fixtures to provide consistent test data.
   - For larger datasets, consider storing them in separate files (e.g., JSON,
     YAML) and loading them within fixtures.
   - Avoid hardcoding large, complex data structures directly in tests.
6. **Assertion Patterns:**
   - Use specific `pytest` assertion functions (e.g.,
     `assert result == expected`, `with pytest.raises(SpecificException):`).
   - Assert not just final output, but also important side effects or state
     changes where applicable.
   - For CLI tests, assert exit codes, `stdout`, and `stderr`.
7. **Isolation (Leveraging `khive info` insights):**
   - Ensure CLI logic is separated from I/O for easier unit testing of core
     logic.
   - Unit tests should test components in isolation as much as possible.

## 5. Integration Testing Strategy

(Leveraging `khive info` insights for microservice-like components)

1. **Approach:**
   - Focus on testing interactions between key Khive components, treating them
     as "microservice-like" units where appropriate (e.g., CLI interacting with
     a Service, Service interacting with Client, multiple Services
     collaborating).
   - Create a new directory, e.g., [`tests/integration/`](tests/integration/),
     for these tests.
2. **Identifying Key Workflows/Scenarios:**
   - **User-Facing CLI Commands:**
     - `khive info <query>`: Test the flow from CLI parsing to `InfoService`
       execution and result display.
     - `khive git "<message>"`: Test CLI to `GitService` interaction, including
       any NLP or MCP calls.
     - `khive dev <args>`: Test CLI to `DevService` interaction.
     - `khive new-doc <type> <id>`: Test CLI to file system interaction and
       template generation.
   - **Service-to-Service Interactions (if any):** Identify if services call
     each other directly and test these interaction points.
   - **Service-to-Client-to-External API:** Test scenarios where a service uses
     a client to call a (mocked) external API, verifying the data flow and error
     handling.
3. **Implementation Details:**
   - **Mocking External Systems:** For integration tests, mock the boundaries of
     the Khive system (e.g., actual external APIs like GitHub, Exa, PPLX).
     Internal interactions between Khive components should be real.
   - **Test Data:** Use realistic but controlled test data.
   - **Setup/Teardown:** Use `pytest` fixtures for setting up preconditions
     (e.g., mock configurations, pre-existing files if needed) and tearing down
     post-test.
   - **Containerization (Consideration):** While `khive info` suggested Docker,
     for this phase, focus on in-process integration tests first.
     Containerization can be explored later if complexity demands it or for
     testing against real external dependencies in a controlled environment.
   - **Focus on Contracts:** Ensure components adhere to their expected
     input/output contracts.

## 6. Testing Framework and Practices

1. **Framework:** Continue using **`pytest`**.
2. **Recommended `pytest` Plugins & Practices:**
   - **`pytest-cov`:** For measuring code coverage. Aim to integrate this into
     CI.
   - **`pytest-mock`:** For easier use of `unittest.mock` via the `mocker`
     fixture.
   - **Fixtures:** Extensively use fixtures for setup, teardown, and providing
     test data. Promote fixture reuse.
     - Scope fixtures appropriately (`function`, `class`, `module`, `session`).
   - **Parametrization (`@pytest.mark.parametrize`):** Use for testing the same
     logic with different inputs/outputs, reducing test code duplication.
   - **Markers (`@pytest.mark.<name>`):**
     - Use for categorizing tests (e.g., `@pytest.mark.slow`,
       `@pytest.mark.integration`, `@pytest.mark.cli`).
     - Allows selective running of tests (e.g., `pytest -m "not slow"`).
   - **`tmp_path` / `tmpdir` fixtures:** For tests that need to interact with
     the filesystem.
   - **CLI Testing (Leveraging `khive info` insights):**
     - Use `subprocess` module or a library like `click.testing.CliRunner` (if
       Khive CLI uses Click) to invoke CLI commands and capture output
       (`stdout`, `stderr`) and exit codes.
     - Test various argument combinations, option flags, and error conditions.
3. **Ensuring Adherence to New Practices:**
   - **Documentation:** This TDS serves as the primary guide.
   - **Code Reviews:** Test code should be part of regular code reviews, with a
     focus on these practices.
   - **Pair Programming/Mentoring:** When introducing new patterns.
   - **Pre-commit Hooks:** Consider adding linters or static analysis tools that
     can check for common test anti-patterns (though this might be a later
     enhancement).

## 7. Success Metrics

The success of the unittest redo will be measured by:

1. **Code Coverage:**
   - **Target:** Achieve a minimum of **85%** overall code coverage as reported
     by `pytest-cov`.
   - **Focus:** Aim for >90% coverage for critical modules identified in
     Phase 1.
2. **Reduction in Post-Release Bugs:** Track the number of bugs reported in
   areas that have undergone test overhaul. A significant reduction will
   indicate success.
3. **Number of Critical Paths Covered:**
   - Identify and document critical user workflows and system interaction paths.
   - Ensure these paths are covered by robust integration tests.
4. **Test Suite Stability and Maintainability:**
   - Reduction in flaky tests.
   - Ease of adding new tests for new features.
   - Clarity and readability of the test suite.
5. **CI Pipeline Health:** Consistent green builds in the CI pipeline for the
   test suite.

## 8. Next Steps

The implementer will use this TDS to:

1. Set up their development environment for testing.
2. Begin with Phase 1 prioritization, starting with the CLI layer.
3. Incrementally address coverage gaps and refactor existing tests according to
   the guidelines.
4. Develop integration tests for key workflows.
5. Regularly report progress and coverage metrics.
