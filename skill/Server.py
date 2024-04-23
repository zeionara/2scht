from flask import Flask, request, json


DEFAULT_PORT = 1217


class Server:
    def __init__(self):
        self.app = Flask('2scht speech skill server')
        json.provider.DefaultJSONProvider.ensure_ascii = False

    def serve(self, host: str = '0.0.0.0', port = DEFAULT_PORT):
        app = self.app

        @app.route('/', methods = ['POST'])
        def pull():
            request_json = request.json

            session = request_json.get('session')
            version = request_json.get('version')
            original_utterance = request_json.get('request', {}).get('original_utterance')

            return {
                'response': {
                    'text': f'Ты говоришь: "{original_utterance}", я тебе отвечаю: привет, мир',
                    'end_session': False
                },
                'session': session,
                'version': version
            }

        app.run(host = host, port = port)  # , ssl_context = ('cert/cert.pem', 'cert/key.pem'))
