import boto3
import json
import logging
import calendar
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Organization credentials and configuration

ORG_ACCESS_KEY = "AKIAX6EIDDRONWPONNOD"
ORG_SECRET_KEY = "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"
ORG_REGION = "ap-south-1"
SSM_PREFIX = "/myorg/creds/"

def get_org_ssm_client():
    """Create SSM client using organization credentials."""
    try:
        return boto3.client(
            'ssm',
            aws_access_key_id=ORG_ACCESS_KEY,
            aws_secret_access_key=ORG_SECRET_KEY,
            region_name=ORG_REGION
        )
    except Exception as e:
        logger.error(f"Failed to create organization SSM client: {str(e)}")
        raise

def get_nubinix_clients() -> List[str]:
    """Get simple list of Nubinix client names from organization SSM."""
    try:
        clients_data = fetch_nubinix_clients()
        return [client['id'] for client in clients_data]
    except Exception as e:
        logger.error(f"Error getting client names: {str(e)}")
        return []

def fetch_nubinix_clients() -> List[Dict[str, Any]]:
    """Fetch list of clients from organization SSM parameter store."""
    try:
        ssm = get_org_ssm_client()
        clients = []
        next_token = None

        while True:
            params = {
                'Path': SSM_PREFIX,
                'Recursive': True,
                'WithDecryption': True
            }
            if next_token:
                params['NextToken'] = next_token

            response = ssm.get_parameters_by_path(**params)

            # Extract unique client names from parameter paths
            for param in response['Parameters']:
                parts = param['Name'].split('/')
                if len(parts) >= 4:
                    client_name = parts[3]
                    if not any(c['id'] == client_name for c in clients):
                        clients.append({
                            'id': client_name,
                            'name': client_name.title().replace('_', ' ')
                        })

            next_token = response.get('NextToken')
            if not next_token:
                break

        logger.info(f"Found {len(clients)} clients in organization SSM")
        return clients

    except Exception as e:
        logger.error(f"Failed to fetch clients from SSM: {str(e)}")
        return []

def get_credentials_for_client(client_name: str) -> Optional[Dict[str, str]]:
    """Get credentials for a specific client, simplified format."""
    try:
        creds = fetch_client_credentials(client_name, 'aws')
        if creds:
            return {
                'access_key': creds['accessKeyId'],
                'secret_key': creds['secretAccessKey'],
                'region': creds.get('region', 'us-east-1')
            }
        return None
    except Exception as e:
        logger.error(f"Error getting credentials for {client_name}: {str(e)}")
        return None

def fetch_client_credentials(client_id: str, cloud_provider: str = 'aws') -> Optional[Dict[str, str]]:
    """Fetch credentials for a specific client from organization SSM."""
    try:
        ssm = get_org_ssm_client()
        creds = {}

        # Fetch the required credential components (access_key and secret_key are required)
        required_keys = ['access_key', 'secret_key']
        optional_keys = ['region']

        # Get required parameters
        for key in required_keys:
            param_name = f"{SSM_PREFIX}{client_id}/{key}"
            try:
                response = ssm.get_parameter(Name=param_name, WithDecryption=True)
                creds[key] = response['Parameter']['Value']
            except ClientError as e:
                logger.error(f"Could not fetch required parameter {key} for {client_id}: {e}")
                return None

        # Get optional parameters with defaults
        for key in optional_keys:
            param_name = f"{SSM_PREFIX}{client_id}/{key}"
            try:
                response = ssm.get_parameter(Name=param_name, WithDecryption=True)
                creds[key] = response['Parameter']['Value']
            except ClientError:
                # Use default region if not found
                if key == 'region':
                    creds[key] = 'us-east-1'
                    logger.info(f"Using default region us-east-1 for {client_id}")

        # Map to the expected format
        credentials = {
            'accessKeyId': creds['access_key'],
            'secretAccessKey': creds['secret_key'],
            'region': creds.get('region', 'us-east-1')
        }

        logger.info(f"Successfully fetched credentials for client {client_id}")
        return credentials

    except Exception as e:
        logger.error(f"Failed to fetch credentials for {client_id}: {str(e)}")
        return None

def validate_ssm_access() -> bool:
    """Validate that we can access SSM with organization credentials."""
    try:
        ssm = get_org_ssm_client()

        # Try to list parameters in the organization prefix
        response = ssm.describe_parameters(
            ParameterFilters=[
                {
                    'Key': 'Name',
                    'Option': 'BeginsWith',
                    'Values': [SSM_PREFIX]
                }
            ],
            MaxResults=1
        )

        has_access = len(response.get('Parameters', [])) > 0
        logger.info(f"SSM access validation: {'SUCCESS' if has_access else 'FAILED'}")
        return has_access

    except Exception as e:
        logger.error(f"SSM access validation failed: {str(e)}")
        return False

def get_client_billing_data(client_creds: Dict[str, str], month: int, year: int, frequency: str = 'monthly') -> Optional[Dict[str, Any]]:
    """Fetch billing data for a client using Cost Explorer API."""
    try:
        # Ensure month and year are integers
        month = int(month)
        year = int(year)

        # Set the time period for the month
        start_date = f'{year}-{month:02d}-01'
        if month == 12:
            end_date = f'{year + 1}-01-01'
        else:
            end_date = f'{year}-{month + 1:02d}-01'

        # Set granularity based on frequency (AWS only supports MONTHLY, DAILY, or HOURLY)
        granularity = 'DAILY' if frequency == 'daily' else 'MONTHLY'

        # Create Cost Explorer client (CE is only available in us-east-1)
        ce_client = boto3.client(
            'ce',
            aws_access_key_id=client_creds['accessKeyId'],
            aws_secret_access_key=client_creds['secretAccessKey'],
            region_name='us-east-1'
        )

        logger.info(f"Fetching billing data from {start_date} to {end_date}")

        # Get cost and usage data with service breakdown
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity=granularity,
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )

        # Process billing data
        services = []
        total_cost = 0.0

        if response.get('ResultsByTime') and len(response['ResultsByTime']) > 0:
            for group in response['ResultsByTime'][0]['Groups']:
                service = group['Keys'][0]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                total_cost += amount

                if amount > 0:  # Only include services with actual costs
                    services.append({
                        'service': service,
                        'amount': amount
                    })

        # Sort by cost (highest first)
        services.sort(key=lambda x: x['amount'], reverse=True)

        return {
            'services': services,
            'total_cost': total_cost,
            'period': f"{start_date} to {end_date}",
            'billing_period': f"{calendar.month_name[month]} {year}",
            'start_date': start_date,
            'end_date': end_date
        }

    except ClientError as e:
        logger.error(f"Failed to fetch billing data: {e}")
        return None