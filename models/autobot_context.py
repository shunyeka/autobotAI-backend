import os
import logging.config

session = {}
context = None
env = os.environ.get('FLASK_ENV', 'development')


class AutobotApp:
    config = {}
    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'default': {
                'format': '[%(asctime)s] %(levelname)s in %(module)s/%(filename)s:%(funcName)s:%(lineno)d -- %(message)s'}
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'stream': 'ext://sys.stdout'
            }
        },
        'loggers': {
            'default': {
                'level': 'INFO',
                'handlers': ['console']
            }
        },
        'root': {'handlers': ['console'], 'level': 'INFO'},
        'disable_existing_loggers': False
    })
    logger = logging.getLogger('autobot_app')

    def __init__(self):
        self.config = {'ENVIRONMENT': env.lower()}


context_app = None


def app():
    global context_app
    if not context_app:
        context_app = AutobotApp()
    return context_app
