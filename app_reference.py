#!/usr/bin/env python3
from flask import Flask, request, send_file, jsonify
import logging
import os
import sys
import json
import tempfile
import argparse
from datetime import datetime, timedelta

from aws_utils import get_instance_metrics
from azure_utils import get_azure_metrics
from report_generator import generate_pdf_report

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'cloud-report-generator'})

@app.route('/generate-report', methods=['POST'])
def generate_report():
    try:
        # Parse request data
        data = request.json
        
        # Extract required parameters
        cloud_provider = data.get('cloudProvider', 'AWS')
        report_type = data.get('reportType', 'utilization')
        resources = data.get('resources', [])
        
        if cloud_provider.upper() == 'AWS':
            credentials = data.get('credentials', {})
            aws_access_key = credentials.get('accessKeyId')
            aws_secret_key = credentials.get('secretAccessKey')
            # Try to get accountName from multiple potential locations
            account_name = data.get('accountName', 
                             credentials.get('accountName', 
                                 data.get('name', 'AWS Account')))
            
            # Validate inputs
            if not aws_access_key or not aws_secret_key:
                return jsonify({'error': 'AWS credentials are required'}), 400
            
            if not resources and report_type == 'utilization':
                return jsonify({'error': 'At least one resource must be selected for utilization reports'}), 400
            
            if report_type == 'utilization':
                frequency = data.get('frequency', 'daily')
                period_days = 1 if frequency == 'daily' else 7
                
                # Get metrics data for selected resources
                logger.info(f"Fetching AWS metrics for {len(resources)} resources")
                metrics_data = get_instance_metrics(aws_access_key, aws_secret_key, resources, period_days)
                
                if not metrics_data:
                    return jsonify({'error': 'Failed to get metrics data'}), 500
                
                # Generate the PDF report
                logger.info("Generating PDF report")
                pdf_data = generate_pdf_report(account_name, metrics_data, cloud_provider, report_type)
            
            else:  # billing report
                month = data.get('month', datetime.now().month)
                year = data.get('year', datetime.now().year)
                
                # Generate billing report
                logger.info(f"Generating AWS billing report for {month}/{year}")
                # Stub for billing report - would use AWS Cost Explorer API in a real implementation
                pdf_data = generate_pdf_report(account_name, [], cloud_provider, report_type, month=month, year=year)
                
        elif cloud_provider.upper() == 'AZURE':
            credentials = data.get('credentials', {})
            client_id = credentials.get('clientId')
            client_secret = credentials.get('clientSecret')
            tenant_id = credentials.get('tenantId')
            subscription_id = credentials.get('subscriptionId')
            # Try to get accountName from multiple potential locations
            account_name = data.get('accountName', 
                             credentials.get('accountName', 
                                 data.get('name', 'Azure Account')))
            
            # Validate inputs
            if not client_id or not client_secret or not tenant_id or not subscription_id:
                return jsonify({'error': 'Azure credentials are required'}), 400
            
            if not resources and report_type == 'utilization':
                return jsonify({'error': 'At least one resource must be selected for utilization reports'}), 400
            
            if report_type == 'utilization':
                frequency = data.get('frequency', 'daily')
                period_days = 1 if frequency == 'daily' else 7
                
                # Get metrics data for selected resources
                logger.info(f"Fetching Azure metrics for {len(resources)} resources")
                metrics_data = get_azure_metrics(client_id, client_secret, tenant_id, subscription_id, resources, period_days)
                
                if not metrics_data:
                    return jsonify({'error': 'Failed to get metrics data'}), 500
                
                # Generate the PDF report
                logger.info("Generating PDF report")
                pdf_data = generate_pdf_report(account_name, metrics_data, cloud_provider, report_type)
            
            else:  # billing report
                month = data.get('month', datetime.now().month)
                year = data.get('year', datetime.now().year)
                
                # Generate billing report
                logger.info(f"Generating Azure billing report for {month}/{year}")
                # Stub for billing report - would use Azure Cost Management API in a real implementation
                pdf_data = generate_pdf_report(account_name, [], cloud_provider, report_type, month=month, year=year)
        else:
            return jsonify({'error': f'Unsupported cloud provider: {cloud_provider}'}), 400
            
        # Create a temporary file to store the PDF
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(temp_fd)
        
        with open(temp_path, 'wb') as f:
            f.write(pdf_data)
        
        # Generate the report filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{cloud_provider.lower()}_{report_type}_report_{timestamp}.pdf"
        
        # Return the PDF file
        return send_file(
            temp_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename,
            # Clean up the temp file after sending
            attachment_filename=filename
        )
    
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return jsonify({'error': f'Failed to generate report: {str(e)}'}), 500

def process_command_line():
    parser = argparse.ArgumentParser(description='Cloud Report Generator')
    parser.add_argument('--params', type=str, help='Path to parameters JSON file')
    parser.add_argument('--output', type=str, help='Path for output PDF')
    parser.add_argument('--test', action='store_true', help='Test the Python backend')
    
    args = parser.parse_args()
    
    if args.test:
        print(json.dumps({"status": "running", "service": "cloud-report-generator"}))
        return
    
    if args.params and args.output:
        try:
            with open(args.params, 'r') as f:
                params = json.load(f)
            
            cloud_provider = params.get('cloudProvider', 'AWS')
            report_type = params.get('reportType', 'utilization')
            resources = params.get('resources', [])
            
            if cloud_provider.upper() == 'AWS':
                credentials = params.get('credentials', {})
                aws_access_key = credentials.get('accessKeyId')
                aws_secret_key = credentials.get('secretAccessKey')
                # Try to get accountName from multiple potential locations
                account_name = params.get('accountName', 
                                  credentials.get('accountName', 
                                      'AWS Account'))
                
                if report_type == 'utilization':
                    frequency = params.get('frequency', 'daily')
                    period_days = 1 if frequency == 'daily' else 7
                    
                    metrics_data = get_instance_metrics(aws_access_key, aws_secret_key, resources, period_days)
                    pdf_data = generate_pdf_report(account_name, metrics_data, cloud_provider, report_type)
                else:
                    month = params.get('month', datetime.now().month)
                    year = params.get('year', datetime.now().year)
                    pdf_data = generate_pdf_report(account_name, [], cloud_provider, report_type, month=month, year=year)
            else:
                credentials = params.get('credentials', {})
                client_id = credentials.get('clientId')
                client_secret = credentials.get('clientSecret')
                tenant_id = credentials.get('tenantId')
                subscription_id = credentials.get('subscriptionId')
                # Try to get accountName from multiple potential locations
                account_name = params.get('accountName',
                                  credentials.get('accountName',
                                      'Azure Account'))
                
                if report_type == 'utilization':
                    frequency = params.get('frequency', 'daily')
                    period_days = 1 if frequency == 'daily' else 7
                    
                    metrics_data = get_azure_metrics(client_id, client_secret, tenant_id, subscription_id, resources, period_days)
                    pdf_data = generate_pdf_report(account_name, metrics_data, cloud_provider, report_type)
                else:
                    month = params.get('month', datetime.now().month)
                    year = params.get('year', datetime.now().year)
                    pdf_data = generate_pdf_report(account_name, [], cloud_provider, report_type, month=month, year=year)
            
            with open(args.output, 'wb') as f:
                f.write(pdf_data)
            
            print(f"Report successfully generated: {args.output}")
        except Exception as e:
            print(f"Error generating report: {str(e)}")
            exit(1)

if __name__ == '__main__':
    # Check if run with command line arguments
    if len(sys.argv) > 1:
        process_command_line()
    else:
        # Run as web service
        app.run(host='0.0.0.0', port=8000, debug=True)
