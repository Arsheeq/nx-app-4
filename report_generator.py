import io
import os
import logging
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.units import inch
from datetime import datetime
import pytz
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_chart(timestamps, values, metric_name, instance_name, avg, min_val, max_val):
    """Create a chart for the metric and return as bytes."""
    try:
        plt.figure(figsize=(10, 4))

        # Plot the data with a bright, highlighted color
        plt.plot(timestamps, values, color='#FF0066', linewidth=2.5, 
                 marker='o', markersize=3, markerfacecolor='#FF0066', 
                 label='Average', alpha=0.9)

        # Add average line
        plt.axhline(y=avg, color='#FF0066', linestyle='-', alpha=0.5, label='Average')

        # Format x-axis to show dates
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=pytz.UTC))
        plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=3))

        # Add grid
        plt.grid(True, linestyle='--', alpha=0.7)

        # Set labels and title
        plt.xlabel('Time', fontweight='bold')

        # Check if the metric is memory or disk (where we use GB)
        if 'gb' in metric_name.lower() or any(word in metric_name.lower() for word in ['memory', 'disk']):
            unit = 'GB'
            plt.ylabel(f"{metric_name} ({unit})", fontweight='bold')
        else:
            unit = 'Percent'
            plt.ylabel(f"{metric_name} ({unit})", fontweight='bold')

        # Find the start and end times from the available timestamps
        if timestamps:
            start_time = min(timestamps)
            end_time = max(timestamps)

            # Format the time span in the title
            start_str = start_time.strftime('%Y-%m-%d %H:%M')
            end_str = end_time.strftime('%Y-%m-%d %H:%M')
            plt.title(f'{instance_name}: {metric_name}\n{start_str} to {end_str}', fontweight='bold')

            # Set explicit x-axis range based on the data
            plt.xlim(start_time, end_time)
        else:
            plt.title(f'{instance_name}: {metric_name}\nNo data available', fontweight='bold')

        # Add legend
        plt.legend(loc='upper right', frameon=True)

        # Add statistics
        if unit == 'Percent':
            stats_text = f"Min: {min_val:.2f}% | Max: {max_val:.2f}% | Avg: {avg:.2f}%"
        else:
            stats_text = f"Min: {min_val:.2f} GB | Max: {max_val:.2f} GB | Avg: {avg:.2f} GB"
        plt.figtext(0.5, 0.01, stats_text, ha='center', fontsize=10, fontweight='bold')

        # Tight layout to maximize graph area
        plt.tight_layout()

        # Save plot to bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)

        return buf.getvalue()
    except Exception as e:
        logger.error(f"Error creating chart: {str(e)}")
        # Create error chart
        plt.figure(figsize=(10, 4))
        plt.text(0.5, 0.5, f'Error creating chart: {str(e)}', horizontalalignment='center', verticalalignment='center')
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        plt.close()
        buf.seek(0)

        return buf.getvalue()

def wrap_table_data(data):
    """Helper function to wrap table data cells as paragraphs for better formatting"""
    wrapped_data = []
    styles = getSampleStyleSheet()

    for row in data:
        wrapped_row = []
        for cell in row:
            if not isinstance(cell, Paragraph):
                wrapped_row.append(Paragraph(str(cell), styles['Normal']))
            else:
                wrapped_row.append(cell)
        wrapped_data.append(wrapped_row)

    return wrapped_data

def create_utilization_report(doc, elements, account_name, metrics_data, cloud_provider):
    """Create utilization report content"""
    styles = getSampleStyleSheet()

    # Define custom styles
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Title'],
        fontSize=18,
        alignment=1,  # Center alignment
        spaceAfter=0.2*inch
    )

    header_style = ParagraphStyle(
        name='HeaderStyle',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=0.1*inch
    )

    subheader_style = ParagraphStyle(
        name='SubHeaderStyle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=0.1*inch
    )

    label_style = ParagraphStyle(
        name='LabelStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceBefore=0.1*inch,
        spaceAfter=0.05*inch,
        fontName='Helvetica-Bold'
    )

    remark_style = ParagraphStyle(
        name='RemarkStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=0.1*inch,
        fontName='Helvetica-Oblique'
    )

    # Cover page
    elements.append(Paragraph(f"{cloud_provider.upper()} UTILIZATION<br/>REPORT", title_style))
    elements.append(Spacer(1, 0.2*inch))

    # Add report information table
    report_data = [
        ["Account", account_name],
        ["Report", "Resource Utilization"],
        ["Date", datetime.now().strftime("%Y-%m-%d")]
    ]

    report_table = Table(wrap_table_data(report_data), colWidths=[1.5*inch, 3*inch])
    report_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6)
    ]))

    elements.append(report_table)
    elements.append(Spacer(1, 0.4*inch))

    # Group metrics by service type
    service_types = {}
    for resource in metrics_data:
        service_type = resource.get('service_type', 'Unknown')
        if service_type not in service_types:
            service_types[service_type] = []
        service_types[service_type].append(resource)

    # Add resources summary
    for service_type, resources in service_types.items():
        elements.append(Paragraph(f"{service_type} Resources Covered in Report:", header_style))
        elements.append(Spacer(1, 0.2*inch))

        # Create a table for instance summary based on service type
        if service_type in ['EC2', 'VM']:
            summary_data = [["Instance ID", "Name", "Type", "Status"]]
            for resource in resources:
                summary_data.append([
                    resource['id'],
                    resource['name'],
                    resource['type'],
                    resource['state']
                ])
        else:  # RDS or Database
            summary_data = [["Instance Name", "Type", "Status", "Engine"]]
            for resource in resources:
                summary_data.append([
                    resource['id'],
                    resource['type'],
                    resource['state'],
                    resource.get('engine', 'Unknown')
                ])

        # Create and add the summary table
        summary_table = Table(wrap_table_data(summary_data), colWidths=[1.59*inch, 3*inch, 1.5*inch, 1*inch])
        summary_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(summary_table)
        elements.append(Spacer(1, 0.4*inch))

    # Process each resource
    for resource in metrics_data:
        # Start a new page for each resource
        elements.append(PageBreak())

        service_type = resource.get('service_type', 'Unknown')

        if service_type in ['EC2', 'VM']:
            # Add instance details
            elements.append(Paragraph(f"Host: {resource['name']}", header_style))
            elements.append(Spacer(1, 0.1*inch))

            # Host information
            host_info_data = [
                ["Instance ID", resource['id']],
                ["Type", resource['type']],
                ["Operating System", resource.get('platform', 'Unknown')],
                ["State", resource['state']]
            ]

            host_info_table = Table(wrap_table_data(host_info_data), colWidths=[1.5*inch, 4*inch])
            host_info_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (0, -1), colors.white),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6)
            ]))

            elements.append(host_info_table)
            elements.append(Spacer(1, 0.3*inch))
        else:
            # Add database instance details
            elements.append(Paragraph(f"Database: {resource['name']}", header_style))
            elements.append(Spacer(1, 0.1*inch))

            # Database information
            db_info_data = [
                ["Instance ID", resource['id']],
                ["Type", resource['type']],
                ["Engine", resource.get('engine', 'Unknown')],
                ["State", resource['state']]
            ]

            db_info_table = Table(wrap_table_data(db_info_data), colWidths=[1.5*inch, 4*inch])
            db_info_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (0, -1), colors.white),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6)
            ]))

            elements.append(db_info_table)
            elements.append(Spacer(1, 0.3*inch))

        # Check if resource has metrics
        if 'metrics' in resource:
            # Process CPU metrics
            if 'cpu' in resource['metrics']:
                cpu_data = resource['metrics']['cpu']

                if cpu_data.get('timestamps'):
                    # CPU utilization title
                    elements.append(Paragraph("CPU UTILIZATION", label_style))

                    # Add remarks about CPU utilization
                    avg_val = cpu_data['average']

                    if avg_val > 85:
                        remarks = "Average utilisation is high. Explore possibility of optimising the resources."
                    else:
                        remarks = "Average utilisation is normal. No action needed at the time."

                    elements.append(Paragraph(f"Remarks: {remarks}", remark_style))

                    # Create and add CPU chart
                    cpu_chart = create_chart(
                        cpu_data['timestamps'],
                        cpu_data['values'],
                        "CPU Utilization",
                        resource['name'],
                        cpu_data['average'],
                        cpu_data['min'],
                        cpu_data['max']
                    )

                    elements.append(Image(io.BytesIO(cpu_chart), width=6.5*inch, height=3*inch))
                    elements.append(Spacer(1, 0.2*inch))

            # Process Memory metrics
            if 'memory' in resource['metrics']:
                memory_data = resource['metrics']['memory']

                if memory_data.get('timestamps'):
                    # Memory utilization title
                    elements.append(Paragraph("MEMORY UTILIZATION", label_style))

                    # Add remarks about memory utilization
                    avg_val = memory_data['average']

                    if 'GB' in str(avg_val):  # This is for RDS instances where memory is reported in GB
                        if avg_val < 1:
                            remarks = "Memory availability is low. Consider upgrading the instance."
                        else:
                            remarks = "Memory availability is normal."
                    else:
                        if avg_val > 90:
                            remarks = "Memory utilization is high. Consider upgrading the instance."
                        else:
                            remarks = "Memory utilization is normal."

                    elements.append(Paragraph(f"Remarks: {remarks}", remark_style))

                    # Create and add Memory chart
                    memory_chart = create_chart(
                        memory_data['timestamps'],
                        memory_data['values'],
                        "Memory Utilization",
                        resource['name'],
                        memory_data['average'],
                        memory_data['min'],
                        memory_data['max']
                    )

                    elements.append(Image(io.BytesIO(memory_chart), width=6.5*inch, height=3*inch))
                    elements.append(Spacer(1, 0.2*inch))

            # Process Disk metrics
            if 'disk' in resource['metrics']:
                disk_data = resource['metrics']['disk']

                if disk_data.get('timestamps'):
                    # Disk utilization title
                    elements.append(Paragraph("DISK UTILIZATION", label_style))

                    # Add remarks about disk utilization
                    avg_val = disk_data['average']

                    if 'GB' in str(avg_val):  # This is for RDS instances where disk is reported in GB
                        if avg_val < 5:
                            remarks = "Storage availability is low. Consider increasing storage."
                        else:
                            remarks = "Storage availability is normal."
                    else:
                        if avg_val > 85:
                            remarks = "Disk utilization is high. Consider increasing storage."
                        else:
                            remarks = "Disk utilization is normal."

                    elements.append(Paragraph(f"Remarks: {remarks}", remark_style))

                    # Create and add Disk chart
                    disk_chart = create_chart(
                        disk_data['timestamps'],
                        disk_data['values'],
                        "Disk Utilization",
                        resource['name'],
                        disk_data['average'],
                        disk_data['min'],
                        disk_data['max']
                    )

                    elements.append(Image(io.BytesIO(disk_chart), width=6.5*inch, height=3*inch))
                    elements.append(Spacer(1, 0.2*inch))

def create_billing_report(doc, elements, account_name, cloud_provider, month, year, billing_data=None):
    """Create billing report content with real billing data"""
    styles = getSampleStyleSheet()
    
    # Define custom styles for professional appearance
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Title'],
        fontSize=20,
        alignment=1,  # Center alignment
        spaceAfter=0.3*inch,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        name='HeaderStyle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=0.15*inch,
        textColor=colors.HexColor('#34495e'),
        fontName='Helvetica-Bold'
    )
    
    detail_style = ParagraphStyle(
        name='DetailStyle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=0.1*inch,
        fontName='Helvetica'
    )
    
    total_style = ParagraphStyle(
        name='TotalStyle',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=0.1*inch,
        textColor=colors.HexColor('#e74c3c'),
        fontName='Helvetica-Bold',
        alignment=2  # Right alignment
    )
    
    month_name = datetime(year, month, 1).strftime('%B')
    
    # Cover page with professional styling
    elements.append(Paragraph(f"{cloud_provider.upper()} BILLING REPORT", title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Add report information table with professional styling
    report_info_data = [
        ["Client", account_name],
        ["Report Type", "Billing Report"],
        ["Billing Period", f"{month_name} {year}"],
        ["Report Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["Currency", "USD"]
    ]
    
    report_table = Table(wrap_table_data(report_info_data), colWidths=[2*inch, 3.5*inch])
    report_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('FONTSIZE', (0, 0), (-1, -1), 11)
    ]))
    
    elements.append(report_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # Process billing data if provided
    if billing_data and 'services' in billing_data:
        total_cost = billing_data.get('total_cost', 0)
        
        # Add billing summary with total cost prominently displayed
        elements.append(Paragraph("Billing Summary", header_style))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph(f"Total Cost: ${total_cost:.2f}", total_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Service breakdown table with professional styling
        elements.append(Paragraph("Service Breakdown", header_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Prepare table data
        table_data = [['Service', 'Cost (USD)', 'Percentage']]
        
        # Separate Tax items from other services for better organization
        tax_items = []
        regular_services = []
        
        for service_data in billing_data['services']:
            service = service_data['service']
            amount = service_data['amount']
            percentage = (amount / total_cost * 100) if total_cost > 0 else 0
            
            service_row = [
                service,
                f"${amount:.2f}",
                f"{percentage:.1f}%"
            ]
            
            if 'tax' in service.lower():
                tax_items.append(service_row)
            else:
                regular_services.append(service_row)
        
        # Sort regular services by cost (highest first)
        regular_services.sort(key=lambda x: float(x[1].replace('$', '')), reverse=True)
        
        # Add services to table
        table_data.extend(regular_services)
        
        # Add separator line for taxes if any tax items exist
        if tax_items:
            table_data.append(['', '', ''])  # Empty row as separator
            table_data.extend(tax_items)
        
        # Add total row
        table_data.append(['TOTAL', f"${total_cost:.2f}", '100.0%'])
        
        # Create table with professional styling
        service_table = Table(wrap_table_data(table_data), colWidths=[3.5*inch, 1.5*inch, 1*inch])
        service_table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows styling
            ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f8f9fa')),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 10),
            ('LEFTPADDING', (0, 1), (-1, -2), 8),
            ('RIGHTPADDING', (0, 1), (-1, -2), 8),
            ('TOPPADDING', (0, 1), (-1, -2), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -2), 6),
            
            # Total row styling
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('TOPPADDING', (0, -1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
            
            # Borders and grid
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2c3e50')),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#3498db')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternating row colors for better readability
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        
        elements.append(service_table)
        elements.append(Spacer(1, 0.4*inch))
        
        # Add cost analysis section
        elements.append(Paragraph("Cost Analysis", header_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # Find top 3 services by cost
        top_services = sorted(regular_services, key=lambda x: float(x[1].replace('$', '')), reverse=True)[:3]
        
        if top_services:
            analysis_text = f"Your top 3 cost centers for {month_name} {year} are:<br/><br/>"
            for i, service in enumerate(top_services, 1):
                analysis_text += f"{i}. {service[0]}: {service[1]} ({service[2]})<br/>"
            
            elements.append(Paragraph(analysis_text, detail_style))
        
    else:
        # Fallback if no billing data is provided
        elements.append(Paragraph("Billing Summary", header_style))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph(
            "No billing data available for the selected period. This may be due to:",
            detail_style
        ))
        
        reasons = [
            "• No charges incurred during this billing period",
            "• Insufficient permissions to access AWS Cost Explorer data",
            "• Billing data not yet available (reports typically have a 24-48 hour delay)",
            "• Selected time period is outside available billing data range"
        ]
        
        for reason in reasons:
            elements.append(Paragraph(reason, detail_style))
    
    elements.append(Spacer(1, 0.4*inch))
    
    # Add footer with disclaimer
    footer_text = """
    <para align="center">
    <font size="9" color="#7f8c8d">
    This report was automatically generated from AWS Cost Explorer data.<br/>
    All costs are in USD and represent unblended costs for the specified billing period.<br/>
    Data is typically updated within 24-48 hours after the end of each day.
    </font>
    </para>
    """
    elements.append(Paragraph(footer_text, styles['Normal']))

def generate_pdf_report(account_name, metrics_data=None, cloud_provider='AWS', 
                       report_type='utilization', month=None, year=None, billing_data=None):
    """Generate a PDF report with metrics data or billing information."""
    logger.info("Generating PDF report...")
    
    # Create a buffer for the PDF
    buffer = io.BytesIO()
    
    # Define header function for all pages
    def header(canvas, doc):
        canvas.saveState()
        # Draw border around page
        canvas.rect(doc.leftMargin - 10, doc.bottomMargin - 10,
                   doc.width + 20, doc.height + 20)
        
        # Add website URL on the left
        canvas.setFont('Helvetica', 8)
        canvas.drawString(doc.leftMargin, doc.height + doc.topMargin - 12, "www.nubinix.com")
        
        # Add logo on the right
        logo_path = os.path.join(os.getcwd(), 'public', 'nubinix-icon.png')
        if os.path.exists(logo_path):
            canvas.drawImage(logo_path, doc.width + doc.leftMargin - 60, 
                           doc.height + doc.topMargin - 40, width=40, height=40)
        canvas.restoreState()
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.8*inch,  # Increased top margin for header
        bottomMargin=0.5*inch
    )
    
    # Initialize the list of flowables
    elements = []
    
    # Create appropriate report content based on report type
    if report_type == 'utilization':
        create_utilization_report(doc, elements, account_name, metrics_data, cloud_provider)
    else:  # billing report
        # For billing reports, metrics_data actually contains billing_data
        create_billing_report(doc, elements, account_name, cloud_provider, month, year, billing_data)
    
    # Build the PDF document with header template
    doc.build(elements, onFirstPage=header, onLaterPages=header)
    
    # Get the PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

def generate_comprehensive_report(client_name: str, cloud_provider: str, report_type: str,
                                credentials: Dict[str, str], resources: List[str] = None,
                                frequency: str = 'daily') -> bytes:
    """Generate a comprehensive report based on the request parameters."""
    logger.info(f"Generating {report_type} report for {client_name}")
    
    if report_type == 'utilization':
        # Import AWS utilities
        from aws_utils import get_instance_metrics
        
        # Convert frequency to period days
        period_days = 1 if frequency == 'daily' else 7
        
        # Get metrics for the selected resources
        metrics_data = []
        if resources:
            for resource in resources:
                # Parse resource format if needed (assuming format: type|id|region)
                if '|' in resource:
                    resource_type, resource_id, region = resource.split('|')
                else:
                    resource_id = resource
                    region = credentials.get('region', 'us-east-1')
                
                # Get EC2 metrics
                if 'ec2' in resource_id.lower() or 'i-' in resource_id:
                    from aws_utils import get_ec2_metrics
                    metrics = get_ec2_metrics(
                        credentials['access_key'],
                        credentials['secret_key'],
                        resource_id,
                        region,
                        period_days
                    )
                    if metrics:
                        metrics_data.append(metrics)
                
                # Get RDS metrics
                elif 'rds' in resource_id.lower() or 'db-' in resource_id:
                    from aws_utils import get_rds_metrics
                    metrics = get_rds_metrics(
                        credentials['access_key'],
                        credentials['secret_key'],
                        resource_id,
                        region,
                        period_days
                    )
                    if metrics:
                        metrics_data.append(metrics)
        
        # Generate utilization report
        return generate_pdf_report(
            account_name=client_name,
            metrics_data=metrics_data,
            cloud_provider=cloud_provider,
            report_type=report_type
        )
    
    elif report_type == 'billing':
        # Import SSM utilities for billing data
        from ssm_utils import get_client_billing_data
        from datetime import datetime
        
        # Use current month/year if not specified
        now = datetime.now()
        month = now.month
        year = now.year
        
        # Convert credentials to expected format
        billing_creds = {
            'accessKeyId': credentials['access_key'],
            'secretAccessKey': credentials['secret_key']
        }
        
        # Get billing data
        billing_data = get_client_billing_data(billing_creds, month, year)
        
        # Generate billing report
        return generate_pdf_report(
            account_name=client_name,
            cloud_provider=cloud_provider,
            report_type=report_type,
            month=month,
            year=year,
            billing_data=billing_data
        )
    
    else:
        raise ValueError(f"Unsupported report type: {report_type}")