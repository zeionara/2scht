from __future__ import annotations
from abc import ABC, abstractmethod
from threading import Thread as ExecutableThread, RLock
from time import sleep, time
from dataclasses import dataclass
from bs4 import BeautifulSoup

from requests import get

from much import Fetcher

from .Thread import Thread
from .util import normalize, normalize_spaces


CATALOG_URL = 'https://2ch.hk/b/catalog.json'
HTTP_SUCCESS = 200
CLEANUP_INTERVAL = 3600
CLEANUP_TIMEOUT = 3600

HELP_TEXT = (
    'Я могу озвучивать треды с двача. '
    'Просто назовите номер заинтересовавшего вас треда'
)


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

    def __init__(self, n_threads_per_response: int = 5, n_chars_per_response = 5000, post_sep_length: int = 0, timeout: int = 60, overlap: int = 2, disabled_thread_starters: tuple[str] = None):
        self.n_threads_per_response = n_threads_per_response
        self.n_chars_per_response = n_chars_per_response
        self.post_sep_length = post_sep_length
        self.timeout = timeout
        self.overlap = overlap

        self._fetcher = Fetcher()
        self._users = None
        self._cached_post_lists = {}  # None
        # self._cached_post_lists = {'foo': CacheEntry(['bar', 'baz'], time())}
        self._cached_post_lists_lock = RLock()
        self.disabled_thread_starters = disabled_thread_starters

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
                all_posts = [normalize(thread.title_text)] + [
                    normalize(post)
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

        # print(
        #     len([
        #         normalize_spaces(BeautifulSoup(thread['comment'], 'lxml').get_text().strip())
        #         for thread in response.json()['threads']
        #         if any(
        #             normalize_spaces(BeautifulSoup(thread['comment'], 'lxml').get_text().lower().strip()).startswith(disabled_thread_starter)
        #             for disabled_thread_starter in self.disabled_thread_starters
        #         )
        #     ])
        # )

        return sorted(
            Thread.from_list(
                [
                    thread
                    for thread in response.json()['threads']
                    if not any(
                        normalize_spaces(BeautifulSoup(thread['comment'], 'lxml').get_text().lower().strip()).startswith(disabled_thread_starter)
                        for disabled_thread_starter in self.disabled_thread_starters
                    )
                ]
            ),
            key = lambda thread: (thread.length, thread.freshness),
            reverse = reverse
        )[skip_first_n:]

    def should_reset_threads(self, utterance: str):
        return 'хочу' in utterance

    def should_stop(self, utterance: str):
        return 'стоп' in utterance

    def should_continue(self, utterance: str):
        # print(utterance)
        return 'дальше' in utterance or 'скилл' in utterance or 'skill' in utterance

    def should_rewind(self, utterance: str):
        # print(utterance)
        return 'включи' in utterance

    def should_go_forward(self, utterance: str):
        return 'вперед' in utterance or 'вперёд' in utterance

    def should_go_back(self, utterance: str):
        return 'назад' in utterance

    def should_repeat(self, utterance: str):
        return 'поиграем' in utterance

    def should_help(self, utterance: str):
        return 'можешь' in utterance or 'умеешь' in utterance or 'можете' in utterance or 'умеете' in utterance

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
        self._distance = 0  # number of posts to skip when showing current thread to user in the next response
        self._last_distance = 0  # number of posts to skip which was used in the last response

    @property
    def n_threads(self):
        if self._threads is None:
            raise ValueError('Threads are not initialized')

        return len(self._threads)

    def infer_index(self, utterance: str):
        index = self._hub.infer_index(utterance)

        # print(index, index is not None, (last_batch_size := self._last_batch_size) is not None, last_batch_size)

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
        overlap = self._hub.overlap

        # print(self._hub.overlap)

        if distance is not None:
            if distance >= len(posts):
                return None, None

            posts = posts[max(0, distance - overlap):]

            shift = 0  # skip n posts in the beginning if they are too large to not to stuck with them

            while sum(len(post) for post in posts[shift:overlap]) > self._hub.n_chars_per_response:
                shift += 1

            posts = posts[shift:]

        # if distance is None:
        #     for post, i in enumerate(posts):
        #         print(post, i)

        n_chars = 0
        top_posts = []

        for post in posts:
            n_chars += len(post)

            if n_chars < (self._hub.n_chars_per_response + self._hub.post_sep_length * len(top_posts)):
                top_posts.append(post)
            else:
                if len(top_posts) < 1:
                    top_posts.append(post[:self._hub.n_chars_per_response])
                elif len(top_posts) > 1:
                    top_posts = top_posts[:-1]

                break

        return top_posts, (0 if distance is None else distance) + len(top_posts) - 1 - (0 if distance is None else self._hub.overlap)

    def handle(self, request: dict):
        utterance = self._hub.get_utterance(request).lower().strip()

        print(f'Got utterance "{utterance}"')

        if self._hub.should_help(utterance):
            return self._hub.make_response(request, HELP_TEXT)

        threads = self._threads

        if threads is None or self._hub.should_reset_threads(utterance):
            self._threads = threads = self._hub.list_threads()
            self._offset = 0
        else:
            if self._hub.should_stop(utterance):
                return self._hub.make_response(request, 'Завершаю показ тредов', interactive = False)

            if self._hub.should_repeat(utterance):
                posts, _ = self.get_posts(self._offset + self._index, self._last_distance + 1)

                if posts is None:
                    return self._hub.make_response(request, 'Больше не осталось комментариев')

                return self._hub.posts_to_response(request, posts)

            # print(self._hub.should_continue(utterance), self._index, self._distance)
            if self._hub.should_continue(utterance) and self._index is not None and self._distance is not None:
                posts, distance = self.get_posts(self._offset + self._index, self._distance + 1)

                # print(f'current distance = {self._distance}, next distance = {distance}')

                if posts is None or distance is None:
                    return self._hub.make_response(request, 'Больше не осталось комментариев')

                self._last_distance = self._distance
                self._distance = distance

                return self._hub.posts_to_response(request, posts)

            if self._hub.should_rewind(utterance) and self._index is not None and self._distance is not None:
                # print('foo', self._offset + self._index, max(self._distance - 1, 0))
                posts, distance = self.get_posts(self._offset + self._index, max(self._distance - 1, 0))

                if posts is None or distance is None:
                    return self._hub.make_response(request, 'Больше не осталось комментариев')

                self._last_distance = self._distance
                self._distance = distance

                return self._hub.posts_to_response(request, posts)

            if self._hub.should_go_forward(utterance):
                self._distance = 0
                self._last_distance = 0

                current_index = self._index

                if current_index is None:
                    index = 0
                else:
                    index = min(current_index + 1, self.n_threads - self._offset - 1)

                    if index >= self._last_batch_size:
                        self._last_batch_size += 1
            elif self._hub.should_go_back(utterance):
                self._distance = 0
                self._last_distance = 0

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
                    self._last_distance = 0
                    self._distance = distance

                return self._hub.posts_to_response(request, posts)

        thread_headers_len = 0
        thread_headers = []
        offset = self._offset
        threads = self._threads

        # for i in range(offset, offset + self._hub.n_threads_per_response):
        for i in range(self._hub.n_threads_per_response):
            next_thread = f'Тред номер {i + 1}. {normalize(threads[offset + i].title_text)}.'

            if len(thread_headers) > 0:
                if thread_headers_len + len(next_thread) > self._hub.n_chars_per_response:
                    break
            elif len(next_thread) > self._hub.n_chars_per_response:
                next_thread = next_thread[:self._hub.n_chars_per_response]

            thread_headers.append(next_thread)
            thread_headers_len += len(next_thread)

        self._last_batch_size = len(thread_headers)

        return self._hub.posts_to_response(request, thread_headers)
