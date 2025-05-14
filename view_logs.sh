#!/bin/bash
echo "Monitoring CallHub logs for activation process..."
# Filtered to only show callhub updates
ps aux | grep 13810 | grep -v grep
echo "Filtering logs for process 13810 (Claude's CallHub MCP)"
if command -v lsof > /dev/null 2>&1; then
    LOGS=$(lsof -p 13810 -a -d 2 | grep -v "pipe" | tail -1 | awk '{print $9}')
    if [ -n "$LOGS" ] && [ -e "$LOGS" ]; then
        echo "Found log at: $LOGS"
        # Highlight important status messages with color
        echo "Displaying CallHub logs with important updates highlighted:"
        echo "  - Blue text: Normal callhub logs"
        echo "  - Green text: Batch start/complete messages"
        echo "  - Yellow text: Important status updates"
        echo "  - Red text: Error or warning messages"
        echo ""
        tail -f "$LOGS" | grep '\[callhub\]' | grep -v 'Looking for' | grep -v 'Found element' | grep -v 'Element HTML' | \
        awk '{ \
            if ($0 ~ /\*\*\* BATCH.*STARTED/) { print "\033[1;32m" $0 "\033[0m"; } \
            else if ($0 ~ /\*\*\* BATCH.*COMPLETE/) { print "\033[1;32m" $0 "\033[0m"; } \
            else if ($0 ~ /\*\*\*.*\*\*\*/) { print "\033[1;33m" $0 "\033[0m"; } \
            else if ($0 ~ /Error|error|WARNING|failed/) { print "\033[1;31m" $0 "\033[0m"; } \
            else { print "\033[1;34m" $0 "\033[0m"; } \
        }'
    else
        echo "No log file found. Using process stderr..."
        # Direct capture from stderr is complex, showing how to check process info
        ps -ef | grep 13810 | grep -v grep
        echo "To monitor logs manually, run: sudo dtrace -p 13810 -n 'syscall::write:entry /arg0==2/ { printf(\"%%s\", copyinstr(arg1,arg2)); }' | grep '\[callhub\]'"
    fi
else
    echo "lsof not available. Using process information..."
    ps -ef | grep 13810 | grep -v grep
    echo "To monitor logs manually, run: sudo dtrace -p 13810 -n 'syscall::write:entry /arg0==2/ { printf(\"%%s\", copyinstr(arg1,arg2)); }' | grep '\[callhub\]'"
fi
read -p "Press Enter to close this terminal..."
