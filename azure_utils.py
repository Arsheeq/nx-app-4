import logging
from datetime import datetime, timedelta
import json
from typing import List, Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def discover_azure_resources(credentials: Dict[str, str]) -> List[Dict[str, Any]]:
    """Discover Azure resources - placeholder implementation."""
    # In a real implementation, this would use Azure SDK
    return [
        {
            'id': 'vm-sample-1',
            'name': 'Sample VM 1',
            'type': 'Standard_B2s',
            'state': 'Running',
            'region': 'East US',
            'service_type': 'VM'
        }
    ]

def get_azure_metrics(client_id: str, client_secret: str, tenant_id: str, 
                     subscription_id: str, resource_list: List[str], period_days: int) -> List[Dict[str, Any]]:
    """
    Get metrics for the selected Azure resources.
    
    In a real implementation, this would use the Azure SDK to get metrics for each resource.
    For this sample, we'll generate mock data that has the same structure as the AWS metrics.
    """
    logger.info(f"Getting Azure metrics with period: {period_days} days")
    
    # Validate credentials
    if not client_id or not client_secret or not tenant_id or not subscription_id:
        logger.error("Azure credentials are missing")
        raise ValueError("Azure credentials are required")
    
    metrics_data = []
    
    for resource in resource_list:
        try:
            parts = resource.split('|')
            if len(parts) != 3:
                logger.error(f"Invalid resource format: {resource}")
                continue
            
            service_type, resource_id, region = parts
            
            if service_type == 'VM':
                metrics = generate_vm_metrics(resource_id, region, period_days)
                metrics_data.append(metrics)
            
            elif service_type == 'Database':
                metrics = generate_database_metrics(resource_id, region, period_days)
                metrics_data.append(metrics)
        
        except Exception as e:
            logger.error(f"Error parsing resource format: {resource} - {str(e)}")
            continue
    
    return metrics_data

def generate_vm_metrics(resource_id: str, region: str, period_days: int) -> Dict[str, Any]:
    """Generate sample VM metrics."""
    import random
    
    # Generate sample data points
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=period_days)
    
    cpu_data = []
    current_time = start_time
    
    while current_time <= end_time:
        cpu_data.append({
            'timestamp': current_time,
            'value': random.uniform(20, 80)  # CPU utilization percentage
        })
        current_time += timedelta(hours=1)
    
    return {
        'instance_id': resource_id,
        'instance_name': resource_id,
        'region': region,
        'service_type': 'VM',
        'metrics': {
            'CPU Utilization (%)': cpu_data
        }
    }

def generate_database_metrics(resource_id: str, region: str, period_days: int) -> Dict[str, Any]:
    """Generate sample database metrics."""
    import random
    
    # Generate sample data points
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=period_days)
    
    cpu_data = []
    current_time = start_time
    
    while current_time <= end_time:
        cpu_data.append({
            'timestamp': current_time,
            'value': random.uniform(10, 60)  # CPU utilization percentage
        })
        current_time += timedelta(hours=1)
    
    return {
        'instance_id': resource_id,
        'instance_name': resource_id,
        'region': region,
        'service_type': 'Database',
        'metrics': {
            'CPU Utilization (%)': cpu_data
        }
    }