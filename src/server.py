from base64 import b64encode
import datetime
from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
import os
import json
import re
import threading
import time
import hashlib
from urllib.parse import urlparse
import uuid
import asyncio
from websockets import ConnectionClosed, WebSocketServerProtocol
from websockets.server import serve as ws_serve


# -------- Utility --------
def validate_username(username: str) -> bool:
    return (
        3 <= len(username) <= 28
        and all(ch in USERNAME_CHARSET for ch in username)
        and "__" not in username
        and "--" not in username
    )


class FileReadError(Exception): ...
class FileWriteError(Exception): ...

def generate_token() -> str:
    random_bytes = os.urandom(128)
    token = str(b64encode(random_bytes, bytes("-_", 'utf-8')), 'utf-8')
    return token


def hash_password(password:str, username:str) -> str:
    m = hashlib.sha256()
    m.update(bytes(password, 'utf-8'))
    salt1 = bytes("o8i3Sidf/B2", 'utf-8')
    m.update(salt1)
    salt2 = bytes(username[::-1], 'utf-8')
    m.update(salt2)
    password_hash = m.hexdigest()
    print(password_hash)
    return password_hash


def hash_token(token:str) -> str:
    m = hashlib.sha256()
    m.update(bytes(token, 'utf-8'))
    token_hashed = m.hexdigest()
    return token_hashed


class WSConnectedClient:
    def __init__(self, sock:WebSocketServerProtocol, username:str, token:str, channel_id:int) -> None:
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
                channel_id = int(channel_id)
                assert len(username) <= 28 and channel_id >= 0
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
        
    except ConnectionClosed:
        print("Client disconnected:", sock.id)


async def ws_main():
    print("Started Websocket server.")
    async with ws_serve(ws_client_connect, "0.0.0.0", 8982):
        await asyncio.Future()


# -------- Globals --------
# WARNING: / or \ SHOULD NEVER BE ALLOWED FOR PATH SECURITY
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

    def send_error(self, code:int, message:str):
        self.send_response(code)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        response = {"error": message}
        self.wfile.write(bytes(json.dumps(response), "utf8"))
    
    
    def read_json_file(
        self,
        file_path:str,
        error_message_notfound: str = "The requested file does not exist.",
        error_message_os: str = ""
        ):
        """Tries to read a JSON file in the server backend using the provided absolute `file_path`.\n
        If it fails, it will respond to the HTTP request automatically and then raise a `FileReadError`."""
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        
        except FileNotFoundError:
            self.send_error(404, error_message_notfound)
            raise FileReadError
        
        except OSError:
            if error_message_os: error_message_os += ' '
            self.send_error(500, f"(Server Error) Could not read {error_message_os}file.")
            raise FileReadError
        
        
    def write_json_file(
        self,
        file_path: str,
        json_object,
        error_message_os: str = "",
        create_file: bool = False,
        error_message_notfound: str = "(Server Error) Did not create {}file because it should already exist."
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
                self.send_error(500, error_message_notfound.format(error_message_os))
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
        except KeyError:
            self.send_error(400, "JSON object needs to have attributes: 'username', 'displayname', 'password'.")
            return

        if not validate_username(username):
            self.send_error(400, "Username should be a 3-28 character string of alphanumeric characters including - and _")
            return

        if not (1 <= len(displayname) <= 48):
            self.send_error(400, "Display Name should have a length between 1 and 48 characters.")
            return

        if not (1 <= len(password) <= 128):  # TODO maybe only (certain) ascii chars?
            self.send_error(400, "Password should have a length between 1 and 128 characters.")
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
        }

        os.makedirs(user_dir)
        try:
            self.write_json_file(meta_file, meta, "user meta", True)
        except FileWriteError: return
        
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
            self.wfile.write(bytes(json.dumps(response), "utf8"))
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
        except FileReadError: return

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
        except FileWriteError: return
        
        # Success! Return generated token
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()

        response = {'generatedToken': generated_token}
        self.wfile.write(bytes(json.dumps(response), "utf8"))

    
    def do_POST_send_message(self, token:str, username:str):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_error(400, "Content Type should be JSON.")
            return
        
        if not self.validate_auth(token, username):
            return
        
        try:
            sent_message_text = post_data["text"].strip()
            channel_id = post_data["channel"]
            temp_id = post_data["tempID"]
            assert sent_message_text and channel_id and temp_id
        except (KeyError, AssertionError):
            self.send_error(400, "JSON object needs to have attributes: 'text', 'channel', 'tempID'.")
            return
    
        if not 1 <= len(sent_message_text) < 4096:
            self.send_error(400, "Message text should have a length between 1 and 4096.")
            return
        
        
        channel_dir = os.path.join(backend_dir, "channels", str(channel_id))
        channel_meta_file = os.path.join(channel_dir, "meta.json")
        
        # print(channel_meta_file)
        try:
            channel_meta = self.read_json_file(channel_meta_file, "Channel not found.", "channel meta")
        except FileReadError: return
        
        
        batch_id = channel_meta['latestMessageBatch']
        channel_messages_file = os.path.join(channel_dir, "message_batches", str(batch_id)+".json")
        
        try:
            channel_messages = self.read_json_file(channel_messages_file, "Messages batch not found.", "messages batch")
        except FileReadError: return
        
        created_new_batch = False
        if len(channel_messages) >= MESSAGE_BATCH_SIZE:
            created_new_batch = True
            batch_id += 1
            channel_messages_file = os.path.join(channel_dir, "message_batches", str(batch_id)+".json")
            channel_meta['latestMessageBatch'] = batch_id
            try:
                self.write_json_file(channel_meta_file, channel_meta, "channel meta", False)
            except FileWriteError: return
            channel_messages = []
        
        message_obj = {
            "author": username,
            "text": sent_message_text,
            "timestamp": int(time.time()),
        }
        channel_messages.append(message_obj)
        
        try:
            self.write_json_file(channel_messages_file, channel_messages, "messages batch", created_new_batch)
        except FileWriteError: return

        # Success! Append message to latest message batch (or create a new one if necessary)
        #          Also send message to every connected websocket client of that channel
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        
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
                except ConnectionClosed:
                    print(f"WS Connection to {client.username} was closed!")
                # print("DEBUG after send")

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
            self.do_POST_send_message(token=token, username=username)
        else:
            self.send_error(404, "Invalid post URI.")
            return
    
    
    def do_GET_channels(self, path:str, query_components:dict, token:str, username:str):
        regex_match = re.match(r"/channels/(\d+)(/|/messages/?|/about/?)?$", path)
        if regex_match is None:
            self.send_error(400, "Invalid channel ID or URI.")
            return
       
        channel_id, sub = regex_match.groups()
        try:
            channel_id = int(channel_id)
        except ValueError:
            self.send_error(400, "Invalid channel ID.")
            
        sub = "" if sub == None else sub.strip("/")
        channel_dir = os.path.join(backend_dir, "channels", str(channel_id))
        
        if not self.validate_auth(token, username):
            return
        
        if not sub:
            self.path = "/index.html"
            super().do_GET()
            return
        
        channel_meta_file = os.path.join(channel_dir, "meta.json")
        try:
            channel_meta = self.read_json_file(channel_meta_file, "Channel not found.", "channel meta")
        except FileReadError: return
        
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
    
    
    def do_GET_channels_about(self, query_components:dict, channel_dir):
        channel_meta_file = os.path.join(channel_dir, "meta.json")
        
        try:
            channel_meta = self.read_json_file(channel_meta_file, "Channel not found.", "channel meta")
        except FileReadError: return
                        
        # Success, send channel about
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        
        response = channel_meta
        self.wfile.write(bytes(json.dumps(response), "utf8"))
    
    
    def do_GET_channel_messages(self, query_components:dict, channel_dir:str):
        try:
            batch_id = int(query_components['batch'])
        except (ValueError, KeyError):
            self.send_error(400, "Invalid or unspecified messages batch ID.")
            return
        
        channel_messages_file = os.path.join(channel_dir, "message_batches", str(batch_id) + ".json")
        
        try:
            channel_messages = self.read_json_file(channel_messages_file, "Message batch not found.", "messages batch")
        except FileReadError: return
        
        
        # Success! Send channel messages
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        
        response = channel_messages
        self.wfile.write(bytes(json.dumps(response), "utf8"))
    
    
    def do_GET_users(self, path:str, query_components:dict, token:str, username:str):
        regex_match = re.match(r"/users/([A-Za-z0-9\-_]{3,28})(/|/about/?)?$", path)
        if regex_match is None:
            self.send_error(400, "Invalid URI.")
            return
        
        target_username, sub = regex_match.groups()
        sub = "" if sub == None else sub.strip("/")
        
        if not sub:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            message = "<h1>This is not yet implemented!</h1>"
            self.wfile.write(bytes(message, 'utf-8'))
        
        elif sub == "about":
            self.do_GET_users_about(target_username)
    
    
    def do_GET_users_about(self, target_username: str):
        account_dir = os.path.join(backend_dir, "accounts", target_username)
        user_meta_file = os.path.join(account_dir, "meta.json")
        
        try:
            user_meta_private = self.read_json_file(user_meta_file, "User not found.", "user meta")
        except FileReadError: return
        
        # Success! Send filtered account meta
        keys_filter = ['displayname', 'accountCreated', 'deleted']
        user_meta_public = {key:value for key,value in user_meta_private.items() if key in keys_filter}
        
        self.send_response(200)
        self.send_header("Content-Type", "text/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(user_meta_public), 'utf-8'))
    
    
    def do_GET_self_channels(self, token:str, username:str):
        if not self.validate_auth(token, username):
            return
        
        user_meta_file = os.path.join(backend_dir, "accounts", username, "meta.json")
        try:
            user_meta = self.read_json_file(user_meta_file, "There is no user associated with this username.", "user meta")
        except FileReadError: return
        
        channel_names: dict[int, str] = {}
        
        # Get names of all channels
        for channel_id in user_meta['channels']:
            channel_meta_file = os.path.join(backend_dir, "channels", str(channel_id), "meta.json")
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

        super().do_GET()
    
    
    def validate_auth(self, token:str, username:str) -> bool:
        if token is None or username is None:
            self.send_error(401, "Not authorized. Please provide token and username.")
            return False
        
        user_meta_file = os.path.join(backend_dir, "accounts", username, "meta.json")
        
        try:
            with open(user_meta_file, 'r') as file:
                user_meta = json.load(file)
        
        except FileNotFoundError:
            self.send_error(401, "There is no user associated with this username.")
            return False
    
        except OSError:
            self.send_error(500, "(Server Error) Could not read user meta file.")
            return False
        
        m = hashlib.sha256()
        m.update(bytes(token, 'utf-8'))
        token_hashed = m.hexdigest()
        for valid_token_hash in user_meta['validTokens']:
            if token_hashed == valid_token_hash:
                break
        else:
            self.send_error(401, "Invalid token.")
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
