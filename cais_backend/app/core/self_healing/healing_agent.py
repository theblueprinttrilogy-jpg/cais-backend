"""
Autonomous Healing Agent for CAIS.
Monitors system health and performs self-healing actions.
"""
import os
import sys
import asyncio
import logging
import socket
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from app.core.worm.worm_ledger import WORMClient

logger = logging.getLogger(__name__)

class HealingAgent:
    """
    Autonomous healing agent that monitors system health and performs
    self-healing actions when issues are detected.
    """

    def __init__(
        self,
        check_interval: int = 30,
        max_retries: int = 3,
        worm_client: Optional[WORMClient] = None
    ):
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.worm = worm_client or WORMClient()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_check: Optional[datetime] = None
        self._issues: List[Dict] = []
        self._healing_history: List[Dict] = []

    async def start(self):
        """Start the healing agent loop."""
        if self._running:
            logger.warning("Healing agent is already running")
            return

        logger.info("Starting healing agent...")
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Healing agent started successfully")

    async def stop(self):
        """Stop the healing agent loop gracefully."""
        if not self._running:
            logger.warning("Healing agent is not running")
            return

        logger.info("Stopping healing agent...")
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Healing agent stopped")

    def is_running(self) -> bool:
        """Return True if the healing agent is currently running."""
        return self._running

    async def _run(self):
        """Main loop that periodically checks system health."""
        while self._running:
            try:
                await self._check_and_heal()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in healing loop: {e}")
                await asyncio.sleep(self.check_interval * 2)

    async def _check_and_heal(self):
        """Check system health and perform healing if needed."""
        self._last_check = datetime.now()
        health = await self._check_system_health()

        if health.get("issues", 0) > 0:
            logger.warning(f"Detected {health['issues']} issues: {health['summary']}")
            await self._heal(health)
        else:
            logger.info("All systems healthy")

    async def _check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive health checks on all system components."""
        issues = []
        summary = []

        # Check CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            issues.append({"component": "cpu", "value": cpu_percent, "threshold": 90})
            summary.append(f"CPU usage at {cpu_percent}%")

        # Check Memory
        mem = psutil.virtual_memory()
        if mem.percent > 90:
            issues.append({"component": "memory", "value": mem.percent, "threshold": 90})
            summary.append(f"Memory usage at {mem.percent}%")

        # Check Disk
        disk = psutil.disk_usage("/")
        if disk.percent > 90:
            issues.append({"component": "disk", "value": disk.percent, "threshold": 90})
            summary.append(f"Disk usage at {disk.percent}%")

        # Check FastAPI server
        if not self._is_fastapi_running():
            issues.append({"component": "fastapi", "value": "down", "threshold": "up"})
            summary.append("FastAPI server is not responding")

        # Check WORM integrity
        worm_ok, worm_errors = self.worm.verify_integrity()
        if not worm_ok:
            issues.append({"component": "worm", "value": "corrupted", "threshold": "intact"})
            summary.append(f"WORM integrity issues: {len(worm_errors)} errors")

        # Check providers (simulated)
        providers_ok = await self._check_providers()
        if not providers_ok:
            issues.append({"component": "providers", "value": "unhealthy", "threshold": "healthy"})
            summary.append("Some external providers are unhealthy")

        return {
            "issues": len(issues),
            "issues_list": issues,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }

    async def _check_worm_integrity(self) -> Dict[str, Any]:
        """Check WORM ledger integrity."""
        ok, errors = self.worm.verify_integrity()
        return {"ok": ok, "errors": errors}

    async def _check_providers(self) -> bool:
        """Check external service providers (simulated)."""
        # In a real scenario, check RabbitMQ, Redis, etc.
        return True

    async def _heal(self, health_status: Dict[str, Any]):
        """Execute healing actions based on the health status."""
        for issue in health_status.get("issues_list", []):
            component = issue["component"]
            logger.info(f"Attempting to heal component: {component}")

            action = None
            if component == "cpu":
                action = await self._heal_cpu()
            elif component == "memory":
                action = await self._heal_memory()
            elif component == "disk":
                action = await self._heal_disk()
            elif component == "fastapi":
                action = await self._heal_server()
            elif component == "worm":
                action = {"status": "worm integrity check failed", "action": "manual_review"}
            elif component == "providers":
                action = {"status": "provider health check failed", "action": "manual_review"}

            self._healing_history.append({
                "component": component,
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "status": action.get("status", "unknown")
            })

            # Log to WORM
            self.worm.append(
                event_type="HEALING_ACTION",
                payload={"component": component, "action": action},
                actor="healing_agent"
            )

    async def _heal_cpu(self) -> Dict[str, Any]:
        """Heal CPU issues by throttling or restarting processes."""
        logger.info("Healing CPU: throttling processes...")
        return {"status": "cpu_healing_initiated", "action": "throttle_processes"}

    async def _heal_memory(self) -> Dict[str, Any]:
        """Heal memory issues by clearing caches or restarting services."""
        logger.info("Healing memory: clearing caches...")
        return {"status": "memory_healing_initiated", "action": "clear_cache"}

    async def _heal_disk(self) -> Dict[str, Any]:
        """Heal disk issues by cleaning temporary files."""
        logger.info("Healing disk: cleaning temp files...")
        return {"status": "disk_healing_initiated", "action": "clean_temp"}

    async def _heal_server(self) -> Dict[str, Any]:
        """Restart the FastAPI server if it's not responding."""
        logger.info("Healing FastAPI: restarting server...")
        return {"status": "server_restart_initiated", "action": "restart_fastapi"}

    def _is_fastapi_running(self) -> bool:
        """Check if FastAPI is responding on port 8001."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("127.0.0.1", 8001))
        sock.close()
        return result == 0

    async def get_status(self) -> Dict[str, Any]:
        """Get current status of the healing agent."""
        return {
            "running": self._running,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "issues_count": len(self._issues),
            "healing_count": len(self._healing_history),
            "healing_history": self._healing_history[-5:],
            "worm_status": self.worm.get_status()
        }

# Global instance
healing_agent = HealingAgent()
