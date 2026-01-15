"""
NetMonitor Pro - Network Monitoring Module
Handles ping monitoring, bandwidth measurement, and gateway tracking
"""

import asyncio
import psutil
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import subprocess
import platform


@dataclass
class PingResult:
    target_name: str
    target_ip: str
    latency_ms: Optional[float]
    packet_loss: float
    status: str  # 'success', 'timeout', 'error'
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BandwidthMeasurement:
    gateway_name: str
    interface: str
    bytes_sent: int
    bytes_recv: int
    bytes_sent_rate: float  # bytes per second
    bytes_recv_rate: float  # bytes per second
    timestamp: datetime = field(default_factory=datetime.now)


class PingMonitor:
    """Handles ping operations to monitor network targets"""
    
    def __init__(self):
        self.last_results: Dict[str, PingResult] = {}
    
    async def ping(self, ip: str, count: int = 3, timeout: int = 2) -> tuple[Optional[float], float, str]:
        """
        Ping an IP address and return (latency_ms, packet_loss_percent, status)
        Uses system ping command for better compatibility
        """
        try:
            # Determine the ping command based on OS
            system = platform.system().lower()
            
            if system == "windows":
                cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), ip]
            else:  # macOS and Linux
                cmd = ["ping", "-c", str(count), "-W", str(timeout), ip]
            
            # Run ping command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout * count + 5
            )
            
            output = stdout.decode()
            
            # Parse the output
            latency = self._parse_latency(output, system)
            packet_loss = self._parse_packet_loss(output, system)
            
            if latency is not None:
                status = "success"
            elif packet_loss == 100:
                status = "timeout"
                latency = None
            else:
                status = "partial"
            
            return latency, packet_loss, status
            
        except asyncio.TimeoutError:
            return None, 100.0, "timeout"
        except Exception as e:
            print(f"Ping error for {ip}: {e}")
            return None, 100.0, "error"
    
    def _parse_latency(self, output: str, system: str) -> Optional[float]:
        """Parse average latency from ping output"""
        try:
            if system == "windows":
                # Windows: Average = 10ms
                for line in output.split('\n'):
                    if 'Average' in line:
                        parts = line.split('=')
                        if len(parts) >= 2:
                            return float(parts[-1].strip().replace('ms', ''))
            else:
                # macOS/Linux: round-trip min/avg/max/stddev = 10.123/11.456/12.789/0.123 ms
                for line in output.split('\n'):
                    if 'avg' in line.lower() or 'rtt' in line.lower():
                        parts = line.split('=')
                        if len(parts) >= 2:
                            stats = parts[-1].strip().split('/')
                            if len(stats) >= 2:
                                return float(stats[1])  # avg is second value
        except (ValueError, IndexError):
            pass
        return None
    
    def _parse_packet_loss(self, output: str, system: str) -> float:
        """Parse packet loss percentage from ping output"""
        try:
            for line in output.split('\n'):
                if 'loss' in line.lower():
                    # Find percentage in the line
                    parts = line.split()
                    for part in parts:
                        if '%' in part:
                            return float(part.replace('%', '').replace(',', ''))
        except (ValueError, IndexError):
            pass
        return 0.0
    
    async def ping_target(self, name: str, ip: str) -> PingResult:
        """Ping a target and return a PingResult"""
        latency, packet_loss, status = await self.ping(ip)
        result = PingResult(
            target_name=name,
            target_ip=ip,
            latency_ms=latency,
            packet_loss=packet_loss,
            status=status
        )
        self.last_results[name] = result
        return result


class BandwidthMonitor:
    """Monitors bandwidth usage on network interfaces"""
    
    def __init__(self):
        self.last_measurements: Dict[str, tuple[int, int, float]] = {}  # interface -> (sent, recv, timestamp)
        self.current_rates: Dict[str, BandwidthMeasurement] = {}
    
    def get_available_interfaces(self) -> List[str]:
        """Get list of available network interfaces"""
        stats = psutil.net_io_counters(pernic=True)
        return list(stats.keys())
    
    def measure(self, gateway_name: str, interface: str) -> BandwidthMeasurement:
        """Measure current bandwidth on an interface"""
        try:
            stats = psutil.net_io_counters(pernic=True)
            
            if interface not in stats:
                # Try to find a matching interface
                available = self.get_available_interfaces()
                print(f"Interface {interface} not found. Available: {available}")
                # Return zero measurement
                return BandwidthMeasurement(
                    gateway_name=gateway_name,
                    interface=interface,
                    bytes_sent=0,
                    bytes_recv=0,
                    bytes_sent_rate=0,
                    bytes_recv_rate=0
                )
            
            current_sent = stats[interface].bytes_sent
            current_recv = stats[interface].bytes_recv
            current_time = time.time()
            
            # Calculate rates if we have previous measurements
            if interface in self.last_measurements:
                last_sent, last_recv, last_time = self.last_measurements[interface]
                time_diff = current_time - last_time
                
                if time_diff > 0:
                    sent_rate = (current_sent - last_sent) / time_diff
                    recv_rate = (current_recv - last_recv) / time_diff
                else:
                    sent_rate = 0
                    recv_rate = 0
            else:
                sent_rate = 0
                recv_rate = 0
            
            # Store current measurement for next calculation
            self.last_measurements[interface] = (current_sent, current_recv, current_time)
            
            measurement = BandwidthMeasurement(
                gateway_name=gateway_name,
                interface=interface,
                bytes_sent=current_sent,
                bytes_recv=current_recv,
                bytes_sent_rate=max(0, sent_rate),
                bytes_recv_rate=max(0, recv_rate)
            )
            
            self.current_rates[gateway_name] = measurement
            return measurement
            
        except Exception as e:
            print(f"Bandwidth measurement error for {interface}: {e}")
            return BandwidthMeasurement(
                gateway_name=gateway_name,
                interface=interface,
                bytes_sent=0,
                bytes_recv=0,
                bytes_sent_rate=0,
                bytes_recv_rate=0
            )


class NetworkMonitor:
    """Main network monitoring class that coordinates all monitoring activities"""
    
    def __init__(self, config: dict):
        self.config = config
        self.ping_monitor = PingMonitor()
        self.bandwidth_monitor = BandwidthMonitor()
        self.callbacks: List[Callable] = []
        self.running = False
    
    def register_callback(self, callback: Callable):
        """Register a callback function to be called when new data is available"""
        self.callbacks.append(callback)
    
    async def notify_callbacks(self, data_type: str, data: Any):
        """Notify all registered callbacks with new data"""
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data_type, data)
                else:
                    callback(data_type, data)
            except Exception as e:
                print(f"Callback error: {e}")
    
    async def ping_all_targets(self) -> List[PingResult]:
        """Ping all configured targets"""
        results = []
        targets = self.config.get('targets', [])
        
        # Run pings concurrently
        tasks = []
        for target in targets:
            if target.get('enabled', True) and target.get('type') == 'ping':
                tasks.append(
                    self.ping_monitor.ping_target(target['name'], target['ip'])
                )
        
        if tasks:
            results = await asyncio.gather(*tasks)
        
        return results
    
    def measure_all_bandwidth(self) -> List[BandwidthMeasurement]:
        """Measure bandwidth on all configured gateways"""
        results = []
        gateways = self.config.get('gateways', [])
        
        for gateway in gateways:
            if gateway.get('enabled', True):
                measurement = self.bandwidth_monitor.measure(
                    gateway['name'],
                    gateway['interface']
                )
                results.append(measurement)
        
        return results
    
    def get_current_status(self) -> dict:
        """Get current status of all monitored targets and gateways"""
        return {
            "ping_results": {
                name: {
                    "target_ip": result.target_ip,
                    "latency_ms": result.latency_ms,
                    "packet_loss": result.packet_loss,
                    "status": result.status,
                    "timestamp": result.timestamp.isoformat()
                }
                for name, result in self.ping_monitor.last_results.items()
            },
            "bandwidth": {
                name: {
                    "interface": measurement.interface,
                    "bytes_sent_rate": measurement.bytes_sent_rate,
                    "bytes_recv_rate": measurement.bytes_recv_rate,
                    "timestamp": measurement.timestamp.isoformat()
                }
                for name, measurement in self.bandwidth_monitor.current_rates.items()
            },
            "available_interfaces": self.bandwidth_monitor.get_available_interfaces()
        }


def format_bytes(bytes_value: float) -> str:
    """Format bytes into human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(bytes_value) < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_bytes_rate(bytes_per_sec: float) -> str:
    """Format bytes per second into human readable string"""
    return f"{format_bytes(bytes_per_sec)}/s"
