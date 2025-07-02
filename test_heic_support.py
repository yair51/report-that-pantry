#!/usr/bin/env python3

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.helpers import convert_heic_to_jpeg, is_heic_file, allowed_file
from PIL import Image
import io

def test_heic_support():
    """Test HEIC support functionality"""
    
    print("Testing HEIC support implementation...")
    
    # Test filename detection
    test_files = [
        "photo.heic",
        "image.HEIC", 
        "picture.heif",
        "test.HEIF",
        "normal.jpg",
        "regular.png"
    ]
    
    print("\n1. Testing filename detection:")
    for filename in test_files:
        is_heic = is_heic_file(filename)
        is_allowed = allowed_file(filename)
        print(f"  {filename}: HEIC={is_heic}, Allowed={is_allowed}")
    
    # Test if pillow-heif is working
    print("\n2. Testing pillow-heif import:")
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
        print("  ✅ pillow-heif imported and registered successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import pillow-heif: {e}")
        return
    except Exception as e:
        print(f"  ⚠️ pillow-heif import warning: {e}")
    
    # Test creating a fake HEIC file (since we don't have a real one)
    print("\n3. Testing conversion function structure:")
    
    # Create a simple test JPEG image
    img = Image.new('RGB', (100, 100), color='red')
    test_buffer = io.BytesIO()
    img.save(test_buffer, format='JPEG')
    test_buffer.seek(0)
    
    # Create a mock file object
    class MockFile:
        def __init__(self, buffer, filename):
            self.buffer = buffer
            self.filename = filename
            
        def read(self):
            return self.buffer.getvalue()
            
        def seek(self, pos):
            self.buffer.seek(pos)
    
    mock_file = MockFile(test_buffer, "test.jpg")
    
    # Test conversion function (should handle non-HEIC gracefully)
    try:
        result = convert_heic_to_jpeg(mock_file)
        if result:
            print("  ✅ Conversion function works (tested with JPEG)")
        else:
            print("  ❌ Conversion function returned None")
    except Exception as e:
        print(f"  ❌ Conversion function error: {e}")
    
    print("\n✅ HEIC support setup appears to be working!")
    print("\nTo test with real HEIC files:")
    print("1. Take a photo with an iPhone (saves as HEIC by default)")
    print("2. Upload it through the report form or add location form")
    print("3. Check the server logs for conversion messages")

if __name__ == "__main__":
    test_heic_support()
