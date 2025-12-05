#!/bin/bash
source dobot/bin/activate

python stram_server.py &
python dobot_server.py &

wait
