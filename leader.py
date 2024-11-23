import logging
import functools
from flask import(
    Blueprint,flash,g,redirect,render_template,request,session,url_for)
from werkzeug.security import check_password_hash,generate_password_hash
import connectDB
from connectDB import(
    register_member,login
    )
bp = Blueprint('leader',__name__,url_prefix='/leaders')

@bp.route('/leader',methods=('GET','POST'))
def leader():
  
    return render_template('leaders/leader.html')    



