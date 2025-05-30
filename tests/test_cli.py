"""
Unit tests for the CLI module.
These tests check the command-line interface functionality.
"""
import sys
from unittest.mock import patch, MagicMock

import pytest

from src.cli import (
    upload_flashcards,
    list_flashcards,
    setup_db,
    main
)


def test_upload_flashcards_success():
    """Test successful flashcard upload."""
    with patch('src.cli.upsert_flashcards_from_json') as mock_upsert, \
         patch('src.cli.print') as mock_print:
        # Set up the mock
        mock_upsert.return_value = ['id1', 'id2', 'id3']

        # Call the function
        upload_flashcards('test.json')

        # Verify behavior
        mock_upsert.assert_called_once_with('test.json')
        mock_print.assert_called_once_with('Successfully uploaded 3 flashcards to Supabase')


def test_upload_flashcards_error():
    """Test handling of flashcard upload errors."""
    with patch('src.cli.upsert_flashcards_from_json') as mock_upsert, \
         patch('src.cli.print') as mock_print, \
         patch('src.cli.sys.exit') as mock_exit:
        # Set up the mock to raise an exception
        mock_upsert.side_effect = Exception('Test error')

        # Call the function
        upload_flashcards('test.json')

        # Verify behavior
        mock_upsert.assert_called_once_with('test.json')
        mock_print.assert_called_once_with('Error uploading flashcards: Test error')
        mock_exit.assert_called_once_with(1)


def test_list_flashcards_success():
    """Test successful flashcard listing."""
    with patch('src.cli.get_flashcards') as mock_get, \
         patch('src.cli.print') as mock_print:
        # Set up the mock
        mock_get.return_value = [
            {
                'id': 'id1',
                'question': 'Test question',
                'answer': 'Test answer',
                'level': 'intermediate',
                'tags': ['test', 'mock']
            }
        ]

        # Call the function
        list_flashcards(10, 0, 'intermediate', ['test'])

        # Verify behavior
        mock_get.assert_called_once_with(limit=10, offset=0, level='intermediate', tags=['test'])
        assert mock_print.call_count > 0  # Multiple print calls


def test_list_flashcards_error():
    """Test handling of flashcard listing errors."""
    with patch('src.cli.get_flashcards') as mock_get, \
         patch('src.cli.print') as mock_print, \
         patch('src.cli.sys.exit') as mock_exit:
        # Set up the mock to raise an exception
        mock_get.side_effect = Exception('Test error')

        # Call the function
        list_flashcards(10, 0, 'intermediate', ['test'])

        # Verify behavior
        mock_get.assert_called_once_with(limit=10, offset=0, level='intermediate', tags=['test'])
        mock_print.assert_called_once_with('Error retrieving flashcards: Test error')
        mock_exit.assert_called_once_with(1)


def test_setup_db_success():
    """Test successful database setup."""
    with patch('src.cli.initialize_tables') as mock_init, \
         patch('src.cli.print') as mock_print:
        # Set up the mock
        mock_init.return_value = ['Table 1 created', 'Table 2 created']

        # Call the function
        setup_db()

        # Verify behavior
        mock_init.assert_called_once()
        assert mock_print.call_count == 2  # Two print calls


def test_setup_db_error():
    """Test handling of database setup errors."""
    with patch('src.cli.initialize_tables') as mock_init, \
         patch('src.cli.print') as mock_print, \
         patch('src.cli.sys.exit') as mock_exit:
        # Set up the mock to raise an exception
        mock_init.side_effect = Exception('Test error')

        # Call the function
        setup_db()

        # Verify behavior
        mock_init.assert_called_once()
        mock_print.assert_called_once_with('Error setting up database: Test error')
        mock_exit.assert_called_once_with(1)


def test_main_setup():
    """Test main function with setup command."""
    with patch('src.cli.argparse.ArgumentParser.parse_args') as mock_parse_args, \
         patch('src.cli.setup_db') as mock_setup:
        # Set up the mock
        args = MagicMock()
        args.command = 'setup'
        mock_parse_args.return_value = args

        # Call the function
        main()

        # Verify behavior
        mock_setup.assert_called_once()


def test_main_upload():
    """Test main function with upload command."""
    with patch('src.cli.argparse.ArgumentParser.parse_args') as mock_parse_args, \
         patch('src.cli.upload_flashcards') as mock_upload:
        # Set up the mock
        args = MagicMock()
        args.command = 'upload'
        args.filepath = 'test.json'
        mock_parse_args.return_value = args

        # Call the function
        main()

        # Verify behavior
        mock_upload.assert_called_once_with('test.json')


def test_main_list():
    """Test main function with list command."""
    with patch('src.cli.argparse.ArgumentParser.parse_args') as mock_parse_args, \
         patch('src.cli.list_flashcards') as mock_list:
        # Set up the mock
        args = MagicMock()
        args.command = 'list'
        args.limit = 10
        args.offset = 0
        args.level = 'intermediate'
        args.tags = ['test']
        mock_parse_args.return_value = args

        # Call the function
        main()

        # Verify behavior
        mock_list.assert_called_once_with(10, 0, 'intermediate', ['test'])


def test_main_help():
    """Test main function with no command (help)."""
    with patch('src.cli.argparse.ArgumentParser.parse_args') as mock_parse_args, \
         patch('src.cli.argparse.ArgumentParser.print_help') as mock_print_help:
        # Set up the mock
        args = MagicMock()
        args.command = None
        mock_parse_args.return_value = args

        # Call the function
        main()

        # Verify behavior
        mock_print_help.assert_called_once()
