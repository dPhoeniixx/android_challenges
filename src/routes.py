import json
import secrets

import requests
import sqlalchemy
from flask import jsonify, request, Blueprint, session, render_template, current_app
from CTFd.models import db, Challenges
from androguard.core.apk import get_apkid
from androguard.core.apk import APK
from time import time
from sqlalchemy.orm import scoped_session, sessionmaker
from CTFd.utils.decorators import (
    admins_only, require_verified_emails, during_ctf_time_only
)
from .models import GenymotionEmulator, EmulatorSession, AndroidChallenge
from .utils import get_genymotion_auth, addJob, addExtraTimeToJob, seconds_to_str, unassign, EmulatorSearchForm, \
    response_json

plugin_blueprint = Blueprint("androidtrigger", __name__, template_folder="assets")
jobs = {}

db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=db.engine))


@plugin_blueprint.route("/admin/androidTrigger", methods=["GET"])
@admins_only
def testPanel():
    return render_template("android_settings.html", EmulatorSearchForm=EmulatorSearchForm,
                           emulators=GenymotionEmulator.query.options(
                               sqlalchemy.orm.defer(GenymotionEmulator.password)).all())


@plugin_blueprint.route("/api/v1/androidTrigger/emulators/<int:id>", methods=["POST"])
@plugin_blueprint.route("/api/v1/androidTrigger/emulators", methods=["PUT"])
@admins_only
def addEmulator(id=None):
    if not set(['url', 'username', 'password', 'verify_tls']).issubset(request.form):
        return jsonify(
            {"message": "One or more required fields (url, username, password, verify_tls) are missing."}), 400

    if request.method == 'PUT':
        db.session.add(GenymotionEmulator(request.form['url'], request.form['username'], request.form['password'],
                                          True if request.form['verify_tls'] == 'true' else False))
    else:
        emulator = GenymotionEmulator.query.filter(GenymotionEmulator.id == id).scalar()
        emulator.url = request.form['url']
        emulator.username = request.form['username']
        emulator.password = request.form['password'] if request.form['password'] != "REDACTED" else emulator.password
        emulator.verify_ssl = True if request.form['verify_tls'] == 'true' else False

    db.session.commit()

    return jsonify({"message": "Successfully added."}), 200


@plugin_blueprint.route("/api/v1/androidTrigger/emulators/<int:id>", methods=["DELETE"])
@admins_only
def deleteEmulator(id):
    db.session.delete(GenymotionEmulator.query.get(id))
    db.session.commit()

    return jsonify({"message": "Successfully deleted."}), 200


@plugin_blueprint.route("/api/v1/androidTrigger/emulators/<int:id>", methods=["GET"])
@plugin_blueprint.route("/api/v1/androidTrigger/emulators", defaults={'id': None}, methods=["GET"])
@admins_only
def getEmulator(id):
    if id:
        return jsonify(
            GenymotionEmulator.query.options(sqlalchemy.orm.defer(GenymotionEmulator.password)).get(id).as_dict()), 200

    return jsonify(GenymotionEmulator.query.options(sqlalchemy.orm.defer(GenymotionEmulator.password)).all()), 200


@during_ctf_time_only
@require_verified_emails
@plugin_blueprint.route('/api/v1/androidTrigger/install', methods=['POST'])
def install():
    user_id = session.get("id", -1)
    challenge_id = int(request.form.get('challenge_id'))
    challenge = AndroidChallenge.query.filter(
        AndroidChallenge.id == challenge_id).scalar()

    if not challenge:
        return response_json("The challenge was not found.", False, error_code=1), 400

    if 'file' not in request.files:
        return response_json("Please select file.", False, error_code=2), 400

    if request.files['file'].content_length > challenge.max_file_size:
        return response_json('The file size exceeds the allowed limit of {} MB.'.format(
            str(int(challenge.max_file_size / 1024))), False, error_code=32404), 400

    available_emulator = db.session.execute(
        GenymotionEmulator.query.filter(~GenymotionEmulator.session.has())).scalar()
    if available_emulator is None:
        return response_json("No Android instance available right now.", False, error_code=3), 400

    if EmulatorSession.query.filter(
            EmulatorSession.user_id == user_id and EmulatorSession.challenge_id == challenge_id).scalar():
        return response_json("You are already has an emulator session for this challenge.", False, error_code=4), 400

    apk_path = '/tmp/{}-{}-{}.apk'.format(secrets.token_hex(32), user_id, int(time()))
    request.files['file'].save(apk_path)
    try:
        if not APK(apk_path, testzip=True).is_valid_APK():
            return response_json("Please provide valid APK file.", False, error_code=5), 400
    except:
        return response_json("Please provide valid APK file.", False, error_code=5), 400

    package_name = get_apkid(apk_path)[0]
    if package_name == "" or package_name is None:
        return response_json("Can\'t parse the package name from the APK.", False, error_code=6), 400

    install_request = requests.put('{}/api/v1/apk?downgrade=true'.format(available_emulator.url),
                                   data=open(apk_path, 'rb'),
                                   headers={'Authorization': 'Basic ' + get_genymotion_auth(available_emulator)},
                                   verify=bool(int(available_emulator.verify_ssl)))

    if install_request.status_code != 200:
        return response_json("An error happened while installing your apk to the emulator.", False, error_code=7), 400

    jobs[user_id] = {}
    jobs[user_id][challenge_id] = addJob(unassign, challenge.install_time,
                                         args=[user_id, challenge_id, jobs,
                                               db_session])
    session_data = json.dumps({"package_id": package_name, "running": False, "launch_count": 0})

    emulator_session = EmulatorSession(user_id, available_emulator.id, challenge_id,
                                       jobs[user_id][challenge_id]['finishTime'],
                                       session_data)
    db.session.add(emulator_session)
    available_emulator.session = emulator_session
    db.session.commit()

    return response_json('Application installed successfully, your session will expire in {}'.format(
        seconds_to_str(challenge.install_time)), True,
                         {'session_lifetime': challenge.install_time}), 200


@during_ctf_time_only
@require_verified_emails
@plugin_blueprint.route('/api/v1/androidTrigger/launch', methods=['POST'])
def launchApp():
    user_id = session.get("id", -1)
    challenge_id = int(request.form.get('challenge_id'))
    challenge = AndroidChallenge.query.filter(
        AndroidChallenge.id == challenge_id).scalar()

    if not challenge:
        return response_json("The challenge was not found.", False, error_code=1), 400

    assigned_emulator = db.session.query(GenymotionEmulator).outerjoin(EmulatorSession).filter(
        EmulatorSession.user_id == user_id and EmulatorSession.challenge_id == challenge_id).scalar()
    if assigned_emulator is None:
        return response_json("The challenge was not found.", False, error_code=8), 400

    emulator_session = EmulatorSession.query.filter(
        EmulatorSession.user_id == user_id and EmulatorSession.challenge_id == challenge_id).scalar()
    emulator_session.session_data = json.loads(emulator_session.session_data)

    if jobs[user_id][challenge_id]['finishTime'] < int(time()):
        unassign(user_id, challenge_id, jobs, db_session)
        return response_json("Your emulator session has been expired.", False, error_code=9), 400

    launch_reqeust = requests.post('{}/api/v1/android/shell'.format(assigned_emulator.url),
                                   json={'commands': [
                                       'monkey -p ' + emulator_session.session_data[
                                           'package_id'] + ' -c android.intent.category.LAUNCHER 1'],
                                       'timeout_in_seconds': 15},
                                   headers={'Authorization': 'Basic ' + get_genymotion_auth(assigned_emulator)},
                                   verify=bool(int(assigned_emulator.verify_ssl)))
    if launch_reqeust.status_code != 200:
        return response_json("An error happened while trying to launch your apk on the emulator.", False,
                             error_code=10), 400

    jobs[user_id][challenge_id] = addExtraTimeToJob(jobs[user_id][challenge_id],
                                                    challenge.launch_time)
    emulator_session.expire_at = jobs[user_id][challenge_id]['finishTime']
    emulator_session.session_data['running'] = True
    emulator_session.session_data['launch_count'] += 1
    emulator_session.session_data = json.dumps(emulator_session.session_data)
    db.session.commit()

    return response_json(
        'The application launched successfully. You now have an additional {} before unassign the emulator.'.format(
            seconds_to_str(challenge.launch_time)), True,
        {'extra_time': challenge.launch_time}), 200


@plugin_blueprint.route('/api/v1/androidTrigger/emulators/available', methods=['GET'])
def available():
    return response_json(None, True, {'available': True if db.session.execute(
        GenymotionEmulator.query.filter(~GenymotionEmulator.session.has())).scalar() else False}), 200
