#!/usr/bin/env python
"""
Script de débogage pour tester l'import
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from importer.models import ProductImport
from importer.services import parse_import

# Trouver le dernier import
last_import = ProductImport.objects.order_by('-id').first()

if not last_import:
    print("Aucun import trouvé")
    exit(1)

print(f"Import ID: {last_import.id}")
print(f"Status: {last_import.status}")
print(f"File: {last_import.source_file}")
print(f"File name: {last_import.source_file.name if last_import.source_file else 'None'}")
print(f"File type: {last_import.file_type}")
print(f"Row count: {last_import.row_count}")
print(f"Error count: {last_import.error_count}")

if last_import.source_file:
    try:
        print(f"File path: {last_import.source_file.path}")
        print(f"File exists: {os.path.exists(last_import.source_file.path)}")
        if os.path.exists(last_import.source_file.path):
            print(f"File size: {os.path.getsize(last_import.source_file.path)} bytes")
    except Exception as e:
        print(f"Error accessing file path: {e}")
        if hasattr(last_import.source_file, 'read'):
            print("File has read() method, can read from storage")
            last_import.source_file.seek(0)
            first_chunk = last_import.source_file.read(100)
            print(f"First 100 bytes: {first_chunk}")

# Vérifier les ImportRows
from importer.models import ImportRow
rows = ImportRow.objects.filter(product_import=last_import)
print(f"\nImportRows count: {rows.count()}")
if rows.exists():
    print("Sample row:")
    sample = rows.first()
    print(f"  Row number: {sample.row_number}")
    print(f"  Is valid: {sample.is_valid}")
    print(f"  Raw data keys: {list(sample.raw.keys()) if sample.raw else 'None'}")
    print(f"  Raw data sample: {dict(list(sample.raw.items())[:3]) if sample.raw else 'None'}")
