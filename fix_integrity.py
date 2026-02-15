#!/usr/bin/env python3
"""
Fix data integrity checksums using TrainingRun's exact algorithm.
Matches the JavaScript integrity verification in truscore-scores.html and scores.html.
"""

import json
import hashlib
import os

def calculate_trainingrun_checksum(data):
    """Calculate checksum using TrainingRun's exact algorithm."""
    
    # Extract model names and join with "|"
    names = [model['name'] for model in data['models']]
    names_str = "|".join(names)
    
    # Extract all scores and format them exactly as the JavaScript does
    scores = []
    for model in data['models']:
        for score in model['scores']:
            if score is None:
                scores.append("null")
            elif isinstance(score, int) or (isinstance(score, float) and score % 1 == 0):
                # Integer scores get 1 decimal place: score.toFixed(1)
                scores.append(f"{score:.1f}")
            else:
                # Float scores stay as string
                scores.append(str(score))
    
    scores_str = ",".join(scores)
    
    # Create canonical string: "names:scores"
    canonical = f"{names_str}:{scores_str}"
    
    # Calculate SHA-256 hash
    hash_bytes = hashlib.sha256(canonical.encode('utf-8')).digest()
    hash_hex = hash_bytes.hex()
    
    return hash_hex, canonical

def fix_file_integrity(filename):
    """Fix the checksum for a single data file using TrainingRun's algorithm."""
    print(f"Processing {filename}...")
    
    # Read current data
    with open(filename, 'r') as f:
        data = json.load(f)
    
    # Store old checksum for comparison
    old_checksum = data.get('checksum', 'None')
    
    # Calculate new checksum using TrainingRun's algorithm
    new_checksum, canonical_debug = calculate_trainingrun_checksum(data)
    
    # Update checksum
    data['checksum'] = new_checksum
    
    # Write back to file
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"  Old checksum: {old_checksum}")
    print(f"  New checksum: {new_checksum}")
    print(f"  Canonical: {canonical_debug[:100]}..." if len(canonical_debug) > 100 else f"  Canonical: {canonical_debug}")
    print(f"  Status: {'Updated' if old_checksum != new_checksum else 'No change needed'}")
    
    return old_checksum != new_checksum

def main():
    """Fix checksums for all benchmark data files using TrainingRun's algorithm."""
    files = [
        'trs-data.json',
        'trf-data.json', 
        'trscode-data.json',
        'truscore-data.json'
    ]
    
    changed_files = []
    
    print("🔧 Fixing data integrity checksums using TrainingRun's algorithm...\n")
    
    for filename in files:
        if os.path.exists(filename):
            if fix_file_integrity(filename):
                changed_files.append(filename)
        else:
            print(f"❌ File not found: {filename}")
        print()
    
    print("✅ Integrity fix complete!")
    
    if changed_files:
        print(f"📝 Files updated: {', '.join(changed_files)}")
        print("\n🚀 Ready to commit and push changes:")
        print("git add .")
        print('git commit -m "Fix integrity checks using correct TrainingRun algorithm"')
        print("git push origin main")
    else:
        print("ℹ️  All checksums were already correct.")

if __name__ == "__main__":
    main()