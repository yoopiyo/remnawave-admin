"""
Sync service for synchronizing data between API and local PostgreSQL database.
Handles periodic sync, webhook events, and on-demand sync.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.config import get_settings
from src.services.api_client import api_client
from src.services.database import db_service
from src.utils.logger import logger


class SyncService:
    """
    Service for synchronizing data from Remnawave API to local PostgreSQL database.
    
    Features:
    - Periodic full sync (configurable interval)
    - Webhook event handling for real-time updates
    - On-demand sync for specific entities
    - Graceful degradation when DB is unavailable
    """
    
    def __init__(self):
        self._running: bool = False
        self._sync_task: Optional[asyncio.Task] = None
        self._initial_sync_done: bool = False
    
    @property
    def is_running(self) -> bool:
        """Check if sync service is running."""
        return self._running
    
    @property
    def initial_sync_done(self) -> bool:
        """Check if initial sync has been completed."""
        return self._initial_sync_done
    
    async def start(self) -> None:
        """Start the sync service with periodic sync loop."""
        if self._running:
            logger.warning("Sync service is already running")
            return
        
        settings = get_settings()
        
        if not settings.database_enabled:
            logger.info("Database not configured, sync service disabled")
            return
        
        if not db_service.is_connected:
            logger.warning("Database not connected, sync service cannot start")
            return
        
        self._running = True
        logger.info("🔄 Starting sync service (interval: %d seconds)", settings.sync_interval_seconds)
        
        # Run initial sync
        await self._run_initial_sync()
        
        # Start periodic sync loop
        self._sync_task = asyncio.create_task(self._periodic_sync_loop())
    
    async def stop(self) -> None:
        """Stop the sync service."""
        if not self._running:
            return
        
        self._running = False
        
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            self._sync_task = None
        
        logger.info("Sync service stopped")
    
    async def _run_initial_sync(self) -> None:
        """Run initial synchronization of all data."""
        logger.info("🔄 Running initial data sync...")
        
        try:
            # Sync in parallel where possible
            results = await asyncio.gather(
                self.sync_users(),
                self.sync_nodes(),
                self.sync_hosts(),
                self.sync_config_profiles(),
                return_exceptions=True
            )
            
            # Log results
            sync_names = ["users", "nodes", "hosts", "config_profiles"]
            for name, result in zip(sync_names, results):
                if isinstance(result, Exception):
                    logger.error("Initial sync of %s failed: %s", name, result)
                else:
                    logger.info("Initial sync of %s: %d records", name, result)
            
            self._initial_sync_done = True
            logger.info("✅ Initial sync completed")
            
        except Exception as e:
            logger.error("❌ Initial sync failed: %s", e)
    
    async def _periodic_sync_loop(self) -> None:
        """Periodic sync loop."""
        settings = get_settings()
        interval = settings.sync_interval_seconds
        
        while self._running:
            try:
                await asyncio.sleep(interval)
                
                if not self._running:
                    break
                
                logger.debug("Running periodic sync...")
                await self.full_sync()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in periodic sync: %s", e)
                # Continue running, will retry next interval
    
    async def full_sync(self) -> Dict[str, int]:
        """
        Perform full synchronization of all data.
        Returns dict with counts of synced records.
        """
        results = {}
        
        try:
            # Sync users
            results["users"] = await self.sync_users()
        except Exception as e:
            logger.error("Failed to sync users: %s", e)
            results["users"] = -1
        
        try:
            # Sync nodes
            results["nodes"] = await self.sync_nodes()
        except Exception as e:
            logger.error("Failed to sync nodes: %s", e)
            results["nodes"] = -1
        
        try:
            # Sync hosts
            results["hosts"] = await self.sync_hosts()
        except Exception as e:
            logger.error("Failed to sync hosts: %s", e)
            results["hosts"] = -1
        
        try:
            # Sync config profiles (less frequently needed, but included in full sync)
            results["config_profiles"] = await self.sync_config_profiles()
        except Exception as e:
            logger.error("Failed to sync config profiles: %s", e)
            results["config_profiles"] = -1
        
        logger.debug("Full sync completed: %s", results)
        return results
    
    async def sync_users(self) -> int:
        """
        Sync all users from API to database.
        Uses pagination to handle large datasets.
        Returns number of synced users.
        """
        if not db_service.is_connected:
            return 0
        
        total_synced = 0
        page = 1
        page_size = 100
        
        try:
            while True:
                # Fetch users from API with pagination
                response = await api_client.get_users(
                    page=page,
                    size=page_size,
                    skip_cache=True
                )
                
                users = response.get("response", [])
                
                if not users:
                    break
                
                # Upsert users to database
                for user in users:
                    try:
                        await db_service.upsert_user({"response": user})
                        total_synced += 1
                    except Exception as e:
                        logger.warning("Failed to sync user %s: %s", user.get("uuid"), e)
                
                # Check if we've reached the last page
                if len(users) < page_size:
                    break
                
                page += 1
            
            # Update sync metadata
            await db_service.update_sync_metadata(
                key="users",
                status="success",
                records_synced=total_synced
            )
            
            logger.debug("Synced %d users", total_synced)
            return total_synced
            
        except Exception as e:
            await db_service.update_sync_metadata(
                key="users",
                status="error",
                error_message=str(e)
            )
            raise
    
    async def sync_nodes(self) -> int:
        """
        Sync all nodes from API to database.
        Returns number of synced nodes.
        """
        if not db_service.is_connected:
            return 0
        
        try:
            # Fetch all nodes from API
            response = await api_client.get_nodes(skip_cache=True)
            nodes = response.get("response", [])
            
            total_synced = 0
            for node in nodes:
                try:
                    await db_service.upsert_node({"response": node})
                    total_synced += 1
                except Exception as e:
                    logger.warning("Failed to sync node %s: %s", node.get("uuid"), e)
            
            # Update sync metadata
            await db_service.update_sync_metadata(
                key="nodes",
                status="success",
                records_synced=total_synced
            )
            
            logger.debug("Synced %d nodes", total_synced)
            return total_synced
            
        except Exception as e:
            await db_service.update_sync_metadata(
                key="nodes",
                status="error",
                error_message=str(e)
            )
            raise
    
    async def sync_hosts(self) -> int:
        """
        Sync all hosts from API to database.
        Returns number of synced hosts.
        """
        if not db_service.is_connected:
            return 0
        
        try:
            # Fetch all hosts from API
            response = await api_client.get_hosts(skip_cache=True)
            hosts = response.get("response", [])
            
            total_synced = 0
            for host in hosts:
                try:
                    await db_service.upsert_host({"response": host})
                    total_synced += 1
                except Exception as e:
                    logger.warning("Failed to sync host %s: %s", host.get("uuid"), e)
            
            # Update sync metadata
            await db_service.update_sync_metadata(
                key="hosts",
                status="success",
                records_synced=total_synced
            )
            
            logger.debug("Synced %d hosts", total_synced)
            return total_synced
            
        except Exception as e:
            await db_service.update_sync_metadata(
                key="hosts",
                status="error",
                error_message=str(e)
            )
            raise
    
    async def sync_config_profiles(self) -> int:
        """
        Sync all config profiles from API to database.
        Returns number of synced profiles.
        """
        if not db_service.is_connected:
            return 0
        
        try:
            # Fetch all config profiles from API
            response = await api_client.get_config_profiles(skip_cache=True)
            profiles = response.get("response", [])
            
            total_synced = 0
            for profile in profiles:
                try:
                    await db_service.upsert_config_profile({"response": profile})
                    total_synced += 1
                except Exception as e:
                    logger.warning("Failed to sync config profile %s: %s", profile.get("uuid"), e)
            
            # Update sync metadata
            await db_service.update_sync_metadata(
                key="config_profiles",
                status="success",
                records_synced=total_synced
            )
            
            logger.debug("Synced %d config profiles", total_synced)
            return total_synced
            
        except Exception as e:
            await db_service.update_sync_metadata(
                key="config_profiles",
                status="error",
                error_message=str(e)
            )
            raise
    
    # ==================== Webhook Event Handlers ====================
    
    async def handle_webhook_event(self, event: str, event_data: Dict[str, Any]) -> None:
        """
        Handle webhook event and update database accordingly.
        
        Args:
            event: Event type (e.g., "user.created", "node.modified")
            event_data: Event payload data
        """
        if not db_service.is_connected:
            logger.debug("Database not connected, skipping webhook sync for %s", event)
            return
        
        try:
            if event.startswith("user."):
                await self._handle_user_webhook(event, event_data)
            elif event.startswith("node."):
                await self._handle_node_webhook(event, event_data)
            elif event.startswith("host."):
                await self._handle_host_webhook(event, event_data)
            else:
                logger.debug("Unhandled webhook event for sync: %s", event)
                
        except Exception as e:
            logger.error("Error handling webhook event %s: %s", event, e)
    
    async def _handle_user_webhook(self, event: str, event_data: Dict[str, Any]) -> None:
        """Handle user-related webhook events."""
        uuid = event_data.get("uuid")
        
        if not uuid:
            logger.warning("User webhook event without UUID: %s", event)
            return
        
        if event == "user.deleted":
            # Delete user from database
            await db_service.delete_user(uuid)
            logger.debug("Deleted user %s from database (webhook)", uuid)
        else:
            # For all other user events, upsert the user data
            # The event_data should contain the user info
            await db_service.upsert_user({"response": event_data})
            logger.debug("Updated user %s in database (webhook: %s)", uuid, event)
    
    async def _handle_node_webhook(self, event: str, event_data: Dict[str, Any]) -> None:
        """Handle node-related webhook events."""
        uuid = event_data.get("uuid")
        
        if not uuid:
            logger.warning("Node webhook event without UUID: %s", event)
            return
        
        if event == "node.deleted":
            # Delete node from database
            await db_service.delete_node(uuid)
            logger.debug("Deleted node %s from database (webhook)", uuid)
        else:
            # For all other node events, upsert the node data
            await db_service.upsert_node({"response": event_data})
            logger.debug("Updated node %s in database (webhook: %s)", uuid, event)
    
    async def _handle_host_webhook(self, event: str, event_data: Dict[str, Any]) -> None:
        """Handle host-related webhook events."""
        uuid = event_data.get("uuid")
        
        if not uuid:
            logger.warning("Host webhook event without UUID: %s", event)
            return
        
        if event == "host.deleted":
            # Delete host from database
            await db_service.delete_host(uuid)
            logger.debug("Deleted host %s from database (webhook)", uuid)
        else:
            # For all other host events, upsert the host data
            await db_service.upsert_host({"response": event_data})
            logger.debug("Updated host %s in database (webhook: %s)", uuid, event)
    
    # ==================== On-Demand Sync ====================
    
    async def sync_single_user(self, uuid: str) -> bool:
        """
        Sync a single user from API to database.
        Returns True if successful.
        """
        if not db_service.is_connected:
            return False
        
        try:
            user = await api_client.get_user_by_uuid(uuid)
            await db_service.upsert_user(user)
            logger.debug("Synced single user %s", uuid)
            return True
        except Exception as e:
            logger.warning("Failed to sync single user %s: %s", uuid, e)
            return False
    
    async def sync_single_node(self, uuid: str) -> bool:
        """
        Sync a single node from API to database.
        Returns True if successful.
        """
        if not db_service.is_connected:
            return False
        
        try:
            node = await api_client.get_node(uuid)
            await db_service.upsert_node(node)
            logger.debug("Synced single node %s", uuid)
            return True
        except Exception as e:
            logger.warning("Failed to sync single node %s: %s", uuid, e)
            return False
    
    async def sync_single_host(self, uuid: str) -> bool:
        """
        Sync a single host from API to database.
        Returns True if successful.
        """
        if not db_service.is_connected:
            return False
        
        try:
            host = await api_client.get_host(uuid)
            await db_service.upsert_host(host)
            logger.debug("Synced single host %s", uuid)
            return True
        except Exception as e:
            logger.warning("Failed to sync single host %s: %s", uuid, e)
            return False


# Global sync service instance
sync_service = SyncService()
