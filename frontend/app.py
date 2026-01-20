"""
Barcode Buddy Frontend - Flask Web Application
Main application file with routes and API integration
"""

import os
import requests
import jwt
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
ITEMS_SERVICE_URL = os.getenv('ITEMS_SERVICE_URL', 'https://item-service-dev.ronstad.se')
USERS_SERVICE_URL = os.getenv('USERS_SERVICE_URL', 'https://user-service-dev.ronstad.se')
TRANSACTIONS_SERVICE_URL = os.getenv('TRANSACTIONS_SERVICE_URL', 'https://payment-service-dev.ronstad.se')
KC_URL = os.getenv('KC_URL', 'https://keycloak.ronstad.se')
KC_REALM = os.getenv('KC_REALM', 'BB')
KC_CLIENT_ID = os.getenv('KC_CLIENT_ID', 'public-user')
INSECURE = os.getenv('INSECURE', 'false').lower() == 'true'

# Auth decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if not session.get('is_admin', False):
            flash('Admin privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function to make authenticated requests
def make_request(method, url, **kwargs):
    """Make authenticated request to microservices"""
    headers = kwargs.pop('headers', {})
    if 'access_token' in session:
        headers['Authorization'] = f"Bearer {session['access_token']}"
    
    try:
        response = requests.request(
            method, 
            url, 
            headers=headers, 
            verify=not INSECURE, 
            timeout=15,
            **kwargs
        )
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None

# Routes
@app.route('/')
def index():
    """Homepage"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        token_url = f"{KC_URL}/realms/{KC_REALM}/protocol/openid-connect/token"
        data = {
            "grant_type": "password",
            "client_id": KC_CLIENT_ID,
            "username": username,
            "password": password,
        }
        
        try:
            response = requests.post(token_url, data=data, verify=not INSECURE, timeout=15)
            
            if response.status_code == 200:
                token_data = response.json()
                session['access_token'] = token_data.get('access_token')
                session['refresh_token'] = token_data.get('refresh_token')
                session['username'] = username
                
                # Decode JWT locally to check admin status and get user info
                try:
                    jwt_info = jwt.decode(token_data.get('access_token'), options={"verify_signature": False})
                    session['is_admin'] = 'bb_admin' in jwt_info.get('realm_access', {}).get('roles', [])
                    session['user_id'] = jwt_info.get('sub')
                    # Store preferred_username (card_id) from JWT
                    session['card_id'] = jwt_info.get('preferred_username')
                except Exception as e:
                    logger.error(f"Failed to decode JWT: {e}")
                    session['is_admin'] = False
                    session['card_id'] = username  # Fallback to username
                
                flash(f'Welcome back, {username}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'danger')
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    # Get user's balance
    user_balance = None
    card_id = session.get('card_id')
    if card_id:
        try:
            user_id = int(card_id)
            response = make_request('POST', f"{USERS_SERVICE_URL}/user/fetch_info", 
                                  json={'user_id': user_id})
            if response and response.status_code == 200:
                user_balance = response.json().get('balance', 0) / 100  # Convert öre to kr
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to fetch user balance: {e}")
    
    return render_template('dashboard.html', user_balance=user_balance)

# ITEMS ROUTES
@app.route('/items')
@login_required
def items_list():
    """List all items"""
    # Admins can see all items (including inactive), regular users only see active
    active_only = not session.get('is_admin', False)
    response = make_request('POST', f"{ITEMS_SERVICE_URL}/items/list", json={"active_only": active_only})
    items = []
    
    if response and response.status_code == 200:
        items = response.json().get('items', [])
    else:
        if response:
            logger.error(f"Items list failed: {response.status_code} - {response.text}")
    
    return render_template('items/list.html', items=items)

@app.route('/items/create', methods=['GET', 'POST'])
@admin_required
def items_create():
    """Create new item"""
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'price': int(request.form.get('price')),
            'barcode_id': int(request.form.get('barcode_id')) if request.form.get('barcode_id') else None,
        }
        
        response = make_request('POST', f"{ITEMS_SERVICE_URL}/items", json=data)
        
        if response and response.status_code in [200, 201]:
            flash('Item created successfully!', 'success')
            return redirect(url_for('items_list'))
        else:
            flash('Failed to create item.', 'danger')
    
    return render_template('items/create.html')

@app.route('/items/<item_id>/edit', methods=['GET', 'POST'])
@admin_required
def items_edit(item_id):
    """Edit item"""
    if request.method == 'POST':
        data = {
            'item_id': item_id,
            'name': request.form.get('name'),
            'price': int(request.form.get('price')),
            'barcode_id': int(request.form.get('barcode_id')) if request.form.get('barcode_id') else None,
        }
        
        response = make_request('PUT', f"{ITEMS_SERVICE_URL}/items/update", json=data)
        
        if response and response.status_code == 200:
            flash('Item updated successfully!', 'success')
            return redirect(url_for('items_list'))
        else:
            flash('Failed to update item.', 'danger')
    
    # Fetch item info
    response = make_request('POST', f"{ITEMS_SERVICE_URL}/items/fetch_info", json={'item_id': item_id})
    item = {}
    if response and response.status_code == 200:
        item = response.json()
    
    return render_template('items/edit.html', item=item)

@app.route('/items/<item_id>/toggle-status', methods=['POST'])
@admin_required
def items_toggle_status(item_id):
    """Toggle item active status"""
    active = request.form.get('active') == 'true'
    
    response = make_request('POST', f"{ITEMS_SERVICE_URL}/items/set_status", 
                          json={'item_id': item_id, 'item_status': active})
    
    if response and response.status_code == 200:
        flash('Item status updated!', 'success')
    else:
        flash('Failed to update item status.', 'danger')
    
    return redirect(url_for('items_list'))

@app.route('/items/<item_id>/delete', methods=['POST'])
@admin_required
def items_delete(item_id):
    """Delete (soft delete) item"""
    response = make_request('DELETE', f"{ITEMS_SERVICE_URL}/items/delete", 
                          json={'item_id': item_id})
    
    if response and response.status_code == 200:
        flash('Item deleted successfully!', 'success')
    else:
        flash('Failed to delete item.', 'danger')
    
    return redirect(url_for('items_list'))

# USERS ROUTES
@app.route('/users')
@login_required
def users_list():
    """List all users (simplified - you may need to add a list endpoint to your user service)"""
    return render_template('users/list.html')

@app.route('/users/create', methods=['GET', 'POST'])
def users_create():
    """Create new user (public route)"""
    if request.method == 'POST':
        data = {
            'card_id': int(request.form.get('card_id', 0)),
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'email': request.form.get('email'),
            'password': request.form.get('password'),
        }
        
        logger.info(f"Attempting to create user with data: {data}")
        response = make_request('POST', f"{USERS_SERVICE_URL}/users", json=data)
        
        if response and response.status_code in [200, 201]:
            logger.info(f"User created successfully: {response.json()}")
            flash('User created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            if response:
                logger.error(f"User creation failed: Status={response.status_code}, Body={response.text}")
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', 'Failed to create user.')
                except:
                    error_msg = 'Failed to create user. Server error.'
            else:
                logger.error("User creation failed: No response from service")
                error_msg = 'Failed to create user. Service unavailable.'
            flash(error_msg, 'danger')
    
    return render_template('users/create.html')

@app.route('/users/add-funds', methods=['GET', 'POST'])
@login_required
def users_add_funds():
    """Add funds to current user's account"""
    # Get user_id (card_id) from session
    user_id = None
    if 'card_id' in session:
        try:
            user_id = int(session['card_id'])
        except (ValueError, TypeError):
            pass
    
    if not user_id:
        logger.error(f"Could not extract card_id from session: {session.keys()}")
        flash('Could not retrieve user information. Please log in again.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Check if receipt image was uploaded
        if 'receipt' not in request.files or request.files['receipt'].filename == '':
            flash('Please upload a payment receipt.', 'danger')
            return redirect(url_for('users_add_funds'))
        
        receipt = request.files['receipt']
        
        # Validate file is an image
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        if not ('.' in receipt.filename and receipt.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            flash('Please upload a valid image file (PNG, JPG, GIF).', 'danger')
            return redirect(url_for('users_add_funds'))
        
        # Get amount (convert kronor to öre)
        try:
            amount = int(request.form.get('amount', 0)) * 100  # Convert kr to öre
        except (ValueError, TypeError):
            flash('Please enter a valid amount.', 'danger')
            return redirect(url_for('users_add_funds'))
        
        if amount <= 0:
            flash('Please enter a positive amount.', 'danger')
            return redirect(url_for('users_add_funds'))
        
        # For now, we'll just process the request directly
        # In production, you'd store the receipt and create a pending request for admin approval
        data = {
            'card_id': user_id,
            'amount': amount,
        }
        
        response = make_request('POST', f"{USERS_SERVICE_URL}/user/add_balance", json=data)
        
        if response and response.status_code == 200:
            new_balance = response.json().get('new_balance', 0) / 100  # Convert back to kr
            flash(f'Funds added successfully! Your new balance is {new_balance:.2f} kr.', 'success')
            return redirect(url_for('dashboard'))
        else:
            error_msg = response.json().get('detail', 'Failed to add funds.') if response else 'Failed to add funds.'
            flash(error_msg, 'danger')
    
    return render_template('users/add_funds.html', user_id=user_id)

@app.route('/users/<int:user_id>')
@login_required
def users_view(user_id):
    """View user details"""
    # Check if user can access this profile (self or admin)
    if not session.get('is_admin', False):
        # Here you'd check if user_id matches current user's card_id
        pass
    
    response = make_request('POST', f"{USERS_SERVICE_URL}/user/fetch_info", 
                          json={'user_id': user_id})
    
    user = {}
    if response and response.status_code == 200:
        user = response.json()
    
    return render_template('users/view.html', user=user, user_id=user_id)

@app.route('/users/<int:user_id>/add-balance', methods=['POST'])
@login_required
def users_add_balance(user_id):
    """Add balance to user"""
    amount = int(request.form.get('amount', 0))
    
    response = make_request('POST', f"{USERS_SERVICE_URL}/user/add_balance", 
                          json={'card_id': user_id, 'amount': amount})
    
    if response and response.status_code == 200:
        flash('Balance added successfully!', 'success')
    else:
        flash('Failed to add balance.', 'danger')
    
    return redirect(url_for('users_view', user_id=user_id))

@app.route('/users/<int:user_id>/set-status', methods=['POST'])
@admin_required
def users_set_status(user_id):
    """Set user active status"""
    active = request.form.get('active') == 'true'
    
    response = make_request('POST', f"{USERS_SERVICE_URL}/user/set_status", 
                          json={'user_id_input': str(user_id), 'user_status_input': active})
    
    if response and response.status_code == 200:
        flash('User status updated!', 'success')
    else:
        flash('Failed to update user status.', 'danger')
    
    return redirect(url_for('users_view', user_id=user_id))

# TRANSACTIONS ROUTES
@app.route('/transactions')
@login_required
def transactions_list():
    """List transaction history"""
    user_id = request.args.get('user_id')
    limit = request.args.get('limit', 50)
    offset = request.args.get('offset', 0)
    
    params = {'limit': limit, 'offset': offset}
    if user_id:
        params['user_id'] = user_id
    
    response = make_request('GET', f"{TRANSACTIONS_SERVICE_URL}/transactions/history", 
                          params=params)
    
    transactions = []
    if response and response.status_code == 200:
        transactions = response.json().get('transactions', [])
    
    return render_template('transactions/list.html', transactions=transactions)

@app.route('/transactions/<transaction_id>')
@login_required
def transactions_view(transaction_id):
    """View transaction details"""
    response = make_request('GET', 
                          f"{TRANSACTIONS_SERVICE_URL}/transactions/history/{transaction_id}")
    
    transaction = {}
    if response and response.status_code == 200:
        data = response.json()
        transaction = data.get('transaction', {})
    
    return render_template('transactions/view.html', transaction=transaction)

@app.route('/payments/debit', methods=['GET', 'POST'])
@login_required
def payments_debit():
    """Make a payment (debit user)"""
    if request.method == 'POST':
        # Get user_id (card_id) from session
        user_id = None
        if 'card_id' in session:
            try:
                user_id = int(session['card_id'])
            except (ValueError, TypeError):
                pass
        
        if not user_id:
            logger.error(f"Could not extract card_id from session: {session.keys()}")
            flash('Could not retrieve user information. Please log in again.', 'danger')
            return redirect(url_for('payments_debit'))
        
        # Get item_id from form
        item_id = request.form.get('item_id')
        if not item_id:
            flash('Please select an item.', 'danger')
            return redirect(url_for('payments_debit'))
        
        data = {
            'user_id': user_id,
            'item_id': item_id,
        }
        
        response = make_request('POST', f"{TRANSACTIONS_SERVICE_URL}/payments/debit", 
                              json=data)
        
        if response and response.status_code == 200:
            flash('Payment processed successfully!', 'success')
            return redirect(url_for('transactions_list'))
        else:
            error_msg = response.json().get('detail', 'Payment failed.') if response else 'Payment failed.'
            flash(error_msg, 'danger')
    
    # Get items for dropdown
    items_response = make_request('POST', f"{ITEMS_SERVICE_URL}/items/list", 
                                 json={'active_only': True})
    items = []
    if items_response and items_response.status_code == 200:
        items = items_response.json().get('items', [])
    
    return render_template('payments/debit.html', items=items)

# Health check endpoint
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=os.getenv('DEBUG', 'false').lower() == 'true')
