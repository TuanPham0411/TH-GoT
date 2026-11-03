#!/usr/bin/env python3
"""Host-side entry point for the same asset manager used by the container."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'game'))
from assets import main
if __name__ == '__main__':
    main()
