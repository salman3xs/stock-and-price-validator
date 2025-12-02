#!/bin/bash
# Stop Celery worker and beat scheduler

echo "🛑 Stopping Celery services..."
echo ""

# Stop Celery worker
echo "Stopping Celery worker..."
pkill -f 'celery.*worker'
WORKER_EXIT=$?

# Stop Celery beat
echo "Stopping Celery beat..."
pkill -f 'celery.*beat'
BEAT_EXIT=$?

echo ""
if [ $WORKER_EXIT -eq 0 ] || [ $BEAT_EXIT -eq 0 ]; then
    echo "✅ Celery services stopped"
else
    echo "⚠️  No Celery processes found (already stopped)"
fi
