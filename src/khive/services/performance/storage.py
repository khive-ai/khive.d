"""Performance data storage with SQLite and JSON backends."""

import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .benchmark_framework import BenchmarkResult

logger = logging.getLogger(__name__)


class PerformanceDatabase:
    """SQLite database for storing performance benchmark results."""

    def __init__(self, db_path: str | Path = "performance.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS benchmark_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        benchmark_name TEXT NOT NULL,
                        operation_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        duration REAL NOT NULL,
                        success_rate REAL NOT NULL,
                        throughput_ops_per_sec REAL NOT NULL,
                        avg_operation_time_ms REAL NOT NULL,
                        memory_start_mb REAL,
                        memory_end_mb REAL,
                        memory_peak_mb REAL,
                        memory_delta_mb REAL,
                        cpu_percent_avg REAL,
                        cpu_percent_peak REAL,
                        io_read_bytes INTEGER,
                        io_write_bytes INTEGER,
                        io_read_count INTEGER,
                        io_write_count INTEGER,
                        network_sent_bytes INTEGER,
                        network_recv_bytes INTEGER,
                        network_connections INTEGER,
                        operations_count INTEGER,
                        success_count INTEGER,
                        error_count INTEGER,
                        full_data TEXT,  -- JSON serialized full result
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS benchmark_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        benchmark_result_id INTEGER,
                        key TEXT NOT NULL,
                        value TEXT,
                        FOREIGN KEY (benchmark_result_id) REFERENCES benchmark_results (id)
                    )
                """
                )

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS benchmark_tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        benchmark_result_id INTEGER,
                        tag TEXT NOT NULL,
                        FOREIGN KEY (benchmark_result_id) REFERENCES benchmark_results (id)
                    )
                """
                )

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS environment_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        benchmark_result_id INTEGER,
                        key TEXT NOT NULL,
                        value TEXT,
                        FOREIGN KEY (benchmark_result_id) REFERENCES benchmark_results (id)
                    )
                """
                )

                # Create indexes for better query performance
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_benchmark_name
                    ON benchmark_results (benchmark_name)
                """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_operation_type
                    ON benchmark_results (operation_type)
                """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_timestamp
                    ON benchmark_results (timestamp)
                """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_benchmark_operation
                    ON benchmark_results (benchmark_name, operation_type)
                """
                )

    def store_result(self, result: BenchmarkResult) -> int:
        """Store a benchmark result and return the ID."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # Insert main result
                cursor = conn.execute(
                    """
                    INSERT INTO benchmark_results (
                        benchmark_name, operation_type, timestamp, duration,
                        success_rate, throughput_ops_per_sec, avg_operation_time_ms,
                        memory_start_mb, memory_end_mb, memory_peak_mb, memory_delta_mb,
                        cpu_percent_avg, cpu_percent_peak,
                        io_read_bytes, io_write_bytes, io_read_count, io_write_count,
                        network_sent_bytes, network_recv_bytes, network_connections,
                        operations_count, success_count, error_count, full_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        result.benchmark_name,
                        result.operation_type,
                        result.timestamp.isoformat(),
                        result.metrics.duration,
                        result.metrics.success_rate,
                        result.metrics.throughput_ops_per_sec,
                        result.metrics.avg_operation_time_ms,
                        result.metrics.memory_start_mb,
                        result.metrics.memory_end_mb,
                        result.metrics.memory_peak_mb,
                        result.metrics.memory_delta_mb,
                        result.metrics.cpu_percent_avg,
                        result.metrics.cpu_percent_peak,
                        result.metrics.io_read_bytes,
                        result.metrics.io_write_bytes,
                        result.metrics.io_read_count,
                        result.metrics.io_write_count,
                        result.metrics.network_sent_bytes,
                        result.metrics.network_recv_bytes,
                        result.metrics.network_connections,
                        result.metrics.operations_count,
                        result.metrics.success_count,
                        result.metrics.error_count,
                        json.dumps(result.to_dict()),
                    ),
                )

                result_id = cursor.lastrowid

                # Store metadata
                for key, value in result.metadata.items():
                    conn.execute(
                        """
                        INSERT INTO benchmark_metadata (benchmark_result_id, key, value)
                        VALUES (?, ?, ?)
                    """,
                        (result_id, key, json.dumps(value)),
                    )

                # Store tags
                for tag in result.tags:
                    conn.execute(
                        """
                        INSERT INTO benchmark_tags (benchmark_result_id, tag)
                        VALUES (?, ?)
                    """,
                        (result_id, tag),
                    )

                # Store environment info
                for key, value in result.environment.items():
                    conn.execute(
                        """
                        INSERT INTO environment_info (benchmark_result_id, key, value)
                        VALUES (?, ?, ?)
                    """,
                        (result_id, key, json.dumps(value)),
                    )

                conn.commit()
                return result_id

    def get_results(
        self,
        benchmark_name: str | None = None,
        operation_type: str | None = None,
        tags: list[str] | None = None,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[BenchmarkResult]:
        """Retrieve benchmark results with filtering."""

        query = """
            SELECT DISTINCT br.full_data
            FROM benchmark_results br
        """

        conditions = []
        params = []

        # Add tag filtering if needed
        if tags:
            query += """
                JOIN benchmark_tags bt ON br.id = bt.benchmark_result_id
            """
            tag_placeholders = ",".join("?" * len(tags))
            conditions.append(f"bt.tag IN ({tag_placeholders})")
            params.extend(tags)

        # Add other filtering conditions
        if benchmark_name:
            conditions.append("br.benchmark_name = ?")
            params.append(benchmark_name)

        if operation_type:
            conditions.append("br.operation_type = ?")
            params.append(operation_type)

        if since:
            conditions.append("br.timestamp >= ?")
            params.append(since.isoformat())

        # Build final query
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY br.timestamp DESC"

        if limit:
            query += f" LIMIT {limit}"

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                results = []

                for row in cursor:
                    try:
                        result_data = json.loads(row[0])
                        result = BenchmarkResult.from_dict(result_data)
                        results.append(result)
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.warning(f"Failed to parse result: {e}")
                        continue

                return results

    def get_latest_result(
        self, benchmark_name: str, operation_type: str
    ) -> BenchmarkResult | None:
        """Get the most recent result for a specific benchmark and operation."""
        results = self.get_results(
            benchmark_name=benchmark_name, operation_type=operation_type, limit=1
        )
        return results[0] if results else None

    def get_performance_summary(
        self,
        benchmark_name: str | None = None,
        operation_type: str | None = None,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Get performance summary statistics."""

        query = """
            SELECT
                benchmark_name,
                operation_type,
                COUNT(*) as result_count,
                AVG(duration) as avg_duration,
                MIN(duration) as min_duration,
                MAX(duration) as max_duration,
                AVG(success_rate) as avg_success_rate,
                AVG(throughput_ops_per_sec) as avg_throughput,
                AVG(memory_peak_mb) as avg_peak_memory,
                MAX(memory_peak_mb) as max_peak_memory,
                AVG(cpu_percent_peak) as avg_peak_cpu
            FROM benchmark_results
        """

        conditions = []
        params = []

        if benchmark_name:
            conditions.append("benchmark_name = ?")
            params.append(benchmark_name)

        if operation_type:
            conditions.append("operation_type = ?")
            params.append(operation_type)

        if since:
            conditions.append("timestamp >= ?")
            params.append(since.isoformat())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " GROUP BY benchmark_name, operation_type"

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                results = []

                columns = [description[0] for description in cursor.description]
                for row in cursor:
                    result_dict = dict(zip(columns, row, strict=False))
                    results.append(result_dict)

                return {"summaries": results, "total_benchmarks": len(results)}

    def cleanup_old_results(self, days_to_keep: int = 30):
        """Remove benchmark results older than specified days."""
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # Get IDs of old results
                cursor = conn.execute(
                    """
                    SELECT id FROM benchmark_results WHERE timestamp < ?
                """,
                    (cutoff_date,),
                )

                old_ids = [row[0] for row in cursor]

                if old_ids:
                    id_placeholders = ",".join("?" * len(old_ids))

                    # Delete related records
                    conn.execute(
                        f"""
                        DELETE FROM benchmark_metadata
                        WHERE benchmark_result_id IN ({id_placeholders})
                    """,
                        old_ids,
                    )

                    conn.execute(
                        f"""
                        DELETE FROM benchmark_tags
                        WHERE benchmark_result_id IN ({id_placeholders})
                    """,
                        old_ids,
                    )

                    conn.execute(
                        f"""
                        DELETE FROM environment_info
                        WHERE benchmark_result_id IN ({id_placeholders})
                    """,
                        old_ids,
                    )

                    # Delete main records
                    conn.execute(
                        f"""
                        DELETE FROM benchmark_results
                        WHERE id IN ({id_placeholders})
                    """,
                        old_ids,
                    )

                    conn.commit()
                    logger.info(f"Cleaned up {len(old_ids)} old benchmark results")


class BenchmarkStorage:
    """High-level storage interface combining database and file storage."""

    def __init__(self, storage_path: str | Path = ".khive/performance"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize backends
        self.db = PerformanceDatabase(self.storage_path / "benchmarks.db")
        self.json_storage_path = self.storage_path / "json_exports"
        self.json_storage_path.mkdir(exist_ok=True)

    def store_result(self, result: BenchmarkResult) -> int:
        """Store a benchmark result."""
        return self.db.store_result(result)

    def store_results(self, results: list[BenchmarkResult]) -> list[int]:
        """Store multiple benchmark results."""
        return [self.store_result(result) for result in results]

    def get_results(
        self,
        benchmark_name: str | None = None,
        operation_type: str | None = None,
        tags: list[str] | None = None,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[BenchmarkResult]:
        """Retrieve benchmark results with filtering."""
        return self.db.get_results(
            benchmark_name=benchmark_name,
            operation_type=operation_type,
            tags=tags,
            since=since,
            limit=limit,
        )

    def get_baseline(
        self, benchmark_name: str, operation_type: str
    ) -> BenchmarkResult | None:
        """Get baseline (most recent) result for comparison."""
        return self.db.get_latest_result(benchmark_name, operation_type)

    def export_to_json(
        self,
        export_name: str,
        benchmark_name: str | None = None,
        operation_type: str | None = None,
        since: datetime | None = None,
    ) -> Path:
        """Export results to JSON file."""
        results = self.get_results(
            benchmark_name=benchmark_name, operation_type=operation_type, since=since
        )

        export_data = {
            "export_name": export_name,
            "export_timestamp": datetime.now().isoformat(),
            "filters": {
                "benchmark_name": benchmark_name,
                "operation_type": operation_type,
                "since": since.isoformat() if since else None,
            },
            "results_count": len(results),
            "results": [result.to_dict() for result in results],
        }

        export_file = (
            self.json_storage_path
            / f"{export_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(export_file, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        return export_file

    def import_from_json(self, json_file: str | Path) -> int:
        """Import results from JSON file."""
        json_file = Path(json_file)

        with open(json_file) as f:
            data = json.load(f)

        imported_count = 0
        for result_data in data.get("results", []):
            try:
                result = BenchmarkResult.from_dict(result_data)
                self.store_result(result)
                imported_count += 1
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to import result: {e}")
                continue

        logger.info(f"Imported {imported_count} benchmark results from {json_file}")
        return imported_count

    def get_summary(
        self,
        benchmark_name: str | None = None,
        operation_type: str | None = None,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Get performance summary statistics."""
        return self.db.get_performance_summary(
            benchmark_name=benchmark_name, operation_type=operation_type, since=since
        )

    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old benchmark data."""
        self.db.cleanup_old_results(days_to_keep)

        # Also clean up old JSON exports
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        for json_file in self.json_storage_path.glob("*.json"):
            try:
                # Extract timestamp from filename
                filename_parts = json_file.stem.split("_")
                if len(filename_parts) >= 2:
                    date_str = "_".join(filename_parts[-2:])
                    file_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")

                    if file_date < cutoff_date:
                        json_file.unlink()
                        logger.info(f"Removed old JSON export: {json_file}")

            except (ValueError, IndexError):
                # Skip files with unexpected naming format
                continue

    def get_storage_info(self) -> dict[str, Any]:
        """Get information about stored data."""
        total_results = len(self.get_results())

        summary = self.get_summary()

        db_size = (
            self.storage_path.joinpath("benchmarks.db").stat().st_size
            if self.storage_path.joinpath("benchmarks.db").exists()
            else 0
        )

        json_files = list(self.json_storage_path.glob("*.json"))
        json_size = sum(f.stat().st_size for f in json_files)

        return {
            "total_results": total_results,
            "unique_benchmarks": len(summary.get("summaries", [])),
            "database_size_mb": db_size / (1024 * 1024),
            "json_exports_count": len(json_files),
            "json_exports_size_mb": json_size / (1024 * 1024),
            "storage_path": str(self.storage_path),
        }
