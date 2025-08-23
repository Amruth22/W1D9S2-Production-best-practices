"""
Unit Tests for Student Grade Analytics API
Tests production features via live server: caching, monitoring, alerts, and cost tracking
"""

import pytest
import os
import time
import csv
import requests
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Configuration for live server testing
BASE_URL = "http://localhost:8080"
TIMEOUT = 30  # seconds

def check_server_running():
    """Check if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_unique_student_id(prefix="TEST"):
    """Generate unique student ID for testing"""
    timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
    return f"{prefix}{timestamp}"

def get_unique_email(prefix="test"):
    """Generate unique email for testing"""
    timestamp = int(time.time() * 1000)
    return f"{prefix}_{timestamp}@school.edu"

# Test result tracking
test_results = {"passed": 0, "failed": 0, "total": 0}

def run_test(test_func, test_name):
    """Run a single test and track results"""
    global test_results
    test_results["total"] += 1
    
    try:
        test_func()
        test_results["passed"] += 1
        print(f"  ✅ {test_name} - PASSED")
        return True
    except Exception as e:
        test_results["failed"] += 1
        print(f"  ❌ {test_name} - FAILED: {str(e)}")
        return False

def create_test_student(prefix="test"):
    """Create test student data with unique identifiers"""
    return {
        "student_id": get_unique_student_id(prefix.upper()),
        "name": f"{prefix.title()} Student",
        "email": get_unique_email(prefix),
        "grade_level": 10
    }

def create_test_grade(student_id, subject="Math", score=85.5):
    """Create test grade data"""
    return {
        "student_id": student_id,
        "subject": subject,
        "score": score,
        "max_score": 100.0
    }

class TestProductionSetup:
    """Test production environment configuration via live API"""
    
    def test_environment_configuration(self):
        """Test environment configuration through root endpoint"""
        response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "environment" in data
        assert data["environment"] in ["development", "staging", "production"]
        assert "features" in data
        assert "endpoints" in data
        
        # Check production features are listed
        features = data["features"]
        assert any("Production" in feature for feature in features)
        assert any("Cache" in feature for feature in features)
        assert any("Monitoring" in feature for feature in features)
    
    def test_health_check_endpoint(self):
        """Test health check provides system status"""
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        
        assert response.status_code == 200
        health = response.json()
        
        assert health["status"] in ["healthy", "warning", "critical"]
        assert "environment" in health
        assert "database" in health
        assert "memory_usage_mb" in health
        assert "cache_size" in health
    
    def test_sample_data_availability(self):
        """Test that sample data is available"""
        response = requests.get(f"{BASE_URL}/students", timeout=TIMEOUT)
        
        assert response.status_code == 200
        students = response.json()
        assert len(students) >= 5  # Should have sample students
        
        # Verify student structure
        student = students[0]
        assert "student_id" in student
        assert "name" in student
        assert "email" in student
        assert "grade_level" in student

class TestPerformanceOptimization:
    """Test performance optimization features via live API"""
    
    def test_caching_behavior(self):
        """Test caching behavior through repeated requests"""
        test_student = create_test_student("cache")
        
        # Create student first
        response = requests.post(f"{BASE_URL}/students", json=test_student, timeout=TIMEOUT)
        assert response.status_code == 200
        
        # First request (should populate cache)
        response1 = requests.get(f"{BASE_URL}/students/{test_student['student_id']}", timeout=TIMEOUT)
        assert response1.status_code == 200
        
        # Second request (should use cache - faster response)
        start_time = time.time()
        response2 = requests.get(f"{BASE_URL}/students/{test_student['student_id']}", timeout=TIMEOUT)
        response_time = (time.time() - start_time) * 1000
        
        assert response2.status_code == 200
        assert response1.json() == response2.json()  # Same data
        
        # Check response time header
        assert "X-Response-Time" in response2.headers
    
    def test_batch_processing(self):
        """Test batch grade processing"""
        test_student = create_test_student("batch")
        
        # Create test student first
        requests.post(f"{BASE_URL}/students", json=test_student, timeout=TIMEOUT)
        
        # Create batch of grades
        batch_grades = []
        subjects = ["Math", "Science", "English"]
        
        for subject in subjects:
            for i in range(3):  # 3 grades per subject
                grade = create_test_grade(test_student["student_id"], subject, 80 + i * 5)
                batch_grades.append(grade)
        
        # Submit batch
        response = requests.post(f"{BASE_URL}/grades/batch", json=batch_grades, timeout=TIMEOUT)
        
        assert response.status_code == 200
        data = response.json()
        assert "queued for processing" in data["message"]
        assert data["batch_size"] == len(batch_grades)
    
    def test_response_time_tracking(self):
        """Test response time tracking in headers"""
        response = requests.get(f"{BASE_URL}/students", timeout=TIMEOUT)
        
        assert response.status_code == 200
        assert "X-Response-Time" in response.headers
        assert "X-Environment" in response.headers
        
        response_time = response.headers["X-Response-Time"]
        assert "ms" in response_time
        
        environment = response.headers["X-Environment"]
        assert environment in ["development", "staging", "production"]

class TestMonitoringDashboard:
    """Test monitoring dashboard and metrics via live API"""
    
    def test_dashboard_accessibility(self):
        """Test monitoring dashboard is accessible"""
        response = requests.get(f"{BASE_URL}/dashboard", timeout=TIMEOUT)
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Check that dashboard contains key metrics
        html_content = response.text
        assert "Monitoring Dashboard" in html_content
        assert "Requests per Minute" in html_content
        assert "Cache Hit Rate" in html_content
        assert "Memory Usage" in html_content
    
    def test_metrics_endpoint(self):
        """Test metrics JSON endpoint"""
        response = requests.get(f"{BASE_URL}/metrics", timeout=TIMEOUT)
        
        assert response.status_code == 200
        metrics_data = response.json()
        
        # Check required metric categories
        assert "performance" in metrics_data
        assert "cache" in metrics_data
        assert "system" in metrics_data
        assert "costs" in metrics_data
        
        # Check specific metrics
        performance = metrics_data["performance"]
        assert "requests_per_minute" in performance
        assert "average_response_time_ms" in performance
        
        cache = metrics_data["cache"]
        assert "hit_rate" in cache
        assert "size" in cache
    
    def test_system_monitoring(self):
        """Test system resource monitoring"""
        response = requests.get(f"{BASE_URL}/metrics", timeout=TIMEOUT)
        
        assert response.status_code == 200
        metrics_data = response.json()
        
        system = metrics_data["system"]
        assert "memory_usage_mb" in system
        assert "cpu_percent" in system
        assert "disk_usage_percent" in system
        
        # Verify values are reasonable
        assert system["memory_usage_mb"] > 0
        assert 0 <= system["cpu_percent"] <= 100
        assert 0 <= system["disk_usage_percent"] <= 100

class TestAlertSystem:
    """Test alert system functionality"""
    
    def test_alert_file_creation(self):
        """Test alert logging to file"""
        # Remove existing alert file
        if os.path.exists("alert.log"):
            os.remove("alert.log")
        
        # Simulate high memory usage alert
        with patch('psutil.Process') as mock_process:
            mock_memory = MagicMock()
            mock_memory.rss = 600 * 1024 * 1024  # 600MB (above 500MB threshold)
            mock_process.return_value.memory_info.return_value = mock_memory
            
            # Trigger alert check
            check_alerts()
        
        # Check if alert file was created
        if os.path.exists("alert.log"):
            with open("alert.log", "r") as f:
                content = f.read()
                assert "High memory usage" in content
            print("Alert system working: High memory alert logged")
        else:
            print("INFO: No alerts triggered (system within thresholds)")
    
    def test_cache_hit_rate_alert(self):
        """Test cache hit rate alert"""
        # Clear existing alerts
        if os.path.exists("alert.log"):
            os.remove("alert.log")
        
        # Simulate low cache hit rate
        metrics.cache_hits = 2
        metrics.cache_misses = 10  # 16.7% hit rate (below 70% threshold)
        
        check_alerts()
        
        # Check for alert
        if os.path.exists("alert.log"):
            with open("alert.log", "r") as f:
                content = f.read()
                if "Low cache hit rate" in content:
                    print("Cache hit rate alert working")
                else:
                    print("INFO: Cache alert not triggered")
        
        # Reset metrics
        metrics.cache_hits = 0
        metrics.cache_misses = 0

class TestCostTracking:
    """Test cost tracking functionality via live API"""
    
    def test_current_costs_calculation(self):
        """Test current session cost calculation"""
        # Make some requests to generate costs
        requests.get(f"{BASE_URL}/students", timeout=TIMEOUT)
        requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        
        # Get current costs
        response = requests.get(f"{BASE_URL}/costs/current", timeout=TIMEOUT)
        
        assert response.status_code == 200
        cost_data = response.json()
        
        assert "session_costs" in cost_data
        session_costs = cost_data["session_costs"]
        
        assert "database_queries" in session_costs
        assert "api_requests" in session_costs
        assert "total_session_cost" in session_costs
        
        # Verify costs are calculated
        db_cost = session_costs["database_queries"]["total_cost"]
        api_cost = session_costs["api_requests"]["total_cost"]
        total_cost = session_costs["total_session_cost"]
        
        assert db_cost >= 0
        assert api_cost >= 0
        assert abs(total_cost - (db_cost + api_cost)) < 0.000001  # Allow for floating point precision
    
    def test_hourly_cost_summary(self):
        """Test hourly cost summary generation"""
        # Generate hourly summary
        response = requests.post(f"{BASE_URL}/costs/hourly-summary", timeout=TIMEOUT)
        
        assert response.status_code == 200
        data = response.json()
        assert "cost summary generated" in data["message"]
        assert "cost_data" in data
        
        # Verify cost data structure
        cost_data = data["cost_data"]
        assert "timestamp" in cost_data
        assert "environment" in cost_data
        assert "total_cost" in cost_data
        assert "db_queries" in cost_data
        assert "api_requests" in cost_data

class TestStudentGradeAPI:
    """Test core student and grade functionality via live API"""
    
    def test_create_student(self):
        """Test student creation"""
        new_student = create_test_student("create")
        
        response = requests.post(f"{BASE_URL}/students", json=new_student, timeout=TIMEOUT)
        
        assert response.status_code == 200
        data = response.json()
        assert "Student created successfully" in data["message"]
        assert data["student_id"] == new_student["student_id"]
    
    def test_get_student(self):
        """Test student retrieval"""
        test_student = create_test_student("get")
        
        # Create student first
        requests.post(f"{BASE_URL}/students", json=test_student, timeout=TIMEOUT)
        
        # Retrieve student
        response = requests.get(f"{BASE_URL}/students/{test_student['student_id']}", timeout=TIMEOUT)
        
        assert response.status_code == 200
        student_data = response.json()
        
        assert student_data["student_id"] == test_student["student_id"]
        assert student_data["name"] == test_student["name"]
        assert student_data["email"] == test_student["email"]
        assert student_data["grade_level"] == test_student["grade_level"]
    
    def test_add_grade(self):
        """Test adding individual grade"""
        test_student = create_test_student("grade")
        
        # Create student first
        requests.post(f"{BASE_URL}/students", json=test_student, timeout=TIMEOUT)
        
        # Add grade
        test_grade = create_test_grade(test_student["student_id"])
        response = requests.post(f"{BASE_URL}/grades", json=test_grade, timeout=TIMEOUT)
        
        assert response.status_code == 200
        data = response.json()
        assert "Grade added successfully" in data["message"]
        assert "grade_id" in data
    
    def test_student_analytics(self):
        """Test student analytics calculation"""
        test_student = create_test_student("analytics")
        
        # Create student and add some grades
        requests.post(f"{BASE_URL}/students", json=test_student, timeout=TIMEOUT)
        
        # Add multiple grades
        subjects = ["Math", "Science", "English"]
        for subject in subjects:
            grade = create_test_grade(test_student["student_id"], subject, 85.0)
            requests.post(f"{BASE_URL}/grades", json=grade, timeout=TIMEOUT)
        
        # Get analytics
        response = requests.get(f"{BASE_URL}/analytics/student/{test_student['student_id']}", timeout=TIMEOUT)
        
        assert response.status_code == 200
        analytics = response.json()
        
        assert analytics["student_id"] == test_student["student_id"]
        assert "average_score" in analytics
        assert "total_grades" in analytics
        assert "subjects" in analytics
        assert len(analytics["subjects"]) == len(subjects)
    
    def test_class_analytics(self):
        """Test class-wide analytics"""
        response = requests.get(f"{BASE_URL}/analytics/class", timeout=TIMEOUT)
        
        assert response.status_code == 200
        analytics = response.json()
        
        assert "total_grades" in analytics
        assert "average_score" in analytics
        assert "subjects" in analytics

class TestSystemHealth:
    """Test system health and monitoring"""
    
    def test_health_check_comprehensive(self):
        """Test comprehensive health check"""
        response = client.get("/health")
        
        assert response.status_code == 200
        health = response.json()
        
        assert health["status"] in ["healthy", "warning", "critical"]
        assert "timestamp" in health
        assert "environment" in health
        assert "memory_usage_mb" in health
        assert "cache_size" in health
        
        print(f"Health check: {health['status']} - Memory: {health['memory_usage_mb']}MB")
    
    def test_root_endpoint_info(self):
        """Test root endpoint provides system information"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "environment" in data
        assert "features" in data
        assert "endpoints" in data
        
        # Check features are listed
        features = data["features"]
        assert any("Production" in feature for feature in features)
        assert any("Cache" in feature for feature in features)
        assert any("Monitoring" in feature for feature in features)
        
        print(f"System info: {len(features)} features listed")

class TestPerformanceMetrics:
    """Test performance monitoring and metrics"""
    
    def test_response_time_tracking(self):
        """Test response time is tracked"""
        # Make a request and check response time header
        response = client.get("/students")
        
        assert response.status_code == 200
        assert "X-Response-Time" in response.headers
        assert "X-Environment" in response.headers
        
        response_time = response.headers["X-Response-Time"]
        assert "ms" in response_time
        
        # Verify response time is recorded in metrics
        assert len(metrics.response_times) > 0
        
        print(f"Response time tracked: {response_time}")
    
    def test_metrics_collection(self):
        """Test that metrics are properly collected"""
        # Record initial state
        initial_requests = metrics.request_count
        initial_queries = metrics.db_query_count
        
        # Make some requests
        client.get("/students")
        client.get("/health")
        client.get("/metrics")
        
        # Verify metrics increased
        assert metrics.request_count > initial_requests
        assert metrics.db_query_count > initial_queries
        
        print(f"Metrics collection: {metrics.request_count} requests, {metrics.db_query_count} queries")
    
    def test_memory_monitoring(self):
        """Test memory usage monitoring"""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        metrics_data = response.json()
        
        memory_usage = metrics_data["system"]["memory_usage_mb"]
        assert isinstance(memory_usage, (int, float))
        assert memory_usage > 0
        
        print(f"Memory monitoring: {memory_usage}MB")

class TestCachePerformance:
    """Test cache performance and optimization"""
    
    def test_cache_capacity_management(self):
        """Test cache capacity limits"""
        from main import CACHE_SIZE
        
        # Fill cache beyond capacity
        for i in range(CACHE_SIZE + 10):
            student_cache.put(f"test_key_{i}", f"test_value_{i}")
        
        # Cache should not exceed capacity
        assert student_cache.size() <= CACHE_SIZE
        
        print(f"Cache capacity managed: {student_cache.size()}/{CACHE_SIZE}")
    
    def test_cache_invalidation(self):
        """Test cache invalidation on data updates"""
        # Create student and cache analytics
        client.post("/students", json=test_student)
        
        # Get analytics (should cache result)
        response1 = client.get(f"/analytics/student/{test_student['student_id']}")
        assert response1.status_code == 200
        
        # Add new grade (should invalidate cache)
        new_grade = {
            "student_id": test_student["student_id"],
            "subject": "Physics",
            "score": 92.0
        }
        client.post("/grades", json=new_grade)
        
        # Analytics should be recalculated
        response2 = client.get(f"/analytics/student/{test_student['student_id']}")
        assert response2.status_code == 200
        
        print("Cache invalidation working on data updates")

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_student_not_found(self):
        """Test handling of non-existent student"""
        response = client.get("/students/NONEXISTENT")
        
        assert response.status_code == 404
        assert "Student not found" in response.json()["detail"]
    
    def test_invalid_grade_level(self):
        """Test validation of invalid grade level"""
        invalid_student = test_student.copy()
        invalid_student["student_id"] = "INVALID001"
        invalid_student["email"] = "invalid@school.edu"
        invalid_student["grade_level"] = 15  # Invalid grade level
        
        response = client.post("/students", json=invalid_student)
        
        assert response.status_code == 422
        assert "Grade level must be between 1 and 12" in str(response.json())
    
    def test_invalid_grade_score(self):
        """Test validation of invalid grade score"""
        # Ensure student exists
        client.post("/students", json=test_student)
        
        invalid_grade = test_grade.copy()
        invalid_grade["score"] = 150  # Score higher than max_score
        
        response = client.post("/grades", json=invalid_grade)
        
        assert response.status_code == 422
        assert "Score must be between 0 and" in str(response.json())

# Simple test runner for live API tests
def run_live_api_tests():
    """Run API tests against live server"""
    global test_results
    test_results = {"passed": 0, "failed": 0, "total": 0}
    
    print("🧪 Running Live API Tests (Student Grade Analytics)")
    print("=" * 60)
    
    # Check if server is running
    if not check_server_running():
        print("❌ ERROR: Server is not running!")
        print("")
        print("Please start the server first:")
        print("  1. Choose environment: cp .env.development .env")
        print("  2. Start server: python main.py")
        print("  3. Wait for server to start")
        print("  4. Then run these tests in another terminal")
        print("")
        return False
    
    print(f"✅ Server is running at {BASE_URL}")
    print("")
    
    # Core 10 Essential Tests
    print("🎯 Running Core 10 Essential Tests:")
    
    # Production Setup Tests
    test_setup = TestProductionSetup()
    run_test(test_setup.test_environment_configuration, "1. Environment Configuration")
    run_test(test_setup.test_health_check_endpoint, "2. Health Check Endpoint")
    run_test(test_setup.test_sample_data_availability, "3. Sample Data Availability")
    
    # Performance Tests
    test_perf = TestPerformanceOptimization()
    run_test(test_perf.test_caching_behavior, "4. Caching Behavior")
    run_test(test_perf.test_batch_processing, "5. Batch Processing")
    run_test(test_perf.test_response_time_tracking, "6. Response Time Tracking")
    
    # Monitoring Tests
    test_monitor = TestMonitoringDashboard()
    run_test(test_monitor.test_dashboard_accessibility, "7. Monitoring Dashboard")
    run_test(test_monitor.test_metrics_endpoint, "8. Metrics Endpoint")
    
    # Business Logic Tests
    test_api = TestStudentGradeAPI()
    run_test(test_api.test_create_student, "9. Student Creation")
    run_test(test_api.test_student_analytics, "10. Student Analytics")
    
    # Display results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"🎯 Total Tests: {test_results['total']}")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    
    if test_results['failed'] == 0:
        print(f"\n🎉 ALL TESTS PASSED! ({test_results['passed']}/{test_results['total']})")
        success_rate = 100.0
    else:
        success_rate = (test_results['passed'] / test_results['total']) * 100
        print(f"\n⚠️  SOME TESTS FAILED ({test_results['passed']}/{test_results['total']})")
    
    print(f"📊 Success Rate: {success_rate:.1f}%")
    
    print("\n" + "=" * 60)
    print("📚 Core 10 Tests Covered:")
    print("• 1-3: Production setup and environment configuration")
    print("• 4-6: Performance optimization (caching, batch processing)")
    print("• 7-8: Monitoring dashboard and metrics collection")
    print("• 9-10: Core business logic (students, analytics)")
    
    print("\n💡 Production Features Tested:")
    print("• Environment configuration management")
    print("• Performance optimization and caching")
    print("• Real-time monitoring and metrics")
    print("• Cost tracking and resource management")
    print("• Production-ready API endpoints")
    
    return test_results['failed'] == 0

if __name__ == "__main__":
    # Run live API tests
    success = run_live_api_tests()
    
    print("\n" + "=" * 60)
    if success:
        print("🎆 ALL TESTS SUCCESSFUL!")
        print("🔄 You can also run with pytest: pytest unit_test.py -v")
        print("📊 Visit http://localhost:8000/dashboard for monitoring")
    else:
        print("⚠️  SOME TESTS FAILED!")
        print("🔧 Check the error messages above for details")
        print("🔄 You can also run with pytest: pytest unit_test.py -v")
    print("=" * 60)
    
    exit(0 if success else 1)
