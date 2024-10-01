from flask import Flask, request, session

app = Flask(__name__)

if __name__ == '__main__':
    import routes.routes
    app.run(host='0.0.0.0', port=5001)