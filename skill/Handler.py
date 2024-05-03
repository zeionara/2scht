from __future__ import annotations
import re
from abc import ABC, abstractmethod
from threading import Thread as ExecutableThread, RLock
from time import sleep, time
from dataclasses import dataclass

from requests import get

from much import Fetcher

from .Thread import Thread


CATALOG_URL = 'https://2ch.hk/b/catalog.json'
REF_MARK = re.compile(r'^>')
HTTP_SUCCESS = 200
CLEANUP_INTERVAL = 3600
CLEANUP_TIMEOUT = 3600


def cleanup_cached_post_lists(hub: UserHub):
    cache = hub._cached_post_lists

    while True:
        current_time = time()

        # print(cache)

        with hub._cached_post_lists_lock:
            items = list(cache.items())

            for key, value in items:
                if current_time - value.time > CLEANUP_TIMEOUT:
                    cache.pop(key)

        sleep(CLEANUP_INTERVAL)


@dataclass
class CacheEntry:
    posts: list[str]
    time: int


class UserHub(ABC):  # stateless platform-dependent methods

    def __init__(self, n_threads_per_response: int = 5, n_chars_per_response = 5000, timeout: int = 60, overlap: int = 2):
        self.n_threads_per_response = n_threads_per_response
        self.n_chars_per_response = n_chars_per_response
        self.timeout = timeout
        self.overlap = overlap

        self._fetcher = Fetcher()
        self._users = None
        self._cached_post_lists = None
        # self._cached_post_lists = {'foo': CacheEntry(['bar', 'baz'], time())}
        self._cached_post_lists_lock = RLock()

        self.cleanup_thread = cleanup_thread = ExecutableThread(target = cleanup_cached_post_lists, args = (self, ))
        cleanup_thread.start()

    def handle(self, request: dict):
        user_id = self.get_user_id(request)

        if self._users is None:
            handler = Handler(self)
            self._users = {user_id: handler}
        elif (handler := self._users.get(user_id)) is None:
            handler = Handler(self)
            self._users[user_id] = handler

        return handler.handle(request)

    def get_posts(self, thread: Thread):
        thread_id = thread.id

        with self._cached_post_lists_lock:
            if (cached_post_lists := self._cached_post_lists) is not None and (cached_posts := cached_post_lists.get(thread_id)) is not None:
                all_posts = cached_posts.posts
            else:
                all_posts = [thread.title_text] + [
                    REF_MARK.sub(' ', post)
                    for topic in self._fetcher.fetch(thread.link, verbose = True)
                    for post in topic.comments
                ]

                if self._cached_post_lists is None:
                    self._cached_post_lists = {thread_id: CacheEntry(all_posts, time())}
                else:
                    self._cached_post_lists[thread_id] = CacheEntry(all_posts, time())

        return all_posts

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

    def should_continue(self, utterance: str):
        return 'дальше' in utterance or 'скилл' in utterance

    def should_go_forward(self, utterance: str):
        return 'вперед' in utterance

    def should_go_back(self, utterance: str):
        return 'назад' in utterance

    def infer_index(self, utterance: str):
        if 'первый' in utterance:
            return 0
        if 'второй' in utterance:
            return 1
        if 'третий' in utterance:
            return 2
        if 'четвертый' in utterance or 'четвёртый' in utterance:
            return 3
        if 'пятый' in utterance:
            return 4
        if 'шестой' in utterance:
            return 5
        if 'седьмой' in utterance:
            return 6
        if 'восьмой' in utterance:
            return 7
        if 'девятый' in utterance:
            return 8
        if 'десятый' in utterance:
            return 9

        return None

    @abstractmethod
    def make_response(self, request: dict, text: str = None, ssml: str = None, interactive: bool = True):
        pass

    @abstractmethod
    def get_utterance(self, request: dict):
        pass

    @abstractmethod
    def get_user_id(self, request: dict):
        pass

    @abstractmethod
    def posts_to_response(self, request: dict, posts: list[str]):
        pass


class Handler:  # stateful platform-independent methods

    def __init__(self, hub: UserHub):
        self._hub = hub

        self._last_batch_size = None  # number of threads shown in the last message
        self._threads = None  # thread headers
        self._offset = 0  # number of threads to skip when showing next thread to user

        self._index = 0  # index of the next thread to show to user
        self._distance = 0  # number of posts to skip when showing current thread to user

    @property
    def n_threads(self):
        if self._threads is None:
            raise ValueError('Threads are not initialized')

        return len(self._threads)

    def infer_index(self, utterance: str):
        index = self._hub.infer_index(utterance)

        if (
            index is not None and
            (last_batch_size := self._last_batch_size) is not None and
            index < last_batch_size
        ):
            return index

        return None

    def get_posts(self, index: int, distance: int = None):
        if (threads := self._threads) is None:
            raise ValueError('Threads are not initialized')

        posts = self._hub.get_posts(threads[index])

        # print(self._hub.overlap)

        if distance is not None:
            if distance >= len(posts):
                return None, None

            posts = posts[max(0, distance - self._hub.overlap):]

        n_chars = 0
        top_posts = []

        for post in posts:
            n_chars += len(post)

            if n_chars < self._hub.n_chars_per_response:
                top_posts.append(post)
            else:
                break

        return top_posts, (0 if distance is None else distance) + len(top_posts) - 1

    def handle(self, request: dict):
        utterance = self._hub.get_utterance(request).lower().strip()

        threads = self._threads

        if threads is None or self._hub.should_reset_threads(utterance):
            self._threads = threads = self._hub.list_threads()
            self._offset = 0
        else:
            if self._hub.should_stop(utterance):
                return self._hub.make_response(request, 'Завершаю показ тредов', interactive = False)

            if self._hub.should_continue(utterance) and self._index is not None and self._distance is not None:
                posts, distance = self.get_posts(self._offset + self._index, self._distance + 1)

                if posts is None or distance is None:
                    return self._hub.make_response(request, 'Больше не осталось комментариев')

                self._distance = distance

                return self._hub.posts_to_response(request, posts)

            if self._hub.should_go_forward(utterance):
                self._distance = 0

                current_index = self._index

                if current_index is None:
                    index = 0
                else:
                    index = min(current_index + 1, self.n_threads - self._offset - 1)

                    if index >= self._last_batch_size:
                        self._last_batch_size += 1
            elif self._hub.should_go_back(utterance):
                self._distance = 0

                current_index = self._index

                if current_index is None:
                    index = 0
                else:
                    index = max(current_index - 1, -self._offset)
            else:
                index = self.infer_index(utterance)

            self._index = index

            if index is None:
                target_item = None
                self._offset = min(self.n_threads - self._hub.n_threads_per_response, self._offset + self._last_batch_size)
            else:
                target_item = self._offset + index

            if target_item is not None:
                posts, distance = self.get_posts(target_item)

                if distance is not None:
                    self._distance = distance

                return self._hub.posts_to_response(request, posts)

        thread_headers_len = 0
        thread_headers = []
        offset = self._offset
        threads = self._threads

        # for i in range(offset, offset + self._hub.n_threads_per_response):
        for i in range(self._hub.n_threads_per_response):
            next_thread = f'Тред номер {i + 1}. {threads[offset + i].title_text}.'

            if len(thread_headers) > 0:
                if thread_headers_len + len(next_thread) > self._hub.n_chars_per_response:
                    break
            elif len(next_thread) > self._hub.n_chars_per_response:
                next_thread = next_thread[:self._hub.n_chars_per_response]

            thread_headers.append(next_thread)
            thread_headers_len += len(next_thread)

        self._last_batch_size = len(thread_headers)

        return self._hub.posts_to_response(request, thread_headers)
