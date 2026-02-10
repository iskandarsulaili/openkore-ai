"""
Live Integration Monitor
Continuously monitors integration health while system is running.

Watches for:
- HTTP requests from OpenKore
- Database queries
- Decision pipeline execution
- Integration points activation
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
from pathlib import Path

class IntegrationMonitor:
    def __init__(self):
        self.ai_service_url = "http://127.0.0.1:9902"
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'decision_requests': 0,
            'stat_allocation_requests': 0,
            'skill_allocation_requests': 0,
            'database_queries': 0,
            'openmemory_ops': 0,
            'trigger_activations': 0
        }
        self.previous_stats = None
        
    async def monitor(self, duration_seconds: int = 300):
        """
        Monitor for specified duration (default 5 minutes).
        
        Args:
            duration_seconds: How long to monitor (default 300s = 5 min)
        """
        
        start_time = time.time()
        print("=" * 80)
        print("LIVE INTEGRATION MONITOR")
        print("=" * 80)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration_seconds}s ({duration_seconds / 60:.1f} minutes)")
        print(f"Target: {self.ai_service_url}")
        print()
        print("Watching for:")
        print("  - HTTP requests from OpenKore")
        print("  - Database queries")
        print("  - Decision pipeline execution")
        print("  - Integration points activation")
        print("=" * 80)
        print()
        
        iteration = 0
        while time.time() - start_time < duration_seconds:
            iteration += 1
            
            # Check AI service metrics endpoint
            await self.check_metrics()
            
            # Print real-time status
            self.print_status(iteration)
            
            # Wait 10 seconds before next check
            await asyncio.sleep(10)
        
        # Final report
        print()
        print("=" * 80)
        print("MONITORING COMPLETE")
        print("=" * 80)
        self.generate_monitoring_report()
        
    async def check_metrics(self):
        """Query AI service integration stats endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{self.ai_service_url}/api/v1/integration/stats',
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Update stats
                        self.stats['total_requests'] = data.get('total_requests', 0)
                        self.stats['decision_requests'] = data.get('decision_requests', 0)
                        self.stats['stat_allocation_requests'] = data.get('stat_allocation_requests', 0)
                        self.stats['skill_allocation_requests'] = data.get('skill_allocation_requests', 0)
                        self.stats['database_queries'] = data.get('database_queries', {}).get('total', 0)
                        self.stats['openmemory_ops'] = data.get('openmemory_operations', 0)
                        self.stats['trigger_activations'] = data.get('trigger_activations', 0)
                        
                        # Store for delta calculation
                        if self.previous_stats is None:
                            self.previous_stats = self.stats.copy()
                    else:
                        self.stats['failed_requests'] += 1
                        
        except Exception as e:
            self.stats['failed_requests'] += 1
            print(f"  [ERROR] Failed to fetch metrics: {e}")
    
    def print_status(self, iteration: int):
        """Print current integration status"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Calculate deltas if we have previous stats
        if self.previous_stats:
            delta_requests = self.stats['total_requests'] - self.previous_stats['total_requests']
            delta_decisions = self.stats['decision_requests'] - self.previous_stats['decision_requests']
            delta_queries = self.stats['database_queries'] - self.previous_stats['database_queries']
        else:
            delta_requests = 0
            delta_decisions = 0
            delta_queries = 0
        
        print(f"[{timestamp}] Check #{iteration}")
        print(f"  Total Requests: {self.stats['total_requests']} (+{delta_requests} since last check)")
        print(f"  Decision Requests: {self.stats['decision_requests']} (+{delta_decisions})")
        print(f"  Database Queries: {self.stats['database_queries']} (+{delta_queries})")
        print(f"  OpenMemory Ops: {self.stats['openmemory_ops']}")
        print(f"  Trigger Activations: {self.stats['trigger_activations']}")
        
        # Health indicators
        if delta_requests > 0:
            print(f"   OpenKore is communicating")
        else:
            print(f"  ⚠ No new requests (OpenKore may not be active)")
        
        if delta_queries > 0:
            print(f"   Databases are being queried")
        elif self.stats['database_queries'] > 0:
            print(f"  ⚠ No new queries (but {self.stats['database_queries']} total)")
        else:
            print(f"  ⚠ Databases not being queried")
        
        print()
        
        # Update previous stats for next iteration
        self.previous_stats = self.stats.copy()
    
    def generate_monitoring_report(self):
        """Generate monitoring report"""
        print("MONITORING SUMMARY:")
        print(f"  Total Requests: {self.stats['total_requests']}")
        print(f"  Decision Requests: {self.stats['decision_requests']}")
        print(f"  Stat Allocations: {self.stats['stat_allocation_requests']}")
        print(f"  Skill Allocations: {self.stats['skill_allocation_requests']}")
        print(f"  Database Queries: {self.stats['database_queries']}")
        print(f"  OpenMemory Operations: {self.stats['openmemory_ops']}")
        print(f"  Trigger Activations: {self.stats['trigger_activations']}")
        print()
        
        # Diagnosis
        print("INTEGRATION HEALTH:")
        if self.stats['total_requests'] == 0:
            print("   CRITICAL: No requests received - OpenKore not communicating")
        elif self.stats['decision_requests'] == 0:
            print("   CRITICAL: No decision requests - GodTierAI.pm not calling API")
        else:
            print("   OpenKore communication: WORKING")
        
        if self.stats['database_queries'] == 0:
            print("   CRITICAL: No database queries - Databases not integrated")
        else:
            print(f"   Database integration: WORKING ({self.stats['database_queries']} queries)")
        
        if self.stats['decision_requests'] > 0 and self.stats['database_queries'] > 0:
            print()
            print("   FULL INTEGRATION: OPERATIONAL ")
        else:
            print()
            print("  ⚠⚠⚠ INTEGRATION: INCOMPLETE ⚠⚠⚠")

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor AI service integration health')
    parser.add_argument('--duration', type=int, default=300,
                       help='Monitor duration in seconds (default: 300 = 5 minutes)')
    parser.add_argument('--interval', type=int, default=10,
                       help='Check interval in seconds (default: 10)')
    
    args = parser.parse_args()
    
    monitor = IntegrationMonitor()
    
    try:
        await monitor.monitor(duration_seconds=args.duration)
    except KeyboardInterrupt:
        print("\n\nMonitoring interrupted by user")
        monitor.generate_monitoring_report()

if __name__ == '__main__':
    asyncio.run(main())
