from datetime import datetime
import json
import os

# Simple local storage for data persistence
DATA_DIR = "local_data"
os.makedirs(DATA_DIR, exist_ok=True)

class LocalStorage:
    """Simple local storage for app data using JSON files."""
    
    @staticmethod
    def save_data(filename, data):
        """Save data to a JSON file."""
        filepath = os.path.join(DATA_DIR, f"{filename}.json")
        with open(filepath, 'w') as f:
            json.dump(data, f, default=str)
    
    @staticmethod
    def load_data(filename, default=None):
        """Load data from a JSON file."""
        filepath = os.path.join(DATA_DIR, f"{filename}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return default or []

class CloudAccount:
    """Simple cloud account data structure."""
    
    def __init__(self, name, provider, account_id, id=None):
        self.id = id or str(datetime.utcnow().timestamp())
        self.name = name
        self.provider = provider
        self.account_id = account_id
        self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'provider': self.provider,
            'account_id': self.account_id,
            'created_at': self.created_at
        }

class Resource:
    """Simple resource data structure."""
    
    def __init__(self, account_id, resource_id, resource_type, name=None, region=None, status=None, resource_metadata=None, id=None):
        self.id = id or str(datetime.utcnow().timestamp())
        self.account_id = account_id
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.name = name
        self.region = region
        self.status = status
        self.resource_metadata = resource_metadata
        self.discovered_at = datetime.utcnow().isoformat()
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'resource_id': self.resource_id,
            'resource_type': self.resource_type,
            'name': self.name,
            'region': self.region,
            'status': self.status,
            'resource_metadata': self.resource_metadata,
            'discovered_at': self.discovered_at
        }

class Report:
    """Simple report data structure."""
    
    def __init__(self, account_id, report_type, filename, file_path=None, status='generating', id=None):
        self.id = id or str(datetime.utcnow().timestamp())
        self.account_id = account_id
        self.report_type = report_type
        self.filename = filename
        self.file_path = file_path
        self.status = status
        self.created_at = datetime.utcnow().isoformat()
        self.completed_at = None
        self.error_message = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'report_type': self.report_type,
            'filename': self.filename,
            'file_path': self.file_path,
            'status': self.status,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'error_message': self.error_message
        }