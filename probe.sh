#!/bin/bash

curl \
    -H 'Content-Type: application/json' \
    # -d '{"request": {"original_utterance": "foo"}, "session": {"id": 17}, "version": "1.0"}' \
    # 'https://careful-poodle-proven.ngrok-free.app'
    # 'http://localhost:1217/'
    -d '{"session": {"id": 17}, "version": "1.0"}' \
    'https://exotic-frog-blessed.ngrok-free.app'
    # 'https://4b81-77-234-196-15.ngrok-free.app'
    # 'http://localhost:1217'
    # --insecure \
