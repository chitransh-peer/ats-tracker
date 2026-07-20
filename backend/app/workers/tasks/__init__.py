from app.workers.broker import broker  # noqa: F401  (registers the Redis broker on import)
from app.workers.tasks import ai  # noqa: F401  (registers the AI actors on import)
