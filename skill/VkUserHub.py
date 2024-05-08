from .Handler import UserHub


PRIMARY_VOICE = 'vasilisa-hifigan'
SECONDARY_VOICE = 'pavel-hifigan'

CALLBACK_TRIGGER = 'Салют, запусти нужен навык оранжевая нить'
CALLBACK_TRIGGER_LENGTH = len(CALLBACK_TRIGGER)


class VkUserHub(UserHub):

    def __init__(self, *args, n_threads_per_response: int = 10, n_chars_per_response = 7000, callback: bool = False, **kwargs):
        super().__init__(*args, n_threads_per_response = n_threads_per_response, n_chars_per_response = n_chars_per_response - (CALLBACK_TRIGGER_LENGTH if callback else 0), **kwargs)

        self.callback = callback

    def posts_to_response(self, request: dict, posts: list[str]):
        session = request.get('session')
        version = request.get('version')

        print(f'Response length (text) is {sum(len(post) for post in posts)}')

        if self.callback:
            posts.append(CALLBACK_TRIGGER)

        return {
            'response': {
                'commands': [
                    {
                        "type": "TTS",
                        "text": post,
                        "tts": post,
                        "voice": PRIMARY_VOICE if i % 2 < 1 else SECONDARY_VOICE
                    }
                    for i, post in enumerate(posts)
                ],
                'end_session': False
            },
            'session': session,
            'version': version
        }

    def make_response(self, request: dict, text: str, ssml: str = None, interactive: bool = True):
        if ssml is not None:
            raise ValueError('SSML markup is not supported')

        session = request.get('session')
        version = request.get('version')

        print(f'Response length (text) is {len(text)}')

        return {
            'response': {
                'text': text,
                'end_session': not interactive
            },
            'session': session,
            'version': version
        }

    def get_utterance(self, request: dict):
        request_prop = request.get('request')

        if request_prop is None:
            return None

        return request_prop.get('original_utterance')

    def get_user_id(self, request: dict):
        session = request.get('session')

        if session is None:
            return None

        user = session.get('user')

        if user is None:
            return None

        return user.get('user_id')
