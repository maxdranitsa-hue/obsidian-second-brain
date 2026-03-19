#!/bin/bash
cd /home/deploy/agent-second-brain
git add -A
git diff --cached --quiet || git commit -m "auto: vault sync $(date '+%Y-%m-%d %H:%M')"
git push origin main 2>&1
