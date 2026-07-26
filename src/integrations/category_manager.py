#!/usr/bin/env python3
"""
Category Manager - Manage document categories.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

class CategoryManager:
    """
    Manages document categories.
    """
    
    def __init__(self, category_file: str = "~/PROMETHEUS/data/categories/categories.json"):
        """
        Initialize the category manager.
        
        Args:
            category_file: Path to the categories JSON file.
        """
        self.category_file = Path(category_file).expanduser()
        self.category_file.parent.mkdir(parents=True, exist_ok=True)
        self.categories = self._load()
    
    def _load(self) -> Dict[str, List[str]]:
        """Load categories from file."""
        if self.category_file.exists():
            with open(self.category_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save(self):
        """Save categories to file."""
        with open(self.category_file, 'w') as f:
            json.dump(self.categories, f, indent=2)
    
    def get_category(self, name: str) -> Optional[List[str]]:
        """Get a category by name."""
        return self.categories.get(name)
    
    def list_categories(self) -> List[str]:
        """List all category names."""
        return list(self.categories.keys())
    
    def add_files(self, category_name: str, file_ids: List[str]):
        """Add files to a category."""
        if category_name not in self.categories:
            self.categories[category_name] = []
        
        existing = set(self.categories[category_name])
        for file_id in file_ids:
            if file_id not in existing:
                self.categories[category_name].append(file_id)
                existing.add(file_id)
        
        self._save()
    
    def remove_files(self, category_name: str, file_ids: List[str]):
        """Remove files from a category."""
        if category_name not in self.categories:
            return
        
        for file_id in file_ids:
            if file_id in self.categories[category_name]:
                self.categories[category_name].remove(file_id)
        
        if not self.categories[category_name]:
            del self.categories[category_name]
        
        self._save()
    
    def delete_category(self, category_name: str):
        """Delete a category entirely."""
        if category_name in self.categories:
            del self.categories[category_name]
            self._save()
            print(f"✅ Category '{category_name}' deleted.")
    
    def merge_categories(self, source: str, target: str):
        """Merge one category into another."""
        if source not in self.categories or target not in self.categories:
            print("❌ One or both categories not found.")
            return
        
        self.categories[target].extend(self.categories[source])
        self.categories[target] = list(set(self.categories[target]))
        
        del self.categories[source]
        self._save()
        
        print(f"✅ Merged '{source}' into '{target}'")
    
    def show_statistics(self):
        """Show category statistics."""
        if not self.categories:
            print("No categories defined.")
            return
        
        print("\n📊 Category Statistics")
        print("="*40)
        total_files = 0
        for name, file_ids in self.categories.items():
            print(f"  {name}: {len(file_ids)} files")
            total_files += len(file_ids)
        print("="*40)
        print(f"  TOTAL: {total_files} files")
