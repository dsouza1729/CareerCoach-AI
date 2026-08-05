from routes.ai_tools import tools_bp as ai_tools_bp
from routes.auth_routes import auth_bp
from routes.chat_routes import chat_bp
from routes.core import core_bp
from routes.resume_routes import resume_bp


def register_routes(app):
    for blueprint in (auth_bp, core_bp, chat_bp, resume_bp, ai_tools_bp):
        app.register_blueprint(blueprint)
