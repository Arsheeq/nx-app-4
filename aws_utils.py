import boto3
import logging
from datetime import datetime, timedelta
import pytz
import json
import os
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_aws_client(service: str, region: str, aws_access_key: str, aws_secret_key: str):
    """Create and return an AWS service client."""
    try:
        return boto3.client(
            service,
            region_name=region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
    except Exception as e:
        logger.error(f"Failed to create AWS client for {service}: {str(e)}")
        raise

def get_all_regions(aws_access_key: str, aws_secret_key: str) -> List[str]:
    """Get a list of all available AWS regions."""
    try:
        ec2_client = get_aws_client('ec2', 'us-east-1', aws_access_key, aws_secret_key)
        regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
        return regions
    except Exception as e:
        logger.error(f"Failed to get AWS regions: {str(e)}")
        # Fallback to common regions if API fails
        return ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 'ap-south-1']

def discover_aws_resources(aws_access_key: str, aws_secret_key: str) -> List[Dict[str, Any]]:
    """Discover all AWS resources across all regions."""
    all_resources = []
    regions = get_all_regions(aws_access_key, aws_secret_key)

    for region in regions:
        # Get EC2 instances
        ec2_instances = list_ec2_instances(aws_access_key, aws_secret_key, region)
        all_resources.extend(ec2_instances)

        # Get RDS instances
        rds_instances = list_rds_instances(aws_access_key, aws_secret_key, region)
        all_resources.extend(rds_instances)

    return all_resources

def list_ec2_instances(aws_access_key: str, aws_secret_key: str, region: str) -> List[Dict[str, Any]]:
    """List EC2 instances in the specified region."""
    try:
        ec2_client = get_aws_client('ec2', region, aws_access_key, aws_secret_key)
        response = ec2_client.describe_instances()

        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_name = 'Unnamed'
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name':
                            instance_name = tag['Value']

                platform = instance.get('Platform', 'Linux')
                if platform is None:
                    platform = 'Linux'

                instance_data = {
                    'id': instance['InstanceId'],
                    'name': instance_name,
                    'type': instance['InstanceType'],
                    'os': platform,
                    'state': instance['State']['Name'],
                    'region': region,
                    'service_type': 'EC2'
                }
                instances.append(instance_data)

        return instances
    except Exception as e:
        logger.error(f"Failed to list EC2 instances in {region}: {str(e)}")
        return []

def list_rds_instances(aws_access_key: str, aws_secret_key: str, region: str) -> List[Dict[str, Any]]:
    """List RDS instances in the specified region."""
    try:
        rds_client = get_aws_client('rds', region, aws_access_key, aws_secret_key)
        response = rds_client.describe_db_instances()

        instances = []
        for instance in response['DBInstances']:
            instance_data = {
                'id': instance['DBInstanceIdentifier'],
                'name': instance['DBInstanceIdentifier'],
                'type': instance['DBInstanceClass'],
                'status': instance['DBInstanceStatus'],
                'engine': instance['Engine'],
                'region': region,
                'service_type': 'RDS'
            }
            instances.append(instance_data)

        return instances
    except Exception as e:
        logger.error(f"Failed to list RDS instances in {region}: {str(e)}")
        return []

def get_cloudwatch_metric_data(cloudwatch, metric_name: str, namespace: str, 
                              dimensions: List[Dict[str, str]], period_days: int, statistic: str = 'Average') -> Dict[str, Any]:
    """Get CloudWatch metric data for the specified period."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=period_days)
    logger.info(f"Fetching metrics for {metric_name} from {start_time} to {end_time}")

    # Use 3 hour intervals for weekly reports, 15 min for daily
    period = 10800 if period_days > 1 else 900  # 3 hours for weekly, 15 min for daily

    try:
        # Set a more aggressive timeout for CloudWatch requests
        import botocore.config
        config = botocore.config.Config(
            connect_timeout=5,
            read_timeout=10,
            retries={'max_attempts': 2}
        )
        
        # Create a new CloudWatch client with timeout configuration
        cloudwatch_with_timeout = boto3.client(
            'cloudwatch',
            region_name=cloudwatch._client_config.region_name,
            aws_access_key_id=cloudwatch._request_signer._credentials.access_key,
            aws_secret_access_key=cloudwatch._request_signer._credentials.secret_key,
            config=config
        )

        response = cloudwatch_with_timeout.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=[statistic]
        )

        return {
            'Datapoints': response['Datapoints']
        }
    except Exception as e:
        logger.warning(f"Failed to get CloudWatch metric {metric_name}: {str(e)}")
        return {
            'Datapoints': []
        }

def get_ec2_metrics(aws_access_key: str, aws_secret_key: str, instance_id: str, 
                   region: str, period_days: int) -> Optional[Dict[str, Any]]:
    """Get EC2 instance metrics from CloudWatch."""
    try:
        cloudwatch = get_aws_client('cloudwatch', region, aws_access_key, aws_secret_key)
        ec2_client = get_aws_client('ec2', region, aws_access_key, aws_secret_key)

        # Get instance details
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]

        instance_name = instance_id
        if 'Tags' in instance:
            for tag in instance['Tags']:
                if tag['Key'] == 'Name':
                    instance_name = tag['Value']

        platform = instance.get('Platform', 'Linux')
        if platform is None:
            platform = 'Linux'

        os_type = platform.lower()
        dimensions = [{'Name': 'InstanceId', 'Value': instance_id}]

        # Get CPU metrics
        cpu_data = get_cloudwatch_metric_data(
            cloudwatch, 
            'CPUUtilization', 
            'AWS/EC2',
            dimensions,
            period_days
        )

        # Get memory metrics
        memory_metric = 'Memory % Committed Bytes In Use' if os_type == 'windows' else 'mem_used_percent'
        memory_data = get_cloudwatch_metric_data(
            cloudwatch,
            memory_metric,
            'CWAgent',
            dimensions,
            period_days
        )

        # Get disk metrics
        disk_metrics = {}

        if os_type == 'windows':
            # For Windows, get C:, D:, E: disks if present
            drives = ['C:', 'D:', 'E:']
            for drive in drives:
                drive_dimensions = dimensions + [
                    {'Name': 'instance', 'Value': drive}
                ]
                drive_key = f"disk {drive[0]}"
                disk_metrics[drive_key] = get_cloudwatch_metric_data(
                    cloudwatch,
                    'LogicalDisk % Free Space',
                    'CWAgent',
                    drive_dimensions,
                    period_days
                )
        else:
            # For Linux, just get root (/) disk
            disk_dimensions = dimensions + [
                {'Name': 'path', 'Value': '/'}
            ]
            disk_metrics['disk'] = get_cloudwatch_metric_data(
                cloudwatch,
                'disk_used_percent',
                'CWAgent',
                disk_dimensions,
                period_days
            )

        return {
            'id': instance_id,
            'name': instance_name,
            'type': instance['InstanceType'],
            'state': instance['State']['Name'],
            'os': platform,
            'region': region,
            'cpu': cpu_data,
            'memory': memory_data,
            'disk_metrics': disk_metrics
        }
    except Exception as e:
        logger.error(f"Failed to get EC2 metrics for {instance_id}: {str(e)}")
        return None

def get_rds_metrics(aws_access_key: str, aws_secret_key: str, instance_id: str, 
                   region: str, period_days: int) -> Optional[Dict[str, Any]]:
    """Get RDS instance metrics from CloudWatch."""
    try:
        cloudwatch = get_aws_client('cloudwatch', region, aws_access_key, aws_secret_key)
        rds_client = get_aws_client('rds', region, aws_access_key, aws_secret_key)

        # Get instance details
        response = rds_client.describe_db_instances(DBInstanceIdentifier=instance_id)
        instance = response['DBInstances'][0]

        dimensions = [{'Name': 'DBInstanceIdentifier', 'Value': instance_id}]

        # Get CPU metrics
        cpu_data = get_cloudwatch_metric_data(
            cloudwatch, 
            'CPUUtilization', 
            'AWS/RDS',
            dimensions,
            period_days
        )

        # Get memory metrics (available memory)
        memory_data = get_cloudwatch_metric_data(
            cloudwatch,
            'FreeableMemory',
            'AWS/RDS',
            dimensions,
            period_days
        )

        # Get disk metrics (available storage)
        disk_data = get_cloudwatch_metric_data(
            cloudwatch,
            'FreeStorageSpace',
            'AWS/RDS',
            dimensions,
            period_days
        )

        return {
            'id': instance_id,
            'name': instance_id,
            'type': instance['DBInstanceClass'],
            'status': instance['DBInstanceStatus'],
            'engine': instance['Engine'],
            'region': region,
            'cpu': cpu_data,
            'memory': memory_data,
            'disk': disk_data
        }
    except Exception as e:
        logger.error(f"Failed to get RDS metrics for {instance_id}: {str(e)}")
        return None

def convert_bytes_to_gb(data: Dict[str, Any]) -> None:
    """Convert byte values to gigabytes in the data structure"""
    if 'Datapoints' not in data or not data['Datapoints']:
        return

    for point in data['Datapoints']:
        if 'Average' in point:
            point['Average'] = point['Average'] / (1024 * 1024 * 1024)
        if 'Minimum' in point:
            point['Minimum'] = point['Minimum'] / (1024 * 1024 * 1024)
        if 'Maximum' in point:
            point['Maximum'] = point['Maximum'] / (1024 * 1024 * 1024)

def process_metric_data(metric_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process metric data for report generation"""
    if not metric_data or 'Datapoints' not in metric_data or not metric_data['Datapoints']:
        return {
            'timestamps': [],
            'values': [],
            'average': 0,
            'min': 0,
            'max': 0
        }

    datapoints = sorted(metric_data['Datapoints'], key=lambda x: x['Timestamp'])

    timestamps = [point['Timestamp'] for point in datapoints]
    values = [point.get('Average', 0) for point in datapoints]

    avg_value = sum(values) / len(values) if values else 0
    min_value = min(values) if values else 0
    max_value = max(values) if values else 0

    return {
        'timestamps': timestamps,
        'values': values,
        'average': avg_value,
        'min': min_value,
        'max': max_value
    }

def get_instance_metrics(aws_access_key: str, aws_secret_key: str, 
                        resource_list: List[str], period_days: int) -> List[Dict[str, Any]]:
    """Get metrics for the selected EC2 and RDS instances."""
    logger.info(f"Getting metrics with period: {period_days} days")
    if not aws_access_key or not aws_secret_key:
        logger.error("AWS credentials are missing")
        raise ValueError("AWS credentials are required")

    metrics_data = []

    # Limit resources only for weekly reports to prevent timeout
    if period_days > 1 and len(resource_list) > 5:
        logger.warning(f"Limiting weekly resources from {len(resource_list)} to 5 to prevent timeout")
        resource_list = resource_list[:5]
    
    logger.info(f"Processing {len(resource_list)} resources for {'weekly' if period_days > 1 else 'daily'} report")

    for resource in resource_list:
        try:
            parts = resource.split('|')
            if len(parts) != 3:
                # Try to infer the format if possible (for backward compatibility)
                if len(parts) == 1:
                    # This is just an instance ID, try to determine if it's EC2 or RDS
                    resource_id = parts[0]
                    if resource_id.startswith('i-'):
                        # Most likely an EC2 instance
                        service_type = 'EC2'
                        instance_id = resource_id
                        region = 'us-east-1'  # Default to us-east-1
                        logger.warning(f"Resource format inferred for {resource_id} as EC2 in us-east-1")
                    else:
                        # Assume it's RDS
                        service_type = 'RDS' 
                        instance_id = resource_id
                        region = 'us-east-1'  # Default to us-east-1
                        logger.warning(f"Resource format inferred for {resource_id} as RDS in us-east-1")
                else:
                    logger.error(f"Invalid resource format: {resource}")
                    continue
            else:
                service_type, instance_id, region = parts

            logger.info(f"Processing {service_type} resource: {instance_id} in {region}")

            if service_type == 'EC2':
                instance_info = get_ec2_metrics(aws_access_key, aws_secret_key, instance_id, region, period_days)
                if instance_info:
                    # Convert to the format expected by the report generator
                    processed_result = {
                        'id': instance_id,
                        'name': instance_info['name'],
                        'type': instance_info['type'],
                        'state': instance_info['state'],
                        'os': instance_info.get('os', 'Unknown'),
                        'region': region,
                        'service_type': 'EC2',
                        'metrics': {}
                    }

                    # Process CPU metrics
                    if 'cpu' in instance_info and instance_info['cpu']['Datapoints']:
                        processed_result['metrics']['cpu'] = process_metric_data(instance_info['cpu'])

                    # Process memory metrics
                    if 'memory' in instance_info and instance_info['memory']['Datapoints']:
                        processed_result['metrics']['memory'] = process_metric_data(instance_info['memory'])

                    # Process disk metrics
                    if 'disk_metrics' in instance_info:
                        disk_metrics_processed = {}
                        for disk_name, disk_data in instance_info['disk_metrics'].items():
                            if disk_data and disk_data.get('Datapoints'):
                                disk_metrics_processed[disk_name] = process_metric_data(disk_data)

                        # Add processed disk metrics to the result
                        if disk_metrics_processed:
                            processed_result['metrics']['disk_metrics'] = disk_metrics_processed

                        # Also add the main disk metric for compatibility
                        if 'disk' in instance_info['disk_metrics'] and instance_info['disk_metrics']['disk'].get('Datapoints'):
                            processed_result['metrics']['disk'] = process_metric_data(instance_info['disk_metrics']['disk'])

                    metrics_data.append(processed_result)

            elif service_type == 'RDS':
                result = get_rds_metrics(aws_access_key, aws_secret_key, instance_id, region, period_days)
                if result:
                    # Convert to format expected by report generator
                    processed_result = {
                        'id': result['id'],
                        'name': result['name'],
                        'type': result['type'],
                        'state': result.get('status', 'Unknown'),
                        'engine': result.get('engine', 'Unknown'),
                        'region': result['region'],
                        'service_type': 'RDS',
                        'metrics': {}
                    }

                    # Process CPU metrics
                    if 'cpu' in result and result['cpu']['Datapoints']:
                        processed_result['metrics']['cpu'] = process_metric_data(result['cpu'])

                    # Process memory metrics (convert bytes to GB)
                    if 'memory' in result and result['memory']['Datapoints']:
                        convert_bytes_to_gb(result['memory'])
                        processed_result['metrics']['memory'] = process_metric_data(result['memory'])

                    # Process disk metrics (convert bytes to GB)
                    if 'disk' in result and result['disk']['Datapoints']:
                        convert_bytes_to_gb(result['disk'])
                        processed_result['metrics']['disk'] = process_metric_data(result['disk'])

                    metrics_data.append(processed_result)
            else:
                logger.warning(f"Unknown service type: {service_type}")

        except Exception as e:
            logger.error(f"Failed to get metrics for {resource}: {str(e)}")
            continue

    return metrics_data