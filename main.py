import math
import mimetypes
from flask import Flask, request, redirect, send_from_directory, url_for, session, jsonify, abort, send_file
from flask_socketio import SocketIO, emit
import pyperclip
import os, re, datetime
import winsound
import secrets
import qrcode
import socket ,time, uuid
import webbrowser
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from zeroconf import ServiceInfo, Zeroconf
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask import render_template
import shutil
from flask_cors import CORS
from werkzeug.utils import secure_filename


# ---------------- CONFIG ---------------

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
# app.secret_key =  input("Set session password: ")
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

# --------- DataBase ---------

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///airdrop_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String, nullable=False)
    sender = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class UploadHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String, nullable=False)
    sender = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)


# --------- STARTUP SETUP ---------
# APP_PIN = input("🔐 Set access PIN for phone: ").strip()
APP_PIN = "4444" # for dev branch
SESSION_TOKEN = secrets.token_urlsafe(24)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not require internet — just finds LAN IP
        s.connect(("192.168.0.1", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

LOCAL_IP = get_local_ip()
BASE_URL = f"http://{LOCAL_IP}:5000"


# ---------------- m DNS ----------------

info = ServiceInfo(
    "_http._tcp.local.",
    "AirDropServer._http._tcp.local.",
    addresses=[socket.inet_aton(LOCAL_IP)],
    port=5000,
    properties={},
    server="airdrop.local."
)
zeroconf = Zeroconf()
zeroconf.register_service(info)


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
def generate_qr():
    url = f"{BASE_URL}/connect?token={SESSION_TOKEN}"
    img = qrcode.make(url)
    img.save("connect_qr.png")

    print("\n📱 Scan this QR with your phone:")
    print(url)
    print("QR saved as connect_qr.png\n")


@app.before_request
def capture_user_agent():
    ua = request.headers.get("User-Agent")
    # Send UA to JS if you want
    print("Connected device UA:", ua)

    device = session.get("device_name", "Unknown Device")

@app.route("/connect")
def connect():
    token = request.args.get("token")

    if token != SESSION_TOKEN:
        abort(403)

    session["logged_in"] = True
    return redirect(url_for("send_page"))

@app.route("/", methods=["GET", "POST"])
def login():
    db.create_all()

    if request.method == "POST":
        password = request.form.get("password")

        if password == APP_PIN:
            session["logged_in"] = True
            return redirect(url_for("send_page"))
        else:
            return "<script>alert('Wrong PIN'); window.location='/';</script>"

    return render_template("login.html")


# ---------------- SEND PAGE ----------------
@app.route("/send")
def send_page():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("send.html")


# ---------------- WEBSOCKET ----------------
@socketio.on("send_message")
def handle_message(data):
    text = data.get("text")
    pyperclip.copy(text)

    sender = session.get("device_name", "Unknown")
    db.session.add(Message(content=text, sender=sender))
    db.session.commit()

    # Auto open URL
    url_pattern = r"(http?://[^\s]+)"
    match = re.search(url_pattern, text)
    if match:
        import webbrowser
        webbrowser.open(match.group())

    winsound.MessageBeep(winsound.MB_OK)
    print("Received:", text)
    emit("receive_message", {"text": text}, broadcast=True)

@socketio.on('start_text_send')
def send_progress(data):
    text = data["text"]
    for i in range(len(text)):
        time.sleep(0.01)
        percent = int((i+1)/len(text)*100)
        emit('progress_update', {'progress': percent})

# !!---------------- PC ==> Phone ----------------

SHARED_FOLDER = r"E:\GitHub\AirDrop\uploads"


@app.route('/api/status', methods=['GET'])
def server_status():
    return jsonify({
        'status': 'online',
        'server_time': datetime.now().isoformat(),
        'clients_connected': len(socketio.server.manager.rooms.get('/', {}))
    }), 200

@app.route('/api/network/info', methods=['GET'])
def network_info():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    return jsonify({
        'hostname': hostname,
        'local_ip': local_ip,
        'port': 5000,
        'websocket_url': f'ws://{local_ip}:5000'
    }), 200

@app.route("/api/mobile/recive", methods=["POST"])
def mobile_recive():
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        device_id = data.get('device_id')
        payload = data.get('data')
        
        # Process the data (store, broadcast, etc.)
        print(f"Received from mobile {device_id}: {payload}")

        socketio.emit('mobile_data', {
            'device_id': device_id,
            'data': payload,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'status': 'success',
            'message': 'Data received',
            'device_id': device_id
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@socketio.on('mobile_connect')
def handle_mobile_connect(data):
    device_id = data.get('device_id')
    device_type = data.get('device_type', 'mobile')
    
    print(f"Mobile device connected: {device_id}")
    
    if 'mobile_devices' not in session:
        session['mobile_devices'] = []
    
    session['mobile_devices'].append({
        'id': device_id,
        'type': device_type,
        'connected_at': datetime.now().isoformat()
    })


    emit('mobile_connected', {
        'status': 'connected',
        'server_time': datetime.now().isoformat()
    })

@socketio.on('mobile_data_stream')
def handle_mobile_stream(data):
    socketio.emit('stream_update', {
        'source': 'mobile',
        'data': data,
        'timestamp': datetime.now().isoformat()
    })



# --- Helper function to get file metadata ---
def get_file_metadata(folder_path):
    files_data = []
    try:
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath):
                file_stat = os.stat(filepath)
                mod_time = datetime.datetime.fromtimestamp(file_stat.st_mtime)
                file_size = file_stat.st_size # Size in bytes

                # Determining file type for icon mapping
                _, ext = os.path.splitext(filename)
                ext = ext.lower()
                file_type = "unknown"
                if ext in ['.pdf']:
                    file_type = "pdf"
                elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
                    file_type = "image"
                elif ext in ['.zip', '.rar', '.tar', '.gz', '.7z']:
                    file_type = "archive"
                elif ext in ['.mp3', '.wav', '.aac', '.flac', '.ogg']:
                    file_type = "audio"
                elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.mkv']:
                    file_type = "video"
                elif ext in ['.txt', '.doc', '.docx', '.odt', '.rtf']:
                    file_type = "document"

                files_data.append({
                    "name": filename,
                    "size_bytes": file_size,
                    "modified_timestamp": mod_time.timestamp(),
                    "modified_date": mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                    "type": file_type,
                    "extension": ext
                })
    except Exception as e:
        print(f"Error accessing shared folder: {e}")
        return []
    return files_data

# --- Routes ---


@app.route("/viewer")
def viewer():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    all_files_data = get_file_metadata(SHARED_FOLDER)
    return render_template("viewer.html", files_data=all_files_data)

@app.route("/pc", methods=["GET", "POST"])
def login_to_pc():
    db.create_all()

    if request.method == "POST":
        password = request.form.get("password")

        if password == APP_PIN:
            session["logged_in"] = True
            return redirect(url_for("viewer"))
        else:
            return "<script>alert('Wrong PIN'); window.location='/pc';</script>"

    return render_template("login2pc.html")

#!! PC → Phone endpoint
@app.route("/api/download/<filename>", methods=["GET"])
def download_file(filename):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    return send_from_directory(SHARED_FOLDER, filename, as_attachment=True)


@socketio.on("request_file_list")
def handle_file_list_request():
    if not session.get("logged_in"):
        return

    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            files.append({
                "name": filename,
                "size": os.path.getsize(file_path),
                "modified": os.path.getmtime(file_path),
                "type": mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            })

    emit("file_list", {"files": files}, room=request.sid)


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


# ---------------- FILE CHUNK UPLOAD ----------------
CHUNKS_FOLDER = "uploads/chunks"
if not os.path.exists(CHUNKS_FOLDER):
    os.makedirs(CHUNKS_FOLDER)

UPLOAD_PROGRESS = {}

@app.route("/api/upload_chunk", methods=["POST"])
def upload_chunk():
    file_id = request.form["file_id"]
    chunk_index = int(request.form["chunk_index"])
    total_chunks = int(request.form["total_chunks"])
    chunk = request.files["chunk"]

    file_dir = os.path.join(CHUNKS_FOLDER, file_id)
    os.makedirs(file_dir, exist_ok=True)

    chunk_path = os.path.join(file_dir, str(chunk_index))
    chunk.save(chunk_path)

    UPLOAD_PROGRESS.setdefault(file_id, set()).add(chunk_index)

    if len(UPLOAD_PROGRESS[file_id]) == total_chunks:
        final_path = os.path.join(UPLOAD_FOLDER, file_id)

        with open(final_path, "wb") as f:
            for i in range(total_chunks):
                with open(os.path.join(file_dir, str(i)), "rb") as part:
                    f.write(part.read())

        shutil.rmtree(file_dir)
        del UPLOAD_PROGRESS[file_id]

        return jsonify({"status": "complete"})

    return jsonify({"status": "incomplete"})


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@socketio.on("connect")
def client_connect():
    print(f"📶 Client connected: {request.remote_addr}")
    emit("status", {"message": "connected", "ip": request.remote_addr}, broadcast=True)

@socketio.on("disconnect")
def client_disconnect():
    print(f"📴 Client disconnected: {request.remote_addr}")
    emit("status", {"message": "disconnected"}, broadcast=True)



# ---------------- RUN ----------------
@app.route("/history")
def show_history():
    messages = Message.query.order_by(Message.timestamp.desc()).all()
    uploads = UploadHistory.query.order_by(UploadHistory.timestamp.desc()).all()
    return render_template("history.html", messages=messages, uploads=uploads)


@app.route("/info", methods=["GET", "POST"])
def show_info():
    QR_CODE_FILENAME = "connect_qr.png"

    return render_template(
        "info.html",
        token = SESSION_TOKEN,
        BaseUrl = BASE_URL,
        IP = LOCAL_IP,
        qr_code_url = QR_CODE_FILENAME,
        pin = APP_PIN
    )


def run_server():
    # webbrowser.open(BASE_URL)
    # webbrowser.open("http://airdrop.local:5000/info")

    print("-" * 60)
    print(f"⚡️ Server starting...")
    print(f"   Local IP Address: {LOCAL_IP}")
    print(f"   Base URL (IP): {BASE_URL}")
    print(f"   Access URL: http://airdrop.local:5000")
    print(f"   QR Code saved as: connect-qr.png")
    print("-" * 60)

    socketio.run(
        app,
        # host="172.20.32.1",
        # host=f"{LOCAL_IP}",
        host=f"0.0.0.0",
        use_reloader=False,
        # ssl_context=(cert_file, key_file), # needs to be commented if there is no internet
        debug=True
    )


    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/socket.io/*": {"origins": "*"}
    })


if __name__ == "__main__":
    run_server()