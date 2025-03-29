from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from forms import StudentForm, RoomForm, StudentSearchForm, LoginForm, AddUserForm
import os
import pytz
from datetime import datetime, timezone
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # если пользователь не вошёл — перенаправить на /login
login_manager.login_message = "Пожалуйста, войдите в систему"
login_manager.login_message_category = "warning"
app.config['SECRET_KEY'] = 'supersecretkey'
base_dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(base_dir, "dormitory.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# 🚀 Модель комнаты
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)
    room_type = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"<Room {self.number} - {self.room_type}>"

# 🚀 Модель жильцов
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    room_number = db.Column(db.Integer, db.ForeignKey('room.number'), nullable=False)
    room_type = db.Column(db.String(50), nullable=True)
    payment_status = db.Column(db.String(50), default="Не оплачено")
    check_in_date = db.Column(db.Date, default=datetime.utcnow)
    check_out_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Student {self.name}, Room {self.room_number}>"
    
# 🚀 Модель истории поселения    
class SettlementHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    room_number = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(50), nullable=True)
    payment_status = db.Column(db.String(50), nullable=True)
    check_in_date = db.Column(db.Date, nullable=True)
    check_out_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    action_type = db.Column(db.String(20), nullable=False)  # "выселение", "удаление"
    action_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<История: {self.student_name} - {self.action_type}>"

# Модель пользователя (сотрудника)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))  # Кто выполнил
    action = db.Column(db.String(255))    # Что сделал
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Когда сделал

    def __repr__(self):
        return f"<AuditLog {self.username} - {self.action}>"

def log_action(action):
    if current_user.is_authenticated:
        log = AuditLog(username=current_user.username, action=action)
        db.session.add(log)
        db.session.commit()


@app.route('/')
def home():
    return render_template('index.html')
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Вы успешно вошли", "success")
            return redirect(url_for("home"))
        flash("Неверный логин или пароль", "danger")
    return render_template("login.html", form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Вы вышли из системы", "info")
    return redirect(url_for("login"))

@app.route('/add-user', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        flash("Доступ только для администратора", "danger")
        return redirect(url_for("home"))

    form = AddUserForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(username=form.username.data).first()
        if existing:
            flash("Пользователь с таким логином уже существует", "danger")
            return redirect(url_for("add_user"))

        new_user = User(
            username=form.username.data,
            password=generate_password_hash(form.password.data),
            is_admin=form.is_admin.data
        )
        db.session.add(new_user)
        db.session.commit()
        log_action(f"добавил пользователя: {form.username.data}")
        flash("Пользователь создан!", "success")
        return redirect(url_for("home"))

    return render_template('add_user.html', form=form)

@app.route('/users')
@login_required
def users():
    if not current_user.is_admin:
        flash("Доступ только для администратора", "danger")
        return redirect(url_for("home"))

    all_users = User.query.all()
    return render_template('users.html', users=all_users)

@app.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash("Доступ только для администратора", "danger")
        return redirect(url_for("home"))

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash("Пользователь удалён", "success")
    else:
        flash("Пользователь не найден", "danger")

    return redirect(url_for("users"))


# 🚀 Страница списка комнат
@app.route('/rooms')
@login_required
def rooms():
    all_rooms = Room.query.all()
    return render_template('rooms.html', rooms=all_rooms)

# 🚀 Страница добавления комнаты
@app.route('/add-room', methods=['GET', 'POST'])
@login_required
def add_room():
    if not current_user.is_admin:
        flash("Доступ только для администратора", "danger")
        return redirect(url_for("home"))

    form = RoomForm()

    if form.validate_on_submit():
        existing_room = Room.query.filter_by(number=form.number.data).first()
        if existing_room:
            flash("Ошибка: Комната с таким номером уже существует!", "danger")
            return redirect(url_for("add_room"))

        new_room = Room(
            number=form.number.data,
            room_type=form.room_type.data
        )

        db.session.add(new_room)
        db.session.commit()
        log_action(f"добавил комнату: {new_room.number}")
        flash("Комната успешно добавлена!", "success")
        return redirect(url_for("rooms"))

    return render_template('add_room.html', form=form)

# 🚀 Маршрут для удаления комнаты
@app.route('/delete-room/<int:id>', methods=['POST'])
@login_required
def delete_room(id):
    if not current_user.is_admin:
        flash("Доступ только для администратора", "danger")
        return redirect(url_for("home"))

    room = Room.query.get(id)

    if not room:
        flash("Ошибка: Комната не найдена!", "danger")
        return redirect(url_for("rooms"))

    # Проверяем, есть ли жильцы в этой комнате
    occupied = Student.query.filter_by(room_number=room.number).first()
    
    if occupied:
        flash("Ошибка: Нельзя удалить комнату, в которой живут жильцы!", "danger")
        return redirect(url_for("rooms"))
    
    log_action(f"удалил комнату: {room.number}")
    db.session.delete(room)
    db.session.commit()
    flash("Комната успешно удалена!", "success")

    return redirect(url_for('rooms'))

# 🚀 Страница списка жильцов
@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    form = StudentSearchForm(request.args)
    query = Student.query

    if form.name.data:
        query = query.filter(Student.name.ilike(f"%{form.name.data}%"))
    if form.room_number.data:
        query = query.filter(Student.room_number == form.room_number.data)
    if form.payment_status.data:
        query = query.filter(Student.payment_status == form.payment_status.data)

    filtered_students = query.order_by(Student.room_number).all()

    return render_template('students.html', students=filtered_students, form=form)


# 🚀 Страница добавления жильца
@app.route('/add-student', methods=['GET', 'POST'])
@login_required
def add_student():
    form = StudentForm()

    # Формируем список только свободных комнат
    available_rooms = []
    all_rooms = Room.query.order_by(Room.number).all()
    for room in all_rooms:
        existing = Student.query.filter_by(room_number=room.number).count()
        if room.room_type == "Одноместная" and existing < 1:
            available_rooms.append((room.number, f"{room.number} (одноместная)"))
        elif room.room_type == "Двухместная" and existing < 2:
            available_rooms.append((room.number, f"{room.number} (двухместная)"))

    form.room_number.choices = available_rooms

    # Автозаполнение типа комнаты (при первом открытии страницы или при ошибке)
    if form.room_number.data:
        selected_room = Room.query.filter_by(number=form.room_number.data).first()
        if selected_room:
            form.room_type.data = selected_room.room_type

    if form.validate_on_submit():
        room_number = form.room_number.data
        room = Room.query.filter_by(number=room_number).first()

        if not room:
            flash("Ошибка: выбранная комната не найдена.", "danger")
            return redirect(url_for("add_student"))

        existing_count = Student.query.filter_by(room_number=room_number).count()
        if room.room_type == "Одноместная" and existing_count >= 1:
            flash("Ошибка: Эта одноместная комната уже занята!", "danger")
            return redirect(url_for("add_student"))
        if room.room_type == "Двухместная" and existing_count >= 2:
            flash("Ошибка: В этой двухместной комнате уже 2 человека!", "danger")
            return redirect(url_for("add_student"))

        new_student = Student(
            name=form.name.data,
            phone=form.phone.data,
            room_number=room_number,
            room_type=room.room_type,
            payment_status=form.payment_status.data,
            check_in_date=form.check_in_date.data,
            check_out_date=form.check_out_date.data,
            notes=form.notes.data
        )
        db.session.add(new_student)
        db.session.commit()
        log_action(f"добавил жильца: {new_student.name}")
        flash("Жилец успешно добавлен!", "success")
        return redirect(url_for("students"))

    return render_template("add_student.html", form=form)


# Новый маршрут для получения типа комнаты по номеру комнаты
@app.route('/get-room-type/<int:room_number>', methods=['GET'])
def get_room_type(room_number):
    room = Room.query.filter_by(number=room_number).first()
    if room:
        return jsonify({'room_type': room.room_type})
    else:
        return jsonify({'error': 'Комната не найдена'}), 404
        
# 🚀 Маршрут для редактирования жильца
@app.route('/edit-student/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_student(id):
    student = Student.query.get_or_404(id)  # Получаем студента по ID
    form = StudentForm(obj=student)  # Создаем форму с данными текущего студента

    # Обновляем список доступных комнат в поле room_number
    available_rooms = Room.query.all()
    form.room_number.choices = [(room.number, f"Комната {room.number} ({room.room_type})") for room in available_rooms]
    
    # Обновляем список доступных типов комнат
    form.room_type.choices = [("Одноместная", "Одноместная"), ("Двухместная", "Двухместная")]

    if form.validate_on_submit():  # Если форма прошла валидацию
        student.name = form.name.data
        student.phone = form.phone.data
        student.room_number = form.room_number.data
        student.room_type = form.room_type.data
        student.payment_status = form.payment_status.data
        student.check_in_date = form.check_in_date.data if form.check_in_date.data else None
        student.check_out_date = form.check_out_date.data if form.check_out_date.data else None
        student.notes = form.notes.data

        db.session.commit()  # Сохраняем изменения в базе
        log_action(f"отредактировал жильца: {student.name}")
        flash("Данные жильца обновлены!", "success")  # Уведомление об успешном редактировании
        return redirect(url_for("students"))  # Перенаправляем на страницу списка жильцов

    return render_template('edit_student.html', form=form, student=student)  # Отображаем форму для редактирования

# 🚀 Маршрут для удаления жильца
@app.route('/delete-student/<int:id>', methods=['POST'])
@login_required
def delete_student(id):
    if not current_user.is_admin:
        flash("Доступ только для администратора", "danger")
        return redirect(url_for("home"))

    student = Student.query.get(id)
    if student:
        # Сохраняем информацию в историю перед удалением
        history_entry = SettlementHistory(
            student_name=student.name,
            phone=student.phone,
            room_number=student.room_number,
            room_type=student.room_type,
            payment_status=student.payment_status,
            check_in_date=student.check_in_date,
            check_out_date=student.check_out_date,
            notes=student.notes,
            action_type="удаление"
        )
        db.session.add(history_entry)

        # Удаляем студента
        log_action(f"удалил жильца: {student.name}")
        db.session.delete(student)
        db.session.commit()
        flash("Жилец удалён. Запись добавлена в историю.", "success")
    else:
        flash("Жилец не найден!", "danger")

    return redirect(url_for('students'))

    
# 🚀 Маршрут для редактирования комнаты
@app.route('/edit-room/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_room(id):
    if not current_user.is_admin:
        flash("Доступ только для администратора", "danger")
        return redirect(url_for("home"))

    room = Room.query.get_or_404(id)
    form = RoomForm(obj=room)

    # Проверяем, занята ли комната
    occupied = Student.query.filter_by(room_number=room.number).first()
    
    if occupied:
        flash("Ошибка: Нельзя редактировать комнату, в которой уже живут жильцы!", "danger")
        return redirect(url_for("rooms"))

    if form.validate_on_submit():
        # Проверяем, если номер уже существует (кроме текущей комнаты)
        existing_room = Room.query.filter(Room.number == form.number.data, Room.id != id).first()
        if existing_room:
            flash("Ошибка: Комната с таким номером уже существует!", "danger")
            return redirect(url_for("edit_room", id=id))

        room.number = form.number.data
        room.room_type = form.room_type.data

        db.session.commit()
        log_action(f"отредактировал комнату: {room.number}")
        flash("Данные комнаты обновлены!", "success")
        return redirect(url_for("rooms"))

    return render_template('edit_room.html', form=form, room=room)
    
@app.route('/evict-student/<int:id>', methods=['POST'])
@login_required
def evict_student(id):
    student = Student.query.get(id)
    if student:
        # Запись в историю
        history_entry = SettlementHistory(
            student_name=student.name,
            phone=student.phone,
            room_number=student.room_number,
            room_type=student.room_type,
            payment_status=student.payment_status,
            check_in_date=student.check_in_date,
            check_out_date=datetime.utcnow(),
            notes=student.notes,
            action_type="выселение"
        )
        db.session.add(history_entry)

        # Обновление поля check_out_date у текущего жильца
        student.check_out_date = datetime.utcnow()
        db.session.commit()
        log_action(f"выселил жильца: {student.name}, комната {student.room_number}")

        flash("Жилец выселен. Запись добавлена в историю.", "success")
    else:
        flash("Жилец не найден!", "danger")

    return redirect(url_for('students'))

@app.route('/audit-log')
@login_required
def audit_log():
    if not current_user.is_admin:
        flash("Доступ только для администратора", "danger")
        return redirect(url_for("home"))

    username_filter = request.args.get("username", "").strip()
    action_filter = request.args.get("action", "").strip()

    query = AuditLog.query

    if username_filter:
        query = query.filter(AuditLog.username.ilike(f"%{username_filter}%"))
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))

    logs = query.order_by(AuditLog.timestamp.desc()).all()

    return render_template("audit_log.html", logs=logs)


@app.route('/history')
@login_required
def history():
    if not current_user.is_admin:
        flash("Доступ только для администратора", "danger")
        return redirect(url_for("home"))

    all_history = SettlementHistory.query.order_by(SettlementHistory.action_date.desc()).all()
    return render_template("history.html", history=all_history, pytz=pytz)

@app.route('/report')
@login_required
def report():
    if not current_user.is_admin:
        flash("Доступ только для администратора", "danger")
        return redirect(url_for("home"))

    total_rooms = Room.query.count()
    total_students = Student.query.filter_by(check_out_date=None).count()

    # Занятость комнат
    occupied_rooms = db.session.query(Student.room_number).filter(Student.check_out_date == None).distinct().count()
    free_rooms = total_rooms - occupied_rooms

    # Оплата
    paid = Student.query.filter_by(payment_status="Оплачено", check_out_date=None).count()
    unpaid = Student.query.filter_by(payment_status="Не оплачено", check_out_date=None).count()

    # Выселения
    history_evicts = SettlementHistory.query.filter_by(action_type="выселение").count()

    return render_template("report.html",
                           total_rooms=total_rooms,
                           total_students=total_students,
                           occupied_rooms=occupied_rooms,
                           free_rooms=free_rooms,
                           paid=paid,
                           unpaid=unpaid,
                           history_evicts=history_evicts)
                           


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
