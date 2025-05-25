import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from click.testing import CliRunner

# Mock problematic imports before any khive imports
sys.modules['docling'] = MagicMock()
sys.modules['docling.document_converter'] = MagicMock()
sys.modules['docling_core'] = MagicMock()
sys.modules['docling_ibm_models'] = MagicMock()
sys.modules['docling_ibm_models.layoutmodel'] = MagicMock()
sys.modules['docling_ibm_models.layoutmodel.layout_predictor'] = MagicMock()
sys.modules['tiktoken'] = MagicMock()
sys.modules['transformers'] = MagicMock()

from khive.cli.khive_reader import reader


class TestKhiveReaderFunctions:
    """Test core functionality of khive reader command."""

    def test_cache_file_location(self):
        """Test cache file location is correctly determined."""
        from khive.cli.khive_reader import get_cache_file_path
        
        cache_path = get_cache_file_path()
        assert cache_path.name == "khive_reader_cache.json"
        assert cache_path.parent.name == ".khive"

    def test_load_cache_empty(self):
        """Test loading cache when no cache file exists."""
        from khive.cli.khive_reader import load_cache
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "nonexistent_cache.json"
            cache = load_cache(cache_file)
            assert cache == {}

    def test_load_cache_with_data(self):
        """Test loading cache with existing data."""
        from khive.cli.khive_reader import load_cache
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "cache.json"
            test_data = {"doc1": {"content": "test"}}
            cache_file.write_text(json.dumps(test_data))
            
            cache = load_cache(cache_file)
            assert cache == test_data

    def test_load_cache_invalid_json(self):
        """Test loading cache with invalid JSON."""
        from khive.cli.khive_reader import load_cache
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "cache.json"
            cache_file.write_text("invalid json")
            
            cache = load_cache(cache_file)
            assert cache == {}

    def test_save_cache(self):
        """Test saving cache to file."""
        from khive.cli.khive_reader import save_cache
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "cache.json"
            test_data = {"doc1": {"content": "test"}}
            
            save_cache(cache_file, test_data)
            
            assert cache_file.exists()
            loaded_data = json.loads(cache_file.read_text())
            assert loaded_data == test_data

    @patch('khive.cli.khive_reader.asyncio.run')
    def test_main_with_keyboard_interrupt(self, mock_run):
        """Test main function handles KeyboardInterrupt gracefully."""
        mock_run.side_effect = KeyboardInterrupt()
        
        with patch('khive.cli.khive_reader.sys.exit') as mock_exit:
            from khive.cli.khive_reader import main
            main()
            mock_exit.assert_called_once_with(130)

    @patch('khive.cli.khive_reader.asyncio.run')
    def test_main_with_exception(self, mock_run):
        """Test main function handles general exceptions."""
        mock_run.side_effect = Exception("Test error")
        
        with patch('khive.cli.khive_reader.sys.exit') as mock_exit:
            from khive.cli.khive_reader import main
            main()
            mock_exit.assert_called_once_with(1)

    @patch('khive.cli.khive_reader.reader_service')
    def test_handle_request_and_print_success(self, mock_service):
        """Test successful request handling and printing."""
        from khive.cli.khive_reader import _handle_request_and_print
        
        # Mock successful response
        mock_response = {
            "success": True,
            "content": {
                "doc_id": "test_doc",
                "text": "Test content"
            }
        }
        mock_service.handle_request = AsyncMock(return_value=mock_response)
        
        # Mock request
        mock_request = {"action": "open", "path_or_url": "test.txt"}
        
        with patch('builtins.print') as mock_print:
            import asyncio
            result = asyncio.run(_handle_request_and_print(mock_request))
            
            assert result == 0
            mock_print.assert_called()

    @patch('khive.cli.khive_reader.reader_service')
    def test_handle_request_and_print_failure(self, mock_service):
        """Test failed request handling and printing."""
        from khive.cli.khive_reader import _handle_request_and_print
        
        # Mock failed response
        mock_response = {
            "success": False,
            "error": "Test error"
        }
        mock_service.handle_request = AsyncMock(return_value=mock_response)
        
        # Mock request
        mock_request = {"action": "open", "path_or_url": "nonexistent.txt"}
        
        with patch('builtins.print') as mock_print:
            import asyncio
            result = asyncio.run(_handle_request_and_print(mock_request))
            
            assert result == 1
            mock_print.assert_called()

    @patch('khive.cli.khive_reader.reader_service')
    def test_main_async_with_open_command(self, mock_service):
        """Test main async function with open command."""
        from khive.cli.khive_reader import _main
        
        mock_response = {
            "success": True,
            "content": {"doc_id": "test_doc", "length": 1000}
        }
        mock_service.handle_request = AsyncMock(return_value=mock_response)
        
        with patch('builtins.print'):
            import asyncio
            result = asyncio.run(_main([
                "open", "--path_or_url", "test.txt"
            ]))
            
            assert result == 0

    @patch('khive.cli.khive_reader.reader_service')
    def test_main_async_with_read_command(self, mock_service):
        """Test main async function with read command."""
        from khive.cli.khive_reader import _main
        
        mock_response = {
            "success": True,
            "content": {"text": "Test content", "length": 12}
        }
        mock_service.handle_request = AsyncMock(return_value=mock_response)
        
        with patch('builtins.print'):
            import asyncio
            result = asyncio.run(_main([
                "read", "--doc_id", "test_doc", "--start_offset", "0", "--end_offset", "100"
            ]))
            
            assert result == 0

    @patch('khive.cli.khive_reader.reader_service')
    def test_main_async_with_list_dir_command(self, mock_service):
        """Test main async function with list_dir command."""
        from khive.cli.khive_reader import _main
        
        mock_response = {
            "success": True,
            "content": {
                "files": [
                    {"name": "file1.txt", "size": 100},
                    {"name": "file2.txt", "size": 200}
                ]
            }
        }
        mock_service.handle_request = AsyncMock(return_value=mock_response)
        
        with patch('builtins.print'):
            import asyncio
            result = asyncio.run(_main([
                "list_dir", "--path", "/test/path", "--recursive"
            ]))
            
            assert result == 0


class TestKhiveReaderIntegration:
    """Test integration aspects of khive reader."""

    def test_cache_persistence(self):
        """Test that cache persists across operations."""
        from khive.cli.khive_reader import load_cache, save_cache
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "cache.json"
            
            # Save some data
            test_data = {"doc1": {"content": "test"}}
            save_cache(cache_file, test_data)
            
            # Load it back
            loaded_data = load_cache(cache_file)
            assert loaded_data == test_data

    def test_global_cache_initialization(self):
        """Test that global cache is properly initialized."""
        from khive.cli.khive_reader import CACHE
        assert isinstance(CACHE, dict)

    def test_argparse_integration(self):
        """Test argparse integration works correctly."""
        from khive.cli.khive_reader import _main
        
        # Test with invalid arguments - should not crash
        import asyncio
        with patch('builtins.print'):
            result = asyncio.run(_main(["invalid_command"]))
            # Should handle gracefully, not crash

    @patch('khive.cli.khive_reader.reader_service')
    def test_reader_service_integration(self, mock_service):
        """Test integration with reader service."""
        mock_service.handle_request = AsyncMock(return_value={
            "success": True,
            "content": {"test": "data"}
        })
        
        from khive.cli.khive_reader import _handle_request_and_print
        
        import asyncio
        with patch('builtins.print'):
            result = asyncio.run(_handle_request_and_print({"action": "test"}))
            assert result == 0

    def test_cli_entry_point(self):
        """Test CLI entry point exists and is callable."""
        from khive.cli.khive_reader import main
        assert callable(main)

    @patch('khive.cli.khive_reader.reader_service')
    def test_exception_handling_in_request_processing(self, mock_service):
        """Test exception handling during request processing."""
        from khive.cli.khive_reader import _handle_request_and_print
        
        mock_service.handle_request = AsyncMock(side_effect=Exception("Test error"))
        
        with patch('builtins.print'):
            import asyncio
            result = asyncio.run(_handle_request_and_print({"action": "test"}))
            assert result == 1

    @patch('khive.cli.khive_reader.reader_service')
    def test_cache_repopulation_for_read(self, mock_service):
        """Test cache repopulation during read operations."""
        from khive.cli.khive_reader import _main
        
        mock_service.handle_request = AsyncMock(return_value={
            "success": True,
            "content": {"text": "content", "length": 7}
        })
        
        import asyncio
        with patch('builtins.print'):
            result = asyncio.run(_main([
                "read", "--doc_id", "test", "--start_offset", "0"
            ]))
            assert result == 0