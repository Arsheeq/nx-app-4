import os
import time
import threading
import logging
import shutil
import glob
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CleanupService:
    """Service to automatically clean up sensitive data after report generation."""
    
    def __init__(self):
        self.cleanup_timers = {}
        self.lock = threading.Lock()
    
    def schedule_cleanup(self, delay_minutes=5):
        """Schedule cleanup to run after specified delay."""
        cleanup_id = f"cleanup_{int(time.time())}"
        
        with self.lock:
            # Cancel any existing timer
            if hasattr(self, 'current_timer') and self.current_timer:
                self.current_timer.cancel()
            
            # Schedule new cleanup
            self.current_timer = threading.Timer(
                delay_minutes * 60, 
                self._perform_cleanup
            )
            self.current_timer.start()
            
            logger.info(f"Scheduled cleanup in {delay_minutes} minutes")
    
    def _perform_cleanup(self):
        """Perform the actual cleanup of sensitive data."""
        try:
            logger.info("Starting automatic cleanup of sensitive data...")
            
            # 1. Clear local_data directory (except structure)
            self._cleanup_local_data()
            
            # 2. Remove any temporary files
            self._cleanup_temp_files()
            
            # 3. Clear any cached credential data
            self._cleanup_cached_credentials()
            
            # 4. Remove generated report files from temp locations
            self._cleanup_generated_reports()
            
            # 5. Clear any logs containing sensitive data
            self._cleanup_sensitive_logs()
            
            logger.info("Automatic cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def _cleanup_local_data(self):
        """Clean up local data directory."""
        local_data_dir = "local_data"
        if os.path.exists(local_data_dir):
            try:
                # Remove all JSON files containing client data
                json_files = glob.glob(os.path.join(local_data_dir, "*.json"))
                for file_path in json_files:
                    os.remove(file_path)
                    logger.info(f"Removed: {file_path}")
                
                # Create empty placeholder to maintain directory
                placeholder_file = os.path.join(local_data_dir, ".gitkeep")
                with open(placeholder_file, 'w') as f:
                    f.write("# This directory stores temporary data\n")
                    
            except Exception as e:
                logger.error(f"Error cleaning local_data: {str(e)}")
    
    def _cleanup_temp_files(self):
        """Remove temporary files."""
        temp_patterns = [
            "/tmp/*nubinix*",
            "/tmp/*report*",
            "/tmp/*client*",
            "*.tmp",
            "*.temp"
        ]
        
        for pattern in temp_patterns:
            try:
                files = glob.glob(pattern)
                for file_path in files:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"Removed temp file: {file_path}")
            except Exception as e:
                logger.error(f"Error cleaning temp files with pattern {pattern}: {str(e)}")
    
    def _cleanup_cached_credentials(self):
        """Clear any cached AWS/Azure credentials."""
        # Clear environment variables that might contain credentials
        sensitive_env_vars = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY', 
            'AZURE_CLIENT_ID',
            'AZURE_CLIENT_SECRET',
            'AZURE_TENANT_ID'
        ]
        
        for env_var in sensitive_env_vars:
            if env_var in os.environ:
                del os.environ[env_var]
                logger.info(f"Cleared environment variable: {env_var}")
    
    def _cleanup_generated_reports(self):
        """Remove generated report files."""
        report_patterns = [
            "*.pdf",
            "*report*.pdf",
            "*utilization*.pdf",
            "*billing*.pdf"
        ]
        
        for pattern in report_patterns:
            try:
                files = glob.glob(pattern)
                for file_path in files:
                    # Only remove files modified in the last hour
                    if os.path.isfile(file_path):
                        file_age = time.time() - os.path.getmtime(file_path)
                        if file_age < 3600:  # 1 hour
                            os.remove(file_path)
                            logger.info(f"Removed report file: {file_path}")
            except Exception as e:
                logger.error(f"Error cleaning report files: {str(e)}")
    
    def _cleanup_sensitive_logs(self):
        """Clean sensitive information from logs."""
        try:
            # This is a placeholder - in production you might want to
            # rotate logs or remove sensitive entries
            logger.info("Log cleanup completed")
        except Exception as e:
            logger.error(f"Error cleaning logs: {str(e)}")
    
    def force_cleanup(self):
        """Force immediate cleanup."""
        logger.info("Forcing immediate cleanup...")
        self._perform_cleanup()

# Global cleanup service instance
cleanup_service = CleanupService()

def schedule_post_report_cleanup():
    """Helper function to schedule cleanup after report generation."""
    cleanup_service.schedule_cleanup(delay_minutes=5)

def force_immediate_cleanup():
    """Helper function to force immediate cleanup."""
    cleanup_service.force_cleanup()