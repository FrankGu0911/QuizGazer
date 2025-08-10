#!/usr/bin/env python3
"""
Test Runner for Knowledge Base RAG System

This script runs all tests for the knowledge base system:
- Unit tests
- Integration tests
- Performance tests
- UI tests (if available)
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """Test runner for knowledge base system."""
    
    def __init__(self):
        self.test_results = []
        self.start_time = time.time()
    
    def run_test_script(self, script_name: str, description: str) -> bool:
        """Run a test script and capture results."""
        print(f"\n{'='*80}")
        print(f"Running: {description}")
        print(f"Script: {script_name}")
        print(f"{'='*80}")
        
        script_path = Path(__file__).parent / script_name
        
        if not script_path.exists():
            print(f"❌ Test script not found: {script_path}")
            self.test_results.append({
                'name': description,
                'script': script_name,
                'status': 'FAILED',
                'reason': 'Script not found',
                'duration': 0
            })
            return False
        
        start_time = time.time()
        
        try:
            # Run the test script
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                print(f"✅ {description} - PASSED ({duration:.1f}s)")
                self.test_results.append({
                    'name': description,
                    'script': script_name,
                    'status': 'PASSED',
                    'reason': 'All tests passed',
                    'duration': duration,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                })
                return True
            else:
                print(f"❌ {description} - FAILED ({duration:.1f}s)")
                print(f"Exit code: {result.returncode}")
                if result.stderr:
                    print(f"Error output: {result.stderr[:500]}...")
                
                self.test_results.append({
                    'name': description,
                    'script': script_name,
                    'status': 'FAILED',
                    'reason': f'Exit code {result.returncode}',
                    'duration': duration,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                })
                return False
        
        except subprocess.TimeoutExpired:
            print(f"⏰ {description} - TIMEOUT")
            self.test_results.append({
                'name': description,
                'script': script_name,
                'status': 'TIMEOUT',
                'reason': 'Test exceeded 10 minute timeout',
                'duration': 600
            })
            return False
        
        except Exception as e:
            print(f"❌ {description} - ERROR: {e}")
            self.test_results.append({
                'name': description,
                'script': script_name,
                'status': 'ERROR',
                'reason': str(e),
                'duration': time.time() - start_time
            })
            return False
    
    def run_unit_tests(self) -> bool:
        """Run unit tests."""
        unit_tests = [
            ('test_knowledge_base_models.py', 'Knowledge Base Models Unit Tests'),
            ('test_document_processor.py', 'Document Processor Unit Tests'),
            ('test_knowledge_retriever.py', 'Knowledge Retriever Unit Tests'),
            ('test_rag_pipeline.py', 'RAG Pipeline Unit Tests'),
            ('test_error_handling.py', 'Error Handling Unit Tests')
        ]
        
        print(f"\n{'='*80}")
        print("RUNNING UNIT TESTS")
        print(f"{'='*80}")
        
        success_count = 0
        
        for script, description in unit_tests:
            # Check if test file exists in knowledge_base directory
            kb_test_path = project_root / 'core' / 'knowledge_base' / script
            if kb_test_path.exists():
                if self.run_python_module(f'core.knowledge_base.{script[:-3]}', description):
                    success_count += 1
            else:
                print(f"⏭️  Skipping {description} - Test file not found")
                self.test_results.append({
                    'name': description,
                    'script': script,
                    'status': 'SKIPPED',
                    'reason': 'Test file not found',
                    'duration': 0
                })
        
        return success_count > 0
    
    def run_python_module(self, module_name: str, description: str) -> bool:
        """Run a Python module as a test."""
        print(f"\nRunning: {description}")
        print(f"Module: {module_name}")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', module_name],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                cwd=str(project_root)
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                print(f"✅ {description} - PASSED ({duration:.1f}s)")
                self.test_results.append({
                    'name': description,
                    'script': module_name,
                    'status': 'PASSED',
                    'reason': 'All tests passed',
                    'duration': duration
                })
                return True
            else:
                print(f"❌ {description} - FAILED ({duration:.1f}s)")
                if result.stderr:
                    print(f"Error: {result.stderr[:200]}...")
                
                self.test_results.append({
                    'name': description,
                    'script': module_name,
                    'status': 'FAILED',
                    'reason': f'Exit code {result.returncode}',
                    'duration': duration
                })
                return False
        
        except Exception as e:
            print(f"❌ {description} - ERROR: {e}")
            self.test_results.append({
                'name': description,
                'script': module_name,
                'status': 'ERROR',
                'reason': str(e),
                'duration': time.time() - start_time
            })
            return False
    
    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        return self.run_test_script(
            'test_knowledge_base_integration.py',
            'Knowledge Base Integration Tests'
        )
    
    def run_performance_tests(self) -> bool:
        """Run performance tests."""
        return self.run_test_script(
            'test_knowledge_base_performance.py',
            'Knowledge Base Performance Tests'
        )
    
    def run_ui_tests(self) -> bool:
        """Run UI tests."""
        # Check if UI test script exists
        ui_test_path = Path(__file__).parent / 'test_knowledge_base_ui.py'
        
        if ui_test_path.exists():
            return self.run_test_script(
                'test_knowledge_base_ui.py',
                'Knowledge Base UI Tests'
            )
        else:
            print("⏭️  Skipping UI Tests - Test file not found")
            self.test_results.append({
                'name': 'Knowledge Base UI Tests',
                'script': 'test_knowledge_base_ui.py',
                'status': 'SKIPPED',
                'reason': 'Test file not found',
                'duration': 0
            })
            return True
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        print("\nChecking dependencies...")
        
        required_packages = [
            'chromadb',
            'sentence-transformers',
            'langchain',
            'pandas',
            'numpy'
        ]
        
        optional_packages = [
            'PySide6',
            'psutil'
        ]
        
        missing_required = []
        missing_optional = []
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"✅ {package}")
            except ImportError:
                print(f"❌ {package} (required)")
                missing_required.append(package)
        
        for package in optional_packages:
            try:
                __import__(package)
                print(f"✅ {package} (optional)")
            except ImportError:
                print(f"⚠️  {package} (optional)")
                missing_optional.append(package)
        
        if missing_required:
            print(f"\n❌ Missing required packages: {', '.join(missing_required)}")
            print("Please install them with: pip install " + " ".join(missing_required))
            return False
        
        if missing_optional:
            print(f"\n⚠️  Missing optional packages: {', '.join(missing_optional)}")
            print("Some tests may be skipped. Install with: pip install " + " ".join(missing_optional))
        
        print("\n✅ Dependency check completed")
        return True
    
    def print_summary(self):
        """Print test summary."""
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        print(f"\n{'='*80}")
        print("TEST EXECUTION SUMMARY")
        print(f"{'='*80}")
        
        # Count results by status
        passed = len([r for r in self.test_results if r['status'] == 'PASSED'])
        failed = len([r for r in self.test_results if r['status'] == 'FAILED'])
        skipped = len([r for r in self.test_results if r['status'] == 'SKIPPED'])
        timeout = len([r for r in self.test_results if r['status'] == 'TIMEOUT'])
        error = len([r for r in self.test_results if r['status'] == 'ERROR'])
        
        total_tests = len(self.test_results)
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏭️  Skipped: {skipped}")
        print(f"⏰ Timeout: {timeout}")
        print(f"💥 Error: {error}")
        print(f"⏱️  Total Duration: {total_duration:.1f}s")
        
        # Success rate
        if total_tests > 0:
            success_rate = (passed / total_tests) * 100
            print(f"📊 Success Rate: {success_rate:.1f}%")
        
        # Detailed results
        print(f"\nDetailed Results:")
        print("-" * 80)
        
        for result in self.test_results:
            status_icon = {
                'PASSED': '✅',
                'FAILED': '❌',
                'SKIPPED': '⏭️',
                'TIMEOUT': '⏰',
                'ERROR': '💥'
            }.get(result['status'], '❓')
            
            print(f"{status_icon} {result['name']}: {result['reason']} ({result['duration']:.1f}s)")
        
        # Overall result
        if failed == 0 and error == 0 and timeout == 0:
            print(f"\n🎉 ALL TESTS SUCCESSFUL! 🎉")
            return True
        else:
            print(f"\n⚠️  SOME TESTS FAILED")
            return False
    
    def save_test_report(self, output_file: str = "test_report.txt"):
        """Save detailed test report to file."""
        report_path = Path(__file__).parent / output_file
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("KNOWLEDGE BASE RAG SYSTEM - TEST REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Duration: {time.time() - self.start_time:.1f}s\n\n")
            
            for result in self.test_results:
                f.write(f"Test: {result['name']}\n")
                f.write(f"Script: {result['script']}\n")
                f.write(f"Status: {result['status']}\n")
                f.write(f"Duration: {result['duration']:.1f}s\n")
                f.write(f"Reason: {result['reason']}\n")
                
                if 'stdout' in result and result['stdout']:
                    f.write(f"Output:\n{result['stdout']}\n")
                
                if 'stderr' in result and result['stderr']:
                    f.write(f"Error Output:\n{result['stderr']}\n")
                
                f.write("-" * 40 + "\n")
        
        print(f"📄 Test report saved to: {report_path}")
    
    def run_all_tests(self, include_performance: bool = True, include_ui: bool = True):
        """Run all test suites."""
        print("🚀 Starting Knowledge Base RAG System Test Suite")
        print(f"{'='*80}")
        
        # Check dependencies first
        if not self.check_dependencies():
            print("❌ Dependency check failed. Cannot proceed with tests.")
            return False
        
        success = True
        
        # Run unit tests
        if not self.run_unit_tests():
            success = False
        
        # Run integration tests
        if not self.run_integration_tests():
            success = False
        
        # Run performance tests (optional)
        if include_performance:
            if not self.run_performance_tests():
                success = False
        else:
            print("⏭️  Skipping performance tests (disabled)")
        
        # Run UI tests (optional)
        if include_ui:
            if not self.run_ui_tests():
                success = False
        else:
            print("⏭️  Skipping UI tests (disabled)")
        
        # Print summary
        overall_success = self.print_summary()
        
        # Save report
        self.save_test_report()
        
        return overall_success


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(
        description="Run Knowledge Base RAG System Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all_tests.py                    # Run all tests
  python run_all_tests.py --no-performance  # Skip performance tests
  python run_all_tests.py --no-ui           # Skip UI tests
  python run_all_tests.py --unit-only       # Run only unit tests
  python run_all_tests.py --integration-only # Run only integration tests
        """
    )
    
    parser.add_argument(
        '--no-performance',
        action='store_true',
        help='Skip performance tests'
    )
    
    parser.add_argument(
        '--no-ui',
        action='store_true',
        help='Skip UI tests'
    )
    
    parser.add_argument(
        '--unit-only',
        action='store_true',
        help='Run only unit tests'
    )
    
    parser.add_argument(
        '--integration-only',
        action='store_true',
        help='Run only integration tests'
    )
    
    parser.add_argument(
        '--performance-only',
        action='store_true',
        help='Run only performance tests'
    )
    
    parser.add_argument(
        '--report',
        default='test_report.txt',
        help='Output file for test report (default: test_report.txt)'
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    try:
        if args.unit_only:
            success = runner.run_unit_tests()
        elif args.integration_only:
            success = runner.run_integration_tests()
        elif args.performance_only:
            success = runner.run_performance_tests()
        else:
            success = runner.run_all_tests(
                include_performance=not args.no_performance,
                include_ui=not args.no_ui
            )
        
        # Save custom report if specified
        if args.report != 'test_report.txt':
            runner.save_test_report(args.report)
        
        return 0 if success else 1
    
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)