"""
NetMonitor Pro - Database Module
Handles all database operations for storing monitoring data
"""

import aiosqlite
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncio

DATABASE_PATH = "netmonitor.db"


async def init_database(db_path: str = DATABASE_PATH):
    """Initialize the database with required tables"""
    async with aiosqlite.connect(db_path) as db:
        # Ping results table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ping_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_name TEXT NOT NULL,
                target_ip TEXT NOT NULL,
                latency_ms REAL,
                packet_loss REAL DEFAULT 0,
                status TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Bandwidth measurements table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bandwidth_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gateway_name TEXT NOT NULL,
                interface TEXT NOT NULL,
                bytes_sent INTEGER NOT NULL,
                bytes_recv INTEGER NOT NULL,
                bytes_sent_rate REAL DEFAULT 0,
                bytes_recv_rate REAL DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Alerts table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                target_name TEXT,
                message TEXT NOT NULL,
                severity TEXT DEFAULT 'warning',
                acknowledged INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for faster queries
        await db.execute("CREATE INDEX IF NOT EXISTS idx_ping_timestamp ON ping_results(timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bandwidth_timestamp ON bandwidth_measurements(timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")
        
        await db.commit()
    print("Database initialized successfully")


async def save_ping_result(db_path: str, target_name: str, target_ip: str, 
                           latency_ms: Optional[float], packet_loss: float, status: str):
    """Save a ping result to the database"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO ping_results (target_name, target_ip, latency_ms, packet_loss, status)
               VALUES (?, ?, ?, ?, ?)""",
            (target_name, target_ip, latency_ms, packet_loss, status)
        )
        await db.commit()


async def save_bandwidth_measurement(db_path: str, gateway_name: str, interface: str,
                                     bytes_sent: int, bytes_recv: int,
                                     bytes_sent_rate: float, bytes_recv_rate: float):
    """Save a bandwidth measurement to the database"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO bandwidth_measurements 
               (gateway_name, interface, bytes_sent, bytes_recv, bytes_sent_rate, bytes_recv_rate)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (gateway_name, interface, bytes_sent, bytes_recv, bytes_sent_rate, bytes_recv_rate)
        )
        await db.commit()


async def save_alert(db_path: str, alert_type: str, target_name: str, 
                     message: str, severity: str = "warning"):
    """Save an alert to the database"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO alerts (alert_type, target_name, message, severity)
               VALUES (?, ?, ?, ?)""",
            (alert_type, target_name, message, severity)
        )
        await db.commit()


async def get_ping_history(db_path: str, target_name: str = None, 
                           hours: int = 24, limit: int = 1000) -> List[Dict]:
    """Get ping history for a target or all targets"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        since = datetime.now() - timedelta(hours=hours)
        
        if target_name:
            cursor = await db.execute(
                """SELECT * FROM ping_results 
                   WHERE target_name = ? AND timestamp > ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (target_name, since.isoformat(), limit)
            )
        else:
            cursor = await db.execute(
                """SELECT * FROM ping_results 
                   WHERE timestamp > ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (since.isoformat(), limit)
            )
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_bandwidth_history(db_path: str, gateway_name: str = None,
                                hours: int = 24, limit: int = 1000) -> List[Dict]:
    """Get bandwidth history for a gateway or all gateways"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        since = datetime.now() - timedelta(hours=hours)
        
        if gateway_name:
            cursor = await db.execute(
                """SELECT * FROM bandwidth_measurements 
                   WHERE gateway_name = ? AND timestamp > ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (gateway_name, since.isoformat(), limit)
            )
        else:
            cursor = await db.execute(
                """SELECT * FROM bandwidth_measurements 
                   WHERE timestamp > ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (since.isoformat(), limit)
            )
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_alerts(db_path: str, unacknowledged_only: bool = False,
                     hours: int = 24, limit: int = 100) -> List[Dict]:
    """Get recent alerts"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        since = datetime.now() - timedelta(hours=hours)
        
        if unacknowledged_only:
            cursor = await db.execute(
                """SELECT * FROM alerts 
                   WHERE acknowledged = 0 AND timestamp > ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (since.isoformat(), limit)
            )
        else:
            cursor = await db.execute(
                """SELECT * FROM alerts 
                   WHERE timestamp > ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (since.isoformat(), limit)
            )
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def acknowledge_alert(db_path: str, alert_id: int):
    """Mark an alert as acknowledged"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE alerts SET acknowledged = 1 WHERE id = ?",
            (alert_id,)
        )
        await db.commit()


async def cleanup_old_data(db_path: str, retention_days: int = 30):
    """Remove data older than retention period"""
    async with aiosqlite.connect(db_path) as db:
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        await db.execute(
            "DELETE FROM ping_results WHERE timestamp < ?",
            (cutoff.isoformat(),)
        )
        await db.execute(
            "DELETE FROM bandwidth_measurements WHERE timestamp < ?",
            (cutoff.isoformat(),)
        )
        await db.execute(
            "DELETE FROM alerts WHERE timestamp < ? AND acknowledged = 1",
            (cutoff.isoformat(),)
        )
        
        await db.commit()
    print(f"Cleaned up data older than {retention_days} days")


async def get_statistics(db_path: str, hours: int = 24) -> Dict[str, Any]:
    """Get aggregated statistics for dashboard"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        since = datetime.now() - timedelta(hours=hours)
        
        # Ping statistics per target
        cursor = await db.execute(
            """SELECT target_name, 
                      AVG(latency_ms) as avg_latency,
                      MIN(latency_ms) as min_latency,
                      MAX(latency_ms) as max_latency,
                      AVG(packet_loss) as avg_packet_loss,
                      COUNT(*) as total_pings,
                      SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_pings
               FROM ping_results 
               WHERE timestamp > ?
               GROUP BY target_name""",
            (since.isoformat(),)
        )
        ping_stats = [dict(row) for row in await cursor.fetchall()]
        
        # Bandwidth statistics per gateway
        cursor = await db.execute(
            """SELECT gateway_name,
                      AVG(bytes_sent_rate) as avg_upload,
                      AVG(bytes_recv_rate) as avg_download,
                      MAX(bytes_sent_rate) as max_upload,
                      MAX(bytes_recv_rate) as max_download
               FROM bandwidth_measurements
               WHERE timestamp > ?
               GROUP BY gateway_name""",
            (since.isoformat(),)
        )
        bandwidth_stats = [dict(row) for row in await cursor.fetchall()]
        
        # Alert count
        cursor = await db.execute(
            """SELECT COUNT(*) as count FROM alerts 
               WHERE timestamp > ? AND acknowledged = 0""",
            (since.isoformat(),)
        )
        alert_count = (await cursor.fetchone())['count']
        
        return {
            "ping_statistics": ping_stats,
            "bandwidth_statistics": bandwidth_stats,
            "unacknowledged_alerts": alert_count,
            "period_hours": hours
        }


async def get_ping_analytics(db_path: str, target_name: str = None, hours: int = 24) -> Dict[str, Any]:
    """Get detailed ping analytics including patterns and outliers"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        since = datetime.now() - timedelta(hours=hours)
        
        # Build WHERE clause
        where_clause = "WHERE timestamp > ?"
        params = [since.isoformat()]
        if target_name:
            where_clause += " AND target_name = ?"
            params.append(target_name)
        
        # Overall statistics
        cursor = await db.execute(f"""
            SELECT 
                target_name,
                COUNT(*) as total_pings,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_pings,
                SUM(CASE WHEN status = 'timeout' THEN 1 ELSE 0 END) as timeouts,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
                AVG(latency_ms) as avg_latency,
                MIN(latency_ms) as min_latency,
                MAX(latency_ms) as max_latency,
                AVG(packet_loss) as avg_packet_loss
            FROM ping_results 
            {where_clause}
            GROUP BY target_name
        """, params)
        overall_stats = [dict(row) for row in await cursor.fetchall()]
        
        # Get peak latency records (top 10 highest latencies)
        cursor = await db.execute(f"""
            SELECT target_name, target_ip, latency_ms, packet_loss, status, timestamp
            FROM ping_results 
            {where_clause} AND latency_ms IS NOT NULL
            ORDER BY latency_ms DESC
            LIMIT 10
        """, params)
        peak_latencies = [dict(row) for row in await cursor.fetchall()]
        
        # Get timeout incidents
        timeout_params = params.copy()
        cursor = await db.execute(f"""
            SELECT target_name, target_ip, timestamp
            FROM ping_results 
            {where_clause} AND status = 'timeout'
            ORDER BY timestamp DESC
            LIMIT 50
        """, timeout_params)
        timeout_incidents = [dict(row) for row in await cursor.fetchall()]
        
        # Hourly breakdown - when do issues occur most?
        cursor = await db.execute(f"""
            SELECT 
                strftime('%H', timestamp) as hour,
                COUNT(*) as total_pings,
                SUM(CASE WHEN status = 'timeout' THEN 1 ELSE 0 END) as timeouts,
                AVG(latency_ms) as avg_latency,
                MAX(latency_ms) as max_latency
            FROM ping_results 
            {where_clause}
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        """, params)
        hourly_breakdown = [dict(row) for row in await cursor.fetchall()]
        
        # Find the worst hour (most timeouts or highest latency)
        worst_hour = None
        if hourly_breakdown:
            worst_by_timeouts = max(hourly_breakdown, key=lambda x: x['timeouts'] or 0)
            if worst_by_timeouts['timeouts'] and worst_by_timeouts['timeouts'] > 0:
                worst_hour = {
                    'hour': worst_by_timeouts['hour'],
                    'reason': 'timeouts',
                    'value': worst_by_timeouts['timeouts']
                }
            else:
                worst_by_latency = max(hourly_breakdown, key=lambda x: x['avg_latency'] or 0)
                if worst_by_latency['avg_latency']:
                    worst_hour = {
                        'hour': worst_by_latency['hour'],
                        'reason': 'high_latency',
                        'value': worst_by_latency['avg_latency']
                    }
        
        # Recent logs (last 100 entries)
        cursor = await db.execute(f"""
            SELECT id, target_name, target_ip, latency_ms, packet_loss, status, timestamp
            FROM ping_results 
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT 100
        """, params)
        recent_logs = [dict(row) for row in await cursor.fetchall()]
        
        return {
            "period_hours": hours,
            "target_filter": target_name,
            "overall_statistics": overall_stats,
            "peak_latencies": peak_latencies,
            "timeout_incidents": timeout_incidents,
            "hourly_breakdown": hourly_breakdown,
            "worst_hour": worst_hour,
            "recent_logs": recent_logs
        }


async def get_ping_logs_paginated(db_path: str, target_name: str = None, 
                                   page: int = 1, per_page: int = 50,
                                   status_filter: str = None) -> Dict[str, Any]:
    """Get paginated ping logs with filtering"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        # Build WHERE clause
        conditions = []
        params = []
        
        if target_name:
            conditions.append("target_name = ?")
            params.append(target_name)
        
        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get total count
        cursor = await db.execute(f"""
            SELECT COUNT(*) as count FROM ping_results {where_clause}
        """, params)
        total = (await cursor.fetchone())['count']
        
        # Get paginated results
        offset = (page - 1) * per_page
        cursor = await db.execute(f"""
            SELECT id, target_name, target_ip, latency_ms, packet_loss, status, timestamp
            FROM ping_results 
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])
        logs = [dict(row) for row in await cursor.fetchall()]
        
        return {
            "logs": logs,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
