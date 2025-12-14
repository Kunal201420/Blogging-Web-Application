from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, ForeignKey
from flask_ckeditor import CKEditor
from forms import RegisterForm, BlogForm, LoginForm, CommentsForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, LoginManager, current_user, login_user, logout_user, login_required
from typing import List
from dotenv import load_dotenv
import datetime
import hashlib
import os

load_dotenv()






app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
Bootstrap5(app)


ckeditor = CKEditor(app)


# For adding profile images to the comment section
def gravatar_url(email, size=100, default="identicon", rating="g"):
    # Normalize the email
    email = email.strip().lower()
    # MD5 hash of the email
    email_hash = hashlib.md5(email.encode("utf-8")).hexdigest()
    # Build the Gravatar URL
    return f"https://www.gravatar.com/avatar/{email_hash}?s={size}&d={default}&r={rating}"

# Register the filter with Jinja
app.jinja_env.filters['gravatar'] = gravatar_url





#login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Blogs.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# User Table
class Users(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    posts: Mapped[List["BlogPost"]] = relationship(
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    user_comments: Mapped[List["Comments"]] = relationship(
        back_populates="comment_author",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    author: Mapped[Users] = relationship(back_populates="posts", lazy="joined")
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    blog_comments: Mapped[List["Comments"]] = relationship(
        back_populates="parent_post",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class Comments(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    comment_author: Mapped[Users] = relationship(back_populates="user_comments", lazy="joined")

    post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"), nullable=False)
    parent_post: Mapped["BlogPost"] = relationship(back_populates="blog_comments", lazy="joined")




with app.app_context():
    db.create_all()

#Loading user
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Users, int(user_id))



#Registration
@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if request.method == "POST":
        if Users.query.filter_by(email=form.email.data).first():
            flash("The email is already registered. Please login instead!", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = Users(
            name= form.name.data,
            email= form.email.data,
            password= hashed_password
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Registration Successful!", "success")
        login_user(new_user)

        return redirect(url_for('get_all_posts'))

    return render_template('register.html', form=form, logged_in=current_user.is_authenticated)

@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if request.method == "POST":
        user = Users.query.filter_by(email=form.email.data).first()
        if not user:
            flash("The email does not exist. Please register first.", "error")
            return redirect(url_for('login'))

        if not check_password_hash(user.password, form.password.data):
            flash("Wrong password. Please try again!", "danger")
            return redirect(url_for('login'))

        flash("Login Successful!", "success")
        login_user(user)
        return redirect(url_for('get_all_posts'))

    return render_template('login.html', form=form, logged_in=current_user.is_authenticated)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!")
    return redirect(url_for('get_all_posts'))


#Getting all posts
@app.route('/')
def get_all_posts():
    posts = []
    results = db.session.execute(db.select(BlogPost))
    all_posts = results.scalars().all()
    for post in all_posts:
        posts.append(post)
    return render_template("index.html", all_posts=posts,)


#Showing a post
@app.route('/show_post/<int:post_id>', methods=["GET", "POST"])
def show_post(post_id):
    comment_form = CommentsForm()
    requested_post = db.get_or_404(BlogPost, post_id)

    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comments(
                text= comment_form.comment.data,
                author_id= current_user.id,
                post_id= post_id
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('show_post', post_id=post_id))

        else:
            error = "Login required, Please log in."
            flash(error)
            return redirect(url_for('login'))

    return render_template("post.html", post=requested_post, form=comment_form)


#Creating a post
@app.route('/make-post', methods=["POST", "GET"])
@login_required
def make_post():
    form = BlogForm()
    if form.validate_on_submit():
        if request.method == "POST":
            new_blog = BlogPost(
                title = form.title.data,
                author_id = current_user.id,
                subtitle = form.subtitle.data,
                date = datetime.date.today().isoformat(),
                img_url = form.img_url.data,
                body = form.body.data
            )
            db.session.add(new_blog)
            db.session.commit()
            flash("Post Created!", "success")
            return redirect(url_for('get_all_posts'))
    return render_template('make-post.html', form=form, logged_in=current_user.is_authenticated)





#Editing a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = BlogForm(obj=post)

    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        post.date = datetime.date.today().isoformat()

        db.session.commit()
        flash("Post Edited!", "success")
        return redirect(url_for('show_post', post_id=post.id))

    return render_template("make-post.html", edit_form=edit_form, is_edit=True, logged_in=current_user.is_authenticated)


#Deleting a post
@app.route('/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Post Deleted!", "success")
    return redirect(url_for('get_all_posts'))





#about
@app.route("/about")
def about():
    return render_template("about.html")

#contact
@app.route("/contact")
def contact():
    return render_template("contact.html")



if __name__ == "__main__":
    app.run(debug=False, port=5003)





