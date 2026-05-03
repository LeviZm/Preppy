'''
Flask Backend for the Preppy app
'''

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv

import os
from urllib.parse import quote_plus, urlunparse

# Load environment variables from .env
load_dotenv()

db = SQLAlchemy()

def create_app():
    '''
    Factory function to create and configure the Flask application.
    This allows for better modularity and testing. The app is configured
    with the database URI from environment variables, CORS is enabled, and
    routes are defined for the API endpoints. Error handlers are also set
    up to return JSON responses for common HTTP errors.
    '''

    # Try to construct the SQLAlchemy connection string from DATABASE_URL
    uri = os.getenv("DATABASE_URL")

    if not uri:
        # If uri is not set, try to construct it from individual components
        user = os.getenv("USER")
        raw_pw = os.getenv("PASSWORD")
        host = os.getenv("HOST")
        port = os.getenv("PORT")
        dbname = os.getenv("DBNAME")

        # Make sure we encode the password to handle special characters
        if not raw_pw:
            raise RuntimeError("Database password is missing in .env file.")

        # Try to encode the password, handle any potential errors in encoding
        try:
            password = quote_plus(raw_pw)
        except Exception as e:
            raise RuntimeError("Error encoding database password") from e

        # Check that all components are present
        if not all([user, password, host, port, dbname]):
            raise RuntimeError("One or more database connection environment variables are missing.\
                Please check your .env file.")

        # If we have them, make the connection string
        netloc = f"{user}:{password}@{host}:{port}"
        uri = urlunparse(("postgresql+psycopg2", netloc, f"/{dbname}", "", "sslmode=require", ""))

    flask_app = Flask(__name__)

    flask_app.config['SQLALCHEMY_DATABASE_URI'] = uri
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    CORS(flask_app)

    db.init_app(flask_app)

    @flask_app.before_request
    def log_request():
        '''
        Middleware to log incoming requests for debugging purposes.
        '''

        print(f"Received {request.method} request for {request.path}")
        if request.is_json:
            print(f"Data: {request.get_json()}")

    @flask_app.route('/')
    def home():
        '''
        Home route to verify the backend is up and running.
        '''

        return jsonify({"message": "Preppy AI Backend is Running!"})

    @flask_app.route('/api/generate-meal', methods=['POST'], strict_slashes=False)
    def generate_meal():
        '''
        This endpoint receives a POST request with a JSON body containing a 'prompt' key
        for Gemini. It then processes the prompt and returns a json response from the Gemini API.
        This generates a meal for the database.
        '''
        # Validate the request sends a JSON body
        if not request.is_json:
            return jsonify({
                "Error": "Unsupported Media Type",
                "message": "Content-Type must be application/json"
                }), 415

        data = request.get_json()

        # Check that the 'prompt' key exists
        user_prompt = data.get('prompt')
        if not user_prompt:
            return jsonify({
                "Error": "bad request",
                "message": "The 'prompt' field is required."
            }), 400

        # print test to verify the request was received correctly
        print(f"Received request for: {user_prompt}")

        return jsonify({
            "status": "success",
            "received": user_prompt,
        }), 200

    @flask_app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            "error": "Bad Request",
            "message": "Check your JSON format. Did you include the 'prompt' key?"
        }), 400

    @flask_app.errorhandler(404)
    def resource_not_found(e):
        return jsonify(error=str(e), message="Make sure your URL is correct and\
        doesn't have an extra slash!"), 404

    @flask_app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({
            "error": "Method Not Allowed",
            "message": "You are trying to 'GET' this URL,\
                but it requires a 'POST' with a JSON body."
        }), 405

    @flask_app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({
            "error": "Internal Server Error",
            "message": "The backend had a hiccup. Check the terminal logs."
        }), 500

    return flask_app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
