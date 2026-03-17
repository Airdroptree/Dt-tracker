from web3 import Web3
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BalanceTracker:
    def __init__(self):
        self.usdt_contract = "0x55d398326f99059fF775485246999027B3197955"
        self.usdt_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        self.bsc_rpc = "https://bsc-dataseed1.binance.org/"
        self.web3 = Web3(Web3.HTTPProvider(self.bsc_rpc))
        self.contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(self.usdt_contract),
            abi=self.usdt_abi
        )
        
        # Aapki di hui Telegram details
        self.bot_token = '8066172896:AAGeYizReYxonwE3nf4GoZUp3CihRZUhKjA'
        self.chat_id = '6888231379'
        self.telegram_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
    
    def send_telegram_alert(self, wallet_address, old_balance, new_balance):
        """Send Telegram alert on balance increase"""
        try:
            increase = float(new_balance) - float(old_balance)
            if increase > 0:
                message = f"""🚨 USDT Activity!
Wallet: {wallet_address}
Balance: {new_balance} USDT
Previous: {old_balance} USDT
Increase: +{increase:.2f} USDT
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                
                payload = {
                    'chat_id': self.chat_id,
                    'text': message
                }
                
                response = requests.post(self.telegram_url, json=payload)
                if response.status_code == 200:
                    logger.info(f"Alert sent for {wallet_address}")
                    return True
                else:
                    logger.error(f"Telegram error: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False
    
    def get_balance(self, address):
        """Get USDT balance for address"""
        try:
            checksum_address = Web3.to_checksum_address(address)
            balance_wei = self.contract.functions.balanceOf(checksum_address).call()
            balance = self.web3.from_wei(balance_wei, 'ether')
            return float(balance)
        except Exception as e:
            logger.error(f"Error getting balance for {address}: {e}")
            return None
    
    def check_wallet_balance(self, address, old_balance):
        """Check wallet balance and send alert if increased"""
        new_balance = self.get_balance(address)
        
        if new_balance is not None:
            # Send alert if balance increased
            if new_balance > old_balance:
                self.send_telegram_alert(address, old_balance, new_balance)
            
            return new_balance
        return old_balance