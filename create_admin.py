from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin():
    username = input("Введите логин администратора: ")
    password = input("Введите пароль администратора: ")

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        print("❌ Пользователь с таким логином уже существует.")
        return

    hashed_password = generate_password_hash(password)
    admin = User(username=username, password=hashed_password, is_admin=True)
    db.session.add(admin)
    db.session.commit()
    print("✅ Администратор создан успешно.")

if __name__ == '__main__':
    with app.app_context():  # <-- ВАЖНО: создаём контекст Flask-приложения
        create_admin()
