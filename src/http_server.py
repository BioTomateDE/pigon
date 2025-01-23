#!/usr/bin/python
import random
import shutil
from base64 import b64encode
from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
import os
import json
import re
import threading
import time
import hashlib
from urllib.parse import urlparse
import asyncio
from websockets import ConnectionClosed as WSConnectionClosed
from websockets import WebSocketServerProtocol
from websockets.server import serve as ws_serve


# -------- Utility --------
def validate_username(username: str) -> bool:
    return (
        isinstance(username, str)
        and 3 <= len(username) <= 28
        and all(ch in USERNAME_CHARSET for ch in username)
        and "__" not in username
        and "--" not in username
    )


class FileReadError(Exception): ...
class FileWriteError(Exception): ...


def generate_token() -> str:
    random_bytes = os.urandom(256)
    token = str(b64encode(random_bytes, bytes("-_", 'utf-8')), 'utf-8')
    return token


def hash_password(password: str, username: str) -> str:
    m = hashlib.sha256()
    m.update(bytes(password, 'utf-8'))
    salt1 = bytes("o8i3Sidf/B2", 'utf-8')
    m.update(salt1)
    salt2 = bytes(username[::-1], 'utf-8')
    m.update(salt2)
    password_hash = m.hexdigest()
    return password_hash


def hash_token(token: str) -> str:
    m = hashlib.sha256()
    m.update(bytes(token, 'utf-8'))
    token_hashed = m.hexdigest()
    return token_hashed


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


# -------- Globals --------
# WARNING: ./\ SHOULD NEVER BE ALLOWED FOR PATH SECURITY
USERNAME_CHARSET = set("abcdefghijklmnopqrstuvwxyz-_")
MESSAGE_BATCH_SIZE = 30
ws_clients_by_channel: dict[int, list[WSConnectedClient]] = {}


class HTTPHandler(SimpleHTTPRequestHandler):
    """This handler uses server.base_path instead of always using os.getcwd()"""

    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(self.server.base_path, relpath)
        return fullpath

    def send_error(self, code: int, message: str):
        self.send_response(code)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        response = {"error": message}
        self.wfile.write(bytes(json.dumps(response), "utf8"))

    def read_json_file(
            self,
            file_path: str,
            error_message_notfound: str = "The requested file does not exist.",
            error_message_os: str = "",
            send_errors: bool = True
    ):
        """Tries to read a JSON file in the server backend using the provided absolute `file_path`.\n
        If it fails, it will respond to the HTTP request automatically and then raise a `FileReadError`."""
        try:
            with open(file_path, 'r') as file:
                return json.load(file)

        except FileNotFoundError:
            if send_errors:
                self.send_error(404, error_message_notfound)
            raise FileReadError

        except OSError:
            if error_message_os: error_message_os += ' '
            if send_errors:
                self.send_error(500, f"(Server Error) Could not read {error_message_os}file.")
            raise FileReadError

    def write_json_file(
            self,
            file_path: str,
            json_object,
            error_message_os: str = "",
            create_file: bool = False,
            error_message_already_exists: str = "(Server Error) Did not create {}file because it should already exist."
    ):
        """Tries to write to a JSON file in the server backend using the provided absolute `file_path`.\n
        If `create_file` is False and the file does not already exist,
        it will respond to the HTTP request automatically using `error_message_notfound` and then raise a `FileWriteError`.
        `error_message_notfound` should have curly brackets for formatting stuff.\n
        If it fails because of `OSError`, it will respond to the HTTP request automatically
        using `error_message_os` and then raise a `FileWriteError`."""
        if error_message_os: error_message_os += ' '

        if create_file is False:
            if not os.path.exists(file_path):  # UNTESTED
                self.send_error(500, error_message_already_exists.format(error_message_os))
                raise FileWriteError

        try:
            with open(file_path, 'w') as file:
                json.dump(json_object, file)

        except OSError:
            self.send_error(500, f"(Server Error) Could not write to {error_message_os}file.")
            raise FileWriteError

    def do_POST_register(self):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_error(400, "Content Type should be JSON.")
            return

        try:
            username = post_data["username"]
            displayname = post_data["displayname"]
            password = post_data["password"]
            public_key = post_data["publicKey"]
            assert isinstance(username, str) and isinstance(displayname, str) and isinstance(password, str) and isinstance(public_key, str)
        except (KeyError, AssertionError):
            self.send_error(400,
                            "JSON object needs to have attributes: 'username', 'displayname', 'password', 'publicKey'.")
            return

        if not validate_username(username):
            self.send_error(400,
                            "Username should be a 3-28 character string of alphanumeric characters including - and _")
            return

        if not (1 <= len(displayname) <= 48):
            self.send_error(400, "Display Name should have a length between 1 and 48 characters.")
            return

        if not (1 <= len(password) <= 128):  # TODO maybe only allow (certain?) ascii chars?
            self.send_error(400, "Password should have a length between 1 and 128 characters.")
            return

        if not (32 <= len(public_key) <= 1024):
            self.send_error(400, "Public key should be in Base64-encoded \"raw\" format.")
            return

        user_dir = os.path.join(backend_dir, "accounts", username)
        meta_file = os.path.join(user_dir, "meta.json")

        if os.path.exists(meta_file):
            self.send_error(400, "User already exists.")
            return

        password_hash = hash_password(password, username)
        generated_token = generate_token()
        generated_token_hash = hash_token(generated_token)

        meta = {
            "displayname": displayname,
            "accountCreated": int(time.time()),
            "passwordHash": password_hash,
            "validTokens": [generated_token_hash],
            "deleted": False,
            "publicKey": public_key,
            "channels": {}
        }

        os.makedirs(user_dir)
        try:
            self.write_json_file(meta_file, meta, "user meta", True)
        except FileWriteError:
            return

        # Success! User dir and meta created. Return generated token.
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        response = {'generatedToken': generated_token}
        self.wfile.write(bytes(json.dumps(response), "utf8"))

    def do_POST_login(self):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_error(400, "Content Type should be JSON.")
            return

        try:
            username = post_data["username"]
            password = post_data["password"]
        except KeyError:
            self.send_error(400, "JSON object needs to have attributes: 'username', 'password'.")
            return

        if not validate_username(username):
            self.send_error(400, "Username should a 3-28 character string of alphanumeric characters including - and _")
            return

        if not (1 <= len(password) <= 128):
            self.send_error(400, "Password should have a length between 1 and 128 characters.")
            return

        user_dir = os.path.join(backend_dir, "accounts", username)
        meta_file = os.path.join(user_dir, "meta.json")

        try:
            meta = self.read_json_file(meta_file, "User does not exist.", "user meta")
        except FileReadError:
            return

        stored_password_hash = meta["passwordHash"]
        password_hash = hash_password(password, username)

        if stored_password_hash != password_hash:
            self.send_error(401, "Incorrect password.")
            return

        generated_token = generate_token()
        generated_token_hashed = hash_token(generated_token)
        meta['validTokens'].append(generated_token_hashed)

        try:
            self.write_json_file(meta_file, meta, "user meta", False)
        except FileWriteError:
            return

        # Success! Return generated token
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()

        response = {'generatedToken': generated_token}
        self.wfile.write(bytes(json.dumps(response), "utf8"))

    def do_POST_send_message(self, token: str, username: str):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_error(400, "Content Type should be JSON.")
            return

        if not self.validate_auth(token, username, True):
            return

        try:
            sent_message_text = post_data["text"].strip()
            channel_id = post_data["channel"]
            temp_id = post_data["tempID"]
            assert sent_message_text and channel_id and temp_id and isinstance(sent_message_text, str) and isinstance(channel_id, str) and isinstance(temp_id, str)
        except (KeyError, AssertionError, ValueError):
            self.send_error(400, "JSON object needs to have attributes: 'text', 'channel', 'tempID'.")
            return

        if not 1 <= len(sent_message_text) < 4096:
            self.send_error(400, "Message text should have a length between 1 and 4096.")
            return

        channel_dir = os.path.join(backend_dir, "channels", channel_id)
        channel_meta_file = os.path.join(channel_dir, "meta.json")

        try:
            channel_meta = self.read_json_file(channel_meta_file, "Channel not found.", "channel meta")
        except FileReadError:
            return

        if username not in channel_meta['members']:
            self.send_error(403, "You do not have permission to send messages in this channel!")
            return

        batch_id = channel_meta['latestMessageBatch']
        channel_messages_file = os.path.join(channel_dir, "message_batches", str(batch_id) + ".json")

        try:
            channel_messages = self.read_json_file(channel_messages_file, "Messages batch not found.", "messages batch")
        except FileReadError:
            return

        created_new_batch = False
        if len(channel_messages) >= MESSAGE_BATCH_SIZE:
            created_new_batch = True
            batch_id += 1
            channel_messages_file = os.path.join(channel_dir, "message_batches", str(batch_id) + ".json")
            channel_meta['latestMessageBatch'] = batch_id
            try:
                self.write_json_file(channel_meta_file, channel_meta, "channel meta", False)
            except FileWriteError:
                return
            channel_messages = []

        message_obj = {
            "author": username,
            "text": sent_message_text,
            "timestamp": int(time.time()),
        }
        channel_messages.append(message_obj)

        try:
            self.write_json_file(channel_messages_file, channel_messages, "messages batch", created_new_batch)
        except FileWriteError:
            return

        # Success! Append message to latest message batch (or create a new one if necessary)
        #          Also send message to every connected websocket client of that channel
        if ws_clients_by_channel.get(channel_id) is not None:
            for client in ws_clients_by_channel[channel_id]:
                print(f"Sending message to WS Client {client.username}")

                if client.username == username:
                    message_obj["tempID"] = temp_id
                response_ws = json.dumps(message_obj)
                if client.username == username:
                    del message_obj["tempID"]

                try:
                    asyncio.run(client.sock.send(response_ws))
                except WSConnectionClosed:
                    print(f"WS Connection to {client.username} was closed!")
                # print("DEBUG after send")

        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        response = {}
        self.wfile.write(bytes(json.dumps(response), "utf8"))

    def do_POST_delete_all_other_sessions(self, token: str, username: str):
        if not self.validate_auth(token, username, send_errors=True):
            # self.send_error(401, "Not authorized.")
            return

        user_dir = os.path.join(backend_dir, "accounts", username)
        meta_file = os.path.join(user_dir, "meta.json")

        try:
            user_meta = self.read_json_file(meta_file, "User does not exist.", "user meta")
        except FileReadError:
            return

        user_meta['validTokens'] = [token]

        try:
            self.write_json_file(meta_file, user_meta, "user meta", False)
        except FileWriteError:
            return

        # Success! Deleted all other sessions
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        response = {}
        self.wfile.write(bytes(json.dumps(response), "utf8"))


    def do_POST_create_channel(self, token: str, username: str):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_error(400, "Content Type should be JSON.")
            return

        try:
            channel_name = post_data['channelName'].strip()
            encrypted_channel_key = post_data['encryptedChannelKey']
            channel_key_iv = post_data['iv']
        except (KeyError, ValueError, TypeError):
            self.send_error(400, "Channel Name/Encrypted Channel Key is missing or invalid; should be string")
            return

        if not self.validate_auth(token, username, True):
            return

        channel_id = str(time.time_ns() + random.randint(1, 100))
        channel_dir = os.path.join(backend_dir, "channels", channel_id)
        message_batches_dir = os.path.join(channel_dir, "message_batches")
        current_message_batch_file = os.path.join(message_batches_dir, "1.json")
        channel_meta_file = os.path.join(channel_dir, "meta.json")

        os.mkdir(channel_dir)
        os.mkdir(message_batches_dir)

        channel_meta = {
            "name": channel_name,
            "timestampCreated": int(time.time()),
            "members": [username],
            "latestMessageBatch": 1,
            "deleted": False
        }

        self.write_json_file(channel_meta_file, channel_meta, "channel meta", True)
        self.write_json_file(current_message_batch_file, [], "message batch", True)

        # Successfully created channel! Add user to channel
        user_meta_file = os.path.join(backend_dir, "accounts", username, "meta.json")
        user_meta = self.read_json_file(user_meta_file, "User doesn't exist but literally should because already authorized.", "user meta")
        user_meta['channels'][channel_id] = {
            "encryptedKey": encrypted_channel_key,
            "iv": channel_key_iv
        }
        self.write_json_file(user_meta_file, user_meta, "user meta")

        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        response = {
            "channelID": channel_id
        }

        self.wfile.write(bytes(json.dumps(response), "utf8"))


    def do_POST_delete_channel(self, token: str, username: str):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_error(400, "Content Type should be JSON.")
            return

        try:
            channel_id = post_data['channelID'].strip()
        except (KeyError, ValueError, TypeError):
            self.send_error(400, "Channel Name is missing or invalid; should be string")
            return

        if not self.validate_auth(token, username, True):
            return

        channel_dir = os.path.join(backend_dir, "channels", channel_id)
        channel_meta_file = os.path.join(channel_dir, "meta.json")

        try:
            channel_meta = self.read_json_file(channel_meta_file, "Channel does not exist", "channel meta")
        except FileReadError:
            return

        if username not in channel_meta['members']:
            self.send_error(403, "You do not have permission to delete this channel!")
            return

        if not channel_dir.strip() or len(channel_dir) < 20:
            print("Channel Dir empty somehow; preventing deleting root!")
            return

        try:
            shutil.rmtree(channel_dir)
        except FileNotFoundError:  # channel didn't exist in the first place
            pass

        # Success! Deleted channel. Remove it from every user's meta file as well
        for user in channel_meta['members']:
            user_meta_file = os.path.join(backend_dir, "accounts", user, "meta.json")

            try:
                user_meta = self.read_json_file(user_meta_file, "User does not exist somehow", "user meta", False)
            except FileReadError:   # user doesn't exist for some reason
                print("User doesn't exist??")
                continue

            try:
                del user_meta['channels'][channel_id]
            except KeyError:   # user wasn't in channel for some reason
                print("User wasn't in channel??")
                continue

            try:
                self.write_json_file(user_meta_file, user_meta, "user meta", False)
            except FileWriteError:
                continue


        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        response = {}
        self.wfile.write(bytes(json.dumps(response), "utf8"))


    def do_POST_add_member_to_channel(self, token: str, username: str):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_error(400, "Content Type should be JSON.")
            return

        try:
            channel_id: str = post_data['channelID'].strip()
            new_member: str = post_data['newMember'].strip()
            encrypted_channel_key = post_data['encryptedChannelKey']
            channel_key_iv: str = post_data['iv']
            assert isinstance(channel_id, str) and isinstance(new_member, str) and isinstance(encrypted_channel_key, str) and isinstance(channel_key_iv, str)
            assert validate_username(new_member)
        except (KeyError, ValueError, TypeError, AssertionError):
            self.send_error(400, "Channel Name/New Member is missing or invalid; should be string")
            return

        if not self.validate_auth(token, username, True):
            return

        new_member_meta_file = os.path.join(backend_dir, "accounts", new_member, "meta.json")
        try:
            new_member_meta = self.read_json_file(new_member_meta_file, "Member does not exist!", "member meta")
        except FileReadError:
            return

        if channel_id in new_member_meta['channels'].keys():
            self.send_error(400, "Member is already in the channel!")
            return

        channel_dir = os.path.join(backend_dir, "channels", channel_id)
        channel_meta_file = os.path.join(channel_dir, "meta.json")
        try:
            channel_meta = self.read_json_file(channel_meta_file, "Channel does not exist!", "channel meta")
        except FileReadError:
            return

        if username not in channel_meta['members']:
            self.send_error(403, "You do not have permission to add members to this channel!")
            return

        # if new_member in channel_meta['members']:
        #     self.send_error(400, "Member is already in the channel!")
        #     return

        new_member_meta['channels'][channel_id] = {
            "encryptedKey": encrypted_channel_key,
            "iv": channel_key_iv
        }
        channel_meta['members'].append(new_member)

        try:
            self.write_json_file(new_member_meta_file, new_member_meta, "member meta")
        except FileWriteError:
            return

        try:
            self.write_json_file(channel_meta_file, channel_meta, "channel meta")
        except FileWriteError:
            return

        # Success! Added member to channel
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        response = {}
        self.wfile.write(bytes(json.dumps(response), "utf8"))


    def do_POST_remove_member_from_channel(self, token: str, username: str):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_error(400, "Content Type should be JSON.")
            return

        try:
            channel_id: str = post_data['channelID'].strip()
            member: str = post_data['newMember'].strip()
            assert validate_username(member)
        except (KeyError, ValueError, TypeError, AssertionError):
            self.send_error(400, "Channel Name/New Member is missing or invalid; should be string")
            return

        if not self.validate_auth(token, username, True):
            return

        member_meta_file = os.path.join(backend_dir, "accounts", member, "meta.json")
        try:
            member_meta = self.read_json_file(member_meta_file, "Member does not exist!", "member meta")
        except FileReadError:
            return

        if channel_id not in member_meta['channels'].keys():
            self.send_error(404, "Member is not in the channel in the first place!")
            return

        channel_dir = os.path.join(backend_dir, "channels", channel_id)
        channel_meta_file = os.path.join(channel_dir, "meta.json")
        try:
            channel_meta = self.read_json_file(channel_meta_file, "Channel does not exist!", "channel meta")
        except FileReadError:
            return

        if username not in channel_meta['members']:
            self.send_error(403, "You do not have permission to remove members from this channel!")
            return

        if member not in channel_meta['members']:
            self.send_error(404, "Member is not in the channel in the first place!")
            return

        del member_meta['channels'][channel_id]
        channel_meta['members'].remove(member)

        try:
            self.write_json_file(member_meta_file, member_meta, "member meta")
        except FileWriteError:
            return

        try:
            self.write_json_file(channel_meta_file, channel_meta, "channel meta")
        except FileWriteError:
            return

        # Success! Removed member from channel
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        response = {}
        self.wfile.write(bytes(json.dumps(response), "utf8"))


    def do_POST_delete_account(self, token: str, username: str):
        if not self.validate_auth(token, username, True):
            return

        user_dir = os.path.join(backend_dir, "accounts", username)
        user_meta_file = os.path.join(user_dir, "meta.json")

        try:
            user_meta = self.read_json_file(user_meta_file, "User does not exist.", "user meta")
        except FileReadError:
            return

        # Delete all messages from every channel, then remove them from that channel as well
        for channel in user_meta['channels']:
            channel_dir = os.path.join(backend_dir, "channels", channel)
            channel_meta_file = os.path.join(channel_dir, "meta.json")
            try:
                channel_meta = self.read_json_file(channel_meta_file, "Channel does not exist somehow", "channel meta", False)
            except FileReadError:   # channel doesn't exist for some reason
                continue

            for batch_number in range(channel_meta['latestMessageBatch'], 1, -1):
                message_batch_file = os.path.join(channel_dir, "message_batches", f"{batch_number}.json")
                try:
                    message_batch = self.read_json_file(message_batch_file, "Message batch does not exist somehow", "message batch")
                except FileReadError:
                    return

                message_batch = [message for message in message_batch if message['author'] != username]

                try:
                    self.write_json_file(message_batch_file, message_batch, "message batch")
                except FileWriteError:
                    return

            try:
                channel_meta['members'].remove(username)
            except ValueError:   # user wasn't in channel for some reason
                continue

            try:
                self.write_json_file(channel_meta_file, channel_meta, "channel meta", False)
            except FileWriteError:
                continue

        # Purge user meta
        user_meta = {
            "displayname": "Deleted User",
            "accountCreated": 0,
            "passwordHash": " ",
            "validTokens": [],
            "channels": [],
            "publicKey": " ",
            "deleted": True,
        }

        try:
            self.write_json_file(user_meta_file, user_meta, "user meta")
        except FileWriteError:
            return

        # Success! Deleted account.
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        response = {}
        self.wfile.write(bytes(json.dumps(response), "utf8"))



    def do_POST(self):
        print("[POST]", self.path)

        cookies = SimpleCookie(self.headers.get('Cookie'))
        try:
            token = cookies['token'].value
            username = cookies['username'].value
            assert validate_username(username)
        except (AssertionError, KeyError):
            token = None
            username = None

        if self.path == "/register":
            self.do_POST_register()
        elif self.path == "/login":
            self.do_POST_login()
        elif self.path == "/send_message":
            self.do_POST_send_message(token, username)
        elif self.path == "/logout_all_other_sessions":
            self.do_POST_delete_all_other_sessions(token, username)
        elif self.path == "/create_channel":
            self.do_POST_create_channel(token, username)
        elif self.path == "/delete_channel":
            self.do_POST_delete_channel(token, username)
        elif self.path == "/add_member_to_channel":
            self.do_POST_add_member_to_channel(token, username)
        elif self.path == "/remove_member_from_channel":
            self.do_POST_remove_member_from_channel(token, username)
        elif self.path == "/delete_account":
            self.do_POST_delete_account(token, username)
        else:
            self.send_error(404, "Invalid post URI.")
            return

    def do_GET_channels(self, path: str, query_components: dict, token: str, username: str):
        regex_match = re.match(r"/channels/(\d+)(/?|/messages/?|/about/?)$", path)
        if regex_match is None:
            self.send_error(400, "Invalid channel ID or URI.")
            return

        channel_id, sub = regex_match.groups()
        if not all(ch in "0123456789" for ch in channel_id):
            self.send_error(400, "Invalid channel ID.")

        sub = "" if sub is None else sub.strip("/")
        channel_dir = os.path.join(backend_dir, "channels", channel_id)

        if not sub:
            if not self.validate_auth(token, username):
                self.send_response(303)
                self.send_header('Location', "/login.html")
                # self.send_header('Content-Type', "text/json")
                self.end_headers()

                response = {}
                self.wfile.write(bytes(json.dumps(response), "utf8"))
                return

            self.path = "/index.html"
            try:
                super().do_GET()
            except ConnectionAbortedError:
                print("Connection was aborted while trying to super().do_GET()")
            return

        if not self.validate_auth(token, username, True):
            # self.send_error(401, "Not authorized.")
            return

        channel_meta_file = os.path.join(channel_dir, "meta.json")
        try:
            channel_meta = self.read_json_file(channel_meta_file, "Channel not found.", "channel meta")
        except FileReadError:
            return

        if username not in channel_meta['members']:
            self.send_error(403, "You don't have permission to view this channel.")
            return

        if sub == "about":
            self.do_GET_channels_about(query_components, channel_dir)
        elif sub == "messages":
            self.do_GET_channel_messages(query_components, channel_dir)
        else:
            self.send_error(404, "This error can only happen if the regex is messed up.")
            return

    def do_GET_channels_about(self, query_components: dict, channel_dir):
        channel_meta_file = os.path.join(channel_dir, "meta.json")

        try:
            channel_meta = self.read_json_file(channel_meta_file, "Channel not found.", "channel meta")
        except FileReadError:
            return

        # Success, send channel about
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()

        response = channel_meta
        self.wfile.write(bytes(json.dumps(response), "utf8"))

    def do_GET_channel_messages(self, query_components: dict, channel_dir: str):
        try:
            batch_id = int(query_components['batch'])
        except (ValueError, KeyError):
            self.send_error(400, "Invalid or unspecified messages batch ID.")
            return

        channel_messages_file = os.path.join(channel_dir, "message_batches", str(batch_id) + ".json")

        try:
            channel_messages = self.read_json_file(channel_messages_file, "Message batch not found.", "messages batch")
        except FileReadError:
            return

        # Success! Send channel messages
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()

        response = channel_messages
        self.wfile.write(bytes(json.dumps(response), "utf8"))

    def do_GET_users(self, path: str, query_components: dict, token: str, username: str):
        regex_match = re.match(r"/users/([A-Za-z0-9\-_]{3,28})(/|/about/?)?$", path)
        if regex_match is None:
            self.send_error(400, "Invalid URI.")
            return

        target_username, sub = regex_match.groups()
        sub = "" if sub is None else sub.strip("/")

        if not sub:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            message = "<h1>This is not yet implemented!</h1>"
            self.wfile.write(bytes(message, 'utf-8'))

        elif sub == "about":
            self.do_GET_users_about(token, username, target_username)

    def do_GET_users_about(self, token: str, username: str, target_username: str):
        account_dir = os.path.join(backend_dir, "accounts", target_username)
        user_meta_file = os.path.join(account_dir, "meta.json")

        if not validate_username(target_username):
            self.send_error(400, "Invalid username.")
            return

        if not self.validate_auth(token, username):
            return

        try:
            user_meta_private = self.read_json_file(user_meta_file, "User not found.", "user meta")
        except FileReadError:
            return

        # Success! Send (filtered) account meta
        if username == target_username:
            user_meta_public = user_meta_private
        else:
            keys_filter = ['displayname', 'accountCreated', 'deleted', 'publicKey']
            user_meta_public = {key: value for key, value in user_meta_private.items() if key in keys_filter}

        self.send_response(200)
        self.send_header("Content-Type", "text/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(user_meta_public), 'utf-8'))

    def do_GET_self_channels(self, token: str, username: str):
        if not self.validate_auth(token, username, True):
            return

        user_meta_file = os.path.join(backend_dir, "accounts", username, "meta.json")
        try:
            user_meta = self.read_json_file(user_meta_file, "There is no user associated with this username.", "user meta")
        except FileReadError:
            return

        channel_names: dict[str, str] = {}

        # Get names of all channels
        for channel_id in user_meta['channels']:
            channel_meta_file = os.path.join(backend_dir, "channels", channel_id, "meta.json")
            try:
                with open(channel_meta_file, 'r') as file:
                    channel_meta = json.load(file)

            except (FileNotFoundError, OSError):
                channel_name = "Unknown Channel"
            else:
                channel_name = channel_meta["name"]

            channel_names[channel_id] = channel_name

        self.send_response(200)
        self.send_header("Content-Type", "text/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(channel_names), 'utf-8'))

    def do_GET(self):
        cookies = SimpleCookie(self.headers.get('Cookie'))
        try:
            token = cookies['token'].value
            username = cookies['username'].value
        except KeyError:
            token = None
            username = None

        query = urlparse(self.path).query
        path = urlparse(self.path).path
        if query:
            query_components = dict(qc.split("=") for qc in query.split("&"))
        else:
            query_components = {}

        print("GET", self.path, query_components)

        if path in {"/login.html", "/register.html"} and token is not None:
            self.send_response(303)
            self.send_header('Location', "/")  # redirect to index if already logged in TODO ??? index is nor
            self.send_header('Content-Type', "text/json")
            self.end_headers()

            response = {}
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        if path.startswith("/channels/"):
            self.do_GET_channels(path, query_components, token, username)
            return

        if path.startswith("/users/"):
            self.do_GET_users(path, query_components, token, username)
            return

        if path == "/get_self_channels":
            self.do_GET_self_channels(token, username)
            return

        try:
            super().do_GET()
        except ConnectionAbortedError:
            print("Connection was aborted while trying to super().do_GET()")

    def validate_auth(self, token: str, username: str, send_errors: bool=False) -> bool:
        send_error = self.send_error if send_errors else lambda *_: None

        if token is None or username is None:
            send_error(401, "Not authorized. Please provide token and username.")
            return False

        user_meta_file = os.path.join(backend_dir, "accounts", username, "meta.json")

        try:
            with open(user_meta_file, 'r') as file:
                user_meta = json.load(file)

        except FileNotFoundError:
            send_error(401, "There is no user associated with this username.")
            return False

        except OSError:
            send_error(500, "(Server Error) Could not read user meta file.")
            return False

        token_hashed = hash_token(token)
        for valid_token_hash in user_meta['validTokens']:
            if token_hashed == valid_token_hash:
                break
        else:
            send_error(401, "Invalid token.")
            return False

        return True


class HTTPServer(BaseHTTPServer):
    """The main server, you pass in base_path which is the path you want to serve requests from"""

    def __init__(self, base_path, server_address, RequestHandlerClass=HTTPHandler):
        self.base_path = base_path
        BaseHTTPServer.__init__(self, server_address, RequestHandlerClass)


web_dir = os.path.join(os.path.dirname(__file__), "../frontend_files")
backend_dir = os.path.join(os.path.dirname(__file__), "../backend_files")
httpd = HTTPServer(web_dir, ("", 8000))

if __name__ == "__main__":
    print("Started.")
    # v TODO less disgusting?????
    threading.Thread(target=asyncio.run, args=(ws_main(),), daemon=True).start()
    httpd.serve_forever()
