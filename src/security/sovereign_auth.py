#!/usr/bin/env python3
"""
Sovereign Authentication - TASK 6.2
Secure 17-character password authentication for the Sovereign Vault.
100% ENGLISH - All comments, messages, and logs in English.
"""

import os
import json
import hashlib
import hmac
import time
import secrets
import bcrypt
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@dataclass
class AuthAttempt:
    """Record of an authentication attempt."""
    timestamp: str
    success: bool
    ip_address: str
    user_agent: str
    details: str = ""


@dataclass
class SessionData:
    """Session data for authenticated user."""
    authenticated: bool
    authenticated_at: Optional[str] = None
    expires_at: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None


class SovereignAuthenticator:
    """
    Secure authentication system for the Sovereign Vault.
    Requires exactly 17-character password.
    Features:
    - bcrypt hashing (12 rounds)
    - 3 attempts max, then 15-minute lockout
    - 1-hour session duration
    - Fernet encryption for stored passwords
    - Audit logging of all attempts
    """
    
    # Security constants
    PASSWORD_LENGTH = 17
    MAX_ATTEMPTS = 3
    LOCKOUT_DURATION = 900  # 15 minutes in seconds
    SESSION_DURATION = 3600  # 1 hour in seconds
    
    def __init__(self, config_dir: str = "~/PROMETHEUS/config/security"):
        """
        Initialize the Sovereign Authenticator.
        
        Args:
            config_dir: Directory for security configuration
        """
        self.config_dir = Path(config_dir).expanduser()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.auth_file = self.config_dir / 'sovereign_auth.json'
        self.log_file = self.config_dir / 'sovereign_access.log'
        self.session_file = self.config_dir / 'sovereign_session.json'
        self.master_key_file = self.config_dir / 'master_password.key'
        
        # Initialize system
        self._initialize_auth_system()
        self._load_session()
    
    def _initialize_auth_system(self):
        """
        Initialize the authentication system.
        Creates master password if it doesn't exist.
        """
        if not self.auth_file.exists():
            # Generate master password
            master_password = self._generate_master_password()
            
            # Hash with bcrypt
            salt = bcrypt.gensalt(rounds=12)
            password_hash = bcrypt.hashpw(
                master_password.encode('utf-8'),
                salt
            ).decode('utf-8')
            
            # Save configuration
            auth_config = {
                'password_hash': password_hash,
                'salt': salt.decode('utf-8'),
                'created_at': datetime.now().isoformat(),
                'attempts': 0,
                'locked_until': None,
                'last_access': None,
                'version': '1.0'
            }
            
            with open(self.auth_file, 'w') as f:
                json.dump(auth_config, f, indent=2)
            
            # Save the master password securely
            self._save_master_password(master_password)
            
            print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                    🔐 SOVEREIGN VAULT                             ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ⚠️  IMPORTANT! Your 17-character master password is:             ║
║                                                                   ║
║  📌  {master_password}  📌                                        ║
║                                                                   ║
║  ⚠️  Store this password in a secure location.                    ║
║  ⚠️  Do NOT share it with anyone.                                ║
║  ⚠️  Do NOT store it unencrypted on disk.                        ║
║                                                                   ║
║  Password stored securely at:                                     ║
║  {self.master_key_file}                                          ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    def _generate_master_password(self) -> str:
        """
        Generate a 17-character master password.
        
        Returns:
            17-character password with mixed case, numbers, and symbols.
        """
        import random
        import string
        
        # Character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        # Ensure at least one of each type
        password = [
            random.choice(lowercase),
            random.choice(uppercase),
            random.choice(digits),
            random.choice(symbols)
        ]
        
        # Fill remaining characters (17 total)
        all_chars = lowercase + uppercase + digits + symbols
        for _ in range(self.PASSWORD_LENGTH - len(password)):
            password.append(random.choice(all_chars))
        
        # Shuffle
        random.shuffle(password)
        
        return ''.join(password)
    
    def _save_master_password(self, password: str):
        """
        Save the master password in an encrypted format.
        
        Args:
            password: The master password to encrypt and save.
        """
        # Generate encryption key
        key = Fernet.generate_key()
        cipher = Fernet(key)
        
        # Encrypt password
        encrypted = cipher.encrypt(password.encode('utf-8'))
        
        # Save encrypted password with metadata
        with open(self.master_key_file, 'w') as f:
            json.dump({
                'key': key.decode('utf-8'),
                'encrypted': encrypted.decode('utf-8'),
                'created_at': datetime.now().isoformat(),
                'version': '1.0'
            }, f, indent=2)
        
        # Set restrictive permissions
        os.chmod(self.master_key_file, 0o600)
    
    def _load_session(self):
        """Load current session state."""
        if self.session_file.exists():
            with open(self.session_file, 'r') as f:
                data = json.load(f)
                self.session = SessionData(
                    authenticated=data.get('authenticated', False),
                    authenticated_at=data.get('authenticated_at'),
                    expires_at=data.get('expires_at'),
                    session_id=data.get('session_id'),
                    ip_address=data.get('ip_address')
                )
        else:
            self.session = SessionData(authenticated=False)
            self._save_session()
    
    def _save_session(self):
        """Save current session state."""
        with open(self.session_file, 'w') as f:
            json.dump({
                'authenticated': self.session.authenticated,
                'authenticated_at': self.session.authenticated_at,
                'expires_at': self.session.expires_at,
                'session_id': self.session.session_id,
                'ip_address': self.session.ip_address
            }, f, indent=2)
    
    def authenticate(self, password: str, ip_address: str = "127.0.0.1", user_agent: str = "unknown") -> Tuple[bool, str]:
        """
        Authenticate the sovereign with the master password.
        
        Args:
            password: The password to verify (must be exactly 17 characters).
            ip_address: IP address of the requester.
            user_agent: User agent of the requester.
            
        Returns:
            Tuple of (success, message).
        """
        # Validate password length
        if len(password) != self.PASSWORD_LENGTH:
            self._log_attempt(False, ip_address, user_agent, f"Invalid length: {len(password)}")
            return False, f"Password must be exactly {self.PASSWORD_LENGTH} characters"
        
        # Check if locked out
        with open(self.auth_file, 'r') as f:
            auth_config = json.load(f)
        
        if auth_config.get('locked_until'):
            lock_time = datetime.fromisoformat(auth_config['locked_until'])
            if datetime.now() < lock_time:
                remaining = int((lock_time - datetime.now()).total_seconds())
                return False, f"Account locked. Try again in {remaining} seconds"
        
        # Verify password
        try:
            stored_hash = auth_config['password_hash'].encode('utf-8')
            password_bytes = password.encode('utf-8')
            
            if bcrypt.checkpw(password_bytes, stored_hash):
                # Success
                auth_config['attempts'] = 0
                auth_config['locked_until'] = None
                auth_config['last_access'] = datetime.now().isoformat()
                
                with open(self.auth_file, 'w') as f:
                    json.dump(auth_config, f, indent=2)
                
                # Create session
                session_id = secrets.token_hex(32)
                self.session.authenticated = True
                self.session.authenticated_at = datetime.now().isoformat()
                self.session.expires_at = (
                    datetime.now() + timedelta(seconds=self.SESSION_DURATION)
                ).isoformat()
                self.session.session_id = session_id
                self.session.ip_address = ip_address
                self._save_session()
                
                self._log_attempt(True, ip_address, user_agent, "Success")
                return True, "Authentication successful"
            else:
                # Failed attempt
                auth_config['attempts'] = auth_config.get('attempts', 0) + 1
                
                if auth_config['attempts'] >= self.MAX_ATTEMPTS:
                    # Lock the account
                    lock_time = datetime.now() + timedelta(seconds=self.LOCKOUT_DURATION)
                    auth_config['locked_until'] = lock_time.isoformat()
                    message = f"Too many attempts. Account locked for {self.LOCKOUT_DURATION//60} minutes"
                else:
                    remaining = self.MAX_ATTEMPTS - auth_config['attempts']
                    message = f"Invalid password. {remaining} attempts remaining"
                
                with open(self.auth_file, 'w') as f:
                    json.dump(auth_config, f, indent=2)
                
                self._log_attempt(False, ip_address, user_agent, f"Invalid password (attempt {auth_config['attempts']})")
                return False, message
            
        except Exception as e:
            self._log_attempt(False, ip_address, user_agent, f"Error: {str(e)}")
            return False, f"Authentication error: {str(e)}"
    
    def is_authenticated(self) -> bool:
        """
        Check if the current session is authenticated.
        
        Returns:
            True if authenticated and session not expired.
        """
        if not self.session.authenticated:
            return False
        
        # Check expiration
        if self.session.expires_at:
            expires = datetime.fromisoformat(self.session.expires_at)
            if datetime.now() > expires:
                self.logout()
                return False
        
        return True
    
    def logout(self):
        """Log out the current session."""
        self.session.authenticated = False
        self.session.authenticated_at = None
        self.session.expires_at = None
        self.session.session_id = None
        self._save_session()
        self._log_attempt(True, "127.0.0.1", "system", "Logout")
    
    def get_session_info(self) -> Dict:
        """
        Get current session information.
        
        Returns:
            Dictionary with session information.
        """
        info = {
            'authenticated': self.session.authenticated,
            'authenticated_at': self.session.authenticated_at,
            'expires_at': self.session.expires_at,
            'session_id': self.session.session_id[:16] + '...' if self.session.session_id else None
        }
        
        if self.session.authenticated and self.session.expires_at:
            expires = datetime.fromisoformat(self.session.expires_at)
            remaining = int((expires - datetime.now()).total_seconds())
            info['seconds_remaining'] = remaining
            info['minutes_remaining'] = remaining // 60
        
        return info
    
    def _log_attempt(self, success: bool, ip_address: str, user_agent: str, details: str):
        """
        Log an authentication attempt to the audit log.
        
        Args:
            success: Whether the attempt was successful.
            ip_address: IP address of the requester.
            user_agent: User agent of the requester.
            details: Additional details about the attempt.
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'details': details,
            'session_id': self.session.session_id
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def reset_password(self, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Reset the master password.
        
        Args:
            old_password: Current password (must be valid).
            new_password: New password (must be 17 characters).
            
        Returns:
            Tuple of (success, message).
        """
        # Validate new password length
        if len(new_password) != self.PASSWORD_LENGTH:
            return False, f"New password must be exactly {self.PASSWORD_LENGTH} characters"
        
        # Verify old password
        success, message = self.authenticate(old_password)
        if not success:
            return False, "Old password verification failed"
        
        # Hash new password
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(
            new_password.encode('utf-8'),
            salt
        ).decode('utf-8')
        
        # Update configuration
        with open(self.auth_file, 'r') as f:
            auth_config = json.load(f)
        
        auth_config['password_hash'] = password_hash
        auth_config['salt'] = salt.decode('utf-8')
        auth_config['updated_at'] = datetime.now().isoformat()
        auth_config['attempts'] = 0
        auth_config['locked_until'] = None
        
        with open(self.auth_file, 'w') as f:
            json.dump(auth_config, f, indent=2)
        
        # Save new password encrypted
        self._save_master_password(new_password)
        
        # Log the change
        self._log_attempt(True, "127.0.0.1", "system", "Password changed")
        
        return True, "Password changed successfully"
    
    def get_status(self) -> Dict:
        """
        Get the status of the authentication system.
        
        Returns:
            Dictionary with status information.
        """
        with open(self.auth_file, 'r') as f:
            auth_config = json.load(f)
        
        return {
            'password_hash': auth_config['password_hash'][:20] + '...',
            'attempts': auth_config.get('attempts', 0),
            'max_attempts': self.MAX_ATTEMPTS,
            'locked_until': auth_config.get('locked_until'),
            'last_access': auth_config.get('last_access'),
            'lockout_duration_seconds': self.LOCKOUT_DURATION,
            'session_duration_seconds': self.SESSION_DURATION,
            'session_authenticated': self.is_authenticated(),
            'password_encrypted': self.master_key_file.exists()
        }
    
    def get_recent_logs(self, limit: int = 20) -> List[Dict]:
        """
        Get recent authentication logs.
        
        Args:
            limit: Maximum number of log entries to return.
            
        Returns:
            List of log entries.
        """
        if not self.log_file.exists():
            return []
        
        logs = []
        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    logs.append(json.loads(line.strip()))
                except:
                    continue
        
        return logs[-limit:]


# Global instance
sovereign_auth = SovereignAuthenticator()


async def main():
    """Test the Sovereign Authentication system."""
    print("\n" + "="*70)
    print(" SOVEREIGN AUTHENTICATION - TEST")
    print("="*70)
    
    auth = SovereignAuthenticator()
    
    # Show status
    status = auth.get_status()
    print(f"\n📊 System Status:")
    print(f"   Password hash: {status['password_hash']}")
    print(f"   Attempts: {status['attempts']}/{status['max_attempts']}")
    print(f"   Locked: {status['locked_until'] is not None}")
    print(f"   Session: {status['session_authenticated']}")
    print(f"   Password encrypted: {status['password_encrypted']}")
    
    # Show session info
    session_info = auth.get_session_info()
    print(f"\n🔐 Session Info:")
    print(f"   Authenticated: {session_info['authenticated']}")
    if session_info.get('minutes_remaining'):
        print(f"   Time remaining: {session_info['minutes_remaining']} minutes")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
