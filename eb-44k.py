#!/usr/bin/env python3
"""44.1 kHz variant — delegates to eb.py --rate 44100."""
import subprocess
import sys

sys.exit(subprocess.call([sys.executable, 'eb.py', '--rate', '44100'] + sys.argv[1:]))
