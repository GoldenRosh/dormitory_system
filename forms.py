from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField, DateField, IntegerField
from wtforms.validators import DataRequired, Length, Optional
from wtforms import PasswordField
from wtforms import BooleanField


class LoginForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Войти")
    
class StudentForm(FlaskForm):
    name = StringField("ФИО", validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField("Телефон", validators=[Optional(), Length(max=20)])
    room_number = SelectField("Номер комнаты", coerce=int)  # Теперь выбор из списка
    room_type = StringField("Тип комнаты", render_kw={'readonly': True})  # Сделано readonly
    payment_status = SelectField("Оплата", choices=[("Оплачено", "Оплачено"), ("Не оплачено", "Не оплачено")])
    check_in_date = DateField("Дата заселения", format='%Y-%m-%d', validators=[Optional()])
    check_out_date = DateField("Дата выселения", format='%Y-%m-%d', validators=[Optional()])
    notes = TextAreaField("Комментарий", validators=[Optional()])
    submit = SubmitField("Добавить жильца")
    
class StudentSearchForm(FlaskForm):
    name = StringField("ФИО", validators=[Optional()])
    room_number = StringField("Номер комнаты", validators=[Optional()])
    payment_status = SelectField("Оплата", choices=[
        ("", "Любой"),
        ("Оплачено", "Оплачено"),
        ("Не оплачено", "Не оплачено")
    ], validators=[Optional()])
    submit = SubmitField("Поиск")

class RoomForm(FlaskForm):
    number = IntegerField("Номер комнаты", validators=[DataRequired()])
    room_type = SelectField("Тип комнаты", choices=[("Одноместная", "Одноместная"), ("Двухместная", "Двухместная")])
    submit = SubmitField("Добавить комнату")
    

class AddUserForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired(), Length(min=3, max=100)])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=4)])
    is_admin = BooleanField("Администратор")
    submit = SubmitField("Создать пользователя")
