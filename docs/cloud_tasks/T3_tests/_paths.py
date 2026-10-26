"""Puts the frozen analysis code on sys.path (read-only use; nothing in eval/ is modified)."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
P9 = os.path.join(ROOT, 'eval', 'phase9')
for d in ('P9-D', 'P9-B', 'P9-A', 'P9-C3', 'P9-C5'):
    p = os.path.join(P9, d)
    if p not in sys.path:
        sys.path.insert(0, p)
