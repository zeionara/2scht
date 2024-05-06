from .VkUserHub import VkUserHub


class YandexUserHub(VkUserHub):

    def __init__(self, *args, n_threads_per_response: int = 10, n_chars_per_response = 1024, version: str = '1.0', **kwargs):
        super().__init__(*args, n_threads_per_response = n_threads_per_response, n_chars_per_response = n_chars_per_response, **kwargs)

        self.version = version

    def posts_to_response(self, request: dict, posts: list[str]):
        return self.make_response(request, '\n'.join(posts), ' sil <[1500]> '.join(posts))

    def make_response(self, request: dict, text: str, ssml: str = None, interactive: bool = True):
        if ssml is None:
            print(f'Response length (text) is {len(text)}')
        else:
            print(f'Response length (ssml) is {len(ssml)}')

        state = request.get('state')

        if state is not None:
            session_state = state.get('session')
            user_state = state.get('user')
            application_state = state.get('application')
        else:
            session_state = None
            user_state = None
            application_state = None

        response_body = {
            "text": text,
            "end_session": not interactive,
        }

        if ssml is not None:
            response_body['tts'] = ssml

        response = {
            "response": response_body,
            "version": self.version
        }

        if session_state is not None:
            response['session_state'] = session_state

        if user_state is not None:
            response['user_state'] = user_state

        if application_state is not None:
            response['application_state'] = application_state

        return response

    def can_handle(self, request: dict):
        meta = request.get('meta')

        if meta is None:
            return False

        client_id = meta.get('client_id')

        if client_id is None:
            return False

        return client_id.startswith('ru.yandex')
