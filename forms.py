from flask_ckeditor import CKEditorField
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, URLField, PasswordField
from wtforms.validators import DataRequired, URL

#User Registration Form
class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


#Blog Creation Form
class BlogForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    subtitle = StringField('Subtitle', validators=[DataRequired()])
    img_url = StringField('Img_URL', validators=[DataRequired(), URL()] )
    body = CKEditorField('Blog Content', validators=[DataRequired()])
    submit = SubmitField("Publish")

#Login form
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")

#Comments form
class CommentsForm(FlaskForm):
    comment = CKEditorField("Comment")
    submit = SubmitField("Submit")



