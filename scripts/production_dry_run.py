#!/usr/bin/env python3
"""
Production Dry Run Script

Orchestrates all production tests and generates a comprehensive readiness report.
This is the main script to run before tournament day to ensure everything is working.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

from utils.logging_utils import SecureLogger

logger = SecureLogger(__name__)


class ProductionDryRunResults:
    """Container for production dry run results."""
    
    def __init__(self):
        self.start_time = time.time()
        self.test_results = {}
        self.health_checks = {}
        self.errors = []
        self.warnings = []
        self.production_ready = False
        
    def add_test_result(self, test_name: str, result: Dict):
        """Add a test result."""
        self.test_results[test_name] = result
        
        if not result.get("success", False):
            self.errors.append(f"{test_name}: {result.get('error', 'Unknown error')}")
            
    def add_health_check(self, check_name: str, status: str, details: str = None):
        """Add a health check result."""
        self.health_checks[check_name] = {
            "status": status,
            "details": details,
            "timestamp": time.time()
        }
        
        if status == "FAIL":
            self.errors.append(f"Health Check: {check_name} - {details}")
        elif status == "WARN":
            self.warnings.append(f"Health Check: {check_name} - {details}")
            
    def is_production_ready(self) -> bool:
        """Determine if system is production ready."""
        # All tests must pass
        tests_passed = all(r.get("success", False) for r in self.test_results.values())
        
        # No critical health check failures
        health_ok = not any(check["status"] == "FAIL" for check in self.health_checks.values())
        
        self.production_ready = tests_passed and health_ok
        return self.production_ready
        
    def get_summary(self) -> Dict:
        """Get a summary of results."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r.get("success", False))
        
        health_checks = list(self.health_checks.values())
        passed_health = sum(1 for h in health_checks if h["status"] == "PASS")
        
        return {
            "duration": time.time() - self.start_time,
            "tests": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0
            },
            "health_checks": {
                "total": len(health_checks),
                "passed": passed_health,
                "failed": len(health_checks) - passed_health
            },
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "production_ready": self.is_production_ready()
        }


async def run_script(script_path: str, args: List[str] = None) -> Tuple[int, str, str]:
    """Run a script and return exit code, stdout, and stderr."""
    if args is None:
        args = []
        
    try:
        # Run the script
        process = await asyncio.create_subprocess_exec(
            sys.executable, script_path, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return (
            process.returncode,
            stdout.decode('utf-8', errors='replace'),
            stderr.decode('utf-8', errors='replace')
        )
    except Exception as e:
        return -1, "", str(e)


async def run_riot_api_test() -> Dict:
    """Run the Riot API integration test."""
    logger.info("🔌 Running Riot API integration test...")
    
    script_path = Path(__file__).parent / "test_riot_integration.py"
    
    if not script_path.exists():
        return {
            "success": False,
            "error": f"Test script not found: {script_path}"
        }
        
    exit_code, stdout, stderr = await run_script(str(script_path))
    
    # Parse results from JSON report if available
    report_file = None
    for line in stdout.split('\n'):
        if "Detailed report saved to:" in line:
            report_file = line.split(": ", 1)[1].strip()
            break
            
    if report_file and os.path.exists(report_file):
        try:
            with open(report_file, 'r') as f:
                report_data = json.load(f)
            return {
                "success": report_data.get("production_ready", False),
                "data": report_data
            }
        except Exception as e:
            logger.warning(f"Failed to parse Riot API test report: {e}")
            
    # Fallback: check exit code
    return {
        "success": exit_code == 0,
        "error": stderr if exit_code != 0 else None,
        "exit_code": exit_code
    }


async def run_scoreboard_api_test() -> Dict:
    """Run the scoreboard API integration test."""
    logger.info("📊 Running scoreboard API test...")
    
    script_path = Path(__file__).parent / "test_scoreboard_api.py"
    
    if not script_path.exists():
        return {
            "success": False,
            "error": f"Test script not found: {script_path}"
        }
        
    exit_code, stdout, stderr = await run_script(str(script_path))
    
    # Parse results from JSON report if available
    report_file = None
    for line in stdout.split('\n'):
        if "Report saved to:" in line:
            report_file = line.split(": ", 1)[1].strip()
            break
            
    if report_file and os.path.exists(report_file):
        try:
            with open(report_file, 'r') as f:
                report_data = json.load(f)
            return {
                "success": report_data.get("success", False),
                "data": report_data
            }
        except Exception as e:
            logger.warning(f"Failed to parse scoreboard API test report: {e}")
            
    # Fallback: check exit code
    return {
        "success": exit_code == 0,
        "error": stderr if exit_code != 0 else None,
        "exit_code": exit_code
    }


def check_environment() -> Dict:
    """Check environment variables and configuration."""
    logger.info("🔧 Checking environment...")
    
    checks = []
    
    # Check required environment variables
    required_vars = ["RIOT_API_KEY"]
    for var in required_vars:
        if os.getenv(var):
            checks.append({"var": var, "status": "OK"})
        else:
            checks.append({"var": var, "status": "MISSING"})
            
    # Check optional but recommended variables
    optional_vars = ["DATABASE_URL", "DISCORD_BOT_TOKEN"]
    for var in optional_vars:
        if os.getenv(var):
            checks.append({"var": var, "status": "OK"})
        else:
            checks.append({"var": var, "status": "NOT_SET"})
            
    # Check Python packages
    try:
        import sqlalchemy
        checks.append({"var": "sqlalchemy", "status": "OK"})
    except ImportError:
        checks.append({"var": "sqlalchemy", "status": "MISSING"})
        
    try:
        import aiohttp
        checks.append({"var": "aiohttp", "status": "OK"})
    except ImportError:
        checks.append({"var": "aiohttp", "status": "MISSING"})
        
    # Determine overall status
    all_ok = all(c["status"] == "OK" for c in checks if c["var"] in required_vars)
    
    return {
        "success": all_ok,
        "data": {
            "checks": checks,
            "required_vars_set": sum(1 for c in checks if c["var"] in required_vars and c["status"] == "OK"),
            "total_required": len(required_vars)
        }
    }


def check_services() -> Dict:
    """Check if required services are accessible."""
    logger.info("🌐 Checking service connectivity...")
    
    checks = []
    
    # Check Riot API connectivity (simple check)
    api_key = os.getenv("RIOT_API_KEY")
    if api_key:
        checks.append({
            "service": "Riot API",
            "status": "CONFIGURED",
            "details": "API key present"
        })
    else:
        checks.append({
            "service": "Riot API",
            "status": "NOT_CONFIGURED",
            "details": "API key missing"
        })
        
    # Check database connectivity (if configured)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            from sqlalchemy import create_engine
            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            checks.append({
                "service": "Database",
                "status": "OK",
                "details": "Connected successfully"
            })
        except Exception as e:
            checks.append({
                "service": "Database",
                "status": "ERROR",
                "details": str(e)
            })
    else:
        checks.append({
            "service": "Database",
            "status": "NOT_CONFIGURED",
            "details": "DATABASE_URL not set"
        })
        
    # Check API service (if running)
    try:
        import httpx
        response = httpx.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            checks.append({
                "service": "API Service",
                "status": "OK",
                "details": f"Healthy (status {response.status_code})"
            })
        else:
            checks.append({
                "service": "API Service",
                "status": "ERROR",
                "details": f"Unexpected status: {response.status_code}"
            })
    except Exception:
        checks.append({
            "service": "API Service",
            "status": "NOT_RUNNING",
            "details": "API service not accessible at http://localhost:8000"
        })
        
    # Determine overall status
    critical_ok = not any(c["status"] in ["ERROR", "NOT_CONFIGURED"] 
                          for c in checks if c["service"] in ["Riot API", "Database"])
    
    return {
        "success": critical_ok,
        "data": {
            "checks": checks,
            "critical_services_ok": critical_ok
        }
    }


def generate_recommendations(results: ProductionDryRunResults) -> List[Dict]:
    """Generate recommendations based on test results."""
    recommendations = []
    
    # Check for Riot API issues
    riot_result = results.test_results.get("riot_api_test", {})
    if not riot_result.get("success", False):
        recommendations.append({
            "priority": "HIGH",
            "category": "Riot API",
            "issue": "Riot API test failed",
            "recommendation": "Verify RIOT_API_KEY is valid and has sufficient rate limits",
            "action": "Check API key configuration and consider increasing rate limit quota"
        })
        
    # Check for scoreboard API issues
    scoreboard_result = results.test_results.get("scoreboard_api_test", {})
    if not scoreboard_result.get("success", False):
        recommendations.append({
            "priority": "HIGH",
            "category": "Backend",
            "issue": "Scoreboard API test failed",
            "recommendation": "Review API logs and check database configuration",
            "action": "Run individual test scripts for detailed error information"
        })
        
    # Check for service issues
    for check_name, check in results.health_checks.items():
        if check["status"] == "FAIL":
            recommendations.append({
                "priority": "HIGH",
                "category": "Infrastructure",
                "issue": f"Health check failed: {check_name}",
                "recommendation": check.get("details", "Unknown issue"),
                "action": "Resolve the failing service before proceeding to production"
            })
        elif check["status"] == "WARN":
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Infrastructure",
                "issue": f"Health check warning: {check_name}",
                "recommendation": check.get("details", "Investigate potential issue"),
                "action": "Monitor this service during tournament"
            })
            
    # Performance recommendations
    for test_name, result in results.test_results.items():
        if result.get("data", {}).get("summary", {}).get("avg_response_time", 0) > 1.0:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Performance",
                "issue": f"Slow response time in {test_name}",
                "recommendation": "Monitor API response times during tournament",
                "action": "Consider optimizing queries or increasing resources if needed"
            })
            
    # General recommendations if everything looks good
    if results.is_production_ready():
        recommendations.append({
            "priority": "INFO",
            "category": "Ready for Production",
            "issue": None,
            "recommendation": "All tests passed! System is ready for tournament day",
            "action": "Run this script again on tournament day as a final check"
        })
        
    return recommendations


async def run_production_dry_run() -> Dict:
    """Run the complete production dry run."""
    print("🚀 Guardian Angel League - Production Dry Run")
    print("=" * 60)
    print("This script validates the entire system is ready for production.")
    print("It will run integration tests and health checks.\n")
    
    # Initialize results
    results = ProductionDryRunResults()
    
    # Phase 1: Environment checks
    logger.info("\n" + "=" * 20 + " PHASE 1: ENVIRONMENT " + "=" * 20)
    print("\n🔧 Checking environment configuration...")
    
    env_result = check_environment()
    results.add_test_result("environment_check", env_result)
    
    status = "✅ OK" if env_result["success"] else "❌ ISSUES"
    print(f"   Environment: {status}")
    
    # Phase 2: Service health checks
    logger.info("\n" + "=" * 20 + " PHASE 2: HEALTH CHECKS " + "=" * 20)
    print("\n🌐 Checking service connectivity...")
    
    service_result = check_services()
    results.add_test_result("service_check", service_result)
    
    # Add individual health checks
    for check in service_result.get("data", {}).get("checks", []):
        status_map = {"OK": "PASS", "NOT_RUNNING": "WARN", "ERROR": "FAIL", "NOT_CONFIGURED": "FAIL"}
        results.add_health_check(
            check["service"],
            status_map.get(check["status"], "FAIL"),
            check.get("details")
        )
    
    status = "✅ OK" if service_result["success"] else "❌ ISSUES"
    print(f"   Services: {status}")
    
    # Phase 3: Integration tests
    logger.info("\n" + "=" * 20 + " PHASE 3: INTEGRATION TESTS " + "=" * 20)
    
    # Run Riot API test
    print("\n🔌 Testing Riot API integration...")
    riot_result = await run_riot_api_test()
    results.add_test_result("riot_api_test", riot_result)
    
    status = "✅ PASS" if riot_result["success"] else "❌ FAIL"
    print(f"   Riot API Test: {status}")
    
    # Run scoreboard API test
    print("\n📊 Testing scoreboard API...")
    scoreboard_result = await run_scoreboard_api_test()
    results.add_test_result("scoreboard_api_test", scoreboard_result)
    
    status = "✅ PASS" if scoreboard_result["success"] else "❌ FAIL"
    print(f"   Scoreboard Test: {status}")
    
    # Generate final report
    logger.info("\n" + "=" * 20 + " PRODUCTION READINESS " + "=" * 20)
    
    summary = results.get_summary()
    
    print("\n📊 SUMMARY")
    print("=" * 60)
    print(f"✅ Tests Passed: {summary['tests']['passed']}/{summary['tests']['total']}")
    print(f"🔍 Health Checks: {summary['health_checks']['passed']}/{summary['health_checks']['total']}")
    print(f"⏱️ Duration: {summary['duration']:.2f}s")
    
    if results.errors:
        print(f"\n❌ ERRORS ({len(results.errors)}):")
        for error in results.errors[:5]:  # Show first 5
            print(f"   • {error}")
        if len(results.errors) > 5:
            print(f"   ... and {len(results.errors) - 5} more")
            
    if results.warnings:
        print(f"\n⚠️ WARNINGS ({len(results.warnings)}):")
        for warning in results.warnings[:3]:  # Show first 3
            print(f"   • {warning}")
        if len(results.warnings) > 3:
            print(f"   ... and {len(results.warnings) - 3} more")
    
    # Production readiness status
    is_ready = results.is_production_ready()
    status = "✅ PRODUCTION READY" if is_ready else "❌ NOT READY"
    print(f"\n🚦 STATUS: {status}")
    
    # Generate recommendations
    recommendations = generate_recommendations(results)
    
    if recommendations:
        print(f"\n💡 RECOMMENDATIONS")
        print("-" * 60)
        for rec in recommendations:
            priority_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "INFO": "🔵"}.get(rec["priority"], "⚪")
            print(f"\n{priority_icon} {rec['priority']} PRIORITY - {rec['category']}")
            if rec["issue"]:
                print(f"   Issue: {rec['issue']}")
            print(f"   Recommendation: {rec['recommendation']}")
            print(f"   Action: {rec['action']}")
    
    # Prepare final report
    report = {
        "timestamp": datetime.now().isoformat(),
        "production_ready": is_ready,
        "summary": summary,
        "test_results": results.test_results,
        "health_checks": results.health_checks,
        "errors": results.errors,
        "warnings": results.warnings,
        "recommendations": recommendations
    }
    
    # Save report
    report_file = f"production_dry_run_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Full report saved to: {report_file}")
    
    # Create simple HTML report
    html_file = report_file.replace('.json', '.html')
    create_html_report(report, html_file)
    print(f"🌐 HTML report saved to: {html_file}")
    
    return report


def create_html_report(report: Dict, output_file: str):
    """Create an HTML version of the report."""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>GAL Production Readiness Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .status-ready {{
            background-color: #27ae60;
            color: white;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            font-size: 24px;
            margin-bottom: 20px;
        }}
        .status-not-ready {{
            background-color: #e74c3c;
            color: white;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            font-size: 24px;
            margin-bottom: 20px;
        }}
        .section {{
            background-color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .error {{
            color: #e74c3c;
        }}
        .warning {{
            color: #f39c12;
        }}
        .success {{
            color: #27ae60;
        }}
        ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        li {{
            padding: 5px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #ecf0f1;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ Guardian Angel League</h1>
        <h2>Production Readiness Report</h2>
        <p>Generated: {report['timestamp']}</p>
    </div>
    
    <div class="{'status-ready' if report['production_ready'] else 'status-not-ready'}">
        {'🚀 PRODUCTION READY' if report['production_ready'] else '❌ NOT PRODUCTION READY'}
    </div>
    
    <div class="section">
        <h3>📊 Summary</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Tests Passed</td><td>{report['summary']['tests']['passed']}/{report['summary']['tests']['total']}</td></tr>
            <tr><td>Health Checks</td><td>{report['summary']['health_checks']['passed']}/{report['summary']['health_checks']['total']}</td></tr>
            <tr><td>Duration</td><td>{report['summary']['duration']:.2f} seconds</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h3>🧪 Test Results</h3>
        {"".join(f"""
        <p><strong>{test_name}</strong>: 
            <span class="{'success' if result['success'] else 'error'}">
                {'✅ PASS' if result['success'] else '❌ FAIL'}
            </span>
        </p>
        """ for test_name, result in report['test_results'].items())}
    </div>
    
    {f"""
    <div class="section">
        <h3>❌ Errors</h3>
        <ul class="error">
            {''.join(f'<li>• {error}</li>' for error in report['errors'][:10])}
        </ul>
        {f'<p>... and {len(report["errors"]) - 10} more errors</p>' if len(report['errors']) > 10 else ''}
    </div>
    """ if report['errors'] else ''}
    
    {f"""
    <div class="section">
        <h3>💡 Recommendations</h3>
        {"".join(f"""
        <div style="margin-bottom: 15px;">
            <strong>{rec['priority']} PRIORITY - {rec['category']}</strong><br>
            {f"<em>Issue: {rec['issue']}</em><br>" if rec['issue'] else ''}
            Recommendation: {rec['recommendation']}<br>
            Action: {rec['action']}
        </div>
        """ for rec in report['recommendations'][:5])}
    </div>
    """ if report['recommendations'] else ''}
</body>
</html>
"""
    
    with open(output_file, "w") as f:
        f.write(html)


def main():
    """Run the production dry run."""
    # Check if running with correct Python environment
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
        
    # Run the async dry run
    try:
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(run_production_dry_run())
        
        # Exit with appropriate code
        sys.exit(0 if results.get("production_ready", False) else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Dry run interrupted by user")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Dry run failed: {e}")
        print(f"\n❌ Dry run failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
