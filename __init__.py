from flask import Blueprint

from CTFd.models import Challenges, db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.android_challenges.src.models import AndroidChallenge
from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from .src.routes import plugin_blueprint
from CTFd.plugins.migrations import upgrade


# Depends on dynamic_challenges plugin

class AndroidValueChallenge(BaseChallenge):
    id = "android"  # Unique identifier used to register challenges
    name = "android"  # Name of a challenge type
    templates = (
        {  # Handlebars templates used for each aspect of challenge editing & viewing
            "create": "/plugins/android_challenges/src/assets/create.html",
            "update": "/plugins/android_challenges/src/assets/update.html",
            "view": "/plugins/android_challenges/src/assets/view.html",
        }
    )
    scripts = {  # Scripts that are loaded when a template is loaded
        "create": "/plugins/android_challenges/src/assets/create.js",
        "update": "/plugins/android_challenges/src/assets/update.js",
        "view": "/plugins/android_challenges/src/assets/view.js",

    }
    # Route at which files are accessible. This must be registered using register_plugin_assets_directory()
    route = "/plugins/android_challenges/src/assets/"

    challenge_model = AndroidChallenge

    @classmethod
    def read(cls, challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.

        :param challenge:
        :return: Challenge object, data dictionary to be returned to the user
        """
        challenge = AndroidChallenge.query.filter_by(id=challenge.id).first()
        data = {
            "id": challenge.id,
            "name": challenge.name,
            "value": challenge.value,
            "package_id": challenge.package_id,
            "max_file_size": challenge.max_file_size,
            "install_time": challenge.install_time,
            "launch_time": challenge.launch_time,
            "description": challenge.description,
            "connection_info": challenge.connection_info,
            "next_id": challenge.next_id,
            "category": challenge.category,
            "state": challenge.state,
            "max_attempts": challenge.max_attempts,
            "type": challenge.type,
            "type_data": {
                "id": cls.id,
                "name": cls.name,
                "templates": cls.templates,
                "scripts": cls.scripts,
            },
        }
        return data

    @classmethod
    def update(cls, challenge, request):
        """
        This method is used to update the information associated with a challenge. This should be kept strictly to the
        Challenges table and any child tables.

        :param challenge:
        :param request:
        :return:
        """
        data = request.form or request.get_json()

        for attr, value in data.items():
            # We need to set these to floats so that the next operations don't operate on strings
            if attr in ("max_file_size", "install_time", "launch_time"):
                value = int(value)
            setattr(challenge, attr, value)

        db.session.commit()
        return challenge

    @classmethod
    def solve(cls, user, team, challenge, request):
        super().solve(user, team, challenge, request)


def load(app):
    upgrade(plugin_name="android_challenges")
    CHALLENGE_CLASSES["android"] = AndroidValueChallenge
    app.register_blueprint(plugin_blueprint)
    register_plugin_assets_directory(
        app, base_path="/plugins/android_challenges/src/assets/"
    )
