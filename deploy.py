#!/usr/bin/env python3
"""
Deployment Script for Student Grade Analytics API
Handles deployment to different environments with proper configuration
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def deploy_to_environment(env: str):
    """Deploy to specific environment"""
    
    valid_environments = ["development", "staging", "production"]
    if env not in valid_environments:
        print(f"❌ Invalid environment: {env}")
        print(f"Valid environments: {', '.join(valid_environments)}")
        return False
    
    print(f"🚀 Deploying to {env.upper()} environment...")
    
    # Copy environment configuration
    env_file = f".env.{env}"
    if not os.path.exists(env_file):
        print(f"❌ Environment file not found: {env_file}")
        return False
    
    shutil.copy(env_file, ".env")
    print(f"✅ Environment configuration copied from {env_file}")
    
    # Install dependencies
    print("📦 Installing dependencies...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Failed to install dependencies: {result.stderr}")
        return False
    
    print("✅ Dependencies installed successfully")
    
    # Run tests
    print("🧪 Running tests...")
    result = subprocess.run([sys.executable, "unit_test.py"], 
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Tests failed: {result.stderr}")
        return False
    
    print("✅ All tests passed")
    
    # Start application based on environment
    print(f"🎯 Starting application in {env} mode...")
    
    if env == "development":
        print("Starting development server with auto-reload...")
        print("Command: python main.py")
        print("Dashboard: http://localhost:8000/dashboard")
        
    elif env == "staging":
        print("Starting staging server...")
        print("Command: uvicorn main:app --host 0.0.0.0 --port 8000")
        
    elif env == "production":
        print("Starting production server with Gunicorn...")
        print("Command: gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000")
    
    print(f"\n🎉 Deployment to {env.upper()} completed successfully!")
    return True

def show_environment_status():
    """Show current environment status"""
    print("📊 Environment Status")
    print("=" * 40)
    
    # Check which environment files exist
    environments = ["development", "staging", "production"]
    
    for env in environments:
        env_file = f".env.{env}"
        status = "✅" if os.path.exists(env_file) else "❌"
        print(f"{status} {env.capitalize()}: {env_file}")
    
    # Check current .env file
    if os.path.exists(".env"):
        print(f"✅ Current .env file exists")
        
        # Try to determine current environment
        try:
            with open(".env", "r") as f:
                content = f.read()
                if "ENVIRONMENT=development" in content:
                    print("🔧 Current environment: DEVELOPMENT")
                elif "ENVIRONMENT=staging" in content:
                    print("🔧 Current environment: STAGING")
                elif "ENVIRONMENT=production" in content:
                    print("🔧 Current environment: PRODUCTION")
                else:
                    print("❓ Current environment: UNKNOWN")
        except:
            print("❌ Could not read .env file")
    else:
        print("❌ No .env file found")
    
    print()

def cleanup_deployment():
    """Clean up deployment artifacts"""
    print("🧹 Cleaning up deployment artifacts...")
    
    cleanup_items = [
        "student_grades*.db",
        "alert.log",
        "costs.csv",
        "__pycache__",
        ".pytest_cache",
        "*.pyc"
    ]
    
    for item in cleanup_items:
        if "*" in item:
            # Handle wildcards
            import glob
            for file in glob.glob(item):
                try:
                    if os.path.isdir(file):
                        shutil.rmtree(file)
                    else:
                        os.remove(file)
                    print(f"   Removed: {file}")
                except:
                    pass
        else:
            try:
                if os.path.exists(item):
                    if os.path.isdir(item):
                        shutil.rmtree(item)
                    else:
                        os.remove(item)
                    print(f"   Removed: {item}")
            except:
                pass
    
    print("✅ Cleanup completed")

def main():
    """Main deployment script"""
    if len(sys.argv) < 2:
        print("🚀 Student Grade Analytics API - Deployment Script")
        print("=" * 50)
        print("\nUsage:")
        print("  python deploy.py <command> [environment]")
        print("\nCommands:")
        print("  deploy <env>    - Deploy to environment (development/staging/production)")
        print("  status          - Show environment status")
        print("  cleanup         - Clean up deployment artifacts")
        print("  test            - Run tests only")
        print("\nExamples:")
        print("  python deploy.py deploy development")
        print("  python deploy.py deploy production")
        print("  python deploy.py status")
        print("  python deploy.py cleanup")
        return
    
    command = sys.argv[1].lower()
    
    if command == "deploy":
        if len(sys.argv) < 3:
            print("❌ Environment required for deploy command")
            print("Usage: python deploy.py deploy <environment>")
            return
        
        environment = sys.argv[2].lower()
        success = deploy_to_environment(environment)
        
        if success:
            print(f"\n🎯 Next Steps:")
            print(f"1. Visit http://localhost:8000/dashboard for monitoring")
            print(f"2. Check http://localhost:8000/docs for API documentation")
            print(f"3. Monitor alert.log for system alerts")
            print(f"4. Review costs.csv for usage costs")
        
        sys.exit(0 if success else 1)
    
    elif command == "status":
        show_environment_status()
    
    elif command == "cleanup":
        cleanup_deployment()
    
    elif command == "test":
        print("🧪 Running tests...")
        result = subprocess.run([sys.executable, "unit_test.py"])
        sys.exit(result.returncode)
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'python deploy.py' to see available commands")
        sys.exit(1)

if __name__ == "__main__":
    main()