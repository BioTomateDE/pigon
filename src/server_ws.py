import asyncio
import hashlib
import json
import os
from websockets import ConnectionClosed, WebSocketServerProtocol
from websockets.server import serve


class ConnectedClient:
    def __init__(self, sock:WebSocketServerProtocol, username:str, token:str, channel_id:int) -> None:
        self.sock = sock
        self.username = username
        self.token = token
        self.channel_id = channel_id

    def __hash__(self):
        return hash((self.username, self.token, self.channel_id))
    
    def __eq__(self, other):
        if not isinstance(other, ConnectedClient):
            raise ValueError(f"Why would you compare a ConnectedUser and {type(other)}?")
        return (self.username == other.username and
                self.token == other.token and
                self.channel_id == other.channel_id)


def send_error(sock: WebSocketServerProtocol, message: str):
    response = {'error': message}
    sock.send(bytes(json.dumps(response), 'utf-8'))


connected_clients = []

async def client_connect(sock: WebSocketServerProtocol):
    global connected_clients
    try:
        async for message in sock:
            print("Received a message:", message)
            
            try:
                token, username, channel_id = message.split(" ")
                channel_id = int(channel_id)
                assert len(username) <= 28 and channel_id >= 0
            except (ValueError, AssertionError):
                send_error(sock, "Format should be: \"{TOKEN} {USERNAME} {CHANNEL_ID}\"")
                return
            
            user_dir = os.path.join(backend_dir, "accounts", username)
            user_meta_file = os.path.join(user_dir, "meta.json")
            
            try:
                with open(user_meta_file, 'r') as file:
                    user_meta = json.load(file)
            except FileNotFoundError:
                send_error(sock, "No user belongs to that username")
                return
            except OSError:
                send_error(sock, "Internal server error (could not read user meta file)")
                return
            
            m = hashlib.sha256()
            m.update(token)
            token_hash = m.hexdigest()
            if token_hash not in user_meta['validTokens']:
                send_error(sock, "Invalid token")
                return
            
            # Success! Add user to connected clients list
            print("New client connected:", username, channel_id)
            
            connected_client = ConnectedClient(username, token, channel_id)
            if connected_client in connected_clients:
                print("Client is already connected; removing other connection.")
                connected_clients.remove(connected_client)
            
            connected_clients.append(connected_client)
            
            for client in connected_clients:
                if client == sock.id:
                    sock.send()
            else:
                connected_clients.append(sock)
            
            await sock.send("ok")
        
    except ConnectionClosed:
        print("Client disconnected:", sock.id)


async def echo(websocket):
    async for message in websocket:
        await websocket.send(message)

async def main():
    print("Started.")
    async with serve(client_connect, "localhost", 8982):
        await asyncio.get_running_loop().create_future()  # run forever

asyncio.run(main())