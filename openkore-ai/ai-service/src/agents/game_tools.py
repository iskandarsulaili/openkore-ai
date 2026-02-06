"""
Custom CrewAI Tools for Ragnarok Online Game Actions
These tools will be used by CrewAI agents to interact with the game
"""

from crewai.tools import BaseTool
from pydantic import Field
from typing import Optional, Dict, Any
from loguru import logger


class AttackMonsterTool(BaseTool):
    """Tool for attacking monsters in the game"""
    
    name: str = "attack_monster"
    description: str = (
        "Attack a specific monster by its name or ID. "
        "Use this when you need to engage in combat. "
        "Input: monster_name (string) or monster_id (int)"
    )
    
    def _run(self, monster_name: str) -> str:
        """Execute monster attack"""
        logger.info(f"[TOOL] Attacking monster: {monster_name}")
        # In production, this would send command to OpenKore
        return f"Initiated attack on {monster_name}"


class UseSkillTool(BaseTool):
    """Tool for using character skills"""
    
    name: str = "use_skill"
    description: str = (
        "Use a character skill on a target. "
        "Input format: 'skill_name, target_name' (comma separated)"
    )
    
    def _run(self, skill_and_target: str) -> str:
        """Execute skill usage"""
        try:
            parts = skill_and_target.split(',')
            skill_name = parts[0].strip()
            target = parts[1].strip() if len(parts) > 1 else "self"
            logger.info(f"[TOOL] Using skill: {skill_name} on {target}")
            return f"Used {skill_name} on {target}"
        except Exception as e:
            return f"Error using skill: {e}"


class MoveToLocationTool(BaseTool):
    """Tool for moving to specific coordinates"""
    
    name: str = "move_to_location"
    description: str = (
        "Move character to specific coordinates on the map. "
        "Input format: 'x,y' (comma separated coordinates)"
    )
    
    def _run(self, coordinates: str) -> str:
        """Execute movement"""
        try:
            x, y = map(int, coordinates.split(','))
            logger.info(f"[TOOL] Moving to: ({x}, {y})")
            return f"Moving to coordinates ({x}, {y})"
        except Exception as e:
            return f"Error moving: {e}"


class UseItemTool(BaseTool):
    """Tool for using items from inventory"""
    
    name: str = "use_item"
    description: str = (
        "Use an item from inventory. "
        "Common items: White Potion, Blue Potion, Fly Wing, Butterfly Wing. "
        "Input: item_name (string)"
    )
    
    def _run(self, item_name: str) -> str:
        """Execute item usage"""
        logger.info(f"[TOOL] Using item: {item_name}")
        return f"Used {item_name}"


class BuyItemTool(BaseTool):
    """Tool for buying items from NPC shops"""
    
    name: str = "buy_item"
    description: str = (
        "Buy items from NPC shop. "
        "Input format: 'item_name, quantity' (comma separated)"
    )
    
    def _run(self, item_and_quantity: str) -> str:
        """Execute item purchase"""
        try:
            parts = item_and_quantity.split(',')
            item_name = parts[0].strip()
            quantity = int(parts[1].strip()) if len(parts) > 1 else 1
            logger.info(f"[TOOL] Buying: {quantity}x {item_name}")
            return f"Purchased {quantity}x {item_name}"
        except Exception as e:
            return f"Error buying item: {e}"


class CheckInventoryTool(BaseTool):
    """Tool for checking inventory status"""
    
    name: str = "check_inventory"
    description: str = (
        "Check current inventory status including weight and items. "
        "Input: 'status' or 'search:item_name' to search for specific item"
    )
    
    def _run(self, query: str = "status") -> str:
        """Check inventory"""
        logger.info(f"[TOOL] Checking inventory: {query}")
        # In production, would query actual game state
        if query == "status":
            return "Inventory: 45/100 weight, 25 slots used"
        elif query.startswith("search:"):
            item = query.split(':')[1]
            return f"Found 5x {item} in inventory"
        return "Inventory checked"


class StoreItemsTool(BaseTool):
    """Tool for storing items in Kafra storage"""
    
    name: str = "store_items"
    description: str = (
        "Store items in Kafra storage to free up weight. "
        "Input: 'all' to store all possible items, or 'item_name' for specific item"
    )
    
    def _run(self, items: str = "all") -> str:
        """Execute item storage"""
        logger.info(f"[TOOL] Storing items: {items}")
        return f"Stored {items} in Kafra storage"


class ChangeMapTool(BaseTool):
    """Tool for changing maps/locations"""
    
    name: str = "change_map"
    description: str = (
        "Change to a different map by using portals or teleport. "
        "Input: map_name (e.g., 'prontera', 'geffen', 'payon')"
    )
    
    def _run(self, map_name: str) -> str:
        """Execute map change"""
        logger.info(f"[TOOL] Changing to map: {map_name}")
        return f"Traveling to {map_name}"


class AnalyzeGameStateTool(BaseTool):
    """Tool for analyzing current game state"""
    
    name: str = "analyze_game_state"
    description: str = (
        "Analyze current game state to get situational awareness. "
        "Returns info about character status, nearby monsters, and environment. "
        "Input: 'full' for complete analysis or 'quick' for summary"
    )
    
    def _run(self, analysis_type: str = "quick") -> str:
        """Analyze game state"""
        logger.info(f"[TOOL] Analyzing game state: {analysis_type}")
        if analysis_type == "full":
            return (
                "Full Analysis:\n"
                "- Character: Lv 50 Knight, HP 2500/3000, SP 150/200\n"
                "- Location: prt_fild08 (150, 200)\n"
                "- Nearby monsters: 3x Poring, 2x Lunatic\n"
                "- Party members: None\n"
                "- Weight: 45/100"
            )
        return "Quick status: Healthy, 3 monsters nearby, safe location"


class ChatWithPlayerTool(BaseTool):
    """Tool for chatting with other players"""
    
    name: str = "chat_with_player"
    description: str = (
        "Send a chat message to a player or public chat. "
        "Input format: 'player_name, message' or 'public, message'"
    )
    
    def _run(self, chat_input: str) -> str:
        """Send chat message"""
        try:
            target, message = chat_input.split(',', 1)
            target = target.strip()
            message = message.strip()
            logger.info(f"[TOOL] Chat to {target}: {message}")
            return f"Sent message to {target}"
        except Exception as e:
            return f"Error sending chat: {e}"


# Collection of all game tools
GAME_TOOLS = [
    AttackMonsterTool(),
    UseSkillTool(),
    MoveToLocationTool(),
    UseItemTool(),
    BuyItemTool(),
    CheckInventoryTool(),
    StoreItemsTool(),
    ChangeMapTool(),
    AnalyzeGameStateTool(),
    ChatWithPlayerTool()
]

# Tool sets for specific agent roles
COMBAT_TOOLS = [
    AttackMonsterTool(),
    UseSkillTool(),
    UseItemTool(),
    AnalyzeGameStateTool()
]

RESOURCE_TOOLS = [
    CheckInventoryTool(),
    StoreItemsTool(),
    BuyItemTool(),
    UseItemTool()
]

NAVIGATION_TOOLS = [
    MoveToLocationTool(),
    ChangeMapTool(),
    AnalyzeGameStateTool()
]

STRATEGIC_TOOLS = [
    AnalyzeGameStateTool(),
    ChatWithPlayerTool(),
    CheckInventoryTool()
]
