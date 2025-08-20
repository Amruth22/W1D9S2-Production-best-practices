"""
Student Grade Analytics API - Production Best Practices
Demonstrates production setup, performance optimization, monitoring, and cost tracking
"""

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel, validator
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import sqlite3
import threading
import time
import os
import csv
import psutil
import logging
from collections import OrderedDict, deque
from statistics import mean, median
import uvicorn
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "student_grades.db")
CACHE_SIZE = int(os.getenv("CACHE_SIZE", "1000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Performance settings
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
QUERY_TIMEOUT = int(os.getenv("QUERY_TIMEOUT", "30"))

# Monitoring settings
ALERT_RESPONSE_TIME_MS = int(os.getenv("ALERT_RESPONSE_TIME_MS", "300"))
ALERT_CACHE_HIT_RATE = float(os.getenv("ALERT_CACHE_HIT_RATE", "0.70"))
ALERT_MEMORY_MB = int(os.getenv("ALERT_MEMORY_MB", "500"))

# Cost tracking settings
COST_PER_DB_QUERY = float(os.getenv("COST_PER_DB_QUERY", "0.0001"))
COST_PER_100_API_CALLS = float(os.getenv("COST_PER_100_API_CALLS", "0.001"))

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_database()
    cleanup_old_audit_logs()
    logger.info("Student Grade Analytics API started")
    yield
    # Shutdown
    logger.info("Student Grade Analytics API shutting down")

app = FastAPI(
    title="Student Grade Analytics API",
    description="Production-ready grade analytics with monitoring, caching, and cost tracking",
    version="1.0.0",
    debug=DEBUG,
    lifespan=lifespan
)

# Global metrics and monitoring
class SystemMetrics:
    def __init__(self):
        self.request_count = 0
        self.db_query_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.response_times = deque(maxlen=100)  # Keep last 100 response times
        self.hourly_costs = []
        self.last_cost_reset = datetime.now()
        self.lock = threading.RLock()
    
    def record_request(self, response_time_ms: float):
        with self.lock:
            self.request_count += 1
            self.response_times.append(response_time_ms)
    
    def record_db_query(self):
        with self.lock:
            self.db_query_count += 1
    
    def record_cache_hit(self):
        with self.lock:
            self.cache_hits += 1
    
    def record_cache_miss(self):
        with self.lock:
            self.cache_misses += 1
    
    def get_cache_hit_rate(self) -> float:
        with self.lock:
            total = self.cache_hits + self.cache_misses
            return (self.cache_hits / total) if total > 0 else 0.0
    
    def get_avg_response_time(self) -> float:
        with self.lock:
            return mean(self.response_times) if self.response_times else 0.0
    
    def get_requests_per_minute(self) -> float:
        with self.lock:
            # Simple approximation based on recent activity
            return len(self.response_times)  # Rough estimate

metrics = SystemMetrics()

# LRU Cache Implementation
class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                metrics.record_cache_hit()
                return value
            metrics.record_cache_miss()
            return None
    
    def put(self, key: str, value: Any):
        with self.lock:
            if key in self.cache:
                self.cache.pop(key)
            elif len(self.cache) >= self.capacity:
                # Remove least recently used
                self.cache.popitem(last=False)
            self.cache[key] = value
    
    def size(self) -> int:
        with self.lock:
            return len(self.cache)

# Global cache instance
student_cache = LRUCache(CACHE_SIZE)

# Pydantic models
class Student(BaseModel):
    student_id: str
    name: str
    email: str
    grade_level: int
    
    @field_validator('grade_level')
    @classmethod
    def validate_grade_level(cls, v):
        if v < 1 or v > 12:
            raise ValueError('Grade level must be between 1 and 12')
        return v

class Grade(BaseModel):
    student_id: str
    subject: str
    score: float
    max_score: float = 100.0
    date_recorded: Optional[datetime] = None
    
    @field_validator('score')
    @classmethod
    def validate_score(cls, v, info):
        max_score = info.data.get('max_score', 100.0) if info.data else 100.0
        if v < 0 or v > max_score:
            raise ValueError(f'Score must be between 0 and {max_score}')
        return v

class StudentAnalytics(BaseModel):
    student_id: str
    student_name: str
    total_grades: int
    average_score: float
    highest_score: float
    lowest_score: float
    subjects: List[str]

# Database initialization
def init_database():
    """Initialize SQLite database with optimized schema"""
    conn = sqlite3.connect(DATABASE_URL, check_same_thread=False)
    cursor = conn.cursor()
    
    # Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            grade_level INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Grades table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            score REAL NOT NULL,
            max_score REAL DEFAULT 100.0,
            date_recorded DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (student_id)
        )
    """)
    
    # Create optimized indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_id ON students(student_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_email ON students(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_grades_student ON grades(student_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_grades_subject ON grades(subject)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_grades_date ON grades(date_recorded)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_grades_student_subject ON grades(student_id, subject)")
    
    # Add sample data if empty
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        sample_students = [
            ("STU001", "Alice Johnson", "alice@school.edu", 10),
            ("STU002", "Bob Smith", "bob@school.edu", 11),
            ("STU003", "Carol Davis", "carol@school.edu", 10),
            ("STU004", "David Wilson", "david@school.edu", 12),
            ("STU005", "Eva Brown", "eva@school.edu", 11)
        ]
        
        cursor.executemany(
            "INSERT INTO students (student_id, name, email, grade_level) VALUES (?, ?, ?, ?)",
            sample_students
        )
        
        # Add sample grades
        import random
        subjects = ["Math", "Science", "English", "History", "Art"]
        
        for student_id, _, _, _ in sample_students:
            for subject in subjects:
                for _ in range(random.randint(3, 8)):  # 3-8 grades per subject
                    score = random.uniform(60, 100)  # Random score between 60-100
                    cursor.execute(
                        "INSERT INTO grades (student_id, subject, score) VALUES (?, ?, ?)",
                        (student_id, subject, round(score, 1))
                    )
        
        logger.info("Sample data added to database")
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

def get_db_connection():
    """Get database connection with query tracking"""
    metrics.record_db_query()
    return sqlite3.connect(DATABASE_URL, check_same_thread=False, timeout=QUERY_TIMEOUT)

# Cost tracking functions
def calculate_hourly_costs():
    """Calculate and log hourly costs"""
    current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
    
    # Calculate costs
    db_cost = metrics.db_query_count * COST_PER_DB_QUERY
    api_cost = (metrics.request_count / 100) * COST_PER_100_API_CALLS
    total_cost = db_cost + api_cost
    
    # Log to CSV
    cost_data = {
        "timestamp": current_hour.isoformat(),
        "environment": ENVIRONMENT,
        "db_queries": metrics.db_query_count,
        "api_requests": metrics.request_count,
        "db_cost": round(db_cost, 6),
        "api_cost": round(api_cost, 6),
        "total_cost": round(total_cost, 6)
    }
    
    # Write to CSV
    file_exists = os.path.exists("costs.csv")
    with open("costs.csv", "a", newline="") as csvfile:
        fieldnames = ["timestamp", "environment", "db_queries", "api_requests", "db_cost", "api_cost", "total_cost"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(cost_data)
    
    logger.info(f"Hourly cost logged: ${total_cost:.6f}")
    return cost_data

# Alert system
def check_alerts():
    """Check alert conditions and log to alert.log"""
    alerts = []
    
    # Check response time
    if len(metrics.response_times) >= 3:
        recent_times = list(metrics.response_times)[-3:]
        if all(t > ALERT_RESPONSE_TIME_MS for t in recent_times):
            alerts.append(f"High response time: {recent_times} ms (threshold: {ALERT_RESPONSE_TIME_MS}ms)")
    
    # Check cache hit rate
    cache_hit_rate = metrics.get_cache_hit_rate()
    if cache_hit_rate < ALERT_CACHE_HIT_RATE and (metrics.cache_hits + metrics.cache_misses) > 10:
        alerts.append(f"Low cache hit rate: {cache_hit_rate:.2%} (threshold: {ALERT_CACHE_HIT_RATE:.0%})")
    
    # Check memory usage
    memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
    if memory_mb > ALERT_MEMORY_MB:
        alerts.append(f"High memory usage: {memory_mb:.1f}MB (threshold: {ALERT_MEMORY_MB}MB)")
    
    # Log alerts
    if alerts:
        with open("alert.log", "a") as f:
            for alert in alerts:
                f.write(f"{datetime.now().isoformat()} - ALERT: {alert}\n")
        logger.warning(f"Alerts triggered: {len(alerts)}")

# Middleware for monitoring
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    """Monitor requests and track performance metrics"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    response_time_ms = (time.time() - start_time) * 1000
    
    # Record metrics
    metrics.record_request(response_time_ms)
    
    # Check alerts
    check_alerts()
    
    # Add performance headers
    response.headers["X-Response-Time"] = f"{response_time_ms:.2f}ms"
    response.headers["X-Environment"] = ENVIRONMENT
    
    return response

# API Endpoints

# Startup logic moved to lifespan context manager above

@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "Student Grade Analytics API",
        "version": "1.0.0",
        "environment": ENVIRONMENT,
        "features": [
            "Production Environment Configuration",
            "LRU Cache for Performance",
            "SQLite Query Optimization",
            "Real-time Monitoring Dashboard",
            "Alert System",
            "Cost Tracking"
        ],
        "endpoints": {
            "students": ["/students", "/students/{id}"],
            "grades": ["/grades", "/grades/batch"],
            "analytics": ["/analytics/student/{id}", "/analytics/class"],
            "monitoring": ["/dashboard", "/metrics", "/health"],
            "costs": ["/costs/current", "/costs/summary"]
        }
    }

# Student management endpoints
@app.post("/students")
async def create_student(student: Student):
    """Create a new student"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO students (student_id, name, email, grade_level)
            VALUES (?, ?, ?, ?)
        """, (student.student_id, student.name, student.email, student.grade_level))
        
        conn.commit()
        
        # Cache the student
        student_cache.put(f"student:{student.student_id}", student.dict())
        
        return {"message": "Student created successfully", "student_id": student.student_id}
    
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Student ID or email already exists")
    finally:
        conn.close()

@app.get("/students/{student_id}")
async def get_student(student_id: str):
    """Get student by ID (with caching)"""
    cache_key = f"student:{student_id}"
    
    # Try cache first
    cached_student = student_cache.get(cache_key)
    if cached_student:
        return cached_student
    
    # Query database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT student_id, name, email, grade_level, created_at
        FROM students WHERE student_id = ?
    """, (student_id,))
    
    student_data = cursor.fetchone()
    conn.close()
    
    if not student_data:
        raise HTTPException(status_code=404, detail="Student not found")
    
    student_dict = {
        "student_id": student_data[0],
        "name": student_data[1],
        "email": student_data[2],
        "grade_level": student_data[3],
        "created_at": student_data[4]
    }
    
    # Cache the result
    student_cache.put(cache_key, student_dict)
    
    return student_dict

@app.get("/students")
async def get_all_students(limit: int = 50):
    """Get all students with pagination"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT student_id, name, email, grade_level, created_at
        FROM students
        ORDER BY name
        LIMIT ?
    """, (limit,))
    
    students = []
    for row in cursor.fetchall():
        students.append({
            "student_id": row[0],
            "name": row[1],
            "email": row[2],
            "grade_level": row[3],
            "created_at": row[4]
        })
    
    conn.close()
    return students

# Grade management endpoints
@app.post("/grades")
async def add_grade(grade: Grade):
    """Add a single grade"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify student exists
    cursor.execute("SELECT id FROM students WHERE student_id = ?", (grade.student_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Add grade
    date_recorded = grade.date_recorded or datetime.now()
    cursor.execute("""
        INSERT INTO grades (student_id, subject, score, max_score, date_recorded)
        VALUES (?, ?, ?, ?, ?)
    """, (grade.student_id, grade.subject, grade.score, grade.max_score, date_recorded))
    
    conn.commit()
    grade_id = cursor.lastrowid
    conn.close()
    
    # Invalidate cache for this student
    student_cache.cache.pop(f"analytics:{grade.student_id}", None)
    
    return {"message": "Grade added successfully", "grade_id": grade_id}

@app.post("/grades/batch")
async def add_grades_batch(grades: List[Grade], background_tasks: BackgroundTasks):
    """Add multiple grades in batch (background processing)"""
    
    def process_batch():
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Batch insert for performance
            grade_data = []
            for grade in grades:
                date_recorded = grade.date_recorded or datetime.now()
                grade_data.append((
                    grade.student_id, grade.subject, grade.score, 
                    grade.max_score, date_recorded
                ))
            
            cursor.executemany("""
                INSERT INTO grades (student_id, subject, score, max_score, date_recorded)
                VALUES (?, ?, ?, ?, ?)
            """, grade_data)
            
            conn.commit()
            logger.info(f"Batch processed: {len(grades)} grades added")
            
            # Clear relevant cache entries
            for grade in grades:
                student_cache.cache.pop(f"analytics:{grade.student_id}", None)
        
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
        finally:
            conn.close()
    
    background_tasks.add_task(process_batch)
    
    return {
        "message": f"Batch of {len(grades)} grades queued for processing",
        "batch_size": len(grades)
    }

# Analytics endpoints
@app.get("/analytics/student/{student_id}", response_model=StudentAnalytics)
async def get_student_analytics(student_id: str):
    """Get analytics for a specific student (with caching)"""
    cache_key = f"analytics:{student_id}"
    
    # Try cache first
    cached_analytics = student_cache.get(cache_key)
    if cached_analytics:
        return cached_analytics
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get student info
    cursor.execute("SELECT name FROM students WHERE student_id = ?", (student_id,))
    student_data = cursor.fetchone()
    
    if not student_data:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get grade analytics
    cursor.execute("""
        SELECT score, subject
        FROM grades
        WHERE student_id = ?
        ORDER BY date_recorded DESC
    """, (student_id,))
    
    grades_data = cursor.fetchall()
    conn.close()
    
    if not grades_data:
        raise HTTPException(status_code=404, detail="No grades found for student")
    
    # Calculate analytics
    scores = [row[0] for row in grades_data]
    subjects = list(set(row[1] for row in grades_data))
    
    analytics = StudentAnalytics(
        student_id=student_id,
        student_name=student_data[0],
        total_grades=len(scores),
        average_score=round(mean(scores), 2),
        highest_score=max(scores),
        lowest_score=min(scores),
        subjects=subjects
    )
    
    # Cache the result
    student_cache.put(cache_key, analytics.dict())
    
    return analytics

@app.get("/analytics/class")
async def get_class_analytics(grade_level: Optional[int] = None, subject: Optional[str] = None):
    """Get class-wide analytics with optional filtering"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query based on filters
    query = """
        SELECT g.score, g.subject, s.grade_level, s.name
        FROM grades g
        JOIN students s ON g.student_id = s.student_id
        WHERE 1=1
    """
    params = []
    
    if grade_level:
        query += " AND s.grade_level = ?"
        params.append(grade_level)
    
    if subject:
        query += " AND g.subject = ?"
        params.append(subject)
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        return {"message": "No data found for the specified criteria"}
    
    # Calculate class analytics
    scores = [row[0] for row in results]
    subjects = list(set(row[1] for row in results))
    grade_levels = list(set(row[2] for row in results))
    
    return {
        "total_grades": len(scores),
        "average_score": round(mean(scores), 2),
        "median_score": round(median(scores), 2),
        "highest_score": max(scores),
        "lowest_score": min(scores),
        "subjects": subjects,
        "grade_levels": grade_levels,
        "filters_applied": {
            "grade_level": grade_level,
            "subject": subject
        }
    }

# Monitoring dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def monitoring_dashboard():
    """Real-time monitoring dashboard"""
    
    # Get current metrics
    memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
    cache_hit_rate = metrics.get_cache_hit_rate()
    avg_response_time = metrics.get_avg_response_time()
    requests_per_min = metrics.get_requests_per_minute()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Grade Analytics - Monitoring Dashboard</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }}
            .metric-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .metric-value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
            .metric-label {{ color: #7f8c8d; margin-top: 5px; }}
            .status-good {{ color: #27ae60; }}
            .status-warning {{ color: #f39c12; }}
            .status-critical {{ color: #e74c3c; }}
            .environment {{ background: #3498db; color: white; padding: 5px 10px; border-radius: 4px; display: inline-block; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Student Grade Analytics - Monitoring Dashboard</h1>
                <p>Environment: <span class="environment">{ENVIRONMENT.upper()}</span> | 
                   Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-value">{requests_per_min:.0f}</div>
                    <div class="metric-label">Requests per Minute</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-value {'status-good' if cache_hit_rate >= 0.7 else 'status-warning'}">{cache_hit_rate:.1%}</div>
                    <div class="metric-label">Cache Hit Rate</div>
                    <small>Hits: {metrics.cache_hits} | Misses: {metrics.cache_misses}</small>
                </div>
                
                <div class="metric-card">
                    <div class="metric-value {'status-good' if avg_response_time < 300 else 'status-warning'}">{avg_response_time:.1f}ms</div>
                    <div class="metric-label">Average Response Time</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-value {'status-good' if memory_mb < 500 else 'status-warning'}">{memory_mb:.1f}MB</div>
                    <div class="metric-label">Memory Usage</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-value">{metrics.db_query_count}</div>
                    <div class="metric-label">Database Queries</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-value">{metrics.request_count}</div>
                    <div class="metric-label">Total API Requests</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-value">{student_cache.size()}</div>
                    <div class="metric-label">Cache Size</div>
                    <small>Capacity: {CACHE_SIZE}</small>
                </div>
                
                <div class="metric-card">
                    <div class="metric-value">${(metrics.db_query_count * COST_PER_DB_QUERY + (metrics.request_count / 100) * COST_PER_100_API_CALLS):.4f}</div>
                    <div class="metric-label">Current Session Cost</div>
                </div>
            </div>
            
            <div style="margin-top: 30px; background: white; padding: 20px; border-radius: 8px;">
                <h3>🚨 Alert Thresholds</h3>
                <ul>
                    <li>Response Time: > {ALERT_RESPONSE_TIME_MS}ms for 3 consecutive requests</li>
                    <li>Cache Hit Rate: < {ALERT_CACHE_HIT_RATE:.0%}</li>
                    <li>Memory Usage: > {ALERT_MEMORY_MB}MB</li>
                </ul>
                
                <h3>💰 Cost Configuration</h3>
                <ul>
                    <li>Database Query: ${COST_PER_DB_QUERY} each</li>
                    <li>API Calls: ${COST_PER_100_API_CALLS} per 100 requests</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

@app.get("/metrics")
async def get_metrics():
    """Get current system metrics (JSON)"""
    memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
    
    return {
        "timestamp": datetime.now().isoformat(),
        "environment": ENVIRONMENT,
        "performance": {
            "requests_per_minute": metrics.get_requests_per_minute(),
            "average_response_time_ms": metrics.get_avg_response_time(),
            "total_requests": metrics.request_count,
            "database_queries": metrics.db_query_count
        },
        "cache": {
            "hit_rate": metrics.get_cache_hit_rate(),
            "hits": metrics.cache_hits,
            "misses": metrics.cache_misses,
            "size": student_cache.size(),
            "capacity": CACHE_SIZE
        },
        "system": {
            "memory_usage_mb": round(memory_mb, 1),
            "cpu_percent": psutil.cpu_percent(),
            "disk_usage_percent": psutil.disk_usage('.').percent
        },
        "costs": {
            "db_queries_cost": metrics.db_query_count * COST_PER_DB_QUERY,
            "api_requests_cost": (metrics.request_count / 100) * COST_PER_100_API_CALLS,
            "total_session_cost": (metrics.db_query_count * COST_PER_DB_QUERY + 
                                 (metrics.request_count / 100) * COST_PER_100_API_CALLS)
        }
    }

@app.get("/costs/current")
async def get_current_costs():
    """Get current session costs"""
    db_cost = metrics.db_query_count * COST_PER_DB_QUERY
    api_cost = (metrics.request_count / 100) * COST_PER_100_API_CALLS
    total_cost = db_cost + api_cost
    
    return {
        "session_costs": {
            "database_queries": {
                "count": metrics.db_query_count,
                "cost_per_query": COST_PER_DB_QUERY,
                "total_cost": round(db_cost, 6)
            },
            "api_requests": {
                "count": metrics.request_count,
                "cost_per_100": COST_PER_100_API_CALLS,
                "total_cost": round(api_cost, 6)
            },
            "total_session_cost": round(total_cost, 6)
        },
        "environment": ENVIRONMENT,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/costs/hourly-summary")
async def generate_hourly_cost_summary():
    """Generate and save hourly cost summary"""
    cost_data = calculate_hourly_costs()
    return {
        "message": "Hourly cost summary generated",
        "cost_data": cost_data,
        "csv_file": "costs.csv"
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
    
    # Determine health status
    status = "healthy"
    issues = []
    
    if memory_mb > ALERT_MEMORY_MB:
        status = "warning"
        issues.append(f"High memory usage: {memory_mb:.1f}MB")
    
    if metrics.get_cache_hit_rate() < ALERT_CACHE_HIT_RATE and (metrics.cache_hits + metrics.cache_misses) > 10:
        status = "warning"
        issues.append(f"Low cache hit rate: {metrics.get_cache_hit_rate():.1%}")
    
    if metrics.get_avg_response_time() > ALERT_RESPONSE_TIME_MS:
        status = "warning"
        issues.append(f"High response time: {metrics.get_avg_response_time():.1f}ms")
    
    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "environment": ENVIRONMENT,
        "database": "connected",
        "cache_size": student_cache.size(),
        "memory_usage_mb": round(memory_mb, 1),
        "issues": issues
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=DEBUG)