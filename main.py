import flask
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, UserForm, LogIn, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
import os
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
log_in_manager = LoginManager()
log_in_manager.init_app(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = relationship('User', back_populates='posts')
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = relationship('Comment', back_populates='parent_post')

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    comment_author = relationship('User', back_populates='comment')
    parent_post = relationship('BlogPost', back_populates="comments")

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = relationship('BlogPost', back_populates='author')
    comment = relationship('Comment', back_populates='comment_author')


with app.app_context():
    db.create_all()

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return flask.abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function


@log_in_manager.user_loader
def load_user(id):
    return User.query.get(id)

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated, year=date.today().year)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = UserForm()
    if form.validate_on_submit():
        email = request.form.get("email")
        if User.query.filter_by(email=email).first():
            flash("The email id already exists. Please enter the password to log in.")
            return redirect(url_for('login'))
        else:
            password = request.form.get('password')
            hash_password = generate_password_hash(password=password, method="pbkdf2:sha256", salt_length=8)
            user = User(
                email = email,
                password = hash_password,
                name = request.form.get('name')
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form, year=date.today().year)


@app.route('/login', methods=['POST', 'GET'])
def login():
    log_in = LogIn()
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            database_email = User.query.filter_by(email=email).first()
            hash_password = database_email.password
            if check_password_hash(pwhash=hash_password, password=password):
                user =load_user(database_email.id)
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Invalid credentials. Please check the password you've entered and try again")
                return redirect(url_for('login'))
        except AttributeError:
            flash("The Email you've entered doesn't exists. Please try again.")
            return redirect(url_for('login'))
    return render_template("login.html", form=log_in, year=date.today().year)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET','POST'])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comment = CommentForm()
    all_comments = db.session.query(Comment).all()
    if request.method == "POST":
        if comment.validate_on_submit() and current_user.is_authenticated:
            add_comment = Comment(
                text = request.form.get("comment"),
                comment_author = current_user,
                parent_post = requested_post
            )
            db.session.add(add_comment)
            db.session.commit()
            return redirect(url_for('get_all_posts'))
        else:
            flash("Kindly Log-in/Register to comment on a post.")
            return redirect(url_for("login"))
    return render_template("post.html", post=requested_post, comments=comment, all_comments=all_comments, logged_in=current_user.is_authenticated, year=date.today().year)


@app.route("/about")
def about():
    return render_template("about.html", year=date.today().year)


@app.route("/contact")
def contact():
    return render_template("contact.html", year=date.today().year)


@app.route("/new-post", methods=['GET','POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, year=date.today().year)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, year=date.today().year)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

#
# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    app.run(debug=True)
