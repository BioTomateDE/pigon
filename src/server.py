import datetime
from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
import os
import json
import re
import time
import hashlib
from urllib.parse import urlparse
import uuid
import bs4


# -------- Globals --------
# WARNING: / or \ SHOULD NEVER BE ALLOWED FOR PATH SECURITY
USERNAME_CHARSET = set("abcdefghijklmnopqrstuvwxyz-_")
MESSAGE_BATCH_SIZE = 30


# -------- Utility --------
def validate_username(username: str) -> bool:
    return (
        3 <= len(username) <= 28
        and all(ch in USERNAME_CHARSET for ch in username)
        and "__" not in username
        and "--" not in username
    )
    

def generate_token() -> str:
    token = uuid.uuid4().hex
    return token

    
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


    def do_POST_register(self, token:str, username:str):
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

        try:
            with open(meta_file, "r") as file:
                pass

        except FileNotFoundError:
            pass
        else:
            self.send_error(400, "User already exists.")
            return
        
        # Success! Create user
        m = hashlib.sha256()
        m.update(bytes(password, 'utf-8'))
        # TODO salting?
        #m.update(salt)
        password_hash = m.hexdigest()
        
        meta = {
            "displayname": displayname,
            "accountCreated": int(time.time()),
            "passwordHash": password_hash,
            "validTokens": [],
        }

        os.makedirs(user_dir)
        with open(meta_file, "w") as file:
            json.dump(meta, file, indent=4)

        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()

        response = {}
        self.wfile.write(bytes(json.dumps(response), "utf8"))


    def do_POST_login(self, token: str, username: str):
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
            with open(meta_file, "r") as file:
                meta = json.load(file)

        except FileNotFoundError:
            self.send_error(404, "User does not exist.")
            return

        stored_password_hash = meta["passwordHash"]
        m = hashlib.sha256()
        m.update(bytes(password, 'utf-8'))
        password_hash = m.hexdigest()

        if stored_password_hash != password_hash:
            self.send_error(401, "Incorrect password.")
            return

        # Success! Return generated token
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        
        generated_token = generate_token()
        m = hashlib.sha256()
        m.update(bytes(generated_token, 'utf-8'))
        generated_token_hashed = m.hexdigest()
        meta['validTokens'].append(generated_token_hashed)
        
        with open(meta_file, 'w') as file:
            json.dump(meta, file, indent=4)

        response = {'generatedToken': generated_token}
        self.wfile.write(bytes(json.dumps(response), "utf8"))

    
    def do_POST_send_message(self, token:str, username:str):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_error(400, "Content Type should be JSON.")

        
        if not self.validate_auth(token, username, False):
            return

        try:
            sent_message_text = post_data["text"].strip()
            channel_id = post_data["channel"]
        except KeyError:
            self.send_error(400, "JSON object needs to have attributes: 'text', 'channel'.")
    
        if not 1 <= len(sent_message_text) < 4096:
            self.send_error(400, "Message text should have a length between 1 and 4096.")
        
        
        channel_dir = os.path.join(backend_dir, "channels", str(channel_id))
        channel_meta_file = os.path.join(channel_dir, "meta.json")
        
        try:
            with open(channel_meta_file, 'r') as file:
                channel_meta = json.load(file)
                
        except OSError:
            self.send_error(500, "(Server Error) Could not read channel meta file.")
            return
        
        except FileNotFoundError:
            self.send_error(404, "Channel not found.")
            return
        
        
        batch_id = channel_meta['latestMessageBatch']
        channel_messages_file = os.path.join(channel_dir, "message_batches", str(batch_id)+".json")
        
        try:
            with open(channel_messages_file, 'r') as file:
                channel_messages = json.load(file)
                
        except FileNotFoundError:
            self.send_error(404, "Channel messages batch file not found. Could be a permanent server issue lol")
            return
    
        except OSError:
            self.send_error(500, "(Server Error) Could not read channel messages file.")
            return
        
        if len(channel_messages) >= MESSAGE_BATCH_SIZE:
            batch_id += 1
            channel_messages_file = os.path.join(channel_dir, "message_batches", str(batch_id)+".json")
            channel_meta['latestMessageBatch'] = batch_id
            try:
                with open(channel_meta_file, 'w') as file:
                    json.dump(channel_meta, file, indent=4)
            except OSError:
                self.send_error(500, "(Server Error) Could not write to channel meta file.")
            channel_messages = []
        
        message_obj = {
            "author": username,
            "text": sent_message_text,
            "timestamp": int(time.time()),
        }
        channel_messages.append(message_obj)
        
        try:
            with open(channel_messages_file, 'w') as file:
                json.dump(channel_messages, file, indent=4)
        except OSError:
            # i hate handling these retarded errors
            # it would have to reset the meta file potentially (which could also OSError)
            self.send_error(500, "(Server Error) Could not write to channel messages file.")
            return

        # Success! Append message to latest message batch (or create a new one if necessary)
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
            self.do_POST_register(token=token, username=username)
        elif self.path == "/login":
            self.do_POST_login(token=token, username=username)
        elif self.path == "/send_message":
            self.do_POST_send_message(token=token, username=username)
        else:
            self.send_error(404, "Invalid post URI.")
    
    
    def do_GET_channels(self, path:str, query_components:dict, token:str, username:str):
        regex_match = re.match(r"/channels/(\d+)(/|/messages/?|/about/?)?$", path)
        if regex_match is None:
            self.send_error(400, "Invalid channel ID.")
            return
        
        channel_id, sub = regex_match.groups()
        sub = "" if sub == None else sub.strip("/")
        
        if not self.validate_auth(token, username, True):
            return
        
        if not sub:
            self.path = "/index.html"
            super().do_GET()
            return
        
        if sub == "about":
            self.do_GET_channels_about(query_components, channel_id)
        elif sub == "messages":
            self.do_GET_channel_messages(query_components, channel_id)
        else:
            self.send_error(404, "This error can only happen if the regex is messed up.")
    
    
    def do_GET_channels_about(self, query_components:dict, channel_id:int):
        channel_dir = os.path.join(backend_dir, "channels", str(channel_id))
        channel_meta_file = os.path.join(channel_dir, "meta.json")
        
        try:
            with open(channel_meta_file, 'r') as file:
                channel_meta = json.load(file)
        
        except FileNotFoundError:
            self.send_error(404, "Channel not found.")
            return

        except OSError:
            self.send_error(500, "(Server Error) Could not read channel meta file.")
            return
                        
        # Success, send channel about
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        
        response = channel_meta
        self.wfile.write(bytes(json.dumps(response), "utf8"))
    
    
    def do_GET_channel_messages(self, query_components:dict, channel_id:int):
        try:
            batch_id = int(query_components['batch'])
        except (ValueError, KeyError):
            self.send_error(400, "Invalid or unspecified messages batch ID.")
            return
        
        channel_dir = os.path.join(backend_dir, "channels", str(channel_id))
        channel_messages_file = os.path.join(channel_dir, "message_batches", str(batch_id) + ".json")
        
        try:
            with open(channel_messages_file, 'r') as file:
                channel_messages = json.load(file)
                
        except FileNotFoundError:
            self.send_error(404, "Channel not found or invalid message batch ID.")
            return
    
        except OSError:
            self.send_error(500, "(Server Error) Could not read channel messages file.")
            return
        
        
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
        account_meta_file = os.path.join(account_dir, "meta.json")
        
        try:
            with open(account_meta_file, 'r') as file:
                account_meta_private = json.load(file)
                
        except FileNotFoundError:
            self.send_error(404, "User does not exist.")
            return
        
        except OSError:
            self.send_error(500, "(Server Error)  Could not read user meta file.")
            return
        
        # Success! Send filtered account meta
        keys_filter = ['displayname', 'accountCreated']
        account_meta_public = {key:value for key,value in account_meta_private.items() if key in keys_filter}
        
        self.send_response(200)
        self.send_header("Content-Type", "text/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(account_meta_public), 'utf-8'))
    
    
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


        super().do_GET()
    
    
    def validate_auth(self, token:str, username:str, redirect_if_not_exist:bool) -> bool:
        if token is None or username is None:
            if redirect_if_not_exist:
                self.send_response(303)
                self.send_header('Location', "/login.html")  # redirect to login.html if not logged in
                self.send_header('Content-Type', "text/json")
                self.end_headers()
                response = {}
            else:
                self.send_error(401, "Not authorized. Please provide token and username.")
                
            self.wfile.write(bytes(json.dumps(response), "utf8"))
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
    httpd.serve_forever()
