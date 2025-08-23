"""Performance tests for large-scale Pydantic model operations."""

import time
from datetime import datetime, timedelta, timezone

from lionagi.fields import Instruct

from khive.prompts import AgentRole
from khive.services.artifacts.models import (
    Author,
    ContributionMetadata,
    Document,
    DocumentType,
)
from khive.services.composition.parts import (
    ComposerRequest,
    ComposerResponse,
    DomainExpertise,
)
from khive.services.orchestration.parts import AgentRequest, OrchestrationPlan
from khive.services.plan.parts import (
    AgentRecommendation,
    ComplexityLevel,
    PlannerResponse,
    QualityGate,
    TaskPhase,
    WorkflowPattern,
)


class TestModelCreationPerformance:
    """Test performance of model creation operations."""

    def test_large_document_creation_performance(self):
        """Test performance of creating documents with large content."""
        large_content = "x" * 1_000_000  # 1MB content
        timestamp = datetime.now(timezone.utc)

        start_time = time.time()
        document = Document(
            session_id="perf_test_session",
            name="large_performance_document",
            type=DocumentType.DELIVERABLE,
            content=large_content,
            last_modified=timestamp,
        )
        creation_time = time.time() - start_time

        # Should create within reasonable time (under 1 second)
        assert creation_time < 1.0
        assert len(document.content) == 1_000_000

    def test_bulk_document_creation_performance(self):
        """Test performance of creating many documents."""
        timestamp = datetime.now(timezone.utc)
        documents = []

        start_time = time.time()
        for i in range(1000):
            document = Document(
                session_id=f"session_{i}",
                name=f"document_{i}",
                type=DocumentType.SCRATCHPAD,
                content=f"Content for document {i}",
                last_modified=timestamp,
            )
            documents.append(document)
        bulk_creation_time = time.time() - start_time

        # Should create 1000 documents within reasonable time
        assert bulk_creation_time < 5.0
        assert len(documents) == 1000

    def test_complex_orchestration_plan_creation_performance(self):
        """Test performance of creating complex orchestration plans."""
        agent_requests = []

        # Create many agent requests
        for i in range(100):
            instruct = Instruct(
                instruction=f"Task {i} for performance testing",
                guidance=f"Guidance for task {i}",
                context=f"Context for task {i} with detailed requirements",
            )
            composer_request = ComposerRequest(
                role=AgentRole.RESEARCHER,
                domains="async-programming,software-architecture",
                context=f"Complex context for agent {i}",
            )
            agent_request = AgentRequest(
                instruct=instruct,
                compose_request=composer_request,
                analysis_type="RequirementsAnalysis",
            )
            agent_requests.append(agent_request)

        start_time = time.time()
        orchestration_plan = OrchestrationPlan(
            common_background="Large-scale performance testing orchestration plan",
            agent_requests=agent_requests,
            execution_strategy="concurrent",
        )
        creation_time = time.time() - start_time

        # Should create complex plan within reasonable time
        assert creation_time < 2.0
        assert len(orchestration_plan.agent_requests) == 100

    def test_composer_response_with_many_domain_expertises_performance(self):
        """Test performance of creating composer responses with many domain expertises."""
        domain_expertises = []

        # Create many domain expertises
        for i in range(50):
            domain_expertise = DomainExpertise(
                domain_id=f"domain_{i}",
                knowledge_patterns={
                    f"pattern_{j}": [f"item_{k}" for k in range(10)] for j in range(5)
                },
                decision_rules={f"rule_{j}": f"description_{j}" for j in range(10)},
                specialized_tools=[f"tool_{j}" for j in range(20)],
                confidence_thresholds={
                    f"threshold_{j}": 0.8 + (j * 0.01) for j in range(5)
                },
            )
            domain_expertises.append(domain_expertise)

        start_time = time.time()
        composer_response = ComposerResponse(
            success=True,
            summary="Complex multi-domain composer response for performance testing",
            agent_id="performance_test_agent",
            role="researcher",
            domains=[f"domain_{i}" for i in range(50)],
            system_prompt="Performance testing system prompt with detailed instructions",
            capabilities=[f"capability_{i}" for i in range(20)],
            tools=[f"tool_{i}" for i in range(30)],
            domain_expertise=domain_expertises,
            confidence=0.95,
        )
        creation_time = time.time() - start_time

        # Should create complex response within reasonable time
        assert creation_time < 1.5
        assert len(composer_response.domain_expertise) == 50


class TestModelSerializationPerformance:
    """Test performance of model serialization operations."""

    def test_large_document_serialization_performance(self):
        """Test serialization performance of large documents."""
        # Create document with large content and many contributions
        large_content = "Large content for serialization testing. " * 10000  # ~400KB
        contributions = []
        base_time = datetime.now(timezone.utc)

        for i in range(100):
            author = Author(id=f"contributor_{i}", role="contributor")
            contribution = ContributionMetadata(
                author=author,
                timestamp=base_time + timedelta(minutes=i),
                content_length=len(large_content) // 100,
            )
            contributions.append(contribution)

        document = Document(
            session_id="serialization_perf_session",
            name="large_serialization_document",
            type=DocumentType.DELIVERABLE,
            content=large_content,
            contributions=contributions,
            last_modified=base_time,
        )

        # Test JSON serialization performance
        start_time = time.time()
        json_data = document.model_dump_json()
        serialization_time = time.time() - start_time

        assert serialization_time < 1.0  # Should serialize quickly
        assert len(json_data) > 400000  # Should have substantial content

        # Test deserialization performance
        start_time = time.time()
        restored_document = Document.model_validate_json(json_data)
        deserialization_time = time.time() - start_time

        assert deserialization_time < 1.0  # Should deserialize quickly
        assert restored_document == document

    def test_bulk_model_serialization_performance(self):
        """Test performance of serializing many models."""
        models = []
        base_time = datetime.now(timezone.utc)

        # Create many documents
        for i in range(500):
            document = Document(
                session_id=f"bulk_session_{i}",
                name=f"bulk_document_{i}",
                type=DocumentType.SCRATCHPAD,
                content=f"Bulk content for document {i} with sufficient detail for testing",
                last_modified=base_time + timedelta(minutes=i),
            )
            models.append(document)

        # Test bulk serialization performance
        start_time = time.time()
        serialized_models = []
        for model in models:
            serialized_models.append(model.model_dump())
        serialization_time = time.time() - start_time

        assert serialization_time < 3.0  # Should serialize bulk data reasonably quickly
        assert len(serialized_models) == 500

        # Test bulk deserialization performance
        start_time = time.time()
        deserialized_models = []
        for data in serialized_models:
            deserialized_models.append(Document.model_validate(data))
        deserialization_time = time.time() - start_time

        assert (
            deserialization_time < 3.0
        )  # Should deserialize bulk data reasonably quickly
        assert len(deserialized_models) == 500

    def test_complex_nested_model_serialization_performance(self):
        """Test serialization performance of deeply nested models."""
        # Create complex planner response with nested structures
        agent_recommendations = []
        for i in range(50):
            agent_rec = AgentRecommendation(
                role=f"role_{i}",
                domain=f"domain_{i}",
                priority=0.5 + (i * 0.01),
                reasoning=f"Detailed reasoning for agent {i} with comprehensive justification",
            )
            agent_recommendations.append(agent_rec)

        task_phases = []
        for i in range(20):
            phase_agents = (
                agent_recommendations[i : i + 3]
                if i + 3 <= len(agent_recommendations)
                else agent_recommendations[i:]
            )
            task_phase = TaskPhase(
                name=f"Phase {i}",
                description=f"Detailed description for phase {i} with comprehensive requirements",
                agents=phase_agents,
                dependencies=[f"phase_{j}" for j in range(max(0, i - 2), i)],
                quality_gate=QualityGate.THOROUGH,
                coordination_pattern=WorkflowPattern.PARALLEL,
            )
            task_phases.append(task_phase)

        planner_response = PlannerResponse(
            success=True,
            summary="Complex nested planner response for performance testing with detailed analysis",
            complexity=ComplexityLevel.VERY_COMPLEX,
            recommended_agents=50,
            phases=task_phases,
            spawn_commands=[f"khive compose role_{i} -d domain_{i}" for i in range(50)],
            session_id="complex_nested_performance_session",
            confidence=0.92,
        )

        # Test complex serialization performance
        start_time = time.time()
        json_data = planner_response.model_dump_json()
        serialization_time = time.time() - start_time

        assert serialization_time < 2.0  # Should handle complex nesting efficiently

        # Test complex deserialization performance
        start_time = time.time()
        restored_response = PlannerResponse.model_validate_json(json_data)
        deserialization_time = time.time() - start_time

        assert deserialization_time < 2.0  # Should handle complex nesting efficiently
        assert restored_response == planner_response


class TestModelValidationPerformance:
    """Test performance of model validation operations."""

    def test_validation_performance_with_large_data(self):
        """Test validation performance with large data structures."""
        # Create data that will stress validation
        large_domains = [f"domain_{i}" for i in range(1000)]
        large_capabilities = [f"capability_{i}" for i in range(500)]
        large_tools = [f"tool_{i}" for i in range(300)]

        start_time = time.time()
        composer_response = ComposerResponse(
            success=True,
            summary="Large data validation performance test with extensive capabilities",
            agent_id="large_data_validation_agent",
            role="performance_test_role",
            domains=large_domains,
            system_prompt="Extensive system prompt for validation performance testing",
            capabilities=large_capabilities,
            tools=large_tools,
            confidence=0.88,
        )
        validation_time = time.time() - start_time

        assert validation_time < 1.0  # Should validate large data efficiently
        assert len(composer_response.domains) == 1000
        assert len(composer_response.capabilities) == 500
        assert len(composer_response.tools) == 300

    def test_validation_error_performance(self):
        """Test performance of validation error generation."""
        invalid_data_sets = []

        # Generate many invalid data sets
        for i in range(100):
            invalid_data = {
                "success": True,
                "summary": "",  # Invalid: empty string
                "agent_id": f"agent_{i}",
                "role": "role",
                "system_prompt": "prompt",
                "confidence": 1.5,  # Invalid: out of range
            }
            invalid_data_sets.append(invalid_data)

        start_time = time.time()
        validation_errors = []
        for data in invalid_data_sets:
            try:
                ComposerResponse(**data)
            except Exception as e:
                validation_errors.append(e)
        validation_error_time = time.time() - start_time

        assert validation_error_time < 2.0  # Should generate errors efficiently
        assert len(validation_errors) == 100

    def test_field_constraint_validation_performance(self):
        """Test performance of field constraint validation."""
        # Test string length constraints
        constraint_test_data = []
        for i in range(200):
            # Create data that will test various constraints
            data = {
                "role": "a" * (50 + i),  # Varying lengths
                "domains": "domain1,domain2," + ("domain," * i),  # Varying lengths
                "context": "Context with varying length " * (i + 1),  # Varying lengths
            }
            constraint_test_data.append(data)

        start_time = time.time()
        valid_requests = []
        validation_errors = []

        for data in constraint_test_data:
            try:
                from khive.services.composition.parts import AgentCompositionRequest

                request = AgentCompositionRequest(**data)
                valid_requests.append(request)
            except Exception as e:
                validation_errors.append(e)

        constraint_validation_time = time.time() - start_time

        assert (
            constraint_validation_time < 3.0
        )  # Should validate constraints efficiently
        # Some should be valid, some should fail due to length constraints
        assert len(valid_requests) + len(validation_errors) == 200


class TestModelMemoryPerformance:
    """Test memory usage patterns of models."""

    def test_memory_efficiency_with_many_models(self):
        """Test memory efficiency when creating many model instances."""
        import tracemalloc

        tracemalloc.start()

        # Create many models
        documents = []
        for i in range(1000):
            document = Document(
                session_id=f"memory_test_session_{i}",
                name=f"memory_test_document_{i}",
                type=DocumentType.SCRATCHPAD,
                content=f"Memory efficiency test content for document {i}",
                last_modified=datetime.now(timezone.utc),
            )
            documents.append(document)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory usage should be reasonable (less than 50MB for 1000 documents)
        assert peak < 50 * 1024 * 1024  # 50MB
        assert len(documents) == 1000

    def test_memory_cleanup_after_serialization(self):
        """Test memory cleanup after serialization operations."""
        import gc
        import tracemalloc

        tracemalloc.start()

        # Create and serialize many models
        for batch in range(10):
            models = []
            for i in range(100):
                document = Document(
                    session_id=f"cleanup_session_{batch}_{i}",
                    name=f"cleanup_document_{batch}_{i}",
                    type=DocumentType.DELIVERABLE,
                    content=f"Memory cleanup test content for batch {batch} document {i}",
                    last_modified=datetime.now(timezone.utc),
                )
                models.append(document)

            # Serialize all models
            serialized = [model.model_dump_json() for model in models]

            # Force cleanup
            del models
            del serialized
            gc.collect()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Peak memory should be reasonable for batch processing
        assert peak < 100 * 1024 * 1024  # 100MB for all batches

    def test_model_copy_performance(self):
        """Test performance of model copying operations."""
        # Create a complex model
        contributions = []
        for i in range(50):
            author = Author(id=f"copy_author_{i}", role="contributor")
            contribution = ContributionMetadata(
                author=author,
                timestamp=datetime.now(timezone.utc) + timedelta(minutes=i),
                content_length=1000 + i,
            )
            contributions.append(contribution)

        original_document = Document(
            session_id="copy_performance_session",
            name="copy_performance_document",
            type=DocumentType.DELIVERABLE,
            content="Complex document content for copy performance testing " * 100,
            contributions=contributions,
            version=5,
            last_modified=datetime.now(timezone.utc),
        )

        # Test copy performance
        start_time = time.time()
        copied_documents = []
        for i in range(100):
            copied_doc = original_document.model_copy(
                update={"name": f"copied_document_{i}", "version": i}
            )
            copied_documents.append(copied_doc)
        copy_time = time.time() - start_time

        assert copy_time < 2.0  # Should copy efficiently
        assert len(copied_documents) == 100
        assert all(doc.content == original_document.content for doc in copied_documents)
        assert all(
            len(doc.contributions) == len(original_document.contributions)
            for doc in copied_documents
        )


class TestModelConcurrencyPerformance:
    """Test model performance under concurrent operations."""

    def test_concurrent_model_creation(self):
        """Test concurrent model creation performance."""
        import concurrent.futures

        def create_document_batch(batch_id: int) -> list[Document]:
            """Create a batch of documents."""
            documents = []
            for i in range(10):
                document = Document(
                    session_id=f"concurrent_session_{batch_id}_{i}",
                    name=f"concurrent_document_{batch_id}_{i}",
                    type=DocumentType.SCRATCHPAD,
                    content=f"Concurrent creation test content for batch {batch_id} document {i}",
                    last_modified=datetime.now(timezone.utc),
                )
                documents.append(document)
            return documents

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_document_batch, i) for i in range(20)]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        concurrent_creation_time = time.time() - start_time

        # Should handle concurrent creation efficiently
        assert concurrent_creation_time < 5.0
        assert len(results) == 20
        assert sum(len(batch) for batch in results) == 200

    def test_concurrent_serialization_performance(self):
        """Test concurrent serialization performance."""
        import concurrent.futures

        # Create documents to serialize
        documents = []
        for i in range(100):
            document = Document(
                session_id=f"concurrent_serial_session_{i}",
                name=f"concurrent_serial_document_{i}",
                type=DocumentType.DELIVERABLE,
                content=f"Concurrent serialization test content for document {i} " * 10,
                last_modified=datetime.now(timezone.utc),
            )
            documents.append(document)

        def serialize_document_batch(documents_batch: list[Document]) -> list[str]:
            """Serialize a batch of documents."""
            return [doc.model_dump_json() for doc in documents_batch]

        # Split documents into batches
        batch_size = 10
        document_batches = [
            documents[i : i + batch_size] for i in range(0, len(documents), batch_size)
        ]

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(serialize_document_batch, batch)
                for batch in document_batches
            ]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        concurrent_serialization_time = time.time() - start_time

        # Should handle concurrent serialization efficiently
        assert concurrent_serialization_time < 3.0
        assert len(results) == 10  # 10 batches
        assert sum(len(batch) for batch in results) == 100
