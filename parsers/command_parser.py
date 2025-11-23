"""Natural language command parser for voice control."""

import re
from typing import Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CommandType(str, Enum):
    """Types of voice commands."""
    SCROLL = "scroll"
    CLICK = "click"
    TYPE = "type"
    NAVIGATE = "navigate"
    SEARCH = "search"
    TAB_CONTROL = "tab_control"
    BROWSER_CONTROL = "browser_control"
    COMPLEX_TASK = "complex_task"
    UNKNOWN = "unknown"


class CommandParser:
    """Parse natural language voice commands into structured actions."""
    
    def __init__(self):
        """Initialize command parser with pattern matching rules."""
        # Quick check patterns for simple commands that should NEVER use AI agent
        self.simple_command_keywords = [
            "scroll", "page up", "page down", "go to top", "go to bottom",
            "next tab", "previous tab", "last tab", "close tab", "new tab",
            "go back", "go forward", "refresh", "reload",
        ]
        
        self.patterns = {
            # Scrolling
            CommandType.SCROLL: [
                (r"scroll\s+(up|down|top|bottom)", self._parse_scroll),
                (r"page\s+(up|down)", self._parse_page),
                (r"go\s+to\s+(top|bottom)", self._parse_scroll_position),
            ],
            
            # Clicking
            CommandType.CLICK: [
                (r"click\s+(.+)", self._parse_click),
                (r"press\s+(.+)", self._parse_click),
                (r"select\s+(.+)", self._parse_click),
            ],
            
            # Typing
            CommandType.TYPE: [
                (r"type\s+(.+)", self._parse_type),
                (r"enter\s+(.+)", self._parse_type),
                (r"input\s+(.+)", self._parse_type),
            ],
            
            # Navigation
            CommandType.NAVIGATE: [
                (r"go\s+to\s+(.+)", self._parse_navigate),
                (r"open\s+(.+)", self._parse_navigate),
                (r"visit\s+(.+)", self._parse_navigate),
                (r"navigate\s+to\s+(.+)", self._parse_navigate),
            ],
            
            # Search
            CommandType.SEARCH: [
                (r"search\s+(?:for\s+)?(.+)", self._parse_search),
                (r"google\s+(.+)", self._parse_search),
                (r"find\s+(.+)", self._parse_search),
            ],
            
            # Tab control
            CommandType.TAB_CONTROL: [
                (r"new\s+tab", self._parse_new_tab),
                (r"close\s+tab", self._parse_close_tab),
                (r"next\s+tab", self._parse_next_tab),
                (r"previous\s+tab", self._parse_previous_tab),
                (r"last\s+tab", self._parse_previous_tab),
                (r"switch\s+to\s+tab\s+(\d+)", self._parse_switch_tab),
            ],
            
            # Browser control
            CommandType.BROWSER_CONTROL: [
                (r"go\s+back", self._parse_back),
                (r"go\s+forward", self._parse_forward),
                (r"refresh|reload", self._parse_refresh),
                (r"stop", self._parse_stop),
            ],
        }
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse voice command text into structured command.
        
        Args:
            text: Voice command text
            
        Returns:
            Dictionary with command type and parameters
        """
        text = text.lower().strip()
        # Remove trailing punctuation (STT often adds periods)
        text = text.rstrip('.!?,;')
        logger.info(f"Parsing command: {text}")
        
        # QUICK CHECK: Ensure simple commands are ALWAYS handled as simple actions
        # This prevents the AI agent from wasting credits on basic navigation
        if self._is_simple_command(text):
            logger.info(f"Quick check: '{text}' identified as simple command")
        
        # Try pattern matching
        for cmd_type, patterns in self.patterns.items():
            for pattern, parser_fn in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result = parser_fn(match)
                    result["type"] = cmd_type
                    result["raw_text"] = text
                    logger.info(f"Parsed as {cmd_type}: {result}")
                    return result
        
        # Check if it's a complex task (multi-step)
        if self._is_complex_task(text):
            return {
                "type": CommandType.COMPLEX_TASK,
                "raw_text": text,
                "description": text,
            }
        
        logger.warning(f"Unknown command: {text}")
        return {
            "type": CommandType.UNKNOWN,
            "raw_text": text,
        }
    
    def _is_simple_command(self, text: str) -> bool:
        """Quick check if command is a simple navigation/control action."""
        # Check if text starts with or contains simple command keywords
        for keyword in self.simple_command_keywords:
            if text.startswith(keyword) or keyword in text:
                return True
        return False
    
    def _is_complex_task(self, text: str) -> bool:
        """Determine if command requires browser-use (complex task)."""
        # First check if it's a simple command - if so, it's NOT complex
        if self._is_simple_command(text):
            return False
        
        complex_indicators = [
            "book", "buy", "order", "compare", "find cheapest",
            "fill out", "submit", "create account", "log in",
            "add to cart", "checkout", "schedule", "reserve",
        ]
        return any(indicator in text for indicator in complex_indicators)
    
    # Parsing functions
    def _parse_scroll(self, match) -> Dict[str, Any]:
        direction = match.group(1)
        return {"direction": direction}
    
    def _parse_page(self, match) -> Dict[str, Any]:
        direction = match.group(1)
        return {"direction": direction, "page": True}
    
    def _parse_scroll_position(self, match) -> Dict[str, Any]:
        position = match.group(1)
        return {"direction": position}
    
    def _parse_click(self, match) -> Dict[str, Any]:
        target = match.group(1).strip()
        return {"target": target}
    
    def _parse_type(self, match) -> Dict[str, Any]:
        text = match.group(1).strip()
        return {"text": text}
    
    def _parse_navigate(self, match) -> Dict[str, Any]:
        url = match.group(1).strip()
        # Add protocol if missing
        if not url.startswith(("http://", "https://")):
            if "." in url:
                url = f"https://{url}"
            else:
                # Assume it's a search query
                url = f"https://www.google.com/search?q={url}"
        return {"url": url}
    
    def _parse_search(self, match) -> Dict[str, Any]:
        query = match.group(1).strip()
        return {"query": query}
    
    def _parse_new_tab(self, match) -> Dict[str, Any]:
        return {"action": "new"}
    
    def _parse_close_tab(self, match) -> Dict[str, Any]:
        return {"action": "close"}
    
    def _parse_next_tab(self, match) -> Dict[str, Any]:
        return {"action": "next"}
    
    def _parse_previous_tab(self, match) -> Dict[str, Any]:
        return {"action": "previous"}
    
    def _parse_switch_tab(self, match) -> Dict[str, Any]:
        tab_index = int(match.group(1))
        return {"action": "switch", "index": tab_index}
    
    def _parse_back(self, match) -> Dict[str, Any]:
        return {"action": "back"}
    
    def _parse_forward(self, match) -> Dict[str, Any]:
        return {"action": "forward"}
    
    def _parse_refresh(self, match) -> Dict[str, Any]:
        return {"action": "refresh"}
    
    def _parse_stop(self, match) -> Dict[str, Any]:
        return {"action": "stop"}
