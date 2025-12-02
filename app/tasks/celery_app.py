"""
Celery configuration for background tasks.

Implements Requirement 14: Background Job
- Uses Redis as message broker
- Scheduled tasks run every 5 minutes
- Cache prewarming and vendor performance logging
"""

import os
from celery import Celery
from celery.schedules import crontab

# Redis connection URL
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Initialize Celery app
celery_app = Celery(
    'stock_validator',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['app.celery_tasks']
)

# Celery configuration
celery_app.conf.update(
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Task execution
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=240,  # 4 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={'master_name': 'mymaster'},
)

# Celery Beat Schedule (Requirement 14: Every 5 minutes)
celery_app.conf.beat_schedule = {
    'run-background-job-every-5-minutes': {
        'task': 'app.celery_tasks.run_scheduled_background_job',
        'schedule': 300.0,  # 5 minutes in seconds
        'options': {
            'expires': 290,  # Expire after 4:50 to avoid overlap
        }
    },
}
