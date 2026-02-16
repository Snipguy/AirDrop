from flask import Flask, request
import pyperclip


app = Flask(__name__)
# PASSWORD = input("What is the password? \n")
PASSWORD = "2545"


@app.route("/")
def home():
    return '''
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial; padding: 20px; }
            textarea { width: 100%; height: 150px; font-size: 16px; }
            input { width: 100%; padding: 10px; font-size: 16px; }
            button { width: 100%; padding: 15px; font-size: 18px; }
        </style>
    </head>
    <body>
        <h2>Send Text to PC</h2>
        <form method="POST" action="/send">
            
            <input type="password" name="password" placeholder="Enter password"><br><br>
            
            <textarea name="text" placeholder="Type your text here"></textarea><br><br>
            
            <button type="submit">Send</button>
        </form>
    </body>
    </html>
    '''

@app.route("/send", methods=["POST"])
def receive():
    password = request.form.get("password")
    text = request.form.get("text")

    if password != PASSWORD or not password:
        return "Wrong password"

    print("Received:", text)
    print("-" * 40)

    pyperclip.copy(text)

    return "Copied to PC clipboard!"


app.run(host="10.152.59.118", port=5000, debug=True)

