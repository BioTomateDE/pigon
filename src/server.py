from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
import os
import json
import time
import hashlib
import uuid


# -------- Globals --------
# WARNING: / or \ SHOULD NEVER BE ALLOWED FOR PATH SECURITY
USERNAME_CHARSET = set("abcdefghijklmnopqrstuvwxyz-_")


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

    def _respond_bad(self):
        self.send_response(400)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        # message = "Bad Request"
        # self.wfile.write(bytes(message, "utf8"))

    def do_POST_register(self, token):
        if token is not None:
            self.send_response(303)
            self.send_header('Location', "/")  # redirect to index if already logged in
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            
            response = {}
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return
        
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Content Type should be JSON.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        try:
            username = post_data["username"]
            displayname = post_data["displayname"]
            password = post_data["password"]
        except KeyError:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "JSON object needs to have attributes: 'username', 'displayname', 'password'.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        if not validate_username(username):
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Username should be a 3-28 character string of alphanumeric characters including '-' and '_'. There should be no consecutive hyphens or underscores.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        if not (1 <= len(displayname) <= 48):
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Display Name should be a 1-48 character string.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        if not (1 <= len(password) <= 128):  # TODO maybe only (certain) ascii chars?
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Password should be a 1-128 character string.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        user_dir = os.path.join(backend_dir, "accounts", username)
        meta_file = os.path.join(user_dir, "meta.json")

        try:
            with open(meta_file, "r") as file:
                pass

        except FileNotFoundError:
            pass
        else:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "User already exists.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return
        
        # Success!
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


    def do_POST_login(self, token: str):
        if token is not None:
            self.send_response(303)
            self.send_header('Location', "/")  # redirect to index if already logged in
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            
            response = {}
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return
        
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Content Type should be JSON.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        try:
            username = post_data["username"]
            password = post_data["password"]
        except KeyError:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "JSON object needs to have attributes: 'username', 'password'.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        if not validate_username(username):
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Username should a 3-28 character string of alphanumeric characters including '-' and '_'.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        if not (1 <= len(password) <= 128):
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Password should be a 1-128 character string.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        user_dir = os.path.join(backend_dir, "accounts", username)
        meta_file = os.path.join(user_dir, "meta.json")

        try:
            with open(meta_file, "r") as file:
                meta = json.load(file)

        except FileNotFoundError:
            self.send_response(404)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "User not found.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        # Success!
        stored_password_hash = meta["passwordHash"]
        m = hashlib.sha256()
        m.update(bytes(password, 'utf-8'))
        password_hash = m.hexdigest()

        if stored_password_hash != password_hash:
            self.send_response(401)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Incorrect password.",
            }
            message = json.dumps(response)
            self.wfile.write(bytes(message, "utf8"))
            return

        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        
        generated_token = generate_token()
        meta['validTokens'].append(generated_token)
        
        with open(meta_file, 'w') as file:
            json.dump(meta, file, indent=4)

        response = {'generatedToken': generated_token}
        self.wfile.write(bytes(json.dumps(response), "utf8"))


    def do_POST(self):
        print("[POST]", self.path)
        
        cookies = SimpleCookie(self.headers.get('Cookie'))
        try:
            token = cookies['token'].value
        except KeyError:
            token = None

        if self.path == "/register":
            self.do_POST_register(token)
        elif self.path == "/login":
            self.do_POST_login(token)
        elif self.path == "/send_message":
            self.do_POST_send_message(token)
        else:
            self.send_response(404)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {'error': "Invalid post URI!"}
            self.wfile.write(bytes(json.dumps(response), "utf8"))
    
    
    def do_GET(self):
        cookies = SimpleCookie(self.headers.get('Cookie'))
        try:
            token = cookies['token'].value
        except KeyError:
            token = None
        
        if self.path == "/login.html" and token is not None:
            self.send_response(303)
            self.send_header('Location', "/")  # redirect to index if already logged in
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            
            response = {}
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        super().do_GET()


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
