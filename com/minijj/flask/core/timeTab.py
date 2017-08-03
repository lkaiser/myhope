import logging.handlers
import threading
import time

logger = logging.getLogger('tst')
class timeTab(object):
    def __init__(self, status=None, interval=3):
        self.status = status
        self.interval = interval


    def acquire(self,status):
        if not self.status or status == self.status:
            return
        else:

