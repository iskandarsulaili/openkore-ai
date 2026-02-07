"""
Wrapper script to run Autonomous Self-Healing System
Fixes import paths and runs the system
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables BEFORE importing other modules
load_dotenv()

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Now import the system
from autonomous_healing.main import AutonomousHealingSystem


async def main():
    """Run the healing system"""
    print("=" * 70)
    print("OpenKore Autonomous Self-Healing System - TEST RUN")
    print("=" * 70)
    print()
    print("Testing Phase 31 enhancements...")
    print("  [1] Issue: Missing auto-heal (death with Apple in inventory)")
    print("  [2] Issue: Teleport spam (no Teleport skill)")
    print("  [3] Issue: Inappropriate thresholds (sitAuto_hp_lower)")
    print("  [4] Issue: Inefficient lockMap range")
    print("  [5] Issue: Unspent stat points (statsAddAuto 0)")
    print()
    print("Starting monitoring...")
    print("=" * 70)
    print()
    
    # Create and start system
    config_path = src_dir / "autonomous_healing" / "config.yaml"
    system = AutonomousHealingSystem(config_path=str(config_path))
    
    try:
        await system.start()
    except KeyboardInterrupt:
        print("\n\nStopping system...")
        await system.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
