import base64
import json
import threading
from time import time
from wtforms import MultipleFileField, SelectField, StringField
from wtforms.validators import InputRequired
from sqlalchemy import select
from CTFd.forms import BaseForm
from CTFd.forms.fields import SubmitField
import requests

from CTFd.models import db
from flask import current_app, Flask, jsonify

from .models import GenymotionEmulator, EmulatorSession, AndroidChallenge


def get_genymotion_auth(emulator):
    return base64.b64encode((emulator.username + ":" + emulator.password).encode('utf-8')).decode('utf-8')


# Copied from original CTFd challenges class
class EmulatorSearchForm(BaseForm):
    fieldEm = SelectField(
        "Search Field",
        choices=[
            ("url", "URL"),
            ("id", "ID"),
            ("username", "Username")
        ],
        default="name",
        validators=[InputRequired()],
    )
    qEm = StringField("Parameter", validators=[InputRequired()])

    submit = SubmitField("Search")

def unassign(user_id, challenge_id, jobs, session):
    emulator_session = session.execute(select(EmulatorSession).filter(
        EmulatorSession.user_id == user_id and EmulatorSession.challenge_id == challenge_id)).scalar()

    if not emulator_session:
        return

    emulator_session.session_data = json.loads(emulator_session.session_data)

    challenge = session.execute(select(AndroidChallenge).filter(
        AndroidChallenge.id == challenge_id)).scalar()

    assigned_emulator = session.execute(
        select(GenymotionEmulator).where(GenymotionEmulator.id == emulator_session.emulator_id)).scalar()

    if assigned_emulator is not None:
        requests.post('{}/api/v1/android/shell'.format(assigned_emulator.url),
                      json={'commands': ['am force-stop ' + challenge.package_id,
                                         'am force-stop ' + emulator_session.session_data['package_id'],
                                         'su -c "pm uninstall ' + emulator_session.session_data['package_id'] + '"'],
                            'timeout_in_seconds': 15},
                      headers={'Authorization': 'Basic ' + get_genymotion_auth(assigned_emulator)},
                      verify=False)
        assigned_emulator.session = None
        session.delete(emulator_session)
        emulator_session.session_data = json.dumps(emulator_session.session_data)
        session.commit()
        del jobs[user_id][challenge_id]


def addJob(func, when, args=None):
    timer = threading.Timer(when, func, args=args)
    timer.start()

    return {"job": timer, "startTime": int(time()), "finishTime": int(time()) + when}


def addExtraTimeToJob(job, seconds):
    remainingSeconds = job["job"].interval - (int(time()) - job["startTime"])
    newTime = remainingSeconds + seconds
    newTimer = threading.Timer(newTime, job["job"].function, args=job["job"].args)
    job["job"].cancel()
    newTimer.start()

    return {"job": newTimer, "startTime": int(time()), "finishTime": int(time()) + newTime}


def seconds_to_str(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    time_str = ""
    if days:
        time_str += f"{days} days, "
    if hours:
        time_str += f"{hours} hours, "
    if minutes:
        time_str += f"{minutes} minutes, "
    if seconds or not (days or hours or minutes):
        time_str += f"{seconds} seconds"

    return time_str.rstrip(', ')

def update_session_data(emulator_session, key, value):
    pass

def response_json(message, success, data=None, error_code=0):
    response = {}
    if not success:
        response['code'] = error_code
    response['message'] = message
    response['success'] = success
    response['data'] = data
    return jsonify(response)