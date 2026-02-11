#!/usr/bin/env python3
"""Demo of Recoll Python API for natural language search"""

from recoll import recoll
import os

# Set config directory
os.environ['RECOLL_CONFDIR'] = os.path.expanduser('~/.config/recoll')

# Connect to the database
db = recoll.connect()

print("=== Recoll Python API Demo ===\n")

# Simple query
query = db.query()
nres = query.execute("todo")
print(f"Search for 'todo': {nres} results\n")

# Get first 5 results
for i in range(min(5, nres)):
    doc = query.fetchone()
    print(f"{i+1}. {doc.filename}")
    print(f"   Type: {doc.mimetype}")
    print(f"   Size: {doc.fbytes} bytes")
    print(f"   Modified: {doc.mtime}")
    if hasattr(doc, 'abstract'):
        print(f"   Preview: {doc.abstract[:100]}...")
    print()

print("\n=== Advanced Query: Date Range ===")
# More complex query with date filtering
query2 = db.query()
nres2 = query2.execute("yubikey", stemming=1)
print(f"Search for 'yubikey' with stemming: {nres2} results\n")

for i in range(min(3, nres2)):
    doc = query2.fetchone()
    print(f"{i+1}. {doc.filename}")
    print(f"   URL: {doc.url}")
    print()
