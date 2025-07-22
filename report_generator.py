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
    elements.append(Paragraph(f"CLOUD UTILIZATION<br/>REPORT", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Add report information table
    report_data = [
        ["Account", account_name],
        ["Report", "Resource Utilization"],
        ["Cloud Provider", cloud_provider.upper()],
        ["Account ID", "N/A"],
        ["Date", datetime.now().strftime("%Y-%m-%d")]
    ]
    
    report_table = Table(wrap_table_data(report_data), colWidths=[1.5*inch, 3*inch])
    report_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.white),
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
        service_type = resource.get('service_type', 'EC2')
        if service_type not in service_types:
            service_types[service_type] = []
        service_types[service_type].append(resource)
    
    # Add resources summary
    for service_type, resources in service_types.items():
        if service_type in ['EC2', 'VM']:
            elements.append(Paragraph("Instances Covered in Report:", header_style))
        else:  # RDS or Database
            elements.append(Paragraph("Instances Covered in Report:", header_style))
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
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#87CEEB')),
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
        
        service_type = resource.get('service_type', 'EC2')
        
        if service_type in ['EC2', 'VM']:
            # Add instance details
            elements.append(Paragraph(f"Host: {resource['name']}", header_style))
            elements.append(Spacer(1, 0.1*inch))
            
            # Host information
            host_info_data = [
                ["Instance ID", resource['id']],
                ["Type", resource['type']],
                ["Operating System", resource.get('os', 'Linux')],
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
            elements.append(Paragraph(f"RDS Instance : {resource['name']}", header_style))
            elements.append(Spacer(1, 0.1*inch))
            
            # Database information
            db_info_data = [
                ["Instance ID", resource['id']],
                ["Type", resource['type']],
                ["Status", resource['state']],
                ["Engine", resource.get('engine', 'Unknown')]
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
        
        # Check if resource has metrics (skip if stopped)
        if resource.get('state', '').lower() == 'stopped':
            # Add note for stopped instances
            elements.append(Paragraph("Instance is stopped - no metrics available", label_style))
            elements.append(Spacer(1, 0.2*inch))
        else:
            # Debug: Log what keys are in the resource
            logger.info(f"Resource keys for {resource.get('name', 'unknown')}: {list(resource.keys())}")
            
            # Check if resource has metrics and log the metrics structure
            if 'metrics' in resource:
                logger.info(f"Metrics keys for {resource.get('name', 'unknown')}: {list(resource['metrics'].keys())}")
                
                # Check CPU metrics
                if 'cpu' in resource['metrics']:
                    cpu_data = resource['metrics']['cpu']
                    logger.info(f"CPU data keys for {resource.get('name', 'unknown')}: {list(cpu_data.keys()) if isinstance(cpu_data, dict) else 'Not a dict'}")
                    
                    if cpu_data.get('Datapoints'):
                        # CPU utilization title
                        elements.append(Paragraph("CPU UTILIZATION", label_style))
                        
                        # Add remarks about CPU utilization
                        datapoints = sorted(cpu_data['Datapoints'], key=lambda x: x['Timestamp'])
                        values = [point.get('Average', 0) for point in datapoints]
                        avg_val = sum(values) / len(values) if values else 0
                        
                        if avg_val > 85:
                            remarks = "Average utilisation is high. Explore possibility of optimising the resources."
                        elif avg_val < 15:
                            remarks = "Average utilisation is low. No action needed at the time."
                        else:
                            remarks = "Average utilisation is normal. No action needed at the time."
                        
                        elements.append(Paragraph(f"<i>Remarks: {remarks}</i>", remark_style))
                        elements.append(Spacer(1, 0.1*inch))
                        
                        # Add Average table
                        avg_table_data = [["Average", f"{avg_val:.2f}%"]]
                        avg_table = Table(wrap_table_data(avg_table_data), colWidths=[1.5*inch, 1.5*inch])
                        avg_table.setStyle(TableStyle([
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                            ('BACKGROUND', (0, 0), (0, -1), colors.white),
                            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('PADDING', (0, 0), (-1, -1), 6)
                        ]))
                        elements.append(avg_table)
                        elements.append(Spacer(1, 0.1*inch))
                        
                        # Create and add CPU chart
                        timestamps = [point['Timestamp'] for point in datapoints]
                        min_val = min(values) if values else 0
                        max_val = max(values) if values else 0
                        
                        cpu_chart = create_chart(
                            timestamps,
                            values,
                            "CPU Utilization",
                            resource['name'],
                            avg_val,
                            min_val,
                            max_val
                        )
                        
                        elements.append(Image(io.BytesIO(cpu_chart), width=6*inch, height=2.5*inch))
                        elements.append(Spacer(1, 0.3*inch))
                # Process Memory metrics
                if 'memory' in resource['metrics']:
                    memory_data = resource['metrics']['memory']
                    
                    if memory_data.get('Datapoints'):
                        # Memory utilization title
                        elements.append(Paragraph("MEMORY UTILIZATION", label_style))
                
                        # Add remarks about memory utilization
                        datapoints = sorted(memory_data['Datapoints'], key=lambda x: x['Timestamp'])
                        values = [point.get('Average', 0) for point in datapoints]
                        avg_val = sum(values) / len(values) if values else 0
                        
                        if service_type in ['RDS', 'Database']:
                            # Convert bytes to GB for RDS
                            avg_val_gb = avg_val / (1024 * 1024 * 1024)
                            if avg_val_gb < 1:
                                remarks = "Memory availability is low. Consider upgrading the instance."
                            else:
                                remarks = "Memory availability is normal."
                            display_val = f"{avg_val_gb:.2f} GB"
                        else:
                            if avg_val > 90:
                                remarks = "Memory utilization is high. Consider upgrading the instance."
                            elif avg_val < 50:
                                remarks = "Average utilisation is low. No action needed at the time."
                            else:
                                remarks = "Average utilisation is normal. No action needed at the time."
                            display_val = f"{avg_val:.2f}%"
                        
                        elements.append(Paragraph(f"<i>Remarks: {remarks}</i>", remark_style))
                        elements.append(Spacer(1, 0.1*inch))
                        
                        # Add Average table
                        avg_table_data = [["Average", display_val]]
                        avg_table = Table(wrap_table_data(avg_table_data), colWidths=[1.5*inch, 1.5*inch])
                        avg_table.setStyle(TableStyle([
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                            ('BACKGROUND', (0, 0), (0, -1), colors.white),
                            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('PADDING', (0, 0), (-1, -1), 6)
                        ]))
                        elements.append(avg_table)
                        elements.append(Spacer(1, 0.1*inch))
                        
                        # Create and add Memory chart
                        timestamps = [point['Timestamp'] for point in datapoints]
                        min_val = min(values) if values else 0
                        max_val = max(values) if values else 0
                        
                        memory_chart = create_chart(
                            timestamps,
                            values,
                            "Memory Utilization" if service_type not in ['RDS'] else "Available Memory",
                            resource['name'],
                            avg_val,
                            min_val,
                            max_val
                        )
                        
                        elements.append(Image(io.BytesIO(memory_chart), width=6*inch, height=2.5*inch))
                        elements.append(Spacer(1, 0.3*inch))
        
            # Process Disk metrics
            if 'metrics' in resource and 'disk_metrics' in resource['metrics']:
                disk_metrics = resource['metrics']['disk_metrics']
                for disk_name, disk_data in disk_metrics.items():
                    if disk_data.get('Datapoints'):
                        # Disk utilization title
                        if 'C' in disk_name:
                            elements.append(Paragraph("DISK C FREE PERCENTAGE", label_style))
                        else:
                            elements.append(Paragraph("DISK UTILIZATION", label_style))
                        
                        # Add remarks about disk utilization
                        datapoints = sorted(disk_data['Datapoints'], key=lambda x: x['Timestamp'])
                        values = [point.get('Average', 0) for point in datapoints]
                        avg_val = sum(values) / len(values) if values else 0
                        
                        if avg_val > 85:
                            remarks = "Average Disk utilisation is high. Explore possibility of optimising the resources."
                        elif avg_val < 30:
                            remarks = "Average Disk utilisation is low. No action needed at the time."
                        else:
                            remarks = "Average Disk utilisation is Normal."
                        
                        elements.append(Paragraph(f"<i>Remarks: {remarks}</i>", remark_style))
                        elements.append(Spacer(1, 0.1*inch))
                        
                        # Add Average table
                        avg_table_data = [["Average", f"{avg_val:.2f}%"]]
                        avg_table = Table(wrap_table_data(avg_table_data), colWidths=[1.5*inch, 1.5*inch])
                        avg_table.setStyle(TableStyle([
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                            ('BACKGROUND', (0, 0), (0, -1), colors.white),
                            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('PADDING', (0, 0), (-1, -1), 6)
                        ]))
                        elements.append(avg_table)
                        elements.append(Spacer(1, 0.1*inch))
                        
                        # Create and add Disk chart
                        timestamps = [point['Timestamp'] for point in datapoints]
                        min_val = min(values) if values else 0
                        max_val = max(values) if values else 0
                        
                        disk_chart = create_chart(
                            timestamps,
                            values,
                            f"Disk {disk_name} Utilization",
                            resource['name'],
                            avg_val,
                            min_val,
                            max_val
                        )
                        
                        elements.append(Image(io.BytesIO(disk_chart), width=6*inch, height=2.5*inch))
                        elements.append(Spacer(1, 0.3*inch))
            elif 'metrics' in resource and 'disk' in resource['metrics']:
                disk_data = resource['metrics']['disk']
                
                if disk_data.get('Datapoints'):
                    # Disk utilization title
                    elements.append(Paragraph("DISK UTILIZATION", label_style))
                
                    # Add remarks about disk utilization
                    datapoints = sorted(disk_data['Datapoints'], key=lambda x: x['Timestamp'])
                    values = [point.get('Average', 0) for point in datapoints]
                    avg_val = sum(values) / len(values) if values else 0
                    
                    if service_type in ['RDS', 'Database']:
                        # Convert bytes to GB for RDS
                        avg_val_gb = avg_val / (1024 * 1024 * 1024)
                        if avg_val_gb < 5:
                            remarks = "Storage availability is low. Consider increasing storage."
                        else:
                            remarks = "Storage availability is normal."
                        display_val = f"{avg_val_gb:.2f} GB"
                    else:
                        if avg_val > 85:
                            remarks = "Average Disk utilisation is high. Explore possibility of optimising the resources."
                        elif avg_val < 30:
                            remarks = "Average Disk utilisation is low. No action needed at the time."
                        else:
                            remarks = "Average Disk utilisation is Normal."
                        display_val = f"{avg_val:.2f}%"
                    
                    elements.append(Paragraph(f"<i>Remarks: {remarks}</i>", remark_style))
                    elements.append(Spacer(1, 0.1*inch))
                    
                    # Add Average table
                    avg_table_data = [["Average", display_val]]
                    avg_table = Table(wrap_table_data(avg_table_data), colWidths=[1.5*inch, 1.5*inch])
                    avg_table.setStyle(TableStyle([
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                        ('BACKGROUND', (0, 0), (0, -1), colors.white),
                        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('PADDING', (0, 0), (-1, -1), 6)
                    ]))
                    elements.append(avg_table)
                    elements.append(Spacer(1, 0.1*inch))
                
                    # Create and add Disk chart
                    timestamps = [point['Timestamp'] for point in datapoints]
                    min_val = min(values) if values else 0
                    max_val = max(values) if values else 0
                    
                    disk_chart = create_chart(
                        timestamps,
                        values,
                        "Disk Utilization" if service_type not in ['RDS'] else "Available Storage",
                        resource['name'],
                        avg_val,
                        min_val,
                        max_val
                    )
                    
                    elements.append(Image(io.BytesIO(disk_chart), width=6*inch, height=2.5*inch))
                    elements.append(Spacer(1, 0.3*inch))

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
    
    # Add billing summary text
    elements.append(Paragraph("This report provides cost breakdown for your selected services during the billing period.", detail_style))
    elements.append(Spacer(1, 0.4*inch))
    
    # Footer text about data accuracy
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

def page_template(canvas, doc):
    """Custom page template with borders and logo"""
    canvas.saveState()
    
    # Draw page border
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(2)
    canvas.rect(20, 20, letter[0]-40, letter[1]-40)
    
    # Add www.nubinix.com in top left
    canvas.setFont('Helvetica', 10)
    canvas.drawString(40, letter[1]-40, "www.nubinix.com")
    
    # Add Nubinix company logo in top right
    logo_path = 'static/nubinix-logo.png'
    if os.path.exists(logo_path):
        # Draw the actual company logo
        canvas.drawImage(logo_path, letter[0]-100, letter[1]-80, width=60, height=40, preserveAspectRatio=True)
    else:
        # Fallback to simple colored logo placeholder if file not found
        canvas.setFillColor(colors.HexColor('#4A90E2'))  # Blue color
        canvas.rect(letter[0]-120, letter[1]-100, 30, 30, fill=1)
        canvas.setFillColor(colors.HexColor('#E24A90'))  # Pink color  
        canvas.rect(letter[0]-90, letter[1]-100, 30, 30, fill=1)
        
        # Add "nubinix" text under logo
        canvas.setFillColor(colors.black)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(letter[0]-110, letter[1]-115, "nubinix")
    
    canvas.restoreState()

def generate_pdf_report(account_name, metrics_data=None, cloud_provider='AWS', 
                       report_type='utilization', month=None, year=None, billing_data=None):
    """Generate a PDF report with metrics data or billing information."""
    logger.info("Generating PDF report...")
    
    # Create a buffer for the PDF
    buffer = io.BytesIO()
    
    # Create the PDF document with custom template
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.8*inch,
        leftMargin=0.8*inch,  
        topMargin=1.2*inch,
        bottomMargin=0.8*inch
    )
    
    # Initialize the list of flowables
    elements = []
    
    # Create appropriate report content based on report type
    if report_type == 'utilization':
        create_utilization_report(doc, elements, account_name, metrics_data, cloud_provider)
    else:  # billing report
        create_billing_report(doc, elements, account_name, cloud_provider, month, year, billing_data)
    
    # Build the PDF document with custom page template
    doc.build(elements, onFirstPage=page_template, onLaterPages=page_template)
    
    # Get the PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

def generate_comprehensive_report(client_name: str, cloud_provider: str, report_type: str,
                                credentials: dict, resources=None,
                                frequency: str = 'daily') -> bytes:
    """Generate a comprehensive report based on the request parameters."""
    logger.info(f"Generating {report_type} report for {client_name}")
    
    if report_type == 'utilization':
        # Import AWS utilities
        from aws_utils import get_instance_metrics
        
        # Convert frequency to period days
        period_days = 1 if frequency == 'daily' else 7
        
        # Get metrics for the selected resources
        metrics_data = get_instance_metrics(
            credentials['access_key'],
            credentials['secret_key'],
            resources or [],
            period_days
        )
        
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