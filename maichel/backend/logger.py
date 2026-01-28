"""
Command Logger for Michael AI
Provides comprehensive audit trail of all actions
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class CommandLogger:
    """Centralized logging system for Michael AI commands"""
    
    def __init__(self):
        # Create .michael directory in user home
        self.log_dir = Path.home() / ".michael"
        self.log_dir.mkdir(exist_ok=True)
        
        # Log file path
        self.log_file = self.log_dir / "command_history.json"
        
        # Initialize log file if it doesn't exist
        if not self.log_file.exists():
            self._initialize_log_file()
    
    def _initialize_log_file(self):
        """Create initial log file structure"""
        initial_data = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "commands": []
        }
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
    
    def log_command(self, 
                   action: str, 
                   params: Optional[Dict] = None,
                   user_input: Optional[str] = None,
                   result: str = "success",
                   message: Optional[str] = None,
                   warnings: Optional[List[str]] = None):
        """
        Log a command execution
        
        Args:
            action: The action performed (e.g., 'delete_file', 'shutdown')
            params: Parameters passed to the action
            user_input: Original user voice/text input
            result: 'success', 'error', 'blocked', 'cancelled'
            message: Additional message or error details
            warnings: List of warnings generated
        """
        try:
            # Read existing log
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            # Create log entry
            entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "params": params or {},
                "user_input": user_input,
                "result": result,
                "message": message,
                "warnings": warnings or []
            }
            
            # Append to commands
            log_data["commands"].append(entry)
            
            # Keep only last 1000 commands to prevent excessive file size
            if len(log_data["commands"]) > 1000:
                log_data["commands"] = log_data["commands"][-1000:]
            
            # Write back to file
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"Failed to log command: {e}")
    
    def get_recent_commands(self, count: int = 10) -> List[Dict]:
        """Get the most recent commands from log"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            return log_data["commands"][-count:]
        except Exception:
            return []
    
    def get_all_commands(self) -> List[Dict]:
        """Get all logged commands"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            return log_data["commands"]
        except Exception:
            return []
    
    def export_logs(self, output_path: str):
        """Export logs to a specified path"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception:
            return False

# Global instance
command_logger = CommandLogger()
