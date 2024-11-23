import logging
import functools
from flask import(
    Blueprint,flash,g,redirect,render_template,request,session,url_for)
from werkzeug.security import check_password_hash,generate_password_hash
import connectDB
from connectDB import(
    register_member,login
    )
bp = Blueprint('auth',__name__,url_prefix='/auth')

@bp.route('/register',methods=('GET','POST'))
def register():
    if request.method =='POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
       # db = connectDB.create_connection()
        error = None
        
        if not username:
            error ='Username is required.'
        elif not password:
            error ='Password is required.'
        elif not email:
            error ='email is required.'

        if error is None:
         try:
           connectDB.register_member(username,password,email)
         except Exception as e:
             logging.error(f'error register member {e}')   
        else:        
         return redirect(url_for("auth.login"))
        

    return render_template('auth/register.html')    

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
       # db = connectDB.create_connection()
        error = None
        user = connectDB.login(username,password)

        if user is None:
            error = 'No  username. please register '
        elif not (user[2]== password):   # password 
            error = 'Incorrect password.'
        
     
        if error is None:
            session.clear()
            session['user_id'] = user[0]  # user ID
            return redirect(url_for('index',username=user[1]))  # user name
        
        #return render_template('auth/register.html')
        return redirect(url_for('auth.register'))
    return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = connectDB.get_user(user_id)

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        error =None
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view
