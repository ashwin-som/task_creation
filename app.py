from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, World!"

@app.route("/create-task")
def create_task():
    return "Task has been created"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)