"""Root Lambda handler module (package path: lambda_handler.handler).

Deploy with handler: ``lambda_handler.handler``
and PYTHONPATH / code root = ``backend/``.
"""

from app.jobs.lambda_entry import handler

__all__ = ["handler"]
