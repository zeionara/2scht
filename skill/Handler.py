from abc import ABC, abstractmethod
import re

from requests import get

from much import Fetcher

from .Thread import Thread


CATALOG_URL = 'https://2ch.hk/b/catalog.json'
REF_MARK = re.compile(r'^>')
HTTP_SUCCESS = 200


class Handler(ABC):

    def __init__(self, n_threads_per_response: int = 5, n_chars_per_response = 5000, timeout: int = 60):
        self.n_threads_per_response = n_threads_per_response
        self.n_chars_per_response = n_chars_per_response
        self.timeout = timeout

        self._fetcher = Fetcher()
        self._last_batch_size = None
        self._threads = None
        self._offset = None

    def list_threads(self, reverse: bool = True, skip_first_n: int = 0):
        response = get(CATALOG_URL, timeout = self.timeout)

        # print(response.content)

        if (status_code := response.status_code) != HTTP_SUCCESS:
            raise ValueError(f'Can\'t pull threads, response status code is {status_code}')

        return sorted(Thread.from_list(response.json()['threads']), key = lambda thread: (thread.length, thread.freshness), reverse = reverse)[skip_first_n:]

    def should_reset_threads(self, utterance: str):
        return 'хочу' in utterance

    def should_stop(self, utterance: str):
        return 'стоп' in utterance

    def infer_index(self, utterance: str, user_id: str):
        index = None

        if 'первый' in utterance:
            index = 0
        elif 'второй' in utterance:
            index = 1
        elif 'третий' in utterance:
            index = 2
        elif 'четвертый' in utterance or 'четвёртый' in utterance:
            index = 3
        elif 'пятый' in utterance:
            index = 4
        elif 'шестой' in utterance:
            index = 5
        elif 'седьмой' in utterance:
            index = 6
        elif 'восьмой' in utterance:
            index = 7
        elif 'девятый' in utterance:
            index = 8
        elif 'десятый' in utterance:
            index = 9

        # if index is not None and index >= self.n_threads_per_response:
        if index is not None and self._last_batch_size is not None and (last_batch_size := self._last_batch_size.get(user_id)) and index < last_batch_size:
            return index

        return None

    def get_comment_list(self, index: int, user_id: str):
        thread_object = self._threads[user_id][index]

        all_comments = [thread_object.title_text] + [
            REF_MARK.sub(' ', comment)
            for topic in self._fetcher.fetch(thread_object.link, verbose = True)
            for comment in topic.comments
        ]
        n_chars = 0

        top_comments = []

        for comment in all_comments:
            n_chars += len(comment)

            if n_chars < self.n_chars_per_response:
                top_comments.append(comment)
            else:
                break

        return top_comments

    @abstractmethod
    def make_response(self, request: dict, text: str = None, ssml: str = None, auto_listening: bool = True):
        pass

    @abstractmethod
    def get_utterance(self, request: dict):
        pass

    @abstractmethod
    def get_user_id(self, request: dict):
        pass

    def handle(self, request: dict):
        utterance = self.get_utterance(request).lower().strip()
        user_id = self.get_user_id(request)

        user_offset = None if self._offset is None else self._offset.get(user_id)
        user_threads = None if self._threads is None else self._threads.get(user_id)

        if user_offset is None:
            if self._offset is None:
                self._offset = {user_id: 0}
            else:
                self._offset[user_id] = 0

        if user_threads is None or self.should_reset_threads(utterance):
            if self._threads is None:
                self._threads = {user_id: self.list_threads()}
            else:
                self._threads[user_id] = self.list_threads()

            self._offset[user_id] = 0
        else:
            if self.should_stop(utterance):
                self._threads.pop(user_id)
                self._offset.pop(user_id)

                return self.make_response(request, 'Завершаю показ тредов', auto_listening = False)

            index = self.infer_index(utterance, user_id)

            if index is None:
                target_item = None
                self._offset[user_id] = min(len(self._threads[user_id]) - self.n_threads_per_response, self._offset[user_id] + self._last_batch_size[user_id])
            else:
                target_item = self._offset[user_id] + index

            if target_item is not None:
                thread = self.get_comment_list(target_item, user_id)

                return self.make_response(request, '\n'.join(thread), ' <break time="1500ms"/> '.join(thread))

        text = ''
        offset = self._offset[user_id]
        threads = self._threads[user_id]

        batch_size = 0

        for i in range(offset, offset + self.n_threads_per_response):
            next_thread = f'Тред номер {i + 1}. {threads[i].title_text}.'

            if len(text) > 0:
                if len(text) + len(next_thread) > self.n_chars_per_response:
                    break

                text += '\n'

            batch_size += 1
            text += next_thread

        if self._last_batch_size is None:
            self._last_batch_size = {user_id: batch_size}
        else:
            self._last_batch_size[user_id] = batch_size

        return self.make_response(request, text)
