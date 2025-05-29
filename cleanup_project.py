#!/usr/bin/env python3
"""
Project cleanup script for study-wise-ai.
Removes obsolete files while preserving working functionality.
"""

import os
import shutil
from pathlib import Path

# Files that are safe to delete (obsolete/temporary)
SAFE_TO_DELETE = [
    # Debug and demo files (functionality moved to manage_test_data.py)
    "test_weaviate_connection.py",
    "debug_search_scores.py",
    "demo_semantic_search.py",

    # Old CLI and main files (replaced by weaviate_cli.py)
    "src/main.py",
    "src/cli.py",
    "src/generate_and_upload.py",
    "tests/test_cli.py",

    # System files
    ".DS_Store",
]

# Files to potentially archive (original functionality we might want to keep)
ARCHIVE_CANDIDATES = [
    # Original flashcard system
    "src/flashcards_db.py",
    "src/flashcard_generator.py",
    "src/model.py",
    "tests/test_flashcards_db.py",

    # Original document processing
    "src/document.py",
    "tests/test_document.py",

    # Supabase initialization
    "src/init_supabase.py",

    # Sample data files
    "flashcards_output.json",
    "yolo_flashcards.json",
]

# Directories to clean up
CLEAN_DIRS = [
    ".pytest_cache",
    "src/__pycache__",
    "tests/__pycache__",
]

def cleanup_obsolete_files():
    """Remove files that are definitely obsolete."""
    print("🧹 Cleaning up obsolete files...")

    deleted_count = 0
    for file_path in SAFE_TO_DELETE:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✅ Deleted: {file_path}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Failed to delete {file_path}: {e}")
        else:
            print(f"ℹ️  Already removed: {file_path}")

    print(f"\n🗑️  Removed {deleted_count} obsolete files")

def archive_legacy_files():
    """Move legacy files to an archive directory."""
    archive_dir = Path("archive_legacy")

    print(f"\n📦 Creating archive directory: {archive_dir}")
    archive_dir.mkdir(exist_ok=True)

    # Create subdirectories
    (archive_dir / "src").mkdir(exist_ok=True)
    (archive_dir / "tests").mkdir(exist_ok=True)

    archived_count = 0
    for file_path in ARCHIVE_CANDIDATES:
        if os.path.exists(file_path):
            try:
                dest_path = archive_dir / file_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(file_path, dest_path)
                print(f"📦 Archived: {file_path} → {dest_path}")
                archived_count += 1
            except Exception as e:
                print(f"❌ Failed to archive {file_path}: {e}")
        else:
            print(f"ℹ️  Not found: {file_path}")

    print(f"\n📚 Archived {archived_count} legacy files")

def clean_cache_dirs():
    """Remove cache and temporary directories."""
    print("\n🧽 Cleaning cache directories...")

    cleaned_count = 0
    for dir_path in CLEAN_DIRS:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"✅ Cleaned: {dir_path}")
                cleaned_count += 1
            except Exception as e:
                print(f"❌ Failed to clean {dir_path}: {e}")
        else:
            print(f"ℹ️  Not found: {dir_path}")

    print(f"\n🗂️  Cleaned {cleaned_count} cache directories")

def show_final_structure():
    """Show the cleaned project structure."""
    print("\n📁 FINAL PROJECT STRUCTURE:")
    print("=" * 50)

    # Root files
    print("\n📄 Root Files:")
    for item in sorted(Path(".").iterdir()):
        if item.is_file() and not item.name.startswith('.'):
            print(f"   {item.name}")

    # Source files
    print("\n🔧 Source Files (src/):")
    src_path = Path("src")
    if src_path.exists():
        for item in sorted(src_path.iterdir()):
            if item.is_file() and item.suffix == '.py':
                print(f"   {item.name}")

    # Test files
    print("\n🧪 Test Files (tests/):")
    tests_path = Path("tests")
    if tests_path.exists():
        for item in sorted(tests_path.iterdir()):
            if item.is_file() and item.suffix == '.py':
                print(f"   {item.name}")

def main():
    print("🚀 Study-Wise AI Project Cleanup")
    print("=" * 50)
    print("This will:")
    print("✅ Delete obsolete debug/demo files")
    print("📦 Archive legacy flashcard/document files")
    print("🧽 Clean cache directories")
    print("🔍 Show final project structure")
    print()

    proceed = input("Continue with cleanup? (y/N): ").strip().lower()
    if proceed != 'y':
        print("❌ Cleanup cancelled")
        return

    # Perform cleanup
    cleanup_obsolete_files()
    archive_legacy_files()
    clean_cache_dirs()
    show_final_structure()

    print("\n" + "=" * 50)
    print("✨ PROJECT CLEANUP COMPLETE!")
    print("=" * 50)
    print("🎯 What's Left:")
    print("   • Working Weaviate implementation (src/weaviate_*.py)")
    print("   • Supporting infrastructure (config, supabase_client)")
    print("   • Test files for new functionality")
    print("   • Utility scripts (manage_test_data.py)")
    print()
    print("📦 What's Archived:")
    print("   • Original flashcard system → archive_legacy/")
    print("   • Original document processing → archive_legacy/")
    print("   • Sample data files → archive_legacy/")
    print()
    print("🗑️  What's Deleted:")
    print("   • Temporary debug files")
    print("   • Cache directories")
    print("   • Obsolete entry points")
    print()
    print("💡 Next Steps:")
    print("   • Continue with DocumentProcessor implementation")
    print("   • Use manage_test_data.py for data management")
    print("   • Archive files can be restored if needed")

if __name__ == "__main__":
    main()
