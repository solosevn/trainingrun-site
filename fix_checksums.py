#!/usr/bin/env python3
"""
Fix data integrity checksums for TrainingRun benchmark data files.
Regenerates SHA-256 checksums using canonical JSON representation.
"""

import json
import hashlib
import os

def calculate_checksum(data):
    """Calculate SHA-256 checksum of JSON data using canonical string format."""
    # Create canonical string representation
    canonical_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
    
    # Calculate SHA-256 hash
    hash_obj = hashlib.sha256(canonical_str.encode('utf-8'))
    return hash_obj.hexdigest()

def fix_file_checksum(filename):
    """Fix the checksum for a single data file."""
    print(f"Processing {filename}...")
    
    # Read current data
    with open(filename, 'r') as f:
        data = json.load(f)
    
    # Store old checksum for comparison
    old_checksum = data.get('checksum', 'None')
    
    # Calculate new checksum (excluding the checksum field itself)
    data_for_checksum = {k: v for k, v in data.items() if k != 'checksum'}
    new_checksum = calculate_checksum(data_for_checksum)
    
    # Update checksum
    data['checksum'] = new_checksum
    
    # Write back to file
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"  Old checksum: {old_checksum}")
    print(f"  New checksum: {new_checksum}")
    print(f"  Status: {'Updated' if old_checksum != new_checksum else 'No change needed'}")
    
    return old_checksum != new_checksum

def main():
    """Fix checksums for all benchmark data files."""
    files = [
        'trs-data.json',
        'trf-data.json', 
        'trscode-data.json',
        'truscore-data.json'
    ]
    
    changed_files = []
    
    print("🔧 Fixing data integrity checksums...\n")
    
    for filename in files:
        if os.path.exists(filename):
            if fix_file_checksum(filename):
                changed_files.append(filename)
        else:
            print(f"❌ File not found: {filename}")
        print()
    
    print("✅ Checksum fix complete!")
    
    if changed_files:
        print(f"📝 Files updated: {', '.join(changed_files)}")
        print("\n🚀 Ready to commit and push changes:")
        print("git add .")
        print('git commit -m "Fix data integrity checksums for TRUscore and TRSBench"')
        print("git push origin main")
    else:
        print("ℹ️  All checksums were already correct.")

if __name__ == "__main__":
    main()