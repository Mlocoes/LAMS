#!/usr/bin/env python3
"""
Decrypt Encrypted Logs (Phase 3.6)

This script decrypts encrypted log files and displays them in readable format.

Usage:
    python decrypt_logs.py <log_file> [--output <file>] [--format json|text]
    python decrypt_logs.py security.encrypted.log
    python decrypt_logs.py security.encrypted.log --output decrypted.log
    python decrypt_logs.py security.encrypted.log --format json
"""

import asyncio
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/home/mloco/Escritorio/LAMS/server')

from database.db import AsyncSessionLocal
from services.key_rotation_service import get_key_rotation_service
from services.encrypted_logging_service import EncryptedLogRecord


async def decrypt_log_file(
    input_file: str,
    output_file: str = None,
    output_format: str = 'text'
):
    """
    Decrypt an encrypted log file.
    
    Args:
        input_file: Path to encrypted log file
        output_file: Optional output file (default: stdout)
        output_format: Output format ('text' or 'json')
    """
    print("=" * 80)
    print("ENCRYPTED LOG DECRYPTION TOOL (Phase 3.6)")
    print("=" * 80)
    print()
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_file}")
        sys.exit(1)
    
    print(f"Input file: {input_file}")
    print(f"Output format: {output_format}")
    if output_file:
        print(f"Output file: {output_file}")
    else:
        print(f"Output: stdout")
    print()
    
    key_service = get_key_rotation_service()
    
    # Cache for Fernet instances by version
    fernet_cache = {}
    
    total_records = 0
    decrypted_records = 0
    failed_records = 0
    
    output_lines = []
    
    async with AsyncSessionLocal() as db:
        try:
            with open(input_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    total_records += 1
                    
                    try:
                        # Parse encrypted record
                        encrypted_record = EncryptedLogRecord.from_json(line)
                        
                        # Get Fernet instance for this key version
                        key_version = encrypted_record.key_version
                        
                        if key_version not in fernet_cache:
                            fernet_cache[key_version] = await key_service.get_key_by_version(
                                db, key_version
                            )
                        
                        fernet = fernet_cache[key_version]
                        
                        # Decrypt data
                        decrypted_json = fernet.decrypt(encrypted_record.encrypted_data.encode()).decode()
                        decrypted_data = json.loads(decrypted_json)
                        
                        # Format output
                        if output_format == 'json':
                            # JSON format: one line per record
                            output_line = json.dumps({
                                'timestamp': encrypted_record.timestamp,
                                'level': encrypted_record.level,
                                'logger': encrypted_record.logger_name,
                                'key_version': key_version,
                                **decrypted_data
                            })
                        else:
                            # Text format: human-readable
                            output_line = (
                                f"[{encrypted_record.timestamp}] "
                                f"{encrypted_record.level:8} "
                                f"{encrypted_record.logger_name:20} "
                                f"- {decrypted_data.get('message', '(no message)')}"
                            )
                            
                            # Add extra fields if present
                            extra_fields = {
                                k: v for k, v in decrypted_data.items()
                                if k not in ['message', 'levelname', 'name', 'pathname', 'lineno',
                                           'funcName', 'created', 'thread', 'threadName',
                                           'process', 'processName']
                            }
                            if extra_fields:
                                output_line += f" | {json.dumps(extra_fields)}"
                        
                        output_lines.append(output_line)
                        decrypted_records += 1
                        
                    except Exception as e:
                        failed_records += 1
                        error_line = f"[ERROR] Line {line_num}: Failed to decrypt - {e}"
                        output_lines.append(error_line)
                        print(error_line, file=sys.stderr)
            
            # Write output
            if output_file:
                with open(output_file, 'w') as f:
                    for line in output_lines:
                        f.write(line + '\n')
                print(f"✅ Decrypted log written to: {output_file}")
            else:
                print()
                print("=" * 80)
                print("DECRYPTED LOG CONTENT")
                print("=" * 80)
                print()
                for line in output_lines:
                    print(line)
            
            print()
            print("=" * 80)
            print("DECRYPTION SUMMARY")
            print("=" * 80)
            print(f"Total records: {total_records}")
            print(f"Decrypted: {decrypted_records}")
            print(f"Failed: {failed_records}")
            print(f"Key versions used: {sorted(fernet_cache.keys())}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            raise


async def search_encrypted_logs(
    input_file: str,
    search_term: str,
    case_sensitive: bool = False
):
    """
    Search encrypted logs without full decryption.
    
    Args:
        input_file: Path to encrypted log file
        search_term: Term to search for
        case_sensitive: Whether search is case-sensitive
    """
    print("=" * 80)
    print("ENCRYPTED LOG SEARCH TOOL (Phase 3.6)")
    print("=" * 80)
    print()
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_file}")
        sys.exit(1)
    
    print(f"Searching in: {input_file}")
    print(f"Search term: '{search_term}'")
    print(f"Case sensitive: {case_sensitive}")
    print()
    
    if not case_sensitive:
        search_term = search_term.lower()
    
    key_service = get_key_rotation_service()
    fernet_cache = {}
    
    matches = []
    
    async with AsyncSessionLocal() as db:
        try:
            with open(input_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Parse encrypted record
                        encrypted_record = EncryptedLogRecord.from_json(line)
                        
                        # Get Fernet instance
                        key_version = encrypted_record.key_version
                        if key_version not in fernet_cache:
                            fernet_cache[key_version] = await key_service.get_key_by_version(
                                db, key_version
                            )
                        
                        fernet = fernet_cache[key_version]
                        
                        # Decrypt data
                        decrypted_json = fernet.decrypt(encrypted_record.encrypted_data.encode()).decode()
                        decrypted_data = json.loads(decrypted_json)
                        
                        # Search in message and all fields
                        search_text = json.dumps(decrypted_data)
                        if not case_sensitive:
                            search_text = search_text.lower()
                        
                        if search_term in search_text:
                            matches.append({
                                'line': line_num,
                                'timestamp': encrypted_record.timestamp,
                                'level': encrypted_record.level,
                                'data': decrypted_data
                            })
                    
                    except Exception:
                        pass  # Skip errors
            
            # Display results
            if matches:
                print(f"✅ Found {len(matches)} matches:")
                print()
                for match in matches:
                    print(f"Line {match['line']}: [{match['timestamp']}] {match['level']}")
                    print(f"  {match['data'].get('message', '(no message)')}")
                    print()
            else:
                print("❌ No matches found")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Decrypt encrypted log files")
    parser.add_argument('log_file', help="Path to encrypted log file")
    parser.add_argument(
        '--output', '-o',
        help="Output file (default: stdout)"
    )
    parser.add_argument(
        '--format', '-f',
        choices=['text', 'json'],
        default='text',
        help="Output format (default: text)"
    )
    parser.add_argument(
        '--search', '-s',
        help="Search for term in logs"
    )
    parser.add_argument(
        '--case-sensitive',
        action='store_true',
        help="Case-sensitive search"
    )
    
    args = parser.parse_args()
    
    if args.search:
        asyncio.run(search_encrypted_logs(
            args.log_file,
            args.search,
            args.case_sensitive
        ))
    else:
        asyncio.run(decrypt_log_file(
            args.log_file,
            args.output,
            args.format
        ))


if __name__ == "__main__":
    main()
