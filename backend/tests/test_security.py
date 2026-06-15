from pathlib import Path
from app.core.security import validate_file, save_file, load_file
import tempfile
import pytest

def test_validate_file_size():
    content = b"x" * (21 * 1024 * 1024)
    err = validate_file(content, "test.pdf", max_mb=20)
    assert "File exceeds 20MB limit" in err

def test_validate_file_extension():
    content = b"dummy content"
    err = validate_file(content, "test.exe", max_mb=20)
    assert err is not None
    assert "Extension not allowed" in err or "File type not allowed" in err

def test_fernet_encryption_decryption():
    content = b"secret data"
    with tempfile.TemporaryDirectory() as tmp:
        upload_dir = Path(tmp)
        
        # Save encrypts it
        saved_path = save_file(content, "doc_123", upload_dir)
        assert saved_path.exists()
        
        # Raw disk content should be encrypted
        raw_disk = saved_path.read_bytes()
        assert raw_disk != content
        
        # Load decrypts it
        loaded_content = load_file("doc_123", upload_dir)
        assert loaded_content == content
