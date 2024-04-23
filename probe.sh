#!/bin/bash

curl \
    -H 'Content-Type: application/json' \
    -d '{"session": {"id": 17}, "version": "1.0"}' \
    'https://4b81-77-234-196-15.ngrok-free.app'
    # 'http://localhost:1217'
    # --insecure \
