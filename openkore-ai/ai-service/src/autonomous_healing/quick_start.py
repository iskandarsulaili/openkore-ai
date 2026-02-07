"""
Quick Start Script for Autonomous Self-Healing System
Run this to start monitoring your OpenKore bot
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from autonomous_healing.main import AutonomousHealingSystem


async def main():
    """Quick start the healing system"""
    print("=" * 70)
    print("OpenKore Autonomous Self-Healing System - Quick Start")
    print("=" * 70)
    print()
    print("This system will:")
    print("  [OK] Monitor OpenKore logs in real-time")
    print("  [OK] Detect errors, warnings, and behavioral issues")
    print("  [OK] Analyze root causes intelligently")
    print("  [OK] Generate context-aware fixes")
    print("  [OK] Apply fixes safely with backup/rollback")
    print("  [OK] Learn from outcomes to improve over time")
    print()
    print("Starting monitoring...")
    print("=" * 70)
    print()
    
    # Create and start system
    config_path = Path(__file__).parent / "config.yaml"
    system = AutonomousHealingSystem(config_path=str(config_path))
    
    await system.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nStopped by user. Goodbye!")
        sys.exit(0)
