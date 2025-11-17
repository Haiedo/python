#!/usr/bin/env python3
import sys
import requests

try:
    response = requests.get('http://localhost:5000/', timeout=5)
    if response.status_code == 200:
        sys.exit(0)
    else:
        sys.exit(1)
except Exception as e:
    print(f"Health check failed: {e}")
    sys.exit(1)
