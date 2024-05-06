from flask import Flask, request, json

from much import Fetcher

from .Handler import UserHub

from .SberUserHub import SberUserHub
from .VkUserHub import VkUserHub
from .YandexUserHub import YandexUserHub


DEFAULT_PORT = 1217
OFFSET = 100


class Server:
    def __init__(self, verbose: bool = False):
        self.app = Flask('2scht speech skill server')
        self.fetcher = Fetcher()
        self.verbose = verbose

        json.provider.DefaultJSONProvider.ensure_ascii = False

        self.sber = SberUserHub()
        self.vk = VkUserHub()
        self.yandex = YandexUserHub()

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
        def sber():
            return handle(self.sber)

        @app.route('/', methods = ['POST'])
        def vk_and_yandex():
            # print(self.yandex.get_user_id(request.json), self.yandex.get_utterance(request.json))

            if self.yandex.can_handle(request.json):
                return handle(self.yandex)

            return handle(self.vk)

        app.run(host = host, port = port)  # , ssl_context = ('cert/cert.pem', 'cert/key.pem'))
