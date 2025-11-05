import os
from django.core.wsgi import get_wsgi_application
from vercel_wsgi import handle 

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eln.settings")  # ganti 'eln' kalau nama project beda
app = get_wsgi_application()

def handler(event, context):
    return handle(event, context, app)
