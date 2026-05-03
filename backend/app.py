"""
Flask Backend for the Preppy app.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from .extensions import db, cors, migrate, jwt
from .settings import Config

# Load environment variables from .env
load_dotenv()

def create_app():
    """
    Factory function to create and configure the Flask application.
    This allows for better modularity and testing. The app is configured
    with the database URI from environment variables, CORS is enabled, and
    routes are defined for the API endpoints. Error handlers are also set
    up to return JSON responses for common HTTP errors.
    """

    flask_app = Flask(__name__)

    flask_app.config.from_object(Config)

    db.init_app(flask_app)
    # Initialize other extensions
    cors.init_app(flask_app)
    migrate.init_app(flask_app, db)

    # JWT config - keep secret in env for production
    flask_app.config.setdefault("JWT_SECRET_KEY", os.getenv("JWT_SECRET_KEY", "change-me"))
    jwt.init_app(flask_app)

    # register blueprints here to avoid circular imports at module import time
    from .routes.meals import meals_bp
    from .routes.auth import auth_bp

    flask_app.register_blueprint(meals_bp)
    flask_app.register_blueprint(auth_bp)

    @flask_app.before_request
    def log_request():
        """
        Middleware to log incoming requests for debugging purposes.
        """

        print(f"Received {request.method} request for {request.path}")
        if request.is_json:
            print(f"Data: {request.get_json()}")

    @flask_app.route('/')
    def home():
        """
        Home route to verify the backend is up and running.
        """

        return jsonify({"message": "Preppy AI Backend is Running!"})

    @flask_app.route('/api/generate-meal', methods=['POST'], strict_slashes=False)
    def generate_meal():
        """
        This endpoint receives a POST request with a JSON body containing a 'prompt' key
        for Gemini. It then processes the prompt and returns a json response from the Gemini API.
        This generates a meal for the database.
        """
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
        """
        Error handler for 400 Bad Request errors.
        :param e:
        :return:
        """
        return jsonify({
            "error": "Bad Request",
            "message": f"Check your JSON format. Did you include the 'prompt' key? ({e})"
        }), 400

    @flask_app.errorhandler(404)
    def resource_not_found(e):
        """
        Error handler for 404 Resource Not Found errors.
        :param e:
        :return:
        """
        return jsonify(error=str(e), message="Make sure your URL is correct and\
        doesn't have an extra slash!"), 404

    @flask_app.errorhandler(405)
    def method_not_allowed(e):
        """
        Error handler for 405 Method Not Allowed errors.
        :param e:
        :return:
        """
        return jsonify({
            "error": "Method Not Allowed",
            "message": f"You are trying to use the wrong HTTP method: {e}"
        }), 405

    @flask_app.errorhandler(500)
    def internal_server_error(e):
        """
        Error handler for 500 Internal Server Error errors.
        :param e:
        :return:
        """
        return jsonify({
            "error": "Internal Server Error",
            "message": f"The backend had a hiccup. Check the terminal logs. ({e})"
        }), 500

    return flask_app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
