"""
Admin routes for investment platform.
Handles admin login, dashboard, user management, deposits, withdrawals, settings, and reports.
Protects routes with admin_required.
Uses Flask, Flask-Login, MongoDB (via extensions.py), and Pandas for reporting.
"""
from flask import Blueprint, request, flash, redirect, url_for, render_template, send_file, current_app
from flask_login import login_required, current_user, login_user
from functools import wraps
from bson import ObjectId
from datetime import datetime
from werkzeug.security import check_password_hash
from extensions import db, User
import os
try:
    import pandas as pd
except ImportError:
    pd = None

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.user_data.get('is_admin'):
            flash('Admin access required')
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated

@bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user_data = db.users.find_one({'email': request.form['email'], 'is_admin': True})
        if user_data and check_password_hash(user_data['password'], request.form['password']):
            user = User(user_data)
            login_user(user)
            flash('Admin login successful!')
            return redirect(url_for('admin.dashboard'))
        flash('Invalid admin credentials')
    return render_template('login.html')

@bp.route('/')
@login_required
@admin_required
def dashboard():
    total_users = db.users.count_documents({'is_admin': False})
    # Sum of all approved deposits
    total_deposits_cursor = db.deposits.aggregate([
        {'$match': {'status': 'approved'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ])
    total_deposits = next(total_deposits_cursor, {}).get('total', 0)

    # Subtract all approved withdrawals from total deposits
    total_withdrawals_cursor = db.withdrawals.aggregate([
        {'$match': {'status': 'approved'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ])
    total_withdrawals = next(total_withdrawals_cursor, {}).get('total', 0)
    net_deposits = total_deposits - total_withdrawals

    # Sum of all pending deposits
    pending_deposits_cursor = db.deposits.aggregate([
        {'$match': {'status': 'pending'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ])
    pending_deposits = next(pending_deposits_cursor, {}).get('total', 0)

    # Sum of all pending withdrawals
    pending_withdrawals_cursor = db.withdrawals.aggregate([
        {'$match': {'status': 'pending'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ])
    pending_withdrawals = next(pending_withdrawals_cursor, {}).get('total', 0)
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_deposits=total_deposits,
                         pending_deposits=pending_deposits,
                         pending_withdrawals=pending_withdrawals)

@bp.route('/users')
@login_required
@admin_required
def users():
    search = request.args.get('search', '').strip()
    query = {}
    if search:
        query = {'$or': [
            {'full_name': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}},
            {'phone': {'$regex': search, '$options': 'i'}}
        ]}
    users_list = list(db.users.find(query))
    return render_template('admin/users.html', users=users_list, search=search)

@bp.route('/deposits')
@login_required
@admin_required
def deposits():
    status = request.args.get('status', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    user_search = request.args.get('user', '')
    
    query = {}
    if status:
        query['status'] = status
    if start_date and end_date:
        query['submitted_at'] = {
            '$gte': datetime.strptime(start_date, '%Y-%m-%d'),
            '$lte': datetime.strptime(end_date, '%Y-%m-%d')
        }
    if user_search:
        user = db.users.find_one({
            '$or': [
                {'email': {'$regex': user_search, '$options': 'i'}},
                {'full_name': {'$regex': user_search, '$options': 'i'}}
            ]
        })
        if user:
            query['user_id'] = user['_id']
    
    deposits = list(db.deposits.find(query).sort('submitted_at', -1))
    # Attach user info for display (fixes 'Unknown' user)
    users = {str(u['_id']): u for u in db.users.find()}
    for d in deposits:
        user = users.get(str(d.get('user_id')))
        d['user_data'] = user if user else {'full_name': 'Unknown'}
    return render_template('admin/deposits.html', deposits=deposits)

@bp.route('/deposits/<deposit_id>/<action>')
@login_required
@admin_required
def handle_deposit(deposit_id, action):
    if action not in ['approve', 'reject']:
        flash('Invalid action')
        return redirect(url_for('admin.deposits'))
    
    db.deposits.update_one(
        {'_id': ObjectId(deposit_id)},
        {
            '$set': {
                'status': 'approved' if action == 'approve' else 'rejected',
                'approved_at': datetime.utcnow()
            }
        }
    )
    
    flash(f'Deposit {action}d successfully')
    return redirect(url_for('admin.deposits'))

@bp.route('/withdrawals')
@login_required
@admin_required
def withdrawals():
    status = request.args.get('status', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    user_search = request.args.get('user', '')
    
    query = {}
    if status:
        query['status'] = status
    if start_date and end_date:
        query['requested_at'] = {
            '$gte': datetime.strptime(start_date, '%Y-%m-%d'),
            '$lte': datetime.strptime(end_date, '%Y-%m-%d')
        }
    if user_search:
        user = db.users.find_one({
            '$or': [
                {'email': {'$regex': user_search, '$options': 'i'}},
                {'full_name': {'$regex': user_search, '$options': 'i'}}
            ]
        })
        if user:
            query['user_id'] = user['_id']
    
    withdrawals = list(db.withdrawals.find(query).sort('requested_at', -1))
    # Attach user info for display
    users = {str(u['_id']): u for u in db.users.find()}
    for w in withdrawals:
        user = users.get(str(w.get('user_id')))
        w['user_data'] = user if user else {'full_name': 'Unknown'}
    return render_template('admin/withdrawals.html', withdrawals=withdrawals)

@bp.route('/withdrawals/<withdrawal_id>/<action>')
@login_required
@admin_required
def handle_withdrawal(withdrawal_id, action):
    if action not in ['approve', 'reject']:
        flash('Invalid action')
        return redirect(url_for('admin.withdrawals'))
    
    db.withdrawals.update_one(
        {'_id': ObjectId(withdrawal_id)},
        {
            '$set': {
                'status': 'approved' if action == 'approve' else 'rejected',
                'approved_at': datetime.utcnow()
            }
        }
    )
    
    flash(f'Withdrawal {action}d successfully')
    return redirect(url_for('admin.withdrawals'))

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if request.method == 'POST':
        interest_rate = float(request.form['interest_rate'])
        db.settings.update_one(
            {},
            {
                '$set': {
                    'interest_rate': interest_rate,
                    'updated_at': datetime.utcnow()
                }
            },
            upsert=True
        )
        flash('Interest rate updated successfully')
        return redirect(url_for('admin.settings'))
    
    settings = db.settings.find_one() or {'interest_rate': 8.0}
    return render_template('admin/settings.html', settings=settings)

@bp.route('/reports')
@login_required
@admin_required
def reports():
    if pd is None:
        flash('Pandas is not installed. Reports are not available.')
        return redirect(url_for('admin.dashboard'))
    
    report_type = request.args.get('type', '')
    if report_type == 'users':
        df = pd.DataFrame(list(db.users.find({'is_admin': False})))
        filename = 'users_report.csv'
    elif report_type == 'deposits':
        deposits = list(db.deposits.find())
        users = {str(u['_id']): u for u in db.users.find()}
        for d in deposits:
            user = users.get(str(d.get('user_id')))
            d['user_full_name'] = user['full_name'] if user else ''
            d['user_email'] = user['email'] if user else ''
            d['user_id'] = str(d.get('user_id', ''))
        df = pd.DataFrame(deposits)
        filename = 'deposits_report.csv'
    elif report_type == 'withdrawals':
        withdrawals = list(db.withdrawals.find())
        users = {str(u['_id']): u for u in db.users.find()}
        for w in withdrawals:
            user = users.get(str(w.get('user_id')))
            w['user_full_name'] = user['full_name'] if user else ''
            w['user_email'] = user['email'] if user else ''
            w['user_id'] = str(w.get('user_id', ''))
        df = pd.DataFrame(withdrawals)
        filename = 'withdrawals_report.csv'
    else:
        flash('Invalid report type')
        return redirect(url_for('admin.dashboard'))
    
    # Remove _id from report for clarity
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    # user_id is now always present and string
    
    # Save to CSV
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    df.to_csv(filepath, index=False)
    
    return send_file(filepath, as_attachment=True, mimetype='text/csv')

@bp.route('/add-admin', methods=['GET', 'POST'])
@login_required
@admin_required
def add_admin():
    # Only allow super-admins (first admin or those with a special flag) to add new admins
    # For now, allow any admin, but you can add a flag like is_super_admin for more control
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        # Validate required fields
        if not full_name or not email or not phone or not password:
            flash('All fields are required.')
            return redirect(url_for('admin.add_admin'))

        # Check for duplicate email
        if db.users.find_one({'email': email}):
            flash('Email already registered')
            return redirect(url_for('admin.add_admin'))

        # Check for duplicate phone
        if db.users.find_one({'phone': phone}):
            flash('Phone number already registered')
            return redirect(url_for('admin.add_admin'))

        # Extra: Check for valid email format (basic)
        import re
        email_regex = r'^\S+@\S+\.\S+$'
        if not re.match(email_regex, email):
            flash('Invalid email format.')
            return redirect(url_for('admin.add_admin'))

        # Extra: Check for valid phone (basic, digits only, min 7 chars)
        if not phone.isdigit() or len(phone) < 7:
            flash('Invalid phone number.')
            return redirect(url_for('admin.add_admin'))

        from werkzeug.security import generate_password_hash
        user = {
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'password': generate_password_hash(password),
            'is_admin': True,
            'created_at': datetime.utcnow()
        }
        db.users.insert_one(user)
        flash('Admin user created successfully!')
        return redirect(url_for('admin.users'))
    return render_template('admin/add_admin.html')

@bp.route('/contacts')
@login_required
@admin_required
def contacts():
    contacts = list(db.contacts.find().sort('submitted_at', -1))
    return render_template('admin/contacts.html', contacts=contacts)

@bp.route('/user-wallets')
@login_required
@admin_required
def user_wallets():
    search = request.args.get('search', '').strip()
    user_query = {'is_admin': False}
    if search:
        user_query['$or'] = [
            {'full_name': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}},
            {'phone': {'$regex': search, '$options': 'i'}}
        ]
    users = list(db.users.find(user_query))
    user_wallets = []
    from datetime import datetime as dt
    now = dt.utcnow()
    for user in users:
        deposits = list(db.deposits.find({'user_id': user['_id']}))
        withdrawals = list(db.withdrawals.find({'user_id': user['_id']}))
        total_deposit = sum(d['amount'] for d in deposits if d.get('status') == 'approved')
        total_withdrawal = sum(w['amount'] for w in withdrawals if w.get('status') == 'approved')
        real_time_interest = 0
        for d in deposits:
            if d.get('status') == 'approved':
                settings = db.settings.find_one() or {'interest_rate': 8.0}
                rate = settings.get('interest_rate', 8.0)
                principal = d.get('amount', 0)
                start = d.get('submitted_at')
                days = d.get('duration_days', 0)
                if start:
                    elapsed = (now - start).days
                    elapsed = min(elapsed, days)
                    real_time_interest += (principal * rate * (elapsed/365)) / 100
        # Wallet balance should be only interest earned minus withdrawals
        wallet_balance = real_time_interest - total_withdrawal
        user_wallets.append({
            'full_name': user.get('full_name'),
            'email': user.get('email'),
            'wallet_balance': wallet_balance,
            'total_deposit': total_deposit,
            'total_withdrawal': total_withdrawal,
            'real_time_interest': real_time_interest
        })
    return render_template('admin/user_wallets.html', user_wallets=user_wallets, search=search)
