"""Browser automation controller using browser-use and WebSocket."""

import asyncio
from browser_use import Agent, Browser, Controller
from typing import Dict, Any, Optional
import websockets
import json
import logging

logger = logging.getLogger(__name__)


class BrowserController:
    """Controls browser through browser-use and WebSocket to Chrome extension."""
    
    def __init__(
        self,
        hub=None,
        cdp_url: str = "http://localhost:9222",
    ):
        """
        Initialize browser controller.
        
        Args:
            hub: VoiceBrowserHub instance for WebSocket communication
            cdp_url: Chrome DevTools Protocol URL
        """
        self.hub = hub
        self.cdp_url = cdp_url
        self.browser: Optional[Browser] = None
        self.agent: Optional[Agent] = None
        
        logger.info("Browser controller initialized")
    
    async def initialize(self):
        """Initialize browser-use agent."""
        try:
            # Don't create browser here - create fresh one for each task
            logger.info("Browser controller ready")
        except Exception as e:
            logger.error(f"Failed to initialize browser controller: {e}")
    
    async def execute_simple_action(self, command: Dict[str, Any]) -> bool:
        """
        Execute simple action via Chrome extension WebSocket, fallback to browser-use.
        
        Args:
            command: Parsed command dictionary
            
        Returns:
            True if successful
        """
        cmd_type = command.get("type")
        
        # Build action for Chrome extension
        action = None
        
        if cmd_type == "scroll":
            direction = command.get("direction")
            if direction in ["up", "top"]:
                action = {"type": "scroll", "direction": "up"}
            elif direction in ["down", "bottom"]:
                action = {"type": "scroll", "direction": "down"}
        
        elif cmd_type == "click":
            target = command.get("target")
            action = {"type": "click", "text": target}
        
        elif cmd_type == "type":
            text = command.get("text")
            action = {"type": "input", "value": text}
        
        elif cmd_type == "navigate":
            url = command.get("url")
            action = {"type": "navigate", "url": url}
        
        elif cmd_type == "search":
            query = command.get("query")
            search_url = f"https://www.google.com/search?q={query}"
            action = {"type": "navigate", "url": search_url}
        
        elif cmd_type == "tab_control":
            action_type = command.get("action")
            action = {"type": "tab", "action": action_type}
            if action_type == "switch":
                action["index"] = command.get("index")
        
        elif cmd_type == "browser_control":
            action_type = command.get("action")
            action = {"type": "browser", "action": action_type}
        
        if action:
            # Try extension first
            if await self._send_to_extension(action):
                # Wait for action to complete (scrolling, clicking, etc.)
                # Add reasonable delay based on action type
                if cmd_type == "scroll":
                    await asyncio.sleep(0.8)  # Wait for smooth scroll
                elif cmd_type == "click":
                    await asyncio.sleep(0.5)  # Wait for click and potential page load
                elif cmd_type == "navigate":
                    await asyncio.sleep(1.5)  # Wait for navigation
                else:
                    await asyncio.sleep(0.5)  # Default delay
                logger.info(f"Action {cmd_type} completed")
                return True
            
            # Fallback to browser-use for simple commands
            logger.info("Extension unavailable, using browser-use fallback")
            return await self._execute_with_browser_use(command)
        
        return False
    
    async def _execute_with_browser_use(self, command: Dict[str, Any]) -> bool:
        """Execute simple command using browser-use as fallback."""
        try:
            cmd_type = command.get("type")
            raw_text = command.get("raw_text", "")
            
            # Convert to natural language task
            task = raw_text
            
            logger.info(f"Executing via browser-use: {task}")
            result = await self.execute_complex_task(task)
            
            return "error" not in result.lower()
        except Exception as e:
            logger.error(f"Browser-use fallback error: {e}")
            return False
    
    async def execute_complex_task(self, description: str) -> str:
        """
        Execute complex task using browser-use agent.
        
        Args:
            description: Natural language task description
            
        Returns:
            Result message
        """
        browser = None
        try:
            logger.info(f"Executing complex task: {description}")
            
            # Create fresh browser for each task to avoid stale connections
            browser = Browser(cdp_url=self.cdp_url)
            
            # Create agent for this task
            agent = Agent(
                task=description,
                llm=None,  # Uses default ChatBrowserUse
                browser=browser,
                max_steps=50,  # Reduced from 100
            )
            
            # Run agent
            result = await agent.run()
            
            logger.info(f"Task completed: {result}")
            
            # Extract meaningful result
            if hasattr(result, 'final_result'):
                return str(result.final_result())
            return str(result)
        
        except Exception as e:
            logger.error(f"Complex task error: {e}")
            return f"Error: {e}"
        
        finally:
            # Clean up browser session
            if browser:
                try:
                    # browser-use Browser doesn't need explicit close
                    # The context manager handles cleanup
                    pass
                except Exception as e:
                    logger.debug(f"Browser cleanup: {e}")
    
    async def _send_to_extension(self, action: Dict[str, Any]) -> bool:
        """
        Send action to Chrome extension via hub's WebSocket connections.
        
        Args:
            action: Action dictionary
            
        Returns:
            True if sent successfully
        """
        if not self.hub:
            logger.error("No hub instance available")
            return False
            
        if not self.hub.ws_connections:
            logger.error(f"No WebSocket connections available (hub has {len(self.hub.ws_connections)} connections)")
            print(f"\n❌ CHROME EXTENSION NOT CONNECTED!")
            print(f"   Make sure Chrome extension is installed and loaded")
            print(f"   Check chrome://extensions/ and look for 'Voice Browser Control'")
            print(f"   The background service worker should show connection logs\n")
            return False
        
        try:
            message = {"action": action}
            sent_count = 0
            
            # Send to all connected WebSocket clients
            disconnected = set()
            for ws in self.hub.ws_connections:
                try:
                    await ws.send_json(message)
                    sent_count += 1
                except Exception as e:
                    logger.debug(f"Failed to send to WebSocket: {e}")
                    disconnected.add(ws)
            
            # Remove disconnected clients
            self.hub.ws_connections -= disconnected
            
            if sent_count > 0:
                logger.info(f"Sent to extension ({sent_count} connections): {action}")
                return True
            else:
                logger.error("No active WebSocket connections")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send to extension: {e}")
            return False
    
    async def cleanup(self):
        """Clean up resources."""
        # No persistent browser to clean up
        logger.info("Browser controller cleaned up")
