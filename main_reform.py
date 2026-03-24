import socket
import qrcode
import os
from flask import Flask, render_template_string, send_file, request, redirect, url_for
from flask_socketio import SocketIO, emit
import uuid
import threading

# --- Configuration ---
SESSION_TOKEN = str(uuid.uuid4()) # Generate a unique token for this session
PIN_CODE = "1234" # Example PIN, should be more secure in production

# --- Helper Functions ---
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.0.1", 1)) # Connect to a dummy address to get local IP
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

LOCAL_IP = get_local_ip()
BASE_URL_IP = f"http://{LOCAL_IP}:5000"
QR_CODE_FILENAME = "connect_qr.png"

# --- Flask App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key' # Change this!
socketio = SocketIO(app, cors_allowed_origins="*")


# --- HTML Template for Info Page ---
INFO_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Connect Your Device</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; padding: 20px; background-color: #f4f7f6; color: #333; }
        .container { max-width: 700px; margin: 40px auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }
        h1 { color: #0056b3; margin-bottom: 20px; }
        .ip-address { font-size: 1.5em; font-weight: bold; color: #e67e22; margin-bottom: 25px; padding: 10px; background-color: #fdf2e7; border-left: 5px solid #e67e22; display: inline-block;}
        .qr-code-section { margin-top: 30px; }
        .qr-code-section img { max-width: 250px; height: auto; border: 1px solid #ddd; padding: 5px; background: white; }
        .instructions { margin-top: 25px; font-size: 0.95em; color: #555; }
        .instructions p { margin-bottom: 10px; }
        .note { font-size: 0.85em; color: #888; margin-top: 15px; }
        .footer { margin-top: 40px; font-size: 0.8em; color: #aaa; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Connect Your Phone</h1>
        <p>Please use your phone to connect to the server.</p>
        
        <div class="ip-address">
            Server IP: {{ ip_address }}
        </div>

        <div class="qr-code-section">
            <p>Scan the QR code below with your phone's camera app or a QR scanner:</p>
            <img src="{{ qr_code_url }}" alt="QR Code">
            <p class="note">If the QR code doesn't scan, try entering the IP address directly.</p>
        </div>

        <div class="instructions">
            <h3>Steps:</h3>
            <p>1. Open your phone's camera app and point it at the QR code above.</p>
            <p>2. Tap the notification that appears to open the link in your phone's browser.</p>
            <p>3. Alternatively, manually enter <code>{{ ip_address }}/connect?token={{ token }}</code> in your phone's browser.</p>
            <p>4. Enter the PIN code: <strong>{{ pin }}</strong></p>
        </div>
        <div class="footer">
            Server running on {{ ip_address }}
        </div>
    </div>
</body>
</html>
"""


# --- Routes ---
@app.route("/")
def index():
    # Generate QR code image if it doesn't exist
    if not os.path.exists(QR_CODE_FILENAME):
        try:
            url = f"{BASE_URL_IP}/connect?token={SESSION_TOKEN}"
            img = qrcode.make(url)
            img.save(QR_CODE_FILENAME)
            print(f"QR code generated: {QR_CODE_FILENAME}")
        except Exception as e:
            print(f"Error generating QR code: {e}")
            return "Error generating QR code.", 500

    qr_code_url = url_for('get_qr_code', filename=QR_CODE_FILENAME)
    return render_template_string(INFO_PAGE_HTML, 
                                  ip_address=LOCAL_IP, 
                                  qr_code_url=qr_code_url, 
                                  token=SESSION_TOKEN,
                                  pin=PIN_CODE)

@app.route('/connect')
def connect_page():
    token = request.args.get('token')
    if token == SESSION_TOKEN:
        # Redirect to a simple page that initiates Socket.IO connection
        # This is where your app.js logic would typically kick in after authentication
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Connecting...</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
            <script>
                // Dynamically set the base URL to the detected IP
                var serverBaseUrl = "{{ BASE_URL_IP }}"; 
                var socket = io.connect(serverBaseUrl); 
                
                // --- Authentication Logic ---
                socket.on('connect', function() {
                    console.log('Socket connected to server.');
                    // Send the token and PIN to authenticate
                    socket.emit('authenticate', {token: '{{ token }}', pin: '{{ pin }}'}); 
                    alert('Connected via Socket.IO! Authenticating...');
                });

                socket.on('auth_success', function(data) {
                    alert('Authentication successful!');
                    // Redirect to your main app page where your app.js takes over
                    window.location.href = '/app'; // Example redirect
                });

                socket.on('auth_fail', function(data) {
                    alert('Authentication failed: ' + data.message);
                    console.error("Authentication failed:", data.message);
                    // Optionally redirect to a page asking for PIN again, or show error
                });

                socket.on('disconnect', function() {
                    console.log('Socket disconnected.');
                    alert('Disconnected from server.');
                    // Handle disconnection - maybe attempt to reconnect or show error message
                });
            </script>
        </head>
        <body>
            <h1>Connecting to server...</h1>
            <p>If you are not redirected automatically, please check the console for errors.</p>
        </body>
        </html>
        """, BASE_URL_IP=BASE_URL_IP, token=token, pin=PIN_CODE) # Pass BASE_URL_IP here
    else:
        return "Invalid or expired token.", 400


@app.route('/app')
def app_page():
    # This would be your main application HTML page loaded after successful connection
    # For now, just a placeholder
    return "<h1>Welcome to the App!</h1><p>Connection established.</p>"

@app.route('/qr/<filename>')
def get_qr_code(filename):
    return send_file(filename, mimetype='image/png')

# --- Socket.IO Event Handlers ---
@socketio.on('authenticate')
def handle_authenticate(data):
    received_token = data.get('token')
    received_pin = data.get('pin')
    
    if received_token == SESSION_TOKEN and received_pin == PIN_CODE:
        emit('auth_success', {'message': 'Authentication successful'})
        print("Client authenticated successfully.")
    else:
        emit('auth_fail', {'message': 'Invalid token or PIN'})
        print("Client authentication failed.")

# --- Start Server ---
def run_server():
    print("-" * 60)
    print(f"⚡️ Server starting...")
    print(f"   Local IP Address: {LOCAL_IP}")
    print(f"   Base URL (IP): {BASE_URL_IP}")
    print(f"   Access URL: {BASE_URL_IP}")
    print(f"   QR Code saved as: {QR_CODE_FILENAME}")
    print("-" * 60)

    # Ensure QR code is generated on startup if it doesn't exist
    if not os.path.exists(QR_CODE_FILENAME):
        try:
            url = f"{BASE_URL_IP}/connect?token={SESSION_TOKEN}"
            img = qrcode.make(url)
            img.save(QR_CODE_FILENAME)
            print(f"QR code generated: {QR_CODE_FILENAME}")
        except Exception as e:
            print(f"Error generating QR code: {e}")

    # Run using Socket.IO and the detected IP
    # Use host="0.0.0.0" to make it accessible from other devices on the network
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

if __name__ == "__main__":
    # Run the server in a separate thread so we can do other things if needed
    # For this example, we just run it directly.
    run_server()
