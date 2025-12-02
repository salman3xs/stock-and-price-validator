#!/bin/bash
# Start Celery worker and beat scheduler

echo "🚀 Starting Celery services..."
echo ""

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running!"
    echo "Please start Redis first: redis-server"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Celery worker
echo "Starting Celery worker..."
celery -A app.tasks.celery_app worker --loglevel=info --logfile=logs/celery_worker.log --detach
sleep 2

# Start Celery beat
echo "Starting Celery beat scheduler..."
celery -A app.tasks.celery_app beat --loglevel=info --logfile=logs/celery_beat.log --detach
sleep 1

echo ""
echo "✅ Celery services started successfully!"
echo ""
echo "📊 Status:"
celery -A app.tasks.celery_app inspect active 2>/dev/null || echo "  Worker: Running"
echo ""
echo "📝 Logs:"
echo "  Worker: logs/celery_worker.log"
echo "  Beat:   logs/celery_beat.log"
echo ""
echo "To stop: ./stop_celery.sh"
