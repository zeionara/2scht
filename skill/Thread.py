import re
from bs4 import BeautifulSoup


SPACE = ' '
MAX_HEADER_LENGTH = 100

BR_TAG = re.compile('<br/?>')


class Thread:
    def __init__(self, title: str, length: int, freshness: float, id_: int):
        self.title = title
        self.length = length
        self.freshness = freshness
        self.id = id_

    def __repr__(self):
        return f'{self.header} (length = {self.length}, freshness = {self.freshness:.2f}, id = {self.id})'

    @property
    def title_text(self):
        # return BeautifulSoup(BR_TAG.sub(self.title, '\n'), features = 'html.parser').get_text(separator = ' ')
        return BeautifulSoup(BR_TAG.sub('\n', self.title), features = 'html.parser').get_text(separator = ' ')

    @property
    def header(self):
        strong = (title := BeautifulSoup(self.title, features = 'html.parser')).find('strong')

        if strong is None:
            return title.get_text(separator = SPACE).split('.', maxsplit = 1)[0][:MAX_HEADER_LENGTH]

        return strong.get_text(separator = SPACE)

    @property
    def link(self):
        return f'https://2ch.su/b/res/{self.id}.html'

    @classmethod
    def from_list(cls, items: list):
        n_items = len(items)

        return tuple(
            Thread(item['comment'], item['posts_count'], 1 - i / n_items, item['num'])
            for i, item in enumerate(items)
        )
