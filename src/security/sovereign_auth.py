#!/usr/bin/env python3
"""
Sistema de Autenticación del Soberano - Área Segura de 17 Caracteres.
"""

import os
import hashlib
import hmac
import time
import json
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import bcrypt
from cryptography.fernet import Fernet

@dataclass
class AuthAttempt:
    """Registro de intento de autenticación."""
    timestamp: str
    success: bool
    ip_address: str
    user_agent: str

class SovereignAuthenticator:
    """
    Sistema de autenticación para el Área Segura del Soberano.
    Requiere contraseña de exactamente 17 caracteres.
    """
    
    # Configuración de seguridad
    REQUIRED_LENGTH = 17
    MAX_ATTEMPTS = 3
    LOCKOUT_DURATION = 900  # 15 minutos en segundos
    SESSION_DURATION = 3600  # 1 hora
    
    def __init__(self, config_dir: str = "~/PROMETHEUS/config/security"):
        """
        Initialize the sovereign authenticator.
        
        Args:
            config_dir: Directory for security configuration.
        """
        self.config_dir = Path(config_dir).expanduser()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de configuración
        self.auth_file = self.config_dir / 'sovereign_auth.json'
        self.log_file = self.config_dir / 'sovereign_access.log'
        self.session_file = self.config_dir / 'sovereign_session.json'
        
        # Inicializar
        self._initialize_auth_system()
        self._load_session()
    
    def _initialize_auth_system(self):
        """
        Initialize the authentication system.
        Creates the master password if it doesn't exist.
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
                'last_access': None
            }
            
            with open(self.auth_file, 'w') as f:
                json.dump(auth_config, f, indent=2)
            
            # Save the master password securely
            self._save_master_password(master_password)
            
            print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    🔐 SOVEREIGN VAULT                           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                ║
║  ¡IMPORTANTE! Su contraseña maestra de 17 caracteres es:       ║
║                                                                ║
║  {master_password}                             ║
║                                                                ║
║  ⚠️  Guarde esta contraseña en un lugar seguro.                ║
║  ⚠️  No la comparta con nadie.                                 ║
║  ⚠️  No la guarde en el sistema sin cifrar.                    ║
║                                                                ║
║  La contraseña está almacenada en:                             ║
║  {self.config_dir / 'master_password.key'}                     ║
║                                                                ║
╚══════════════════════════════════════════════════════════════════╝
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
        
        # Fill remaining characters
        all_chars = lowercase + uppercase + digits + symbols
        for _ in range(17 - len(password)):
            password.append(random.choice(all_chars))
        
        # Shuffle
        random.shuffle(password)
        
        return ''.join(password)
    
    def _save_master_password(self, password: str):
        """
        Save the master password in an encrypted format.
        
        Args:
            password: The master password.
        """
        # Generate encryption key
        key = Fernet.generate_key()
        cipher = Fernet(key)
        
        # Encrypt password
        encrypted = cipher.encrypt(password.encode('utf-8'))
        
        # Save encrypted password
        with open(self.config_dir / 'master_password.key', 'w') as f:
            json.dump({
                'key': key.decode('utf-8'),
                'encrypted': encrypted.decode('utf-8'),
                'created_at': datetime.now().isoformat()
            }, f, indent=2)
        
        # Set restrictive permissions
        os.chmod(self.config_dir / 'master_password.key', 0o600)
    
    def _load_session(self):
        """Load current session state."""
        if self.session_file.exists():
            with open(self.session_file, 'r') as f:
                self.session = json.load(f)
        else:
            self.session = {
                'authenticated': False,
                'authenticated_at': None,
                'expires_at': None,
                'ip_address': None
            }
            self._save_session()
    
    def _save_session(self):
        """Save current session state."""
        with open(self.session_file, 'w') as f:
            json.dump(self.session, f, indent=2)
    
    def authenticate(self, password: str, ip_address: str = "127.0.0.1") -> Tuple[bool, str]:
        """
        Authenticate the sovereign with the master password.
        
        Args:
            password: The password to verify.
            ip_address: IP address of the requester.
            
        Returns:
            Tuple of (success, message).
        """
        # Validate password length
        if len(password) != self.REQUIRED_LENGTH:
            self._log_attempt(False, ip_address, "Invalid length")
            return False, f"Password must be exactly {self.REQUIRED_LENGTH} characters"
        
        # Check if locked out
        with open(self.auth_file, 'r') as f:
            auth_config = json.load(f)
        
        if auth_config.get('locked_until'):
            lock_time = datetime.fromisoformat(auth_config['locked_until'])
            if datetime.now() < lock_time:
                remaining = (lock_time - datetime.now()).seconds
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
                self.session['authenticated'] = True
                self.session['authenticated_at'] = datetime.now().isoformat()
                self.session['expires_at'] = (
                    datetime.now() + timedelta(seconds=self.SESSION_DURATION)
                ).isoformat()
                self.session['ip_address'] = ip_address
                self._save_session()
                
                self._log_attempt(True, ip_address, "Success")
                return True, "Authentication successful"
            else:
                # Failed attempt
                auth_config['attempts'] = auth_config.get('attempts', 0) + 1
                
                if auth_config['attempts'] >= self.MAX_ATTEMPTS:
                    # Lock the account
                    lock_time = datetime.now() + timedelta(seconds=self.LOCKOUT_DURATION)
                    auth_config['locked_until'] = lock_time.isoformat()
                    message = f"Too many attempts. Account locked for {self.LOCKOUT_DURATION/60} minutes"
                else:
                    remaining = self.MAX_ATTEMPTS - auth_config['attempts']
                    message = f"Invalid password. {remaining} attempts remaining"
                
                with open(self.auth_file, 'w') as f:
                    json.dump(auth_config, f, indent=2)
                
                self._log_attempt(False, ip_address, f"Invalid password (attempt {auth_config['attempts']})")
                return False, message
                
        except Exception as e:
            self._log_attempt(False, ip_address, f"Error: {str(e)}")
            return False, f"Authentication error: {str(e)}"
    
    def is_authenticated(self) -> bool:
        """
        Check if the current session is authenticated.
        
        Returns:
            True if authenticated and session not expired.
        """
        if not self.session['authenticated']:
            return False
        
        # Check expiration
        if self.session.get('expires_at'):
            expires = datetime.fromisoformat(self.session['expires_at'])
            if datetime.now() > expires:
                self.logout()
                return False
        
        return True
    
    def logout(self):
        """Log out the current session."""
        self.session['authenticated'] = False
        self.session['authenticated_at'] = None
        self.session['expires_at'] = None
        self._save_session()
    
    def get_session_info(self) -> dict:
        """
        Get current session information.
        
        Returns:
            Dictionary with session information.
        """
        return {
            'authenticated': self.session['authenticated'],
            'authenticated_at': self.session.get('authenticated_at'),
            'expires_at': self.session.get('expires_at'),
            'time_remaining': None
        }
    
    def _log_attempt(self, success: bool, ip_address: str, details: str):
        """
        Log an authentication attempt.
        
        Args:
            success: Whether the attempt was successful.
            ip_address: IP address of the requester.
            details: Additional details.
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'ip_address': ip_address,
            'details': details,
            'user_agent': os.environ.get('HTTP_USER_AGENT', 'unknown')
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def reset_password(self, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Reset the master password.
        
        Args:
            old_password: Current password.
            new_password: New password (must be 17 characters).
            
        Returns:
            Tuple of (success, message).
        """
        # Validate new password length
        if len(new_password) != self.REQUIRED_LENGTH:
            return False, f"New password must be exactly {self.REQUIRED_LENGTH} characters"
        
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
        self._log_attempt(True, "127.0.0.1", "Password changed")
        
        return True, "Password changed successfully"
    
    def get_status(self) -> dict:
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
            'locked_until': auth_config.get('locked_until'),
            'last_access': auth_config.get('last_access'),
            'max_attempts': self.MAX_ATTEMPTS,
            'lockout_duration_seconds': self.LOCKOUT_DURATION,
            'session_authenticated': self.is_authenticated()
        }

# Instancia global del autenticador
sovereign_auth = SovereignAuthenticator()
