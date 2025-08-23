"""Comprehensive Pydantic model testing package for khive system.

This package provides comprehensive test coverage for all Pydantic models
used throughout the khive system, focusing on:

- Individual model validation with valid and invalid data scenarios
- Field constraint enforcement (ranges, lengths, patterns, required fields)
- Enum value validation and error handling
- Nested model validation and complex compositions
- Serialization and deserialization consistency
- Error message clarity and actionability
- Custom validator behavior and edge cases
- Performance testing for large model operations

Test Organization:
- test_base_models.py: Core BaseModel functionality and configuration
- test_orchestration_models.py: Orchestration and planning model types
- test_composition_models.py: Agent composition and request/response types
- test_artifacts_models.py: Document, session, and artifact management types
- fixtures/models/: Shared model test fixtures and data generators
"""

__all__ = [
    "TestAgentCompositionRequest",
    "TestAgentRequest",
    "TestAuthor",
    "TestBaseModelCore",
    "TestBaseModelPerformance",
    "TestBaseModelSerialization",
    "TestBaseModelValidation",
    "TestComposerRequest",
    "TestComposerResponse",
    "TestContributionMetadata",
    "TestDocument",
    "TestDocumentType",
    "TestDomainExpertise",
    "TestOrchestrationPlan",
    "TestPlannerRequest",
    "TestPlannerResponse",
    "TestSessionStatus",
]
