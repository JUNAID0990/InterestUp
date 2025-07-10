from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from dotenv import load_dotenv
import os
from extensions import db, User, calculate_simple_interest
from werkzeug.utils import escape
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# ...existing code...


from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from dotenv import load_dotenv
import os
from extensions import db, User, calculate_simple_interest
from werkzeug.utils import escape
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
# Security: Set secure cookie flags for production
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None

# from flask_wtf import CSRFProtect
# csrf = CSRFProtect(app)
# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = {
            'full_name': request.form['full_name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'password': generate_password_hash(request.form['password']),
            'is_admin': False,
            'created_at': datetime.utcnow()
        }
        if db.users.find_one({'email': user['email']}):
            flash('Email already registered')
            return redirect(url_for('register'))
        db.users.insert_one(user)
        flash('Registration successful. Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        if not email or not password:
            # Missing fields
            error = 'Missing email or password.'
            return render_template('login.html', error=error), 400
        user_data = db.users.find_one({'email': email})
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
            flash('Login successful!')
            return redirect(url_for('dashboard'))
        # Wrong credentials
        error = 'Invalid email or password.'
        return render_template('login.html', error=error), 401
    return render_template('login.html', error=None)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.')
    return redirect(url_for('login'))

@app.route('/help')
def help_page():
    return render_template('help.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = escape(request.form.get('name', '').strip())
        email = escape(request.form.get('email', '').strip())
        message = escape(request.form.get('message', '').strip())
        if not name or not email or not message:
            flash('All fields are required.')
            return render_template('contact.html')
        # Save to DB (secure, no email sent)
        db.contacts.insert_one({
            'name': name,
            'email': email,
            'message': message,
            'submitted_at': datetime.utcnow()
        })
        flash('Your message has been received. We will contact you soon!')
        return render_template('contact.html')
    return render_template('contact.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_data.get('is_admin'):
        return redirect(url_for('admin.dashboard'))
    deposits = list(db.deposits.find({'user_id': ObjectId(current_user.id)}))
    withdrawals = list(db.withdrawals.find({'user_id': ObjectId(current_user.id)}))

    # Calculate wallet balance (approved deposits - approved withdrawals + real-time interest)
    total_deposit = sum(d['amount'] for d in deposits if d.get('status') == 'approved')
    total_withdrawal = sum(w['amount'] for w in withdrawals if w.get('status') == 'approved')

    # Real-time interest calculation for each approved deposit (by days)
    from datetime import datetime as dt
    now = dt.utcnow()
    real_time_interest = 0
    for d in deposits:
        if d.get('status') == 'approved':
            # Use up-to-date interest rate from settings for each deposit
            settings = db.settings.find_one() or {'interest_rate': 8.0}
            rate = settings.get('interest_rate', 8.0)
            principal = d.get('amount', 0)
            start = d.get('submitted_at')
            days = d.get('duration_days', 0)
            if start:
                elapsed = (now - start).days
                elapsed = min(elapsed, days)
                # Fix: Calculate interest as annualized, by days
                real_time_interest += (principal * rate * (elapsed/365)) / 100


    wallet_balance = real_time_interest

    # Transaction history: combine deposits and withdrawals, sort by date
    history = []
    for d in deposits:
        h = dict(type='Deposit', amount=d['amount'], status=d.get('status'), date=d.get('submitted_at'), note=d.get('note', ''), id=str(d.get('_id')))
        history.append(h)
    for w in withdrawals:
        h = dict(type='Withdrawal', amount=w['amount'], status=w.get('status'), date=w.get('requested_at'), note=w.get('note', ''), id=str(w.get('_id')))
        history.append(h)
    history.sort(key=lambda x: x['date'], reverse=True)

    return render_template('dashboard.html', deposits=deposits, withdrawals=withdrawals, wallet_balance=wallet_balance, real_time_interest=real_time_interest, total_deposit=total_deposit, total_withdrawal=total_withdrawal, history=history)

# Wallet page
@app.route('/wallet')
@login_required
def wallet():
    if current_user.user_data.get('is_admin'):
        return redirect(url_for('admin.dashboard'))
    deposits = list(db.deposits.find({'user_id': ObjectId(current_user.id)}))
    # withdrawals and totals are not needed for withdrawable balance, but keep for display
    withdrawals = list(db.withdrawals.find({'user_id': ObjectId(current_user.id)}))
    total_deposit = sum(d['amount'] for d in deposits if d.get('status') == 'approved')
    total_withdrawal = sum(w['amount'] for w in withdrawals if w.get('status') == 'approved')
    from datetime import datetime as dt
    now = dt.utcnow()
    # Calculate daily interest (principal * rate / 100) * days since deposit
    real_time_interest = 0
    for d in deposits:
        if d.get('status') == 'approved':
            settings = db.settings.find_one() or {'interest_rate': 25.0}
            rate = settings.get('interest_rate', 25.0)  # Default to 25% daily if not set
            principal = d.get('amount', 0)
            start = d.get('submitted_at')
            if start:
                elapsed = (now - start).days
                # Daily interest: principal * rate% * days
                real_time_interest += (principal * rate / 100) * elapsed
    # Only interest is withdrawable, principal is non-refundable
    wallet_balance = real_time_interest - total_withdrawal
    # Ensure wallet_balance is always defined for the template
    return render_template(
        'wallet.html',
        wallet_balance=wallet_balance or 0,
        real_time_interest=real_time_interest or 0,
        total_deposit=total_deposit or 0,
        total_withdrawal=total_withdrawal or 0
    )

# History page
@app.route('/history')
@login_required
def history():
    if current_user.user_data.get('is_admin'):
        return redirect(url_for('admin.dashboard'))
    deposits = list(db.deposits.find({'user_id': ObjectId(current_user.id)}))
    withdrawals = list(db.withdrawals.find({'user_id': ObjectId(current_user.id)}))
    history = []
    for d in deposits:
        h = dict(type='Deposit', amount=d['amount'], status=d.get('status'), date=d.get('submitted_at'), note=d.get('note', ''), id=str(d.get('_id')))
        history.append(h)
    for w in withdrawals:
        h = dict(type='Withdrawal', amount=w['amount'], status=w.get('status'), date=w.get('requested_at'), note=w.get('note', ''), id=str(w.get('_id')))
        history.append(h)
    history.sort(key=lambda x: x['date'], reverse=True)
    return render_template('history.html', history=history)

# Register blueprints
from routes.transactions import bp as transactions_bp
from routes.admin import bp as admin_bp
app.register_blueprint(transactions_bp)
app.register_blueprint(admin_bp)


# Article detail route to resolve BuildError
@app.route('/article/<int:article_id>')
def article(article_id):
    # You can fetch article data from a database or static list here
    # For now, just pass the id to the template
    return render_template('article.html', article_id=article_id)

# Main entry point
if __name__ == '__main__':
    app.run(debug=True)
