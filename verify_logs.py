# verify_logs.py - Check if logs are being populated (CORRECTED)

import json
from pathlib import Path
from datetime import datetime

def verify_logs():
    """Verify that experiment logs are being generated and populated correctly"""
    
    log_file = Path("logs/experiment_data.json")
    
    print("=" * 60)
    print(" LOG VERIFICATION REPORT")
    print("=" * 60)
    
    # Check 1: Does the logs directory exist?
    if not Path("logs").exists():
        print(" FAIL: logs/ directory does not exist")
        return False
    else:
        print(" PASS: logs/ directory exists")
    
    # Check 2: Does the log file exist?
    if not log_file.exists():
        print(" FAIL: logs/experiment_data.json does not exist")
        return False
    else:
        print(" PASS: logs/experiment_data.json exists")
    
    # Check 3: Is the file readable?
    try:
        with open(log_file, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f" FAIL: Log file is corrupted - {e}")
        return False
    except Exception as e:
        print(f" FAIL: Cannot read log file - {e}")
        return False
    
    print(" PASS: Log file is readable")
    
    # Check 4: Does it have entries?
    if not data:
        print("  WARNING: Log file is empty (no experiments logged yet)")
        return True
    
    num_entries = len(data)
    print(f" PASS: Found {num_entries} log entries")
    
    # Check 5: Verify structure of entries
    # CORRECTED FIELD NAMES - matching your actual log structure
    required_fields = ["timestamp", "agent", "model", "action", "details", "status"]
    
    valid_entries = 0
    invalid_entries = 0
    
    for i, entry in enumerate(data):
        missing_fields = [field for field in required_fields if field not in entry]
        
        if missing_fields:
            print(f" Entry {i+1}: Missing fields: {missing_fields}")
            invalid_entries += 1
        else:
            valid_entries += 1
    
    print(f"\n SUMMARY:")
    print(f"   Total entries: {num_entries}")
    print(f"   Valid entries: {valid_entries}")
    print(f"   Invalid entries: {invalid_entries}")
    
    # Check 6: Show recent activity
    if data:
        print(f"\n🕒 RECENT ACTIVITY:")
        recent = data[-5:]  # Last 5 entries
        for entry in recent:
            timestamp = entry.get('timestamp', 'Unknown')
            agent = entry.get('agent', 'Unknown')
            action = entry.get('action', 'Unknown')
            status = entry.get('status', 'Unknown')
            model = entry.get('model', 'N/A')
            print(f"   [{timestamp}] {agent} ({model}) - {action} - {status}")
    
    # Check 7: Count successes and failures
    success_count = sum(1 for e in data if e.get('status') == 'SUCCESS')
    failure_count = sum(1 for e in data if e.get('status') == 'FAILURE')
    info_count = sum(1 for e in data if e.get('status') == 'INFO')
    
    print(f"\n STATUS BREAKDOWN:")
    print(f"    SUCCESS: {success_count}")
    print(f"    FAILURE: {failure_count}")
    print(f"    INFO: {info_count}")
    
    # Check 8: Show agent activity
    agent_stats = {}
    for entry in data:
        agent = entry.get('agent', 'Unknown')
        agent_stats[agent] = agent_stats.get(agent, 0) + 1
    
    print(f"\n🤖 AGENT ACTIVITY:")
    for agent, count in sorted(agent_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"   {agent}: {count} actions")
    
    print("\n" + "=" * 60)
    
    if invalid_entries > 0:
        print("⚠️  STATUS: Some entries have issues")
        return False
    else:
        print("✅ STATUS: All checks passed!")
        return True

if __name__ == "__main__":
    verify_logs()