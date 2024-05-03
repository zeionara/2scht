from flask import Flask, request, json

from much import Fetcher

from .Handler import UserHub
from .SberUserHub import SberUserHub


DEFAULT_PORT = 1217
OFFSET = 100


class Server:
    def __init__(self, verbose: bool = False):
        self.app = Flask('2scht speech skill server')
        self.fetcher = Fetcher()
        self.verbose = verbose

        json.provider.DefaultJSONProvider.ensure_ascii = False

        self.sber = SberUserHub()

    def serve(self, host: str = '0.0.0.0', port = DEFAULT_PORT):
        app = self.app

        def handle(hub: UserHub):
            verbose = self.verbose

            if verbose:
                print('-' * OFFSET + 'request')
                print(request.json)

            response = hub.handle(request.json)

            if verbose:
                print('-' * OFFSET + 'response')
                print(request.json)

            return response

        @app.route('/app-connector', methods = ['POST'])
        def connect():
            return handle(self.sber)

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
