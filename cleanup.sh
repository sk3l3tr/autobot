#!/bin/bash
# Cleanup script for Autobot processes

echo "Checking for existing Autobot processes..."
PIDS=$(pgrep -f Autobot)

if [ -n "$PIDS" ]; then
    echo "Found Autobot processes: $PIDS"
    echo "Killing processes..."
    pkill -f Autobot
    sleep 2
    
    # Check if port 65432 is still in use
    if lsof -i :65432 >/dev/null 2>&1; then
        echo "Port 65432 still in use, force killing..."
        lsof -ti :65432 | xargs kill -9
    fi
    
    # Check if port 5555 is still in use
    if lsof -i :5555 >/dev/null 2>&1; then
        echo "Port 5555 still in use, force killing..."
        lsof -ti :5555 | xargs kill -9
    fi

    echo "Cleanup complete!"
else
    echo "No Autobot processes found."
fi

# Verify port is free
if ! lsof -i :65432 >/dev/null 2>&1; then
    echo "Port 65432 is now available."
else
    echo "Warning: Port 65432 is still in use!"
fi

if ! lsof -i :5555 >/dev/null 2>&1; then
    echo "Port 5555 is now available."
else
    echo "Warning: Port 5555 is still in use!"
fi
