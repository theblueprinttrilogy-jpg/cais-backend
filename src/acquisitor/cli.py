#!/usr/bin/env python3
"""
Acquisitor CLI - Command-line interface for the document acquisitor.
"""

import sys
import json
from pathlib import Path
from typing import Optional

from src.acquisitor.acquisitor import Acquisitor
from src.integrations.category_manager import CategoryManager

def main():
    """Main CLI function."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     📦 ACQUISITOR - CAIS Document Downloader             ║
║                                                           ║
║     Download and compress documents from Google Drive     ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m src.acquisitor.cli list")
        print("  python -m src.acquisitor.cli download <category>")
        print("  python -m src.acquisitor.cli download <category> --no-compress")
        print("  python -m src.acquisitor.cli stats")
        print("  python -m src.acquisitor.cli show <category>")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_categories()
    elif command == "download":
        download_category()
    elif command == "stats":
        show_stats()
    elif command == "show":
        show_category()
    else:
        print(f"❌ Unknown command: {command}")

def list_categories():
    """List all available categories."""
    manager = CategoryManager()
    categories = manager.list_categories()
    
    if not categories:
        print("No categories defined.")
        return
    
    print("\n📂 Available Categories:")
    print("="*40)
    total_files = 0
    for cat in categories:
        file_ids = manager.get_category(cat)
        count = len(file_ids) if file_ids else 0
        total_files += count
        print(f"  {cat}: {count} files")
    print("="*40)
    print(f"  TOTAL: {total_files} files")

def download_category():
    """Download a category."""
    if len(sys.argv) < 3:
        print("❌ Please specify a category name.")
        print("   Example: python -m src.acquisitor.cli download CAIS_Plans")
        return
    
    category = sys.argv[2]
    no_compress = "--no-compress" in sys.argv
    
    print(f"📦 Downloading category: {category}")
    
    # Check if category exists
    manager = CategoryManager()
    file_ids = manager.get_category(category)
    
    if not file_ids:
        print(f"❌ Category '{category}' not found.")
        return
    
    print(f"   Files: {len(file_ids)}")
    
    # Download
    acquisitor = Acquisitor()
    result = acquisitor.download_category(category, compress=not no_compress)
    
    if result['success']:
        print("\n" + "="*40)
        print("✅ DOWNLOAD COMPLETE")
        print("="*40)
        print(f"   Category: {result['category']}")
        print(f"   Successful: {result['successful']}/{result['total_files']}")
        print(f"   Failed: {result['failed']}")
        print(f"   Size: {result['total_size_mb']:.1f} MB")
        print(f"   Compressed: {result['compressed']}")
        if result.get('zip_path'):
            print(f"   ZIP: {result['zip_path']}")
        print("="*40)
    else:
        print(f"❌ Download failed: {result.get('error', 'Unknown error')}")

def show_stats():
    """Show category statistics."""
    manager = CategoryManager()
    manager.show_statistics()

def show_category():
    """Show files in a category."""
    if len(sys.argv) < 3:
        print("❌ Please specify a category name.")
        print("   Example: python -m src.acquisitor.cli show CAIS_Plans")
        return
    
    category = sys.argv[2]
    manager = CategoryManager()
    file_ids = manager.get_category(category)
    
    if not file_ids:
        print(f"❌ Category '{category}' not found or empty.")
        return
    
    print(f"\n📄 Files in category '{category}':")
    print("="*40)
    for i, file_id in enumerate(file_ids, 1):
        print(f"  {i}. {file_id}")
    print("="*40)
    print(f"  TOTAL: {len(file_ids)} files")

if __name__ == "__main__":
    main()
