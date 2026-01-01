"""Find the review page file."""
import os

for root, dirs, files in os.walk('.'):
    if 'placements' in root and 'review' in root:
        for f in files:
            if f == 'page.tsx' or f == 'page.ts':
                print(os.path.join(root, f))
