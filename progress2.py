""" Progress dialog with multitheading. """


try:
    from PyQt5.QtWidgets import QProgressDialog
    from PyQt5.QtCore import QTimer
except:
    from PyQt4.QtGui import QProgressDialog
    from PyQt4.QtCore import QTimer

import threading
import Queue

_THREADS = set()


def worker(input, output):
    """ Execute the function from input queue and put the result in output. """
    try:
        while True:
            i, fun, args = input.get(False)
            result = fun(*args)
            # return (fetcher name, result, nonunique, number of results, index)
            output.put({'name': fun.__class__.__name__,
                        'result': result,
                        'nonunique': fun.nonunique,
                        'number': fun.number,
                        'index': i,
                        'query': args[0]})
    except Queue.Empty:
        pass


class Progress(QProgressDialog):

    """Progress dialog with an option to cancel execution of the computation."""

    def __init__(self, fun, args=[], job="Working...",
                 failure=lambda x: x['number'] == 0):
        """
        Create worker threads.

        Function 'failure' can be used to decide what constitutes failure of
        the fetching process.
        """
        self.failure = failure
        try:
            # list of tasks
            self.length = len(fun)
        except:
            # only one task
            self.length = 1
            fun = [fun]
            args = [args]
        super(Progress, self).__init__(job, "Cancel", 0, self.length)
        self.output = Queue.Queue()
        self.input = Queue.Queue()
        self.threads = []
        self.setModal(True)
        for i, fa in enumerate(zip(fun, args)):
            self.input.put((i, fa[0], fa[1]))
        for _ in range(min(4, self.length)):
            t = threading.Thread(target=worker, args=(self.input, self.output))
            t.daemon = True
            t.start()
            _THREADS.add(t)
        self.res = []

        self.canceled.connect(self.cleanup)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(10)

    def update(self):
        """ Check queue length and close if done. """
        try:
            # fetch everything from the queue
            while True:
                outcome = self.output.get(False)
                self.res.append(outcome)
                value = len(self.res)
                self.setValue(value)
                if self.failure(outcome):
                    message = outcome['name'] + ' search failed!'
                else:
                    message = '{0} search found {1} record{2}.' \
                        .format(outcome['name'], outcome['number'],
                                's' if outcome['number'] > 1 else '')
                self.setLabelText('({}/{}) '.format(value, self.length) +
                                  message)
        except:
            pass
        if len(self.res) == self.length:
            self.cleanup()
            self.done(1)

    def cleanup(self):
        """ Sort results and empty input queue if cancelled. """
        self.res.sort(key=lambda x: x['index'])
        self.timer.stop()
        # empty the input queue
        # all processes will die after finishing their current task
        try:
            while True:
                self.input.get(False)
        except Queue.Empty:
            pass
        for t in list(_THREADS):
            if not t.isAlive():
                _THREADS.remove(t)
