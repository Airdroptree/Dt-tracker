from flask import Flask, request, jsonify
from flask_cors import CORS
from database import db, Wallet, BalanceHistory
from balance_tracker import BalanceTracker
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure CORS for Netlify
CORS(app, origins=[
    "http://localhost:3000",
    "http://localhost:5000",
    "https://your-netlify-app.netlify.app",  # Netlify URL
    # Add more origins as needed
])

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wallets.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize tracker (with your Telegram details)
tracker = BalanceTracker()

# Create tables
with app.app_context():
    db.create_all()

def check_all_balances():
    """Background job to check all wallet balances"""
    with app.app_context():
        wallets = Wallet.query.all()
        logger.info(f"Checking {len(wallets)} wallets...")
        
        for wallet in wallets:
            old_balance = float(wallet.last_balance)
            new_balance = tracker.check_wallet_balance(wallet.address, old_balance)
            
            # Update wallet
            wallet.last_balance = str(new_balance)
            wallet.last_checked = datetime.utcnow()
            
            # Save to history
            history = BalanceHistory(
                wallet_address=wallet.address,
                balance=str(new_balance),
                previous_balance=str(old_balance),
                alert_sent=(new_balance > old_balance)
            )
            db.session.add(history)
            
        db.session.commit()
        logger.info("Balance check completed")

# Schedule background job
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=check_all_balances,
    trigger="interval",
    seconds=30,
    id='balance_check_job'
)
scheduler.start()

# API Routes
@app.route('/api/wallets', methods=['GET'])
def get_wallets():
    """Get all wallets"""
    wallets = Wallet.query.all()
    return jsonify([{
        'id': w.id,
        'address': w.address,
        'balance': w.last_balance,
        'last_checked': w.last_checked.isoformat() if w.last_checked else None
    } for w in wallets])

@app.route('/api/wallets', methods=['POST'])
def add_wallets():
    """Add new wallets"""
    data = request.json
    addresses = data.get('addresses', [])
    
    added = []
    for address in addresses:
        existing = Wallet.query.filter_by(address=address).first()
        if not existing:
            balance = tracker.get_balance(address)
            wallet = Wallet(
                address=address,
                last_balance=str(balance) if balance else '0'
            )
            db.session.add(wallet)
            added.append(address)
    
    db.session.commit()
    return jsonify({'added': added, 'count': len(added)})

@app.route('/api/wallets/<int:wallet_id>', methods=['DELETE'])
def delete_wallet(wallet_id):
    """Delete a wallet"""
    wallet = Wallet.query.get(wallet_id)
    if wallet:
        db.session.delete(wallet)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Wallet not found'}), 404

@app.route('/api/wallets/all', methods=['DELETE'])
def delete_all_wallets():
    """Delete all wallets"""
    Wallet.query.delete()
    BalanceHistory.query.delete()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/balances/refresh', methods=['POST'])
def refresh_balances():
    """Manually refresh all balances"""
    check_all_balances()
    return jsonify({'success': True})

@app.route('/api/wallets/count', methods=['GET'])
def get_wallet_count():
    """Get total wallets count"""
    count = Wallet.query.count()
    return jsonify({'count': count})

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'time': datetime.now().isoformat(),
        'wallets': Wallet.query.count()
    })

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)