"""
Flask Backend for the Preppy app.
"""

import logging

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from .extensions import db, cors, migrate, jwt
from .settings import Config
from .services.exceptions import AppError

logger = logging.getLogger(__name__)

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

    # Initialize JWT (config loaded from Config class)
    jwt.init_app(flask_app)

    # register blueprints here to avoid circular imports at module import time
    from .routes.auth_routes import auth_bp
    from .routes.ingredients_routes import ingredients_bp
    from .routes.meals_routes import meals_bp
    from .routes.recipe_routes import recipes_bp
    from .routes.shopping_routes import shopping_bp
    from .routes.oauth_routes import oauth_bp
    from .routes.user_routes import users_bp

    flask_app.register_blueprint(meals_bp)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(recipes_bp)
    flask_app.register_blueprint(ingredients_bp)
    flask_app.register_blueprint(shopping_bp)
    flask_app.register_blueprint(oauth_bp)
    flask_app.register_blueprint(users_bp)

    @flask_app.before_request
    def log_request():
        """Middleware to log incoming requests for debugging purposes."""
        logger.debug("Received %s %s", request.method, request.path)

    @flask_app.route('/')
    def home():
        """Home route to verify the backend is up and running."""

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

        logger.info("generate-meal request received for prompt: %.80r", user_prompt)

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
        logger.warning("400 Bad Request: %s", e)
        return jsonify({"error": "Bad Request"}), 400

    @flask_app.errorhandler(404)
    def resource_not_found(_):
        """
        Error handler for 404 Resource Not Found errors.
        :param e:
        :return:
        """
        logger.warning("404 Not Found: %s %s", request.method, request.path)
        return jsonify({"error": "Not Found"}), 404

    @flask_app.errorhandler(405)
    def method_not_allowed(_):
        """
        Error handler for 405 Method Not Allowed errors.
        :param e:
        :return:
        """
        logger.warning("405 Method Not Allowed: %s %s", request.method, request.path)
        return jsonify({"error": "Method Not Allowed"}), 405

    @flask_app.errorhandler(500)
    def internal_server_error(e):
        """
        Error handler for 500 Internal Server Error errors.
        :param e:
        :return:
        """
        logger.exception("500 Internal Server Error: %s", e)
        return jsonify({"error": "Internal Server Error"}), 500

    @flask_app.errorhandler(AppError)
    def handle_app_error(e):
        """Handle all custom application exceptions."""
        logger.warning("AppError: %s (status=%d)", e.message, e.status_code)
        return jsonify({"error": e.message}), e.status_code

    # JWT error handlers for consistent JSON responses
    @jwt.unauthorized_loader
    def missing_token_callback(error_string):
        """Called when a protected route receives no token."""
        return jsonify({"error": "Authentication required."}), 401


    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        """Called when a token is present but malformed or fails signature check."""
        return jsonify({"error": "Token is invalid."}), 401


    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """Called when a valid token has passed its expiration time."""
        return jsonify({"error": "Token has expired. Please log in again."}), 401

    @flask_app.errorhandler(Exception)
    def handle_generic_exception(e):
        """Catch-all for debugging test failures."""
        logger.exception("Unhandled exception: %s", e)
        return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500

    return flask_app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
