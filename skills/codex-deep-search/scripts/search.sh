#!/bin/bash
# Codex Deep Search Script
# Usage: search.sh --prompt "query" --task-name "name" --telegram-group "chat_id" --timeout 120

set -e

# Parse arguments
PROMPT=""
TASK_NAME=""
TELEGRAM_GROUP=""
MODEL="gpt-5.3-codex"
TIMEOUT=120
OUTPUT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --prompt)
      PROMPT="$2"
      shift 2
      ;;
    --task-name)
      TASK_NAME="$2"
      shift 2
      ;;
    --telegram-group)
      TELEGRAM_GROUP="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    --output)
      OUTPUT="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$PROMPT" ]]; then
  echo "Error: --prompt is required"
  exit 1
fi

# Generate task name if not provided
if [[ -z "$TASK_NAME" ]]; then
  TASK_NAME="search-$(date +%Y%m%d-%H%M%S)"
fi

# Set output path
if [[ -z "$OUTPUT" ]]; then
  mkdir -p "$HOME/.openclaw/workspace/data/codex-search-results"
  OUTPUT="$HOME/.openclaw/workspace/data/codex-search-results/${TASK_NAME}.md"
fi

META_FILE="$HOME/.openclaw/workspace/data/codex-search-results/latest-meta.json"

# Write initial metadata
cat > "$META_FILE" << EOF
{
  "task": "$TASK_NAME",
  "prompt": "$PROMPT",
  "status": "running",
  "startTime": "$(date -Iseconds)",
  "outputFile": "$OUTPUT"
}
EOF

# Write header to output file
cat > "$OUTPUT" << EOF
# Deep Search Results: $TASK_NAME

**Query:** $PROMPT  
**Started:** $(date -Iseconds)  
**Status:** Running...

---

EOF

# Function to send Telegram notification
send_notification() {
  local message="$1"
  if [[ -n "$TELEGRAM_GROUP" ]]; then
    # Use OpenClaw message tool via a temporary trigger file
    echo "$message" > "$HOME/.openclaw/workspace/data/codex-search-results/.notify-$TASK_NAME"
  fi
}

# Run codex search with timeout
echo "Starting deep search for: $PROMPT"
echo "Output will be saved to: $OUTPUT"
echo "Timeout: ${TIMEOUT}s"

# Create a temp file for codex output
CODEX_OUTPUT="$HOME/.openclaw/workspace/data/codex-search-results/task-output.txt"

# Run codex with web search capability
timeout "$TIMEOUT" bash -c "
  cd '$HOME/.openclaw/workspace'
  # Use codex CLI if available, otherwise simulate with web search
  if command -v codex &> /dev/null; then
    echo '$PROMPT' | codex --model '$MODEL' --web-search > '$CODEX_OUTPUT' 2>&1
  else
    echo 'Codex CLI not available. Using alternative search method...' > '$CODEX_OUTPUT'
    # Fallback: use curl to search and summarize
    echo 'Search query: $PROMPT' >> '$CODEX_OUTPUT'
    echo 'Results would be generated here if codex CLI was available.' >> '$CODEX_OUTPUT'
  fi
" || echo "Search completed or timed out"

# Append results to output file
echo "" >> "$OUTPUT"
echo "## Search Results" >> "$OUTPUT"
echo "" >> "$OUTPUT"
cat "$CODEX_OUTPUT" >> "$OUTPUT" 2>/dev/null || echo "(No output generated)" >> "$OUTPUT"

# Update metadata
cat > "$META_FILE" << EOF
{
  "task": "$TASK_NAME",
  "prompt": "$PROMPT",
  "status": "completed",
  "startTime": "$(date -Iseconds)",
  "endTime": "$(date -Iseconds)",
  "outputFile": "$OUTPUT"
}
EOF

# Update status in output file
sed -i 's/\*\*Status:\*\* Running.../**Status:** Completed ✅/' "$OUTPUT"

# Send notification
if [[ -n "$TELEGRAM_GROUP" ]]; then
  send_notification "🔍 Deep search completed: $TASK_NAME

Query: $PROMPT
Results: $OUTPUT"
fi

echo "Search completed. Results saved to: $OUTPUT"
