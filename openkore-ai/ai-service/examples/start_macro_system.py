#!/usr/bin/env python3
"""
Three-Layer Macro Management System - Startup Example
Demonstrates how to start and run the macro system
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from macro.coordinator import MacroManagementCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/macro_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """
    Main entry point for three-layer macro management system
    """
    logger.info("=" * 70)
    logger.info("THREE-LAYER ADAPTIVE MACRO MANAGEMENT SYSTEM")
    logger.info("=" * 70)
    
    # Initialize coordinator
    logger.info("Initializing MacroManagementCoordinator...")
    coordinator = MacroManagementCoordinator(
        openkore_url="http://127.0.0.1:8765",
        db_path="data/openkore-ai.db"
    )
    
    # Health check
    logger.info("Performing health check...")
    health = await coordinator.health_check()
    
    if health['deployment_service']:
        logger.info("[OK] MacroHotReload plugin is accessible")
    else:
        logger.warning(" MacroHotReload plugin not responding")
        logger.warning("  Make sure OpenKore is running with MacroHotReload plugin")
    
    if health['ml_model_trained']:
        logger.info("[OK] ML model is trained and ready")
    else:
        logger.warning(" ML model not trained yet")
        logger.info("  The system will collect data and train automatically")
    
    logger.info(f"Training samples collected: {health['training_samples']}")
    
    # Example game state processing
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE: Processing Game State")
    logger.info("=" * 70)
    
    sample_game_state = {
        'character': {
            'name': 'ExampleChar',
            'level': 50,
            'job_class': 'Knight',
            'hp': 3500,
            'max_hp': 5000,
            'sp': 200,
            'max_sp': 300,
            'weight': 800,
            'max_weight': 2000,
            'zeny': 50000
        },
        'position': {
            'map': 'prt_fild08',
            'x': 175,
            'y': 180
        },
        'nearby': {
            'monsters': [
                {'name': 'Poring', 'level': 1, 'distance': 5.2, 'is_aggressive': False},
                {'name': 'Drops', 'level': 2, 'distance': 8.5, 'is_aggressive': False}
            ]
        },
        'inventory': {
            'items': []
        },
        'objective': 'farm_efficiently'
    }
    
    # Process game state
    result = await coordinator.process_game_state(
        game_state=sample_game_state,
        session_id="example_session"
    )
    
    logger.info(f"\nProcessing Result:")
    logger.info(f"  Layer Used: Layer {result['layer']}")
    logger.info(f"  Action: {result['action']}")
    
    if result['layer'] == 1:
        logger.info(f"  Conscious Reasoning (CrewAI)")
        if result.get('needs_macro'):
            logger.info(f"  Macro Generated: {result.get('macro_name')}")
            logger.info(f"  Macro Type: {result.get('macro_type')}")
    elif result['layer'] == 2:
        logger.info(f"  ML Prediction (Subconscious)")
        logger.info(f"  Macro Type: {result.get('macro_type')}")
        logger.info(f"  Confidence: {result.get('confidence', 0):.1%}")
    else:
        logger.info(f"  Emergency Reflex (Rule-Based)")
        logger.info(f"  Reason: {result.get('reason')}")
    
    # Display system statistics
    logger.info("\n" + "=" * 70)
    logger.info("SYSTEM STATISTICS")
    logger.info("=" * 70)
    
    stats = coordinator.get_system_statistics()
    
    logger.info(f"\nProcessing Stats:")
    logger.info(f"  Total Requests: {stats['processing_stats']['total_requests']}")
    logger.info(f"  Layer 1 (Conscious): {stats['processing_stats']['layer1_used']}")
    logger.info(f"  Layer 2 (ML): {stats['processing_stats']['layer2_used']}")
    logger.info(f"  Layer 3 (Reflex): {stats['processing_stats']['layer3_used']}")
    logger.info(f"  Macros Deployed: {stats['processing_stats']['macros_deployed']}")
    
    logger.info(f"\nML Stats:")
    logger.info(f"  Total Predictions: {stats['ml_stats']['total_predictions']}")
    logger.info(f"  High Confidence: {stats['ml_stats']['high_confidence_predictions']}")
    logger.info(f"  Confidence Rate: {stats['ml_stats']['high_confidence_rate']:.1%}")
    
    logger.info(f"\nTraining Progress:")
    logger.info(f"  Total Samples: {stats['training_progress']['total_samples_collected']}")
    logger.info(f"  Model Trained: {stats['training_progress']['model_trained']}")
    
    # Train ML model if enough data
    if stats['training_progress']['total_samples_collected'] >= 100:
        logger.info("\n" + "=" * 70)
        logger.info("TRAINING ML MODEL")
        logger.info("=" * 70)
        
        training_result = await coordinator.train_ml_model(min_samples=100)
        
        if training_result['status'] == 'success':
            logger.info(f"[OK] Model trained successfully!")
            logger.info(f"  Training Accuracy: {training_result['train_accuracy']:.2%}")
            logger.info(f"  Validation Accuracy: {training_result.get('val_accuracy', 0):.2%}")
        else:
            logger.info(f"Training skipped: {training_result['status']}")
    else:
        logger.info(f"\nNeed {100 - stats['training_progress']['total_samples_collected']} more samples for ML training")
    
    # Continuous processing loop (commented out for example)
    logger.info("\n" + "=" * 70)
    logger.info("SYSTEM READY")
    logger.info("=" * 70)
    logger.info("\nTo enable continuous processing, uncomment the loop in this script")
    logger.info("The system will process game states and generate macros automatically")
    logger.info("\nPress Ctrl+C to stop")
    
    # Uncomment this for continuous operation:
    # try:
    #     while True:
    #         # Get game state from OpenKore (implement your bridge here)
    #         game_state = get_current_game_state()
    #         
    #         # Process game state
    #         result = await coordinator.process_game_state(game_state)
    #         
    #         # Wait before next check
    #         await asyncio.sleep(10)  # Process every 10 seconds
    # except KeyboardInterrupt:
    #     logger.info("\nShutting down...")
    #     await coordinator.close()
    
    # Cleanup
    await coordinator.close()
    logger.info("System shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
