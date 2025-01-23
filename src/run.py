#!/usr/bin/python
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import ws_server
import http_server



# -------- Globals --------
# WARNING: ./\ SHOULD NEVER BE ALLOWED FOR PATH SECURITY
USERNAME_CHARSET = set("abcdefghijklmnopqrstuvwxyz-_")
MESSAGE_BATCH_SIZE = 30
ws_clients_by_channel: dict[int, list[WSConnectedClient]] = {}

