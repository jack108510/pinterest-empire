#!/bin/bash
# Launch all business accounts with staggered posting windows
# Anti-ban: each account runs at a DIFFERENT time of day, not all at 3 AM
# The multi-poster itself adds random jitter + human behavior

WORKSPACE="/Users/jackserver/.openclaw/workspace/pinterest"
LOGS="/Users/jackserver/.openclaw/workspace/logs"

# Check which account to run based on current hour
CURRENT_HOUR=$(date +%H)

# Staggered schedule (MDT):
#   6 AM  → supplements
#   10 AM → cooking
#   2 PM  → beauty
#   6 PM  → fitness
#   9 PM  → thunderpickle99

ACCOUNT=""

case "$CURRENT_HOUR" in
    06) ACCOUNT="supplements" ;;
    10) ACCOUNT="cooking" ;;
    14) ACCOUNT="beauty" ;;
    18) ACCOUNT="fitness" ;;
    21) ACCOUNT="thunderpickle99" ;;
    *)
        # Fallback: if called manually, run the account that's scheduled
        echo "[$(date)] No account scheduled for hour $CURRENT_HOUR. Use --account <id> manually."
        exit 0
        ;;
esac

# Add random jitter: wait 0-15 minutes before starting
JITTER=$((RANDOM % 900))
echo "[$(date)] $ACCOUNT scheduled — waiting ${JITTER}s jitter..."
sleep $JITTER

echo "[$(date)] Starting $ACCOUNT (50 pins)" >> "$LOGS/pinterest-$ACCOUNT.log"
cd "$WORKSPACE"
/opt/homebrew/bin/python3 multi-poster.py --account "$ACCOUNT" --count 50 >> "$LOGS/pinterest-$ACCOUNT.log" 2>&1
echo "[$(date)] Done $ACCOUNT" >> "$LOGS/pinterest-$ACCOUNT.log"

echo "[$(date)] All done."
