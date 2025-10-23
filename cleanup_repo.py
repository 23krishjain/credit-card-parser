#!/usr/bin/env python3
"""
Clean up the repository for deployment
"""

import os
import shutil
from pathlib import Path

def cleanup_repository():
    """Remove unnecessary files and organize the repo"""
    
    # Files to KEEP
    essential_files = [
        'parser_unified.py',      # Main parser
        'unified_app.py',         # Streamlit app
        'requirements.txt',       # Dependencies
        'testCase01.pdf',         # Sample file
        'chase_statement.pdf',    # Sample file
        'amex_statement.pdf',     # Sample file  
        'citi_statement.pdf',     # Sample file
        'README.md',              # Documentation
    ]
    
    # Files/Directories to REMOVE
    files_to_remove = [
        '__pycache__',
        'backup',
        'app_v2.py',
        'app_v3.py', 
        'batch_test.py',
        'indian_banks.py',
        'parser_v2.py',
        'parser_v3.py',
        'debug_output.txt',
        'templates',
        'uploads'
    ]
    
    print("🧹 Cleaning up repository...")
    
    # Remove unnecessary files and directories
    for item in files_to_remove:
        if os.path.exists(item):
            if os.path.isdir(item):
                shutil.rmtree(item)
                print(f"✅ Removed directory: {item}")
            else:
                os.remove(item)
                print(f"✅ Removed file: {item}")
    
    # Create necessary directories
    essential_dirs = ['results', 'sample_statements']
    for dir_name in essential_dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✅ Created directory: {dir_name}")
    
    # Move sample PDFs to sample_statements directory
    sample_files = ['testCase01.pdf', 'chase_statement.pdf', 'amex_statement.pdf', 'citi_statement.pdf']
    for sample_file in sample_files:
        if os.path.exists(sample_file):
            shutil.move(sample_file, f'sample_statements/{sample_file}')
            print(f"✅ Moved {sample_file} to sample_statements/")
    
    print("\n🎉 Repository cleaned up successfully!")
    print("📁 Current structure:")
    for item in sorted(os.listdir('.')):
        if os.path.isdir(item):
            print(f"📂 {item}/")
        else:
            print(f"📄 {item}")

if __name__ == '__main__':
    cleanup_repository()