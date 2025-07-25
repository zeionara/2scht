from .Handler import UserHub, POST_ELEMENT_SEP_MARK

POST_SEP = ' <break time="1500ms"/> '
POST_ELEMENT_SEP = ' <break time="500ms"/> '


class SberUserHub(UserHub):

    def __init__(self, *args, n_threads_per_response: int = 10, n_chars_per_response = 4000, **kwargs):
        super().__init__(
            *args, n_threads_per_response = n_threads_per_response, n_chars_per_response = n_chars_per_response,
            post_sep_length = len(POST_SEP), post_element_sep_length = len(POST_ELEMENT_SEP) - 1,  # 1 character matches the '@' symbol in post body
            n_chars_per_overlap_post = 100,
            **kwargs
        )

    # def fix(self, post: str):
    #     return post.replace('@', '<break time="500ms"/>')

    def should_reset_threads(self, utterance: str):
        return 'хотеть' in utterance

    def should_continue(self, utterance: str):
        return 'далекий' in utterance or 'скил' in utterance or 'skill' in utterance

    def should_repeat(self, utterance: str):
        return 'поиграть' in utterance

    def should_help(self, utterance: str):
        return 'мочь' in utterance or 'уметь' in utterance

    def should_run_callback(self, utterance: str):
        return 'нужный' in utterance

    def infer_index(self, utterance: str):
        if '10' in utterance:
            return 9
        if '1' in utterance:
            return 0
        if '2' in utterance:
            return 1
        if '3' in utterance:
            return 2
        if '4' in utterance:
            return 3
        if '5' in utterance:
            return 4
        if '6' in utterance:
            return 5
        if '7' in utterance:
            return 6
        if '8' in utterance:
            return 7
        if '9' in utterance:
            return 8

        return None

    def posts_to_response(self, request: dict, posts: list[str]):
        # preprocessed_posts = []

        # for post in posts:
        #     preprocessed_posts.append(
        #         normalize(post)
        #     )

        # print(posts)

        # return self.make_response(request, '\n'.join(posts), POST_SEP.join(posts)[:self.n_chars_per_response])
        return self.make_response(request, '\n'.join(posts), POST_SEP.join([post.replace(POST_ELEMENT_SEP_MARK, POST_ELEMENT_SEP) for post in posts]))

    def make_response(self, request: dict, text: str, ssml: str = None, interactive: bool = True):
        payload = request.get('payload', {})

        if ssml is None:
            print(f'Response length (text) is {len(text)}')
        else:
            print(f'Response length (ssml) is {len(ssml)}')

        print(text, len(text))
        if ssml is not None:
            print(ssml, len(ssml))

        # print()
        # print(ssml)
        # ssml = None

        return {
            "sessionId": request.get('sessionId'),
            "messageId": request.get('messageId'),
            "uuid": request.get('uuid'),
            "messageName": "ANSWER_TO_USER",
            "payload": {
                "pronounceText": (text if ssml is None else ssml)[:self.n_chars_per_response],  # "Купил мужик шляпу, а она ему как раз",
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
                "auto_listening": interactive,
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

    def handle(self, request: dict):
        utterance = self.get_utterance(request)

        if self.should_run_callback(utterance):
            return self.make_response(request, 'Маруся, запусти скилл оранжевая нить')

        return super().handle(request)
