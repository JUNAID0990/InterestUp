import csv
from flask import Response

from flask import Blueprint, request, flash, redirect, url_for, render_template, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from bson import ObjectId
from datetime import datetime
from extensions import db, calculate_simple_interest
import os

# Blueprint for deposit and withdrawal routes
bp = Blueprint('transactions', __name__)

# CSV report for all user transactions (admin only)
@bp.route('/transactions-report.csv')
@login_required
def transactions_report():
    if not getattr(current_user.user_data, 'is_admin', False):
        flash('Admin access required.')
        return redirect(url_for('dashboard'))
    # Fetch all users
    users = list(db.users.find())
    # Fetch all deposits and withdrawals
    deposits = list(db.deposits.find())
    withdrawals = list(db.withdrawals.find())
    # Prepare CSV
    def generate():
        yield 'User Name,Email,Type,Amount,Status,Date,Note\n'
        for d in deposits:
            user = next((u for u in users if u['_id'] == d['user_id']), None)
            yield f"{user.get('full_name','')},{user.get('email','')},Deposit,{d.get('amount',0)},{d.get('status','')},{d.get('submitted_at','')},{d.get('note','')}\n"
        for w in withdrawals:
            user = next((u for u in users if u['_id'] == w['user_id']), None)
            yield f"{user.get('full_name','')},{user.get('email','')},Withdrawal,{w.get('amount',0)},{w.get('status','')},{w.get('requested_at','')},{w.get('note','')}\n"
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=transactions_report.csv"})
from flask import Blueprint, request, flash, redirect, url_for, render_template, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from bson import ObjectId
from datetime import datetime
from extensions import db, calculate_simple_interest
import os

# Blueprint for deposit and withdrawal routes
bp = Blueprint('transactions', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        if amount < 500:
            flash('Minimum deposit amount is ₹500.')
            return redirect(url_for('transactions.deposit'))
        # Get duration in days from user input
        try:
            days = int(request.form.get('duration_days', 0))
            if days < 1 or days > 3650:
                raise ValueError
        except Exception:
            flash('Please enter a valid duration in days (1-3650).')
            return redirect(url_for('transactions.deposit'))

        # Get current interest rate from settings
        settings = db.settings.find_one()
        interest_rate = settings['interest_rate'] if settings else 8.0

        expected_return = calculate_simple_interest(amount, interest_rate, days/365)

        deposit = {
            'user_id': ObjectId(current_user.id),
            'amount': amount,
            'duration_days': days,
            'interest_rate': interest_rate,
            'expected_return': expected_return,
            'status': 'pending',
            'submitted_at': datetime.utcnow()
        }

        result = db.deposits.insert_one(deposit)
        return redirect(url_for('transactions.upload_proof', deposit_id=str(result.inserted_id)))

    # Pass current interest rate to template for display
    settings = db.settings.find_one() or {'interest_rate': 8.0}
    return render_template('deposit.html', settings=settings)

@bp.route('/upload-proof/<deposit_id>', methods=['GET', 'POST'])
@login_required
def upload_proof(deposit_id):
    deposit = db.deposits.find_one({'_id': ObjectId(deposit_id)})
    if not deposit or str(deposit['user_id']) != current_user.id:
        flash('Invalid deposit')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        if 'screenshot' not in request.files:
            flash('No file uploaded')
            return redirect(request.url)
        
        file = request.files['screenshot']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            
            db.deposits.update_one(
                {'_id': ObjectId(deposit_id)},
                {
                    '$set': {
                        'screenshot_url': f"uploads/{filename}",
                        'product_id': request.form['product_id'],
                        'note': request.form.get('note', '')
                    }
                }
            )
            flash('Proof uploaded successfully')
            return redirect(url_for('dashboard'))
            
        flash('Invalid file type')
        return redirect(request.url)
    
    return render_template('upload_proof.html', deposit=deposit)

@bp.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():

    if request.method == 'POST':
        amount = float(request.form['amount'])
        note = request.form.get('note', '')
        account_info = request.form.get('account_info', '').strip()

        if not account_info:
            flash('Account number or UPI ID is required for withdrawal.')
            return redirect(url_for('transactions.withdraw'))

        if amount < 500:
            flash('Minimum withdrawal amount is 500.')
            return redirect(url_for('transactions.withdraw'))

        deposits = list(db.deposits.find({'user_id': ObjectId(current_user.id)}))
        withdrawals = list(db.withdrawals.find({'user_id': ObjectId(current_user.id)}))
        from datetime import datetime as dt
        now = dt.utcnow()
        real_time_interest = 0
        for d in deposits:
            if d.get('status') == 'approved':
                settings = db.settings.find_one() or {'interest_rate': 25.0}
                rate = settings.get('interest_rate', 25.0)
                principal = d.get('amount', 0)
                start = d.get('submitted_at')
                if start:
                    elapsed = (now - start).days
                    real_time_interest += (principal * rate / 100) * elapsed
        # Hold all pending and approved withdrawals
        total_withdrawal = sum(w['amount'] for w in withdrawals if w.get('status') in ['approved', 'pending'])
        wallet_balance = real_time_interest - total_withdrawal

        if amount <= 0:
            flash('Withdrawal amount must be greater than zero.')
            return redirect(url_for('transactions.withdraw'))
        if amount > wallet_balance:
            flash(f'You can only withdraw up to your total available balance: ₹{wallet_balance:.2f}')
            return redirect(url_for('transactions.withdraw'))

        withdrawal = {
            'user_id': ObjectId(current_user.id),
            'amount': amount,
            'note': note,
            'account_info': account_info,
            'status': 'pending',
            'requested_at': datetime.utcnow()
        }

        db.withdrawals.insert_one(withdrawal)
        flash('Withdrawal request submitted')
        return redirect(url_for('dashboard'))

    # Calculate wallet_balance for template (interest only, principal is non-refundable)
    deposits = list(db.deposits.find({'user_id': ObjectId(current_user.id)}))
    withdrawals = list(db.withdrawals.find({'user_id': ObjectId(current_user.id)}))
    from datetime import datetime as dt
    now = dt.utcnow()
    real_time_interest = 0
    for d in deposits:
        if d.get('status') == 'approved':
            settings = db.settings.find_one() or {'interest_rate': 25.0}
            rate = settings.get('interest_rate', 25.0)
            principal = d.get('amount', 0)
            start = d.get('submitted_at')
            if start:
                elapsed = (now - start).days
                real_time_interest += (principal * rate / 100) * elapsed
    total_withdrawal = sum(w['amount'] for w in withdrawals if w.get('status') in ['approved', 'pending'])
    total_deposit = sum(d['amount'] for d in deposits if d.get('status') == 'approved')
    wallet_balance = real_time_interest - total_withdrawal
    return render_template('withdraw.html', wallet_balance=wallet_balance, real_time_interest=real_time_interest, total_deposit=total_deposit, total_withdrawal=total_withdrawal)
