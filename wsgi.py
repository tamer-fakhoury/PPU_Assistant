import logging
from a2wsgi import ASGIMiddleware
from main import app

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ppu.wsgi")
log.info("WSGI application initialized")

application = ASGIMiddleware(app)
