# Student Grade Analytics API - Production Best Practices

A production-ready FastAPI application demonstrating best practices for deployment, performance optimization, monitoring, alerting, and cost tracking.

## 🎯 Project Overview

This Student Grade Analytics API showcases real-world production concerns:
- **Environment Configuration** for dev/staging/prod deployments
- **Performance Optimization** with caching and database optimization
- **Real-time Monitoring** with HTML dashboard and metrics
- **Alert System** for proactive issue detection
- **Cost Tracking** for resource usage monitoring

## ✨ Production Features

### 🔧 **Production Setup**
- **Environment Configs**: Separate `.env` files for dev/staging/prod
- **Configuration Management**: Environment-specific settings
- **Database Optimization**: Proper indexing and query optimization
- **Logging Configuration**: Structured logging with levels

### ⚡ **Performance Optimization**
- **LRU Cache**: In-memory caching for frequently accessed student records
- **SQLite Optimization**: Proper indexing for fast queries
- **Batch Processing**: Efficient grade calculations and bulk operations
- **Connection Management**: Optimized database connections

### 📊 **Monitoring Dashboard**
- **Real-time Metrics**: Requests/min, cache hit rate, response times
- **System Monitoring**: Memory usage, CPU, disk space
- **Performance Tracking**: Average calculation times
- **Visual Dashboard**: HTML interface with auto-refresh

### 🚨 **Alert System**
- **Response Time Alerts**: > 300ms for 3 consecutive requests
- **Cache Performance Alerts**: Hit rate < 70%
- **Memory Usage Alerts**: > 500MB usage
- **File-based Logging**: Alerts written to `alert.log`

### 💰 **Cost Tracking**
- **Database Query Costs**: $0.0001 per query
- **API Request Costs**: $0.001 per 100 requests
- **Hourly Summaries**: Automated cost reports in `costs.csv`
- **Environment-specific Rates**: Different costs per environment

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/Amruth22/D1W9S2-Production-best-practices.git
cd D1W9S2-Production-best-practices
pip install -r requirements.txt
```

### 2. Choose Environment
```bash
# Development (default)
cp .env.development .env

# Staging
cp .env.staging .env

# Production
cp .env.production .env
```

### 3. Run the Application
```bash
python main.py
```

### 4. View Monitoring Dashboard
Visit: http://localhost:8000/dashboard

### 5. Run Tests
```bash
python unit_test.py
```

### 6. Run Comprehensive Tests (w1d4s2-style-tests branch)
```bash
# Switch to testing branch
git checkout w1d4s2-style-tests

# Quick component validation (~5-8 seconds)
python run_tests.py quick

# Full component testing (~10-15 seconds)
python run_tests.py full

# Live API tests with auto server management
python run_tests.py auto
```

## 📊 API Endpoints

### **Students**
```http
POST /students           # Create new student
GET  /students           # List all students
GET  /students/{id}      # Get specific student (cached)
```

### **Grades**
```http
POST /grades             # Add single grade
POST /grades/batch       # Batch add grades (background processing)
```

### **Analytics**
```http
GET /analytics/student/{id}  # Student analytics (cached)
GET /analytics/class         # Class-wide analytics
```

### **Monitoring**
```http
GET /dashboard          # HTML monitoring dashboard
GET /metrics           # JSON metrics endpoint
GET /health            # Health check
```

### **Cost Tracking**
```http
GET  /costs/current         # Current session costs
POST /costs/hourly-summary  # Generate hourly cost report
```

## 🔧 Environment Configuration

### **Development** (`.env.development`)
```env
ENVIRONMENT=development
DEBUG=true
CACHE_SIZE=500
ALERT_RESPONSE_TIME_MS=500
ALERT_MEMORY_MB=300
COST_PER_DB_QUERY=0.0001
```

### **Staging** (`.env.staging`)
```env
ENVIRONMENT=staging
DEBUG=false
CACHE_SIZE=1000
ALERT_RESPONSE_TIME_MS=300
ALERT_MEMORY_MB=500
COST_PER_DB_QUERY=0.00015
```

### **Production** (`.env.production`)
```env
ENVIRONMENT=production
DEBUG=false
CACHE_SIZE=2000
ALERT_RESPONSE_TIME_MS=200
ALERT_MEMORY_MB=1000
COST_PER_DB_QUERY=0.0002
```

## 📈 Monitoring Dashboard

The real-time dashboard (`/dashboard`) displays:

### **Performance Metrics**
- **Requests per Minute**: Current API traffic
- **Average Response Time**: Performance indicator
- **Cache Hit Rate**: Caching effectiveness
- **Memory Usage**: System resource consumption

### **System Health**
- **Database Queries**: Total query count
- **Cache Size**: Current cache utilization
- **Environment Status**: Current deployment environment
- **Cost Tracking**: Real-time cost accumulation

### **Visual Indicators**
- 🟢 **Green**: Metrics within normal ranges
- 🟡 **Yellow**: Warning thresholds reached
- 🔴 **Red**: Critical thresholds exceeded

## 🚨 Alert Configuration

### **Alert Conditions**
1. **High Response Time**: > 300ms for 3 consecutive requests
2. **Low Cache Hit Rate**: < 70% hit rate
3. **High Memory Usage**: > 500MB memory consumption

### **Alert Actions**
- **File Logging**: Alerts written to `alert.log`
- **Structured Format**: Timestamp, alert type, details
- **Automatic Monitoring**: Checked on every request

### **Sample Alert Log**
```
2024-01-15T10:30:00 - ALERT: High response time: [350.2, 420.1, 380.5] ms (threshold: 300ms)
2024-01-15T10:35:00 - ALERT: Low cache hit rate: 65% (threshold: 70%)
2024-01-15T10:40:00 - ALERT: High memory usage: 520.3MB (threshold: 500MB)
```

## 💰 Cost Tracking

### **Cost Model**
- **Database Queries**: $0.0001 per query
- **API Requests**: $0.001 per 100 requests
- **Environment Scaling**: Different rates per environment

### **Cost Reports**
Hourly cost summaries saved to `costs.csv`:

```csv
timestamp,environment,db_queries,api_requests,db_cost,api_cost,total_cost
2024-01-15T10:00:00,development,150,1200,0.000150,0.012000,0.012150
2024-01-15T11:00:00,development,200,1500,0.000200,0.015000,0.015200
```

### **Cost Analysis**
```bash
# Get current session costs
curl http://localhost:8000/costs/current

# Generate hourly summary
curl -X POST http://localhost:8000/costs/hourly-summary
```

## 🏗️ Database Schema

### **Optimized Tables**
```sql
-- Students table with indexes
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    grade_level INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Grades table with performance indexes
CREATE TABLE grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    score REAL NOT NULL,
    max_score REAL DEFAULT 100.0,
    date_recorded DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students (student_id)
);

-- Performance indexes
CREATE INDEX idx_students_id ON students(student_id);
CREATE INDEX idx_grades_student ON grades(student_id);
CREATE INDEX idx_grades_subject ON grades(subject);
CREATE INDEX idx_grades_student_subject ON grades(student_id, subject);
```

## 🧪 Testing

### **Run Tests**
```bash
# Run all tests
python unit_test.py

# Run with pytest
pytest unit_test.py -v

# Run specific test categories
pytest unit_test.py::TestPerformanceOptimization -v
pytest unit_test.py::TestMonitoringDashboard -v
```

### **Test Categories**
- **Production Setup**: Environment config, database initialization
- **Performance Optimization**: Caching, batch processing, query optimization
- **Monitoring Dashboard**: Dashboard accessibility, metrics collection
- **Alert System**: Alert conditions, file logging
- **Cost Tracking**: Cost calculation, hourly summaries
- **System Health**: Health checks, error handling

## 📊 Usage Examples

### **1. Create Student**
```bash
curl -X POST "http://localhost:8000/students" \
     -H "Content-Type: application/json" \
     -d '{
       "student_id": "STU123",
       "name": "John Smith",
       "email": "john@school.edu",
       "grade_level": 11
     }'
```

### **2. Add Grade**
```bash
curl -X POST "http://localhost:8000/grades" \
     -H "Content-Type: application/json" \
     -d '{
       "student_id": "STU123",
       "subject": "Math",
       "score": 95.5,
       "max_score": 100.0
     }'
```

### **3. Get Student Analytics**
```bash
curl "http://localhost:8000/analytics/student/STU123"
```

### **4. Batch Add Grades**
```bash
curl -X POST "http://localhost:8000/grades/batch" \
     -H "Content-Type: application/json" \
     -d '[
       {"student_id": "STU123", "subject": "Science", "score": 88.0},
       {"student_id": "STU123", "subject": "English", "score": 92.5}
     ]'
```

### **5. Monitor System**
```bash
# View dashboard
open http://localhost:8000/dashboard

# Get metrics
curl "http://localhost:8000/metrics"

# Check health
curl "http://localhost:8000/health"
```

## 🔍 Performance Monitoring

### **Cache Performance**
- **Hit Rate Monitoring**: Track cache effectiveness
- **Size Management**: LRU eviction when capacity reached
- **Invalidation Strategy**: Clear cache on data updates

### **Database Performance**
- **Query Optimization**: Proper indexing for fast lookups
- **Query Tracking**: Count and cost all database operations
- **Batch Operations**: Efficient bulk data processing

### **Response Time Tracking**
- **Request Timing**: Measure every API call
- **Performance Headers**: Response time in HTTP headers
- **Alert Thresholds**: Automatic detection of slow responses

## 🚨 Production Monitoring

### **Key Metrics to Watch**
1. **Response Time**: Should stay under 300ms
2. **Cache Hit Rate**: Should be above 70%
3. **Memory Usage**: Monitor for memory leaks
4. **Database Query Count**: Track database load
5. **Error Rates**: Monitor for system issues

### **Alert Integration**
- **File-based Alerts**: Simple alert.log for basic monitoring
- **Threshold Configuration**: Adjustable via environment variables
- **Automatic Detection**: Real-time monitoring on every request

## 💡 Production Best Practices Demonstrated

### **1. Environment Management**
- **Configuration Separation**: Different settings per environment
- **Secret Management**: Environment variables for sensitive data
- **Feature Flags**: Debug mode and environment-specific behavior

### **2. Performance Optimization**
- **Caching Strategy**: LRU cache for frequently accessed data
- **Database Optimization**: Proper indexing and query optimization
- **Batch Processing**: Background tasks for bulk operations
- **Resource Monitoring**: Track memory, CPU, and disk usage

### **3. Monitoring & Observability**
- **Real-time Dashboard**: Visual monitoring interface
- **Structured Metrics**: JSON endpoints for integration
- **Performance Tracking**: Response time and throughput monitoring
- **Health Checks**: Comprehensive system status

### **4. Cost Management**
- **Resource Tracking**: Monitor database and API usage
- **Cost Calculation**: Simulate cloud service costs
- **Usage Reports**: Hourly cost summaries
- **Cost Optimization**: Identify expensive operations

### **5. Security & Reliability**
- **Input Validation**: Comprehensive data validation
- **Error Handling**: Graceful error responses
- **Resource Limits**: Prevent resource exhaustion
- **Audit Trail**: Track all system activities

## 🚀 Deployment Guide

### **Development**
```bash
cp .env.development .env
python main.py
```

### **Staging**
```bash
cp .env.staging .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

### **Production**
```bash
cp .env.production .env
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📚 Learning Objectives

This project teaches:

### **Production Deployment**
- Environment-specific configuration
- Database optimization and indexing
- Performance monitoring and alerting
- Cost tracking and optimization

### **FastAPI Best Practices**
- Middleware for cross-cutting concerns
- Background tasks for async processing
- Dependency injection for clean code
- Comprehensive error handling

### **System Monitoring**
- Real-time metrics collection
- Performance dashboard creation
- Alert system implementation
- Health check endpoints

### **Performance Engineering**
- Caching strategies and implementation
- Database query optimization
- Batch processing patterns
- Resource usage monitoring

## 🤝 Contributing

This is an educational project demonstrating production best practices. Feel free to:
- Add new monitoring metrics
- Implement additional alert conditions
- Enhance the dashboard interface
- Add more performance optimizations
- Improve cost tracking accuracy

## 📄 License

This project is for educational purposes. Feel free to use and modify as needed.

---

**Built with ❤️ for learning production best practices**