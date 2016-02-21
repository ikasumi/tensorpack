#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
# File: concurrency.py
# Author: Yuxin Wu <ppwwyyxx@gmail.com>

import threading
from contextlib import contextmanager
import tensorflow as tf

from .naming import *
from . import logger

class StoppableThread(threading.Thread):
    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


class EnqueueThread(threading.Thread):
    def __init__(self, trainer, enqueue_op, dataflow, queue):
        super(EnqueueThread, self).__init__()
        self.sess = trainer.sess
        self.coord = trainer.coord
        self.input_vars = trainer.model.get_input_vars()

        self.dataflow = dataflow
        self.op = enqueue_op
        self.queue = queue
        self.close_op = self.queue.close(cancel_pending_enqueues=True)

        self.daemon = True

    def run(self):
        try:
            while True:
                for dp in self.dataflow.get_data():
                    if self.coord.should_stop():
                        return
                    feed = dict(zip(self.input_vars, dp))
                    self.sess.run([self.op], feed_dict=feed)
        except tf.errors.CancelledError as e:
            pass
        except Exception:
            logger.exception("Exception in EnqueueThread:")
            self.sess.run(self.close_op)
            self.coord.request_stop()
