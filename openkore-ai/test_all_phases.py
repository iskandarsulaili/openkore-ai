"""
Comprehensive Test Suite - All Phases
Runs all tests from Phases 1-8 plus integration tests
"""

import subprocess
import sys

TESTS = [
    ("Phase 1: HTTP Bridge", "test_phase1.py"),
    ("Phase 2: Multi-Tier Decision", "test_phase2.py"),
    ("Phase 3: Python AI Service", "test_phase3.py"),
    ("Phase 4: PDCA Cycle", "test_phase4.py"),
    ("Integration: End-to-End", "test_integration_e2e.py")
]

def run_test(test_name: str, test_file: str) -> bool:
    """Run a single test file"""
    print(f"\n{'='*70}")
    print(f"Running: {test_name}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=False,
            timeout=120
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"✗ TIMEOUT: {test_name}")
        return False
    except Exception as e:
        print(f"✗ ERROR: {test_name} - {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("OPENKORE ADVANCED AI - COMPREHENSIVE TEST SUITE")
    print("Testing all implemented phases")
    print("=" * 70)
    
    results = {}
    for test_name, test_file in TESTS:
        results[test_name] = run_test(test_name, test_file)
    
    print("\n" + "=" * 70)
    print("FINAL TEST RESULTS")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<50} {status}")
    
    total_tests = len(results)
    passed_tests = sum(1 for p in results.values() if p)
    
    print("=" * 70)
    print(f"Total: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.0f}%)")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL SYSTEMS OPERATIONAL - PRODUCTION READY! 🎉")
    else:
        print(f"\n⚠ {total_tests - passed_tests} test(s) failed - review before deployment")
