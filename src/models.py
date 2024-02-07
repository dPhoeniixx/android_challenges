from sqlalchemy.orm import relationship

from CTFd.models import db, Challenges
from dataclasses import dataclass


@dataclass
class GenymotionEmulator(db.Model):
    id = db.Column('id', db.Integer, primary_key=True)
    url = db.Column('url', db.String(255))
    username = db.Column('username', db.String(100))
    password = db.Column('password', db.String(100))
    verify_ssl = db.Column('verify_ssl', db.Boolean)

    session = db.relationship('EmulatorSession', uselist=False, back_populates="emulator")

    def __init__(self, url, username, password, verify_ssl):
        self.url = url
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl

    def as_dict(self, nopassword=True):
        res = {column.name: getattr(self, column.name) for column in self.__table__.columns}
        if nopassword:
            res['password'] = "REDACTED"

        return res


class EmulatorSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column('user_id', db.Integer, unique=True)
    expire_at = db.Column('expire_at', db.Integer)
    emulator_id = db.Column('emulator_id', db.Integer, db.ForeignKey('genymotion_emulator.id'))
    challenge_id = db.Column('challenge_id', db.Integer)
    session_data = db.Column('session_data', db.Text)

    emulator = relationship("GenymotionEmulator")

    def __init__(self, user_id, emulator_id, challenge_id, expire_at, session_data):
        self.user_id = user_id
        self.emulator_id = emulator_id
        self.challenge_id = challenge_id
        self.expire_at = expire_at
        self.session_data = session_data


class AndroidChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "android"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    package_id = db.Column('package_id', db.String(255))
    max_file_size = db.Column('max_file_size', db.Integer)
    install_time = db.Column('install_time', db.Integer)
    launch_time = db.Column('launch_time', db.Integer)

    def __init__(self, *args, **kwargs):
        super(AndroidChallenge, self).__init__(**kwargs)

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
