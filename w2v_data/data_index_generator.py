# coding=utf-8
"""collect the tokenized sentence from worker"""
import logbook as logging
import zmq
from utils.appmetric_util import with_meter
from utils.retry_util import retry


class DataIndexGenerator(object):
    """collect the tokenized sentence from worker
    Parameters
    ----------
        ip : str
            The ip address string without the port to pass to ``Socket.bind()``.
        port:
            The port to receive the tokenized sentence from worker
        tries: int
            Number of times to retry, set to 0 to disable retry
    """

    def __init__(self, ip, port, vocabulary, tries=20):
        self.ip = ip
        self.port = port
        self.tries = tries
        self.vocabulary = vocabulary

    @retry(lambda x: x.tries, exception=zmq.ZMQError,
           name="vocabulary_collector", report=logging.error)
    @with_meter('vocabulary_collector', interval=30)
    def _on_recv(self, receiver):
        words = receiver.recv_pyobj(zmq.NOBLOCK)
        return words

    def convert_words_to_id(self, words):
        indexs = []
        for word in words:
            if word in self.vocabulary:
                index = self.vocabulary[word]
            else:
                index = 0  # dictionary['UNK']
            indexs.append(index)
        return indexs

    def generate(self):
        """Generator that receive the tokenized sentence from worker and produce the words"""
        context = zmq.Context()
        receiver = context.socket(zmq.PULL)
        receiver.bind("tcp://{}:{}".format(self.ip, self.port))
        while True:
            try:
                words = self._on_recv(receiver)
                indexs = self.convert_words_to_id(words)
                yield indexs
            except zmq.ZMQError as e:
                logging.error(e)
                break
