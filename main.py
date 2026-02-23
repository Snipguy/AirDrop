import socket
from flask import Flask, request, redirect, url_for, session, jsonify, abort, send_file
from flask_socketio import SocketIO, emit
import pyperclip
import os, re, datetime
import winsound
import secrets
import qrcode
import io



from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# ---------------- CONFIG ---------------
APP_PIN = input("Set access PIN for phone:").strip()
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
# app.secret_key =  input("Set session password: ")
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

socketio = SocketIO(app, async_mode="threading")



# generate one-time session token
SESSION_TOKEN = secrets.token_urlsafe(16)

# ---------------- HTTPS CERT ----------------
def generate_cert():
    if os.path.exists("key.pem") and os.path.exists("cert.pem"):
        return "cert.pem", "key.pem"

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"MyApp"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"MyApp LAN"),
    ])
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(
        key.public_key()
    ).serial_number(x509.random_serial_number()).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).sign(key, hashes.SHA256(), default_backend())

    with open("key.pem", "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    with open("cert.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    return "cert.pem", "key.pem"

cert_file, key_file = generate_cert()

# ---------------- LOGIN ----------------

@app.route("/qr")
def show_qr():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    url = f"https://{local_ip}:5000/connect?token={SESSION_TOKEN}"

    img = qrcode.make(url)

    file_path = "./qr/connect_qr.png"

    img.save(file_path, format="PNG")

    print("\nQR Saved:", os.path.abspath(file_path))
    print("Open this URL on phone: ", url)
    

    return send_file(file_path, mimetype="image/png")


@app.route("/connect")
def connect():
    token = request.args.get("token")

    if token != SESSION_TOKEN:
        abort(403)

    return "Connected to session!"


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")

        if password == APP_PIN:
            session["logged_in"] = True
            return redirect(url_for("send_page"))
        else:
            return "Wrong PIN"

    return '''
    <html>
    <body style="background:#121212;color:white;text-align:center;padding:40px;">
        <h2>Enter PIN</h2>
        <form method="POST">
            <input type="password" name="password" placeholder="Enter PIN">
            <button type="submit">Unlock</button>
        </form>
    </body>
    </html>
    '''


# @app.route("/", methods=["GET", "POST"])
# def login():
#     if request.method == "POST":
#         password = request.form.get("password")
#         if password == app.secret_key:
#             session["logged_in"] = True
#             return redirect(url_for("send_page"))
#         else:
#             return "Wrong password"
#     return '''
#     <html>
#     <head>
#         <meta name="viewport" content="width=device-width, initial-scale=1">
#         <style>
#             body { font-family: 'Segoe UI', sans-serif; background:#121212; color:white; text-align:center; padding:40px;}
#             .card { background:#1e1e1e; padding:30px; border-radius:20px; box-shadow:0 0 25px rgba(0,0,0,0.6);}
#             input, button { width:100%; padding:15px; margin-top:10px; border-radius:12px; border:none; font-size:18px;}
#             button { font-weight:bold; }
#             button:hover { opacity:0.85; transition:0.2s; }
#         </style>
#     </head>
#     <body>
#         <div class="card">
#             <h2>Login</h2>
#             <form method="POST">
#                 <input type="password" name="password" placeholder="Enter password">
#                 <button type="submit">Login</button>
#             </form>
#         </div>
#     </body>
#     </html>
#     '''

# ---------------- SEND PAGE ----------------
@app.route("/send", methods=["GET"])
def send_page():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return '''
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family:'Segoe UI', sans-serif; background:#121212; color:white; padding:20px;}
            .card { background:#1e1e1e; padding:25px; border-radius:20px; box-shadow:0 0 20px rgba(0,0,0,0.6);}
            textarea { width:100%; height:120px; padding:10px; border-radius:12px; border:none; background:#2a2a2a; color:white; font-size:16px;}
            .button { width:100%; padding:14px; border:none; border-radius:12px; margin-top:10px; font-weight:bold; font-size:18px; cursor:pointer; }
            .send { background:#00c853; color:white; }
            .upload { background:#2962ff; color:white; }
            .logout { background:#d50000; color:white; }
            button:hover { opacity:0.85; transition:0.2s; }
            .msg { margin-top:15px; text-align:center; font-weight:bold; }
            #dropZone { border:2px dashed #555; padding:40px; text-align:center; border-radius:15px; margin-top:15px;}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Send to PC</h2>
            <textarea id="text" placeholder="Type text here"></textarea>
            <button class="button send" onclick="sendText()">Send Text</button>

            <div id="dropZone">Drag & Drop File Here</div>
            <input type="file" id="fileInput" hidden>
            <button class="button upload" onclick="document.getElementById('fileInput').click()">Choose File</button>

            <button class="button logout" onclick="logout()">Logout</button>
            <div class="msg" id="message"></div>
        </div>

<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<script>
var socket = io();

socket.on("receive_message", function(data){
    document.getElementById("message").innerText = "Received: " + data.text;
});

// Send text
function sendText(){
    let text = document.getElementById("text").value;
    socket.emit("send_message", {text: text});
    document.getElementById("text").value = "";
}

// Drag & Drop
let dropZone = document.getElementById("dropZone");
dropZone.addEventListener("dragover", e=>{ e.preventDefault(); dropZone.style.background="#333"; });
dropZone.addEventListener("dragleave", e=>{ dropZone.style.background=""; });
dropZone.addEventListener("drop", e=>{
    e.preventDefault(); dropZone.style.background="";
    let file = e.dataTransfer.files[0];
    uploadFile(file);
});

// File upload
document.getElementById("fileInput").addEventListener("change", function(){
    let file = this.files[0];
    uploadFile(file);
});

function uploadFile(file){
    let formData = new FormData();
    formData.append("file", file);
    fetch("/api/upload", {method:"POST", body: formData})
        .then(res=>res.json())
        .then(data=> document.getElementById("message").innerText=data.message);
}

// Logout
function logout(){ window.location.href="/logout"; }
</script>

    </body>
    </html>
    '''

# ---------------- WEBSOCKET ----------------
@socketio.on("send_message")
def handle_message(data):
    text = data.get("text")
    pyperclip.copy(text)

    # Auto open URL
    url_pattern = r"(https?://[^\s]+)"
    match = re.search(url_pattern, text)
    if match:
        import webbrowser
        webbrowser.open(match.group())

    winsound.MessageBeep(winsound.MB_OK)
    print("Received:", text)
    emit("receive_message", {"text": text}, broadcast=True)

# ---------------- FILE UPLOAD ----------------
@app.route("/api/upload", methods=["POST"])
def upload_file():
    if not session.get("logged_in"):
        return jsonify({"message": "Not authorized"})
    file = request.files.get("file")
    if not file:
        return jsonify({"message":"No file selected"})
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)
    print("File saved:", path)
    winsound.MessageBeep(winsound.MB_OK)
    return jsonify({"message":"File uploaded successfully!"})

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- RUN ----------------
# socketio.run(app, host="10.152.59.118", port=5000, certfile=cert_file, keyfile=key_file, debug=True)



socketio.run(
    app,
    host="0.0.0.0",
    port=5000,
    ssl_context=(cert_file, key_file),
    debug=True
)
