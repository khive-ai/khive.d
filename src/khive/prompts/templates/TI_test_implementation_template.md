---
title: "Test Implementation Template"
by: "khive-implementer"
created: "2025-04-12"
updated: "2025-05-26"
version: "2.0"
doc_type: "TI"
output_subdir: "ti"
description: "Test planning with service integration"
---

# Guidance

**Purpose**\
Plan comprehensive tests that work with khive services.

**Service Integration**

- Tests run automatically via khive dev/ci
- Focus on test cases, not infrastructure
- Services handle coverage and reporting

---

# Test Implementation: [Component Name]

## 1. Service-Integrated Testing

### 1.1 Automatic Test Execution

```bash
# All tests run automatically with:
khive dev "check"  # Quick validation
khive ci          # Full test suite
```

### 1.2 Service-Provided Features

- Automatic coverage reporting
- Performance benchmarking
- Security scanning
- Parallel execution

## 2. Test Strategy

### 2.1 Test Categories

| Category    | Purpose              | Service Support           |
| ----------- | -------------------- | ------------------------- |
| Unit        | Component logic      | khive dev tracks coverage |
| Integration | Service interactions | khive ci validates        |
| Performance | Speed/resource usage | khive dev benchmarks      |
| Security    | Vulnerability checks | Automatic scanning        |

### 2.2 Service-Aware Test Design

```python
class TestAuthService:
    """Tests designed to work with khive services"""

    def test_token_storage(self):
        """khive dev will validate this test"""
        # Clear, focused test
        service = AuthService()
        token = service.store_token("test-token")
        assert token.is_stored

    def test_performance(self):
        """khive dev automatically benchmarks this"""
        # Service provides timing metrics
        pass
```

## 3. Test Implementation

### 3.1 Unit Tests

```python
# Simple, clear tests that services can analyze
def test_refresh_logic():
    """Test token refresh with backoff"""
    service = AuthService()

    # Mock external service
    with patch('auth.external_api') as mock:
        mock.return_value = new_token()

        result = service.refresh_token()
        assert result.is_valid

    # khive dev ensures this is covered
```

### 3.2 Integration Tests

```python
async def test_full_auth_flow():
    """End-to-end authentication test"""
    # khive ci handles test database setup

    async with test_client() as client:
        # Test complete flow
        response = await client.post("/auth/login",
                                   json={"user": "test"})
        assert response.status == 200

        # Verify token works
        token = response.json()["token"]
        auth_response = await client.get("/protected",
                                       headers={"Authorization": token})
        assert auth_response.status == 200
```

## 4. Service Validation

### 4.1 Coverage Requirements

```yaml
# Enforced automatically by khive dev
coverage:
  minimum: 80%
  target: 90%
  critical_paths: 95%
```

### 4.2 Performance Baselines

```python
# Service tracks these automatically
performance_targets = {
    "auth_request": "< 100ms",
    "token_refresh": "< 200ms",
    "batch_operation": "< 1s for 100 items"
}
```

## 5. Test Data Management

### 5.1 Service-Friendly Fixtures

```python
# Services can analyze and validate fixtures
@pytest.fixture
def valid_user():
    """Standard test user"""
    return User(
        id="test-123",
        name="Test User",
        # khive dev validates fixture usage
    )
```

## 6. Continuous Testing

### 6.1 Development Workflow

```bash
# Write test
# edit test_auth.py

# Validate immediately
khive dev "test this module"

# Fix issues
# edit auth.py

# Validate again
khive dev "check everything"

# Commit when green
khive git "added auth tests"
```

### 6.2 Service Intelligence

khive dev provides:

- Missing test detection
- Coverage gaps
- Performance regressions
- Security issues

## 7. Test Maintenance

### 7.1 Service-Assisted Updates

When tests fail:

```bash
khive dev "why is this test failing?"
khive info "how to mock [specific service]"
```

### 7.2 Evolution Strategy

- Let services track test health
- Focus on business logic tests
- Services handle infrastructure tests

## 8. Success Criteria

- [ ] khive dev shows >80% coverage
- [ ] All tests pass with khive ci
- [ ] No performance regressions
- [ ] Security scan clean
