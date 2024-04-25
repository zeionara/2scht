from flask import Flask, request, json
from requests import get

from much import Fetcher

from .Thread import Thread


DEFAULT_PORT = 1217
CATALOG_URL = 'https://2ch.hk/b/catalog.json'
N_THREADS_PER_RESPONSE = 5
N_CHARS_PER_RESPONSE = 7000


def make_response(request_json: dict, payload: dict, text: str, ssml: str = None):
    return {
        "sessionId": request_json.get('sessionId'),
        "messageId": request_json.get('messageId'),
        "uuid": request_json.get('uuid'),
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
            "auto_listening": True,
            "finished": False,
            "device": payload.get('device'),
            "intent": "string",
            "asr_hints": {}
        }
    }


class Server:
    def __init__(self):
        self.app = Flask('2scht speech skill server')
        self.fetcher = Fetcher()

        json.provider.DefaultJSONProvider.ensure_ascii = False

        self._threads = None
        self._offset = None
        self._first_call = True

    def list_threads(self, reverse: bool = True, skip_first_n: int = 0):
        response = get(CATALOG_URL, timeout = 60)

        if (status_code := response.status_code) != 200:
            raise ValueError(f'Can\'t pull threads, response status code is {status_code}')

        return sorted(Thread.from_list(response.json()['threads']), key = lambda thread: (thread.length, thread.freshness), reverse = reverse)[skip_first_n:]

    def serve(self, host: str = '0.0.0.0', port = DEFAULT_PORT):
        app = self.app

        @app.route('/app-connector', methods = ['POST'])
        def connect():
            request_json = request.json
            payload = request_json.get('payload', {})
            annotations = payload.get('annotations', {})
            original_utterance = annotations.get('unified_normalized_text')

            if self._offset is None:
                self._offset = 0

            # print(json.dumps(request_json, ensure_ascii = False, indent = 2))

            # threads = self.list_threads()

            # next_offset = self._offset + N_THREADS_PER_RESPONSE

            if self._threads is None or 'хочу' in original_utterance:
                self._threads = self.list_threads()
                self._offset = 0
            else:
                if 'стоп' in original_utterance:
                    self._threads = None
                    self._offset = None

                    return make_response(request_json, payload, 'Завершаю показ тредов')
                else:
                    if '1' in original_utterance:
                        target_item = self._offset
                    elif '2' in original_utterance:
                        target_item = self._offset + 1
                    elif '3' in original_utterance:
                        target_item = self._offset + 2
                    elif '4' in original_utterance or 'четвёртый' in original_utterance:
                        target_item = self._offset + 3
                    elif '5' in original_utterance:
                        target_item = self._offset + 4
                    else:
                        target_item = None
                        self._offset = min(len(self._threads) - N_THREADS_PER_RESPONSE, self._offset + N_THREADS_PER_RESPONSE)

                    if target_item is not None:
                        thread_ = [self._threads[target_item].title_text] + [
                            comment
                            for topic in self.fetcher.fetch(self._threads[target_item].link, verbose = True)
                            for comment in topic.comments
                        ]
                        thread = []

                        n_chars = 0

                        for comment in thread_:
                            n_chars += len(comment)
                            if n_chars < N_CHARS_PER_RESPONSE:
                                thread.append(comment)
                            else:
                                break

                        return make_response(request_json, payload, '\n'.join(thread), ' <break time="1000ms"/> '.join(thread))

            tts = ''
            offset = self._offset
            threads = self._threads

            for i in range(offset, offset + N_THREADS_PER_RESPONSE):
                if len(tts) > 0:
                    tts += '\n'
                tts += f'Тред номер {i + 1}. {threads[i].title_text}.'

            return make_response(request_json, payload, tts)

            # response = {
            #     "sessionId": request_json.get('sessionId'),
            #     "messageId": request_json.get('messageId'),
            #     "uuid": request_json.get('uuid'),
            #     "messageName": "ANSWER_TO_USER",
            #     "payload": {
            #         "pronounceText": tts,  # "Купил мужик шляпу, а она ему как раз",
            #         "pronounceTextType": "application/text",
            #         "emotion": {
            #             "emotionId": "laugh"
            #         },
            #         "items": [
            #             {
            #                 "bubble": {
            #                     "text": tts,
            #                     "expand_policy": "auto_expand"
            #                 }
            #             }
            #         ],
            #         #     {
            #         #         'command': {
            #         #             'type': 'action',
            #         #             'action': {
            #         #                 'type': 'text',
            #         #                 'text': 'Один два три четыре пять',
            #         #                 'pronounceText': 'Один два три четыре пять',
            #         #                 'pronounceTextType': 'application/text',
            #         #                 'should_send_to_backend': False  # self._first_call
            #         #             }
            #         #         }
            #         #     }
            #         # ],
            #         # "items": [
            #         #     {
            #         #         # "bubble": {},
            #         #         # "card": {},
            #         #         "command": {
            #         #             "type": "action",
            #         #             "action": {
            #         #                 "type": "text",
            #         #                 "text": "Один",
            #         #                 "tts": "Один"
            #         #             }
            #         #         }
            #         #     },
            #         #     {
            #         #         "command": {
            #         #             "type": "action",
            #         #             "action": {
            #         #                 "type": "text",
            #         #                 "text": "Два",
            #         #                 "tts": "Два"
            #         #             }
            #         #         }
            #         #     }
            #         # ],
            #         # "suggestions": {
            #         #     "buttons": [
            #         #         {
            #         #             "title": "string",
            #         #             "action": {},
            #         #             "actions": [
            #         #                 {}
            #         #             ]
            #         #         }
            #         #     ]
            #         # },
            #         "auto_listening": True,
            #         "finished": False,
            #         "device": payload.get('device'),
            #         "intent": "string",
            #         "asr_hints": {}
            #     }
            # }

            # if self._first_call:
            #     self._first_call = False

            # self._offset += N_THREADS_PER_RESPONSE

            # return response

        @app.route('/', methods = ['POST'])
        def pull():
            request_json = request.json

            session = request_json.get('session')
            version = request_json.get('version')
            original_utterance = request_json.get('request', {}).get('original_utterance').lower()

            # print(self._offset)

            if self._threads is None or 'хочу' in original_utterance:
                self._threads = self.list_threads()
                self._offset = 0
            else:

                # if 'альфа' in original_utterance:
                #     self._offset = min(len(self._threads) - N_THREADS_PER_RESPONSE, self._offset + N_THREADS_PER_RESPONSE)

                if 'стоп' in original_utterance:
                    self._threads = None
                    self._offset = None

                    return {
                        'response': {
                            'text': 'Завершаю показ тредов',
                            'end_session': True
                        },
                        'session': session,
                        'version': version
                    }
                else:
                    if 'первый' in original_utterance:
                        target_item = self._offset
                    elif 'второй' in original_utterance:
                        target_item = self._offset + 1
                    elif 'третий' in original_utterance:
                        target_item = self._offset + 2
                    elif 'четвертый' in original_utterance or 'четвёртый' in original_utterance:
                        target_item = self._offset + 3
                    elif 'пятый' in original_utterance:
                        target_item = self._offset + 4
                    else:
                        target_item = None
                        self._offset = min(len(self._threads) - N_THREADS_PER_RESPONSE, self._offset + N_THREADS_PER_RESPONSE)

                    if target_item is not None:
                        thread_ = [self._threads[target_item].title_text] + [
                            comment
                            for topic in self.fetcher.fetch(self._threads[target_item].link, verbose = True)
                            for comment in topic.comments
                        ]
                        thread = []

                        n_chars = 0

                        for comment in thread_:
                            n_chars += len(comment)
                            if n_chars < N_CHARS_PER_RESPONSE:
                                thread.append(comment)
                            else:
                                break

                        print(len(thread), thread)

                        return {
                            'response': {
                                # 'text': f'Ты говоришь: "{original_utterance}", я тебе отвечаю: привет, мир',
                                'commands': [
                                    {
                                        "type": "TTS",
                                        "text": comment,
                                        "tts": comment,
                                        "voice": "vasilisa-hifigan" if i % 2 < 1 else 'pavel-hifigan'
                                    }
                                    for i, comment in enumerate(thread)
                                ],
                                'end_session': False
                            },
                            'session': session,
                            'version': version
                        }

                    # print(self._threads[self._offset].link)
                    # self._offset = max(0, self._offset - N_THREADS_PER_RESPONSE)

            threads = self._threads
            offset = self._offset

            return {
                'response': {
                    # 'text': f'Ты говоришь: "{original_utterance}", я тебе отвечаю: привет, мир',
                    'commands': [
                        {
                            "type": "TTS",
                            "text": threads[i].title_text,
                            "tts": f'Тред номер {i + 1}. {threads[i].title_text}',
                            "voice": "vasilisa-hifigan" if i % 2 < 1 else 'pavel-hifigan'
                        }
                        for i in range(offset, offset + N_THREADS_PER_RESPONSE)
                    ],
                    'end_session': False
                },
                'session': session,
                'version': version
            }

        app.run(host = host, port = port)  # , ssl_context = ('cert/cert.pem', 'cert/key.pem'))
