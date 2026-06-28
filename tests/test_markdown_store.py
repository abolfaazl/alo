from pathlib import Path
from alo import markdown_store

def test_markdown_store_create_and_read(tmp_path: Path):
    test_file = tmp_path / "test.md"
    assert markdown_store.file_exists(test_file) is False
    
    # Create missing
    created = markdown_store.create_if_missing(test_file, "# Test")
    assert created is True
    assert markdown_store.file_exists(test_file) is True
    assert markdown_store.read_text_safely(test_file) == "# Test"
    
    # Don't overwrite
    created_again = markdown_store.create_if_missing(test_file, "# Overwrite")
    assert created_again is False
    assert markdown_store.read_text_safely(test_file) == "# Test"

def test_markdown_store_append(tmp_path: Path):
    test_file = tmp_path / "test.md"
    markdown_store.write_text_safely(test_file, "# Test\n")
    markdown_store.append_text_safely(test_file, "Append")
    assert markdown_store.read_text_safely(test_file) == "# Test\nAppend"
