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
        chrome_ws_url: str = "ws://localhost:8765",
        cdp_url: str = "http://localhost:9222",
    ):
        """
        Initialize browser controller.
        
        Args:
            chrome_ws_url: WebSocket URL for Chrome extension
            cdp_url: Chrome DevTools Protocol URL
        """
        self.chrome_ws_url = chrome_ws_url
        self.cdp_url = cdp_url
        self.browser: Optional[Browser] = None
        self.agent: Optional[Agent] = None
        self.ws_connections = set()
        
        logger.info("Browser controller initialized")
    
    async def initialize(self):
        """Initialize browser-use agent."""
        try:
            self.browser = Browser(cdp_url=self.cdp_url)
            logger.info("Browser-use initialized")
        except Exception as e:
            logger.error(f"Failed to initialize browser-use: {e}")
    
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
        try:
            if not self.browser:
                await self.initialize()
            
            logger.info(f"Executing complex task: {description}")
            
            # Create agent for this task
            agent = Agent(
                task=description,
                llm=None,  # Uses default ChatBrowserUse
                browser=self.browser,
                max_steps=100,
            )
            
            # Run agent
            result = await agent.run()
            
            logger.info(f"Task completed: {result}")
            return str(result)
        
        except Exception as e:
            logger.error(f"Complex task error: {e}")
            return f"Error: {e}"
    
    async def _send_to_extension(self, action: Dict[str, Any]) -> bool:
        """
        Send action to Chrome extension via WebSocket.
        
        Args:
            action: Action dictionary
            
        Returns:
            True if sent successfully
        """
        try:
            async with websockets.connect(self.chrome_ws_url) as websocket:
                await websocket.send(json.dumps(action))
                logger.info(f"Sent to extension: {action}")
                return True
        except Exception as e:
            logger.error(f"Failed to send to extension: {e}")
            return False
    
    async def cleanup(self):
        """Clean up resources."""
        if self.browser:
            try:
                # browser-use Browser doesn't have close method, just clear reference
                self.browser = None
            except Exception as e:
                logger.error(f"Error cleaning up browser: {e}")
        logger.info("Browser controller cleaned up")
