import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Cat(db.Model):
    __tablename__ = 'cats'

    cat_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nickname = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10))
    color = db.Column(db.String(30))
    personality_tags = db.Column(db.Text)
    health_status = db.Column(db.String(50), default='健康')
    is_neutered = db.Column(db.Boolean, default=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    location_description = db.Column(db.String(200))
    photo_url = db.Column(db.String(255))
    description = db.Column(db.Text)
    age_info = db.Column(db.String(50))
    area_tag = db.Column(db.String(50))
    adoption_status = db.Column(db.String(20), default='normal')
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)

    check_ins = db.relationship('CheckIn', backref='cat', lazy='dynamic',
                                cascade='all, delete-orphan')

    def to_dict(self):
        tags = []
        if self.personality_tags:
            try:
                tags = json.loads(self.personality_tags)
            except (json.JSONDecodeError, TypeError):
                tags = self.personality_tags.split(',') if self.personality_tags else []
        return {
            'cat_id': self.cat_id,
            'nickname': self.nickname,
            'gender': self.gender,
            'color': self.color,
            'personality_tags': tags,
            'health_status': self.health_status,
            'is_neutered': self.is_neutered,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'location_description': self.location_description,
            'photo_url': self.photo_url,
            'description': self.description,
            'age_info': self.age_info,
            'area_tag': self.area_tag,
            'adoption_status': self.adoption_status,
            'view_count': self.view_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(50))
    role = db.Column(db.String(20), default='user')
    avatar_url = db.Column(db.String(255))
    bio = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)

    check_ins = db.relationship('CheckIn', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'display_name': self.display_name,
            'role': self.role,
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class CheckIn(db.Model):
    __tablename__ = 'check_ins'

    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cat_id = db.Column(db.Integer, db.ForeignKey('cats.cat_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    type = db.Column(db.String(20))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location_description = db.Column(db.String(200))
    photo_url = db.Column(db.String(255))
    comment = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'record_id': self.record_id,
            'cat_id': self.cat_id,
            'user_id': self.user_id,
            'type': self.type,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'location_description': self.location_description,
            'photo_url': self.photo_url,
            'comment': self.comment,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'cat_nickname': self.cat.nickname if self.cat else None,
            'username': self.user.display_name or self.user.username if self.user else None,
        }
