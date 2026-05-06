import os
import json
import uuid
from datetime import datetime

from flask import (Flask, render_template, request, jsonify, session,
                   redirect, url_for, send_from_directory)
from flask_cors import CORS
from werkzeug.utils import secure_filename

from models import db, Cat, User, CheckIn

app = Flask(__name__,
            template_folder='templates',
            static_folder='static',
            static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY', 'school-cat-guardian-secret-key-2026')
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school_cats.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['TIANDITU_API_KEY'] = os.environ.get('TIANDITU_API_KEY', '535c911b2638af104180ea40aac536a7')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db.init_app(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated


# ===================== Auth Routes =====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '用户名和密码不能为空'}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': '用户名已存在'}), 400
    user = User(
        username=data['username'],
        display_name=data.get('display_name', data['username']),
        role=data.get('role', 'user'),
        bio=data.get('bio', ''),
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.user_id
    session['username'] = user.username
    session['role'] = user.role
    return jsonify({'message': '注册成功', 'user': user.to_dict()}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '用户名和密码不能为空'}), 400
    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': '用户名或密码错误'}), 401
    session['user_id'] = user.user_id
    session['username'] = user.username
    session['role'] = user.role
    return jsonify({'message': '登录成功', 'user': user.to_dict()})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': '已退出登录'})


@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({'user': None})
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'user': None})
    return jsonify({'user': user.to_dict()})


# ===================== Cat Routes =====================

@app.route('/api/cats', methods=['GET'])
def list_cats():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)
    search = request.args.get('search', '')
    area = request.args.get('area', '')
    health = request.args.get('health', '')
    neutered = request.args.get('neutered', '')
    adoption = request.args.get('adoption', '')

    query = Cat.query

    if search:
        query = query.filter(
            db.or_(
                Cat.nickname.ilike(f'%{search}%'),
                Cat.description.ilike(f'%{search}%'),
                Cat.location_description.ilike(f'%{search}%'),
            )
        )
    if area:
        query = query.filter(Cat.area_tag == area)
    if health:
        query = query.filter(Cat.health_status == health)
    if neutered == '1':
        query = query.filter(Cat.is_neutered == True)
    elif neutered == '0':
        query = query.filter(Cat.is_neutered == False)
    if adoption == '1':
        query = query.filter(Cat.adoption_status == 'adoptable')

    query = query.order_by(Cat.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'cats': [cat.to_dict() for cat in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@app.route('/api/cats/<int:cat_id>', methods=['GET'])
def get_cat(cat_id):
    cat = Cat.query.get_or_404(cat_id)
    cat.view_count = (cat.view_count or 0) + 1
    db.session.commit()
    data = cat.to_dict()
    data['check_ins'] = [
        ci.to_dict() for ci in cat.check_ins.order_by(CheckIn.created_at.desc()).limit(20).all()
    ]
    return jsonify(data)


@app.route('/api/cats', methods=['POST'])
@login_required
def create_cat():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    cat = Cat(
        nickname=data.get('nickname', '未命名'),
        gender=data.get('gender'),
        color=data.get('color'),
        personality_tags=data.get('personality_tags'),
        health_status=data.get('health_status', '健康'),
        is_neutered=data.get('is_neutered') in ('true', 'True', True, '1', 1),
        latitude=try_float(data.get('latitude')),
        longitude=try_float(data.get('longitude')),
        location_description=data.get('location_description'),
        description=data.get('description'),
        age_info=data.get('age_info'),
        area_tag=data.get('area_tag'),
        adoption_status=data.get('adoption_status', 'normal'),
    )

    if 'photo' in request.files:
        file = request.files['photo']
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f'cat_{uuid.uuid4().hex}.{ext}'
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cat.photo_url = f'/api/uploads/{filename}'

    db.session.add(cat)
    db.session.commit()
    return jsonify(cat.to_dict()), 201


@app.route('/api/cats/<int:cat_id>', methods=['PUT'])
@login_required
def update_cat(cat_id):
    cat = Cat.query.get_or_404(cat_id)
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    for field in ['nickname', 'gender', 'color', 'personality_tags', 'health_status',
                  'location_description', 'description', 'age_info', 'area_tag', 'adoption_status']:
        if field in data:
            setattr(cat, field, data[field])
    if 'is_neutered' in data:
        cat.is_neutered = data['is_neutered'] in ('true', 'True', True, '1', 1)
    if 'latitude' in data:
        cat.latitude = try_float(data['latitude'])
    if 'longitude' in data:
        cat.longitude = try_float(data['longitude'])

    if 'photo' in request.files:
        file = request.files['photo']
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f'cat_{uuid.uuid4().hex}.{ext}'
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cat.photo_url = f'/api/uploads/{filename}'

    db.session.commit()
    return jsonify(cat.to_dict())


@app.route('/api/cats/<int:cat_id>', methods=['DELETE'])
@admin_required
def delete_cat(cat_id):
    cat = Cat.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    return jsonify({'message': '删除成功'})


# ===================== Check-in Routes =====================

@app.route('/api/checkins', methods=['GET'])
def list_checkins():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')
    cat_id = request.args.get('cat_id', type=int)

    query = CheckIn.query

    if status_filter:
        query = query.filter(CheckIn.status == status_filter)
    if type_filter:
        query = query.filter(CheckIn.type == type_filter)
    if cat_id:
        query = query.filter(CheckIn.cat_id == cat_id)

    query = query.order_by(CheckIn.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'checkins': [ci.to_dict() for ci in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@app.route('/api/checkins', methods=['POST'])
@login_required
def create_checkin():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    checkin = CheckIn(
        cat_id=int(data.get('cat_id', 0)),
        user_id=session['user_id'],
        type=data.get('type', 'encounter'),
        latitude=try_float(data.get('latitude'), 0),
        longitude=try_float(data.get('longitude'), 0),
        location_description=data.get('location_description'),
        comment=data.get('comment'),
        status='pending',
    )

    if 'photo' in request.files:
        file = request.files['photo']
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f'checkin_{uuid.uuid4().hex}.{ext}'
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            checkin.photo_url = f'/api/uploads/{filename}'

    db.session.add(checkin)
    db.session.commit()
    return jsonify(checkin.to_dict()), 201


@app.route('/api/checkins/<int:record_id>', methods=['PUT'])
@admin_required
def update_checkin(record_id):
    checkin = CheckIn.query.get_or_404(record_id)
    data = request.get_json() or {}
    if 'status' in data:
        checkin.status = data['status']
    if 'comment' in data:
        checkin.comment = data['comment']
    db.session.commit()
    return jsonify(checkin.to_dict())


@app.route('/api/checkins/<int:record_id>', methods=['DELETE'])
@admin_required
def delete_checkin(record_id):
    checkin = CheckIn.query.get_or_404(record_id)
    db.session.delete(checkin)
    db.session.commit()
    return jsonify({'message': '删除成功'})


# ===================== Stats Route =====================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    total_cats = Cat.query.count()
    adopted_count = Cat.query.filter(Cat.adoption_status == 'adopted').count()
    medical_count = Cat.query.filter(
        Cat.health_status.in_(['常规治疗中', '紧急救治'])
    ).count()
    healthy_count = Cat.query.filter(Cat.health_status == '健康').count()
    neutered_count = Cat.query.filter(Cat.is_neutered == True).count()
    neutered_observe_count = Cat.query.filter(
        Cat.health_status == '已绝育观察'
    ).count()
    treating_count = Cat.query.filter(Cat.health_status == '常规治疗中').count()
    emergency_count = Cat.query.filter(Cat.health_status == '紧急救治').count()
    active_volunteers = User.query.filter(User.role == 'volunteer').count()
    total_users = User.query.count()
    pending_checkins = CheckIn.query.filter(CheckIn.status == 'pending').count()

    # Area distribution
    areas = db.session.query(
        Cat.area_tag, db.func.count(Cat.cat_id)
    ).filter(Cat.area_tag.isnot(None)).group_by(Cat.area_tag).all()

    # Recent activities
    recent_checkins = CheckIn.query.order_by(
        CheckIn.created_at.desc()
    ).limit(10).all()

    return jsonify({
        'total_cats': total_cats,
        'adopted_count': adopted_count,
        'medical_count': medical_count,
        'healthy_count': healthy_count,
        'neutered_count': neutered_count,
        'neutered_observe_count': neutered_observe_count,
        'treating_count': treating_count,
        'emergency_count': emergency_count,
        'active_volunteers': active_volunteers,
        'total_users': total_users,
        'pending_checkins': pending_checkins,
        'area_distribution': [{'name': a[0], 'count': a[1]} for a in areas],
        'recent_activities': [ci.to_dict() for ci in recent_checkins],
    })


# ===================== Upload Serving =====================

@app.route('/api/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ===================== Page Routes =====================

@app.route('/')
def index_page():
    return render_template('index.html',
                           tianditu_api_key=app.config['TIANDITU_API_KEY'])


@app.route('/admin')
def admin_page():
    return render_template('admin.html')


@app.route('/archive')
def archive_page():
    return render_template('archive.html')


@app.route('/api/seed', methods=['POST'])
def seed_database():
    """Seed the database with sample data for testing."""
    if Cat.query.first():
        return jsonify({'message': '数据库已有数据，跳过种子数据'})

    # Create admin user
    admin = User(
        username='admin',
        display_name='系统管理员',
        role='admin',
        bio='系统管理员',
    )
    admin.set_password('admin123')
    db.session.add(admin)

    volunteer = User(
        username='volunteer',
        display_name='爱猫志愿者',
        role='volunteer',
        bio='热心志愿者',
    )
    volunteer.set_password('vol123')
    db.session.add(volunteer)

    # Create sample cats
    sample_cats = [
        {'nickname': '大橘', 'gender': '公猫', 'color': '橘色', 'personality_tags': '["亲人","温顺","贪吃"]',
         'health_status': '健康', 'is_neutered': True, 'latitude': 31.9162, 'longitude': 118.7833,
         'location_description': '图书馆东南角', 'description': '性格温顺，常出现在图书馆正门。喜欢吃罐头，不太怕人，是校内的明星猫。',
         'age_info': '2岁左右', 'area_tag': '北校区', 'photo_url': '/static/images/cat1.jpg'},
        {'nickname': '奶牛', 'gender': '母猫', 'color': '黑白', 'personality_tags': '["害羞","温柔","独特"]',
         'health_status': '绝育恢复中', 'is_neutered': False, 'latitude': 31.9170, 'longitude': 118.7843,
         'location_description': '东区操场旁', 'description': '黑白分明，花纹独特。比较害羞，需要耐心接触，希望能找到一个温暖的家。',
         'age_info': '1岁左右', 'area_tag': '东校区', 'adoption_status': 'adoptable', 'photo_url': '/static/images/cat2.jpg'},
        {'nickname': '小煤球', 'gender': '公猫', 'color': '黑色', 'personality_tags': '["活泼","敏捷","好奇"]',
         'health_status': '健康', 'is_neutered': True, 'latitude': 31.9173, 'longitude': 118.7813,
         'location_description': '西食堂附近', 'description': '通体全黑，眼睛亮晶晶。喜欢在操场附近活动，奔跑速度极快。',
         'age_info': '3岁', 'area_tag': '西校区', 'photo_url': '/static/images/cat3.jpg'},
        {'nickname': '小饼干', 'gender': '母猫', 'color': '玳瑁', 'personality_tags': '["胆小","安静"]',
         'health_status': '健康', 'is_neutered': False, 'latitude': 31.9155, 'longitude': 118.7823,
         'location_description': '教学楼B区', 'description': '新发现的玳瑁猫，大约6个月大，比较胆小。',
         'age_info': '约6个月', 'area_tag': '西校区', 'adoption_status': 'adoptable', 'photo_url': '/static/images/cat4.jpg'},
        {'nickname': '雪团', 'gender': '母猫', 'color': '白色', 'personality_tags': '["粘人","安静","优雅"]',
         'health_status': '常规治疗中', 'is_neutered': False, 'latitude': 31.9175, 'longitude': 118.7830,
         'location_description': '实验楼A座', 'description': '纯白长毛猫，眼睛一蓝一黄。目前在治疗皮肤病中。',
         'age_info': '幼猫', 'area_tag': '南校区', 'photo_url': '/static/images/cat5.jpg'},
        {'nickname': '煤球', 'gender': '公猫', 'color': '黑色', 'personality_tags': '["独立","警觉"]',
         'health_status': '紧急救治', 'is_neutered': False, 'latitude': 31.9190, 'longitude': 118.7827,
         'location_description': '北区宿舍后山', 'description': '玄猫，成年，近期发现腿部受伤正在治疗中。',
         'age_info': '成年', 'area_tag': '北校区', 'photo_url': '/static/images/cat6.jpg'},
    ]

    for cat_data in sample_cats:
        cat = Cat(**cat_data)
        db.session.add(cat)
    db.session.flush()

    # Create sample check-ins
    cats = Cat.query.all()
    sample_checkins = [
        {'cat_id': cats[0].cat_id, 'user_id': 2, 'type': 'feeding',
         'latitude': 31.9162, 'longitude': 118.7833,
         'location_description': '图书馆东南角',
         'comment': '大橘今天吃了整罐罐头！', 'status': 'approved'},
        {'cat_id': cats[1].cat_id, 'user_id': 2, 'type': 'encounter',
         'latitude': 31.9170, 'longitude': 118.7843,
         'location_description': '东区操场旁',
         'comment': '奶牛在操场边晒太阳，看起来很放松', 'status': 'approved'},
        {'cat_id': cats[2].cat_id, 'user_id': 2, 'type': 'encounter',
         'latitude': 31.9173, 'longitude': 118.7813,
         'location_description': '西食堂附近',
         'comment': '小煤球在食堂门口等着投喂', 'status': 'approved'},
        {'cat_id': cats[3].cat_id, 'user_id': 2, 'type': 'encounter',
         'latitude': 31.9155, 'longitude': 118.7823,
         'location_description': '教学楼B区',
         'comment': '发现一只新的玳瑁猫，暂取名小饼干', 'status': 'pending'},
        {'cat_id': cats[4].cat_id, 'user_id': 1, 'type': 'feeding',
         'latitude': 31.9175, 'longitude': 118.7830,
         'location_description': '实验楼A座',
         'comment': '雪团今天食欲不错，伤口恢复中', 'status': 'pending'},
    ]

    for ci_data in sample_checkins:
        checkin = CheckIn(**ci_data)
        db.session.add(checkin)

    db.session.commit()
    return jsonify({'message': '种子数据创建成功', 'cats_count': len(sample_cats)})


def try_float(val, default=None):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print('* Database tables created (if not exists)')
    print('* Starting server at http://localhost:5000')
    print('* Admin login: admin / admin123')
    app.run(debug=True, host='0.0.0.0', port=5000)
