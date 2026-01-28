"""
Safety Guardian Module for Michael AI
Provides intelligent protection for critical system operations
"""
import os
from pathlib import Path
from typing import List, Dict, Tuple

class SafetyGuardian:
    """Centralized safety checking system"""
    
    def __init__(self):
        # Protected system directories
        self.protected_paths = [
            r"C:\Windows",
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            os.path.join(os.path.expanduser("~"), "Documents"),
            os.path.join(os.path.expanduser("~"), "Pictures"),
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.path.expanduser("~"), "Videos"),
            os.path.join(os.path.expanduser("~"), "Music"),
        ]
        
        # Thresholds for safety checks
        self.max_file_count_threshold = 100
        self.max_size_mb_threshold = 1000  # 1GB
        
    def is_protected_path(self, path: str) -> Tuple[bool, str]:
        """
        Check if a path is in a protected directory
        Returns: (is_protected, reason)
        """
        normalized_path = os.path.normpath(os.path.abspath(path))
        
        for protected in self.protected_paths:
            normalized_protected = os.path.normpath(protected)
            
            # Check if path is within protected directory
            try:
                if Path(normalized_path).is_relative_to(Path(normalized_protected)):
                    return True, f"Path is within protected directory: {protected}"
            except (ValueError, AttributeError):
                # Fallback for older Python versions
                if normalized_path.lower().startswith(normalized_protected.lower()):
                    return True, f"Path is within protected directory: {protected}"
        
        return False, ""
    
    def check_file_count(self, directory: str) -> Tuple[bool, int]:
        """
        Check if directory has too many files
        Returns: (exceeds_threshold, file_count)
        """
        if not os.path.isdir(directory):
            return False, 0
        
        try:
            file_count = sum(1 for _ in Path(directory).rglob('*') if _.is_file())
            exceeds = file_count > self.max_file_count_threshold
            return exceeds, file_count
        except Exception:
            return False, 0
    
    def get_directory_size(self, directory: str) -> int:
        """Get total size of directory in bytes"""
        if not os.path.isdir(directory):
            return 0
        
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception:
            pass
        
        return total_size
    
    def validate_file_operation(self, path: str, operation: str) -> Dict:
        """
        Validate if a file operation is safe
        Returns: {
            'safe': bool,
            'requires_confirmation': bool,
            'warnings': List[str],
            'blocked': bool,
            'blocked_reason': str
        }
        """
        result = {
            'safe': True,
            'requires_confirmation': False,
            'warnings': [],
            'blocked': False,
            'blocked_reason': ''
        }
        
        # Check if path exists
        if not os.path.exists(path):
            result['safe'] = False
            result['warnings'].append(f"Path does not exist: {path}")
            return result
        
        # Check if in protected directory
        is_protected, reason = self.is_protected_path(path)
        if is_protected:
            result['blocked'] = True
            result['blocked_reason'] = reason
            result['safe'] = False
            return result
        
        # For delete operations on directories
        if operation == 'delete' and os.path.isdir(path):
            # Check file count
            exceeds_count, file_count = self.check_file_count(path)
            if exceeds_count:
                result['requires_confirmation'] = True
                result['warnings'].append(f"Directory contains {file_count} files (threshold: {self.max_file_count_threshold})")
            
            # Check size
            size_bytes = self.get_directory_size(path)
            size_mb = size_bytes / (1024 * 1024)
            if size_mb > self.max_size_mb_threshold:
                result['requires_confirmation'] = True
                result['warnings'].append(f"Directory size is {size_mb:.2f} MB (threshold: {self.max_size_mb_threshold} MB)")
        
        return result
    
    def validate_system_command(self, command: str) -> Dict:
        """
        Validate system commands for safety
        Returns similar dict as validate_file_operation
        """
        result = {
            'safe': True,
            'requires_confirmation': False,
            'warnings': [],
            'blocked': False,
            'blocked_reason': ''
        }
        
        dangerous_keywords = ['format', 'diskpart', 'del /f /s /q C:\\', 'rmdir /s /q C:\\']
        
        cmd_lower = command.lower()
        for keyword in dangerous_keywords:
            if keyword.lower() in cmd_lower:
                result['blocked'] = True
                result['blocked_reason'] = f"Command contains dangerous keyword: {keyword}"
                result['safe'] = False
                return result
        
        return result

# Global instance
safety_guardian = SafetyGuardian()
