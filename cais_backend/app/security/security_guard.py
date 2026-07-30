"""
Security Guard - Anti-Hacker Protection System

Provides automatic IP blocking, suspicious activity detection,
and logging of security events to the WORM Ledger.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 7.2
"""

import logging
import re
from datetime import datetime
from typing import Optional, Set, List
from fastapi import Request, HTTPException

from app.services.worm_ledger import WORMService

logger = logging.getLogger(__name__)


class SecurityGuard:
    """
    Security Guard - Anti-Hacker System.

    Features:
    - Automatic IP blocking
    - Suspicious pattern detection
    - SQL injection detection
    - Path traversal detection
    - WORM Ledger logging
    """

    SUSPICIOUS_PATTERNS = [
        r'/\.env', r'/\.git', r'/\.aws', r'/\.ssh',
        r'/admin', r'/config', r'/backup', r'/dump',
        r'/wp-admin', r'/wp-config', r'/wp-content',
        r'/etc/passwd', r'/etc/shadow', r'/proc/self',
        r'/cgi-bin', r'/phpmyadmin', r'/mysql',
        r'/webshell', r'/shell', r'/cmd',
        r'/exec', r'/eval', r'/system',
    ]

    SQL_PATTERNS = [
        r'SELECT.*FROM', r'INSERT.*INTO', r'UPDATE.*SET',
        r'DELETE.*FROM', r'DROP.*TABLE', r'ALTER.*TABLE',
        r'UNION.*SELECT', r'OR.*1=1', r'OR.*\'1\'=\'1',
        r'--', r';.*DROP', r'EXEC', r'EXECUTE',
    ]

    PATH_TRAVERSAL = [
        r'\.\./', r'\.\.\\', r'%2e%2e%2f', r'%2e%2e%5c',
        r'\.\.%2f', r'\.\.%5c', r'%252e%252e%252f',
    ]

    def __init__(self, worm_service: Optional[WORMService] = None):
        self.blocked_ips: Set[str] = set()
        self.ip_attempts: dict = {}
        self.max_attempts = 10
        self.attempt_window = 300  # 5 minutes
        self.worm_service = worm_service

    def check_access(self, request: Request) -> bool:
        """
        Check if the request should be allowed.

        Args:
            request: FastAPI request object

        Returns:
            bool: True if access is allowed

        Raises:
            HTTPException: If access is denied
        """
        client_ip = self._get_client_ip(request)

        if client_ip in self.blocked_ips:
            self._log_suspicious(client_ip, "BLOCKED_IP_ACCESS_ATTEMPT")
            raise HTTPException(status_code=403, detail="Access denied by security guard")

        if not self._check_rate_limit(client_ip):
            self.block_ip(client_ip)
            raise HTTPException(status_code=429, detail="Rate limit exceeded. IP has been blocked.")

        path = request.url.path
        query = str(request.query_params)
        full_path = f"{path}?{query}" if query else path

        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, full_path, re.IGNORECASE):
                self.block_ip(client_ip)
                self._log_suspicious(client_ip, "SUSPICIOUS_PATTERN_DETECTED", full_path)
                raise HTTPException(status_code=403, detail="Suspicious pattern detected.")

        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, full_path, re.IGNORECASE):
                self.block_ip(client_ip)
                self._log_suspicious(client_ip, "SQL_INJECTION_ATTEMPT", full_path)
                raise HTTPException(status_code=403, detail="SQL injection detected.")

        for pattern in self.PATH_TRAVERSAL:
            if re.search(pattern, full_path, re.IGNORECASE):
                self.block_ip(client_ip)
                self._log_suspicious(client_ip, "PATH_TRAVERSAL_ATTEMPT", full_path)
                raise HTTPException(status_code=403, detail="Path traversal detected.")

        return True

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "0.0.0.0"

    def _check_rate_limit(self, ip: str) -> bool:
        now = datetime.now().timestamp()

        if ip not in self.ip_attempts:
            self.ip_attempts[ip] = []

        self.ip_attempts[ip] = [t for t in self.ip_attempts[ip] if now - t < self.attempt_window]
        self.ip_attempts[ip].append(now)

        return len(self.ip_attempts[ip]) <= self.max_attempts

    def block_ip(self, ip_address: str) -> None:
        self.blocked_ips.add(ip_address)
        self._log_suspicious(ip_address, "IP_BLOCKED")
        logger.warning(f"IP {ip_address} has been blocked.")

    def unblock_ip(self, ip_address: str) -> bool:
        if ip_address in self.blocked_ips:
            self.blocked_ips.remove(ip_address)
            logger.info(f"IP {ip_address} has been unblocked.")
            return True
        return False

    def _log_suspicious(self, ip_address: str, action: str, details: str = ""):
        if self.worm_service:
            # Log to WORM Ledger asynchronously
            try:
                import asyncio
                asyncio.create_task(
                    self.worm_service.add_entry(
                        evidence_gcs_uri=f"security_event_{datetime.now().timestamp()}",
                        violation_codes={
                            "action": action,
                            "ip": ip_address,
                            "details": details,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                )
            except Exception as e:
                logger.error(f"Failed to log to WORM Ledger: {e}")

    def get_blocked_ips(self) -> List[str]:
        return list(self.blocked_ips)

    def get_stats(self) -> dict:
        return {
            'blocked_ips': len(self.blocked_ips),
            'total_attempts': sum(len(v) for v in self.ip_attempts.values()),
            'unique_ips': len(self.ip_attempts),
        }
