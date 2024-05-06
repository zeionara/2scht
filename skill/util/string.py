import re
from emoji import replace_emoji


URL_REGEXP = re.compile(r'http[^\s]+')
HANDLE_REGEXP = re.compile(r'@[^\s]+')
SPACE_REGEXP = re.compile(r'\s+')
REF_MARK = re.compile(r'^>')


def normalize(text: str):
    return normalize_spaces(
        replace_emoji(
            HANDLE_REGEXP.sub(
                ' ',
                URL_REGEXP.sub(
                    ' ',
                    REF_MARK.sub(
                        ' ',
                        text.replace('☹️', '')
                    )
                )
            ),
            ' '
        )
    )


def normalize_spaces(text: str):
    return SPACE_REGEXP.sub(' ', text)
