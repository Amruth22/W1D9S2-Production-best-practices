#!/usr/bin/env python3
"""
Test Runner for Production Best Practices
Provides multiple test execution modes for different use cases
"""

import os
import sys
import subprocess
import time
import requests
from dotenv import load_dotenv

def print_banner():
    """Print test runner banner"""
    print("=" * 70)
    print("🧪 PRODUCTION BEST PRACTICES - TEST RUNNER")
    print("=" * 70)

def check_environment():
    """Check environment setup"""
    # Check for environment files
    env_files = [f for f in os.listdir('.') if f.startswith('.env.')]
    
    if len(env_files) == 0:
        print("❌ No environment files found!")
        print("\n📋 Setup Instructions:")
        print("1. Copy template: cp .env.example .env")
        print("2. Or use specific environments:")
        print("   cp .env.development .env  # for development")
        print("   cp .env.staging .env      # for staging") 
        print("   cp .env.production .env   # for production")
        return False
    
    # Load environment
    if os.path.exists('.env'):
        load_dotenv()
    elif os.path.exists('.env.development'):
        load_dotenv('.env.development')
        print("📋 Using .env.development (no .env found)")
    else:
        load_dotenv(env_files[0])
        print(f"📋 Using {env_files[0]} (no .env found)")
    
    environment = os.getenv('ENVIRONMENT', 'unknown')
    print(f"✅ Environment configured: {environment}")
    print(f"✅ Found {len(env_files)} environment configuration files")
    
    return True

def check_server_running():
    """Check if the FastAPI server is running"""
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def run_quick_tests():
    """Run quick component tests without server startup"""
    print("\n🚀 QUICK TEST MODE")
    print("- Component validation without server startup")
    print("- Environment configuration testing")
    print("- Expected time: ~5-8 seconds")
    print("-" * 50)
    
    # Set environment variable for quick mode
    env = os.environ.copy()
    env['QUICK_TEST_MODE'] = 'true'
    env['MAX_API_CALLS_PER_TEST'] = '0'
    env['API_TIMEOUT'] = '5'
    
    start_time = time.time()
    result = subprocess.run([sys.executable, 'testsss.py'], env=env)
    total_time = time.time() - start_time
    
    print(f"\n⏱️  Quick tests completed in {total_time:.2f} seconds")
    return result.returncode == 0

def run_full_tests():
    """Run comprehensive component tests"""
    print("\n🔬 FULL TEST MODE")
    print("- Comprehensive component validation")
    print("- Production feature testing")
    print("- Expected time: ~10-15 seconds")
    print("-" * 50)
    
    # Set environment variable for full mode
    env = os.environ.copy()
    env['QUICK_TEST_MODE'] = 'false'
    env['MAX_API_CALLS_PER_TEST'] = '1'
    env['API_TIMEOUT'] = '10'
    
    start_time = time.time()
    result = subprocess.run([sys.executable, 'testsss.py'], env=env)
    total_time = time.time() - start_time
    
    print(f"\n⏱️  Full tests completed in {total_time:.2f} seconds")
    return result.returncode == 0

def run_live_api_tests():
    """Run live API tests (requires server)"""
    print("\n🌐 LIVE API TEST MODE")
    print("- Tests against running FastAPI server")
    print("- Real API endpoint validation")
    print("- Expected time: ~30-60 seconds")
    print("-" * 50)
    
    # Check if server is running
    if not check_server_running():
        print("❌ Server is not running!")
        print("\n📋 To run live API tests:")
        print("1. Start server in another terminal:")
        print("   python main.py")
        print("2. Wait for server to start")
        print("3. Then run: python run_tests.py live")
        return False
    
    print("✅ Server is running at http://localhost:8080")
    
    start_time = time.time()
    result = subprocess.run([sys.executable, 'unit_test.py'])
    total_time = time.time() - start_time
    
    print(f"\n⏱️  Live API tests completed in {total_time:.2f} seconds")
    return result.returncode == 0

def run_specific_test(test_name):
    """Run a specific test"""
    print(f"\n🎯 SPECIFIC TEST: {test_name}")
    print("-" * 50)
    
    env = os.environ.copy()
    env['QUICK_TEST_MODE'] = 'true'  # Use quick mode for specific tests
    
    cmd = [
        sys.executable, '-m', 'unittest', 
        f'testsss.CoreProductionBestPracticesTests.{test_name}', 
        '-v'
    ]
    
    start_time = time.time()
    result = subprocess.run(cmd, env=env)
    total_time = time.time() - start_time
    
    print(f"\n⏱️  Test {test_name} completed in {total_time:.2f} seconds")
    return result.returncode == 0

def start_server_and_test():
    """Start server and run tests"""
    print("\n🚀 SERVER + TEST MODE")
    print("- Start FastAPI server")
    print("- Run live API tests")
    print("- Stop server")
    print("-" * 50)
    
    # Start server in background
    print("Starting FastAPI server...")
    server_process = subprocess.Popen([sys.executable, 'main.py'])
    
    try:
        # Wait for server to start
        print("Waiting for server to start...")
        for i in range(30):  # Wait up to 30 seconds
            if check_server_running():
                print("✅ Server started successfully")
                break
            time.sleep(1)
        else:
            print("❌ Server failed to start within 30 seconds")
            return False
        
        # Run live API tests
        print("Running live API tests...")
        result = run_live_api_tests()
        
        return result
        
    finally:
        # Stop server
        print("Stopping server...")
        server_process.terminate()
        server_process.wait()
        print("✅ Server stopped")

def show_usage():
    """Show usage instructions"""
    print("\n📖 USAGE:")
    print("python run_tests.py [mode]")
    print("\n🎯 Available modes:")
    print("  quick     - Fast component validation (~5-8s)")
    print("  full      - Comprehensive component testing (~10-15s)")
    print("  live      - Live API tests (requires running server)")
    print("  auto      - Start server + run live tests + stop server")
    print("  specific  - Run specific test")
    print("\n💡 Examples:")
    print("  python run_tests.py quick")
    print("  python run_tests.py full")
    print("  python run_tests.py live")
    print("  python run_tests.py auto")
    print("  python run_tests.py specific test_01_fastapi_application_and_environment_configuration")
    print("\n🔧 Environment Variables:")
    print("  QUICK_TEST_MODE=true/false")
    print("  MAX_API_CALLS_PER_TEST=0-5")
    print("  API_TIMEOUT=5-30")
    print("\n🧪 Available Tests:")
    print("  test_01_fastapi_application_and_environment_configuration")
    print("  test_02_component_structure_and_production_features")
    print("  test_03_performance_optimization_and_caching_systems")
    print("  test_04_monitoring_alerting_and_cost_tracking")
    print("  test_05_integration_workflow_and_production_readiness")
    print("\n🌐 Server Management:")
    print("  Start server: python main.py")
    print("  Check health: curl http://localhost:8080/health")
    print("  View dashboard: http://localhost:8080/dashboard")

def main():
    """Main test runner function"""
    print_banner()
    
    # Check environment
    if not check_environment():
        return False
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        show_usage()
        return False
    
    mode = sys.argv[1].lower()
    
    if mode == 'quick':
        return run_quick_tests()
    elif mode == 'full':
        return run_full_tests()
    elif mode == 'live':
        return run_live_api_tests()
    elif mode == 'auto':
        return start_server_and_test()
    elif mode == 'specific':
        if len(sys.argv) < 3:
            print("❌ Please specify test name for specific mode")
            print("Example: python run_tests.py specific test_01_fastapi_application_and_environment_configuration")
            return False
        return run_specific_test(sys.argv[2])
    else:
        print(f"❌ Unknown mode: {mode}")
        show_usage()
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Tests completed successfully!")
        else:
            print("\n❌ Tests failed or incomplete")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        sys.exit(1)