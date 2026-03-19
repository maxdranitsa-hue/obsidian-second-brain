#!/bin/bash
export HOME=/home/deploy
source /home/deploy/agent-second-brain/.env
cd /home/deploy/agent-second-brain
/home/deploy/.local/bin/uv run python -c "
from d_brain.services.processor import ClaudeProcessor
from pathlib import Path
import os
processor = ClaudeProcessor(vault_path=Path('./vault'), todoist_api_key=os.environ.get('TODOIST_API_KEY',''))
result = processor.process_daily()
print(result)
"
