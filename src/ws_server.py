#!/usr/bin/python
import asyncio
import hashlib
import json
import os

from websockets import ConnectionClosed as WSConnectionClosed
from websockets import WebSocketServerProtocol
from websockets.server import serve as ws_serve



class WSConnectedClient:
    def __init__(self, sock: WebSocketServerProtocol, username: str, token: str, channel_id: str) -> None:
        self.sock = sock
        self.username = username
        self.token = token
        self.channel_id = channel_id

    def __hash__(self):
        return hash((self.username, self.token, self.channel_id))

    def __eq__(self, other):
        if not isinstance(other, WSConnectedClient):
            raise ValueError(f"Why would you compare {type(self)} with {type(other)}?")
        return (self.username == other.username and
                self.token == other.token and
                self.channel_id == other.channel_id)


async def ws_send_error(sock: WebSocketServerProtocol, message: str):
    response = {'error': message}
    await sock.send(json.dumps(response))
    print("[WS] Sent error message:", message)


async def ws_client_connect(sock: WebSocketServerProtocol):
    global ws_clients_by_channel
    try:
        async for message in sock:
            print("[WS] Received a message:", message)

            try:
                token, username, channel_id = message.split(" ")
                assert len(username) <= 28, all(ch in "0123456789" for ch in channel_id)
            except (ValueError, AssertionError):
                await ws_send_error(sock, "Format should be: \"{TOKEN} {USERNAME} {CHANNEL_ID}\"")
                continue

            user_dir = os.path.join(backend_dir, "accounts", username)
            user_meta_file = os.path.join(user_dir, "meta.json")

            try:
                with open(user_meta_file, 'r') as file:
                    user_meta = json.load(file)
            except FileNotFoundError:
                await ws_send_error(sock, "No user belongs to that username")
                continue
            except OSError:
                await ws_send_error(sock, "Internal server error (could not read user meta file)")
                continue

            m = hashlib.sha256()
            m.update(bytes(token, 'utf-8'))
            token_hash = m.hexdigest()
            if token_hash not in user_meta['validTokens']:
                await ws_send_error(sock, "Invalid token")
                continue

            # Success! Add user to connected clients list
            print("New client connected:", username, channel_id)

            client = WSConnectedClient(sock, username, token, channel_id)
            if ws_clients_by_channel.get(channel_id) is not None and client in ws_clients_by_channel[channel_id]:
                print("Client is already connected; removing other connection.")
                ws_clients_by_channel[channel_id].remove(client)

            try:
                ws_clients_by_channel[channel_id].append(client)
            except KeyError:
                ws_clients_by_channel[channel_id] = [client]

            # await sock.send("ok")  # TODO placeholder

    except WSConnectionClosed:
        print("Client disconnected:", sock.id)


async def ws_main():
    print("Started Websocket server.")
    async with ws_serve(ws_client_connect, "0.0.0.0", 8982):
        await asyncio.Future()

