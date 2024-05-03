from .Handler import Handler


class SberHandler(Handler):

    def __init__(self, *args, n_threads_per_response: int = 10, n_chars_per_response = 7000, **kwargs):
        super().__init__(*args, n_threads_per_response = n_threads_per_response, n_chars_per_response = n_chars_per_response, **kwargs)

    def should_reset_threads(self, utterance: str):
        return 'хотеть' in utterance

    def infer_index(self, utterance: str, user_id: str):
        index = None

        if '1' in utterance:
            index = 0
        elif '2' in utterance:
            index = 1
        elif '3' in utterance:
            index = 2
        elif '4' in utterance:
            index = 3
        elif '5' in utterance:
            index = 4
        elif '6' in utterance:
            index = 5
        elif '7' in utterance:
            index = 6
        elif '8' in utterance:
            index = 7
        elif '9' in utterance:
            index = 8
        elif '10' in utterance:
            index = 9

        # if index is not None and index >= self.n_threads_per_response:
        if index is not None and self._last_batch_size is not None and (last_batch_size := self._last_batch_size.get(user_id)) and index < last_batch_size:
            return index

        return None

    def make_response(self, request: dict, text: str, ssml: str = None, auto_listening: bool = True):
        payload = request.get('payload', {})

        # assert not (text is None and ssml is None), 'text or ssml is required'

        if ssml is None:
            print(f'Response length (text) is {len(text)}')
        else:
            print(f'Response length (ssml) is {len(ssml)}')

        return {
            "sessionId": request.get('sessionId'),
            "messageId": request.get('messageId'),
            "uuid": request.get('uuid'),
            "messageName": "ANSWER_TO_USER",
            "payload": {
                "pronounceText": text if ssml is None else ssml,  # "Купил мужик шляпу, а она ему как раз",
                "pronounceTextType": "application/text" if ssml is None else 'application/ssml',
                "emotion": {
                    "emotionId": "laugh"
                },
                "items": [
                    {
                        "bubble": {
                            "text": text,
                            "expand_policy": "auto_expand"
                        }
                    }
                ],
                "auto_listening": auto_listening,
                "finished": False,
                "device": payload.get('device'),
                "intent": "string",
                "asr_hints": {}
            }
        }

    def get_utterance(self, request: dict):
        payload = request.get('payload')

        if payload is None:
            return None

        annotations = payload.get('annotations')

        if annotations is None:
            return None

        return annotations.get('unified_normalized_text')

    def get_user_id(self, request: dict):
        uuid = request.get('uuid')

        if uuid is None:
            return None

        return uuid.get('userId')
