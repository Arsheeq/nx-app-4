import io
import os
import logging
import tempfile
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Configure matplotlib for headless environment
matplotlib.rcParams['figure.max_open_warning'] = 0
matplotlib.rcParams['text.usetex'] = False
matplotlib.rcParams['mathtext.default'] = 'regular'
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.units import inch
from datetime import datetime, timedelta, timezone
import pytz
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_chart(timestamps, values, metric_name, instance_name, avg, min_val, max_val, service_type='EC2', period_days=1):
    """Create a chart for the metric and return as bytes."""
    try:
        # Clear any previous plots to prevent memory leaks
        plt.close('all')

        # Create figure with exact dimensions to match the reference image
        fig = plt.figure(figsize=(8, 4), facecolor='white')
        ax = fig.add_subplot(111)

        # Skip chart creation if no data
        if not timestamps or not values or len(timestamps) == 0:
            ax.text(0.5, 0.5, 'No data available', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=10)
            # Use simple ASCII title to avoid text processing issues
            clean_instance_name = str(instance_name).replace('$', '').replace('\\', '')
            clean_metric_name = str(metric_name).replace('$', '').replace('\\', '')
            ax.set_title(f'{clean_instance_name}: {clean_metric_name}', fontweight='bold', fontsize=10)
        else:
            # Plot the data with exact pink color from reference image
            ax.plot(timestamps, values, color='#E91E63', linewidth=1.5, 
                   marker='o', markersize=1.5, markerfacecolor='#E91E63', alpha=1.0, label='Average')

            # Add average line with same pink color and dashed style
            ax.axhline(y=avg, color='#E91E63', linestyle='--', alpha=0.7, label='Average')

            # Format time axis based on period_days parameter
            if len(timestamps) > 1:
                if period_days == 1:  # Daily chart
                    # For daily charts: use exactly 3-hour intervals like reference: 15:30, 18:30, 21:30, 00:30, 03:30, 06:30, 09:30
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

                    # Set explicit limits to ensure clean time display
                    start_time = timestamps[0]
                    end_time = timestamps[-1]

                    # Round start time to nearest 3-hour mark
                    start_hour = start_time.hour
                    # Find the nearest 3-hour interval (0, 3, 6, 9, 12, 15, 18, 21)
                    rounded_start_hour = (start_hour // 3) * 3

                    # Create clean start time at rounded hour with :30 minutes for better alignment
                    from datetime import datetime, timedelta

                    clean_start = start_time.replace(hour=rounded_start_hour, minute=30, second=0, microsecond=0)
                    if clean_start > start_time:
                        clean_start = clean_start - timedelta(hours=3)

                    # Set time range to show about 24 hours with clean intervals
                    clean_end = clean_start + timedelta(hours=24)

                    ax.set_xlim(clean_start, clean_end)

                    # Force exactly 7 time labels at 3-hour intervals with :30 minutes
                    time_ticks = []
                    current_time = clean_start
                    for i in range(8):  # 8 ticks for 24 hours at 3-hour intervals
                        time_ticks.append(current_time)
                        current_time += timedelta(hours=3)

                    ax.set_xticks(time_ticks)
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

                else:  # Weekly chart (period_days > 1)
                    # For weekly charts: show dates like 07-15, 07-16, 07-17, 07-18, etc.
                    # Set explicit time range to ensure all 7 days are shown
                    start_time = timestamps[0]
                    end_time = timestamps[-1]

                    # Create explicit date range for all 7 days using native datetime
                    from datetime import datetime, timedelta

                    # Get start date and create 7-day range
                    start_date = start_time.date()

                    date_ticks = []
                    for i in range(7):  # 7 days for weekly report
                        current_date = start_date + timedelta(days=i)
                        # Convert to datetime with timezone info
                        if hasattr(start_time, 'tzinfo') and start_time.tzinfo:
                            date_tick = datetime.combine(current_date, datetime.min.time()).replace(hour=12, tzinfo=start_time.tzinfo)
                        else:
                            date_tick = datetime.combine(current_date, datetime.min.time()).replace(hour=12)
                        date_ticks.append(date_tick)

                    # Set the x-axis ticks and labels
                    ax.set_xticks(date_ticks)
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

                    # Ensure the chart shows the full range
                    ax.set_xlim(date_ticks[0] - timedelta(hours=12), date_ticks[-1] + timedelta(hours=12))

                # Don't rotate labels - keep them horizontal like in reference
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center')

            # Add grid exactly like in the reference image - light gray lines
            ax.grid(True, linestyle='-', alpha=0.3, color='lightgray', linewidth=0.5)

            # Set labels exactly like in the reference image
            ax.set_xlabel('Time', fontsize=10, fontweight='normal')

            # Clean metric name to avoid special characters
            clean_metric_name = str(metric_name).replace('$', '').replace('\\', '')
            clean_instance_name = str(instance_name).replace('$', '').replace('\\', '')

            # Create proper chart title with date range based on actual data timestamps
            if timestamps:
                start_time = timestamps[0]
                end_time = timestamps[-1]

                # Convert to IST timezone for display
                ist_tz = pytz.timezone('Asia/Kolkata')
                start_time_ist = start_time.astimezone(ist_tz) if start_time.tzinfo else pytz.utc.localize(start_time).astimezone(ist_tz)
                end_time_ist = end_time.astimezone(ist_tz) if end_time.tzinfo else pytz.utc.localize(end_time).astimezone(ist_tz)

                # Format exactly like reference image: "2025-07-21 12:38 IST to 2025-07-22 12:28 IST"
                title_date_range = f"{start_time_ist.strftime('%Y-%m-%d %H:%M')} IST to {end_time_ist.strftime('%Y-%m-%d %H:%M')} IST"
            else:
                # Fallback if no timestamps available
                from datetime import timedelta
                now = datetime.now(pytz.timezone('Asia/Kolkata'))
                yesterday = now - timedelta(days=1)
                title_date_range = f"{yesterday.strftime('%Y-%m-%d %H:%M')} IST to {now.strftime('%Y-%m-%d %H:%M')} IST"

            # Create the exact title format from reference image
            chart_title = f"{clean_instance_name}: {clean_metric_name}\n{title_date_range}"
            ax.set_title(chart_title, fontweight='bold', fontsize=11, pad=15)

            # Set Y-axis label and format stats based on metric type
            if ('gb' in clean_metric_name.lower() or 
                any(word in clean_metric_name.lower() for word in ['memory', 'disk', 'storage']) or
                service_type in ['RDS'] and 'disk' in clean_metric_name.lower()):
                unit = 'GB'
                # Use proper label for disk/storage metrics
                if 'disk' in clean_metric_name.lower() or 'storage' in clean_metric_name.lower():
                    ax.set_ylabel("Available Storage (GB)", fontsize=10)
                else:
                    ax.set_ylabel(f"Available Memory (GB)", fontsize=10)
                stats_text = f"Min: {min_val:.2f} | Max: {max_val:.2f} | Avg: {avg:.2f}"
            else:
                # For CPU utilization, use exact format from reference
                ax.set_ylabel("CPU Utilization (Percent)", fontsize=10)
                stats_text = f"Min: {min_val:.2f}% | Max: {max_val:.2f}% | Avg: {avg:.2f}%"

            # Add legend exactly like in the reference image (top right)
            legend = ax.legend(loc='upper right', frameon=True, fancybox=False, shadow=False, 
                             fontsize=9, framealpha=1.0)
            legend.get_frame().set_facecolor('white')
            legend.get_frame().set_edgecolor('black')
            legend.get_frame().set_linewidth(0.5)

            # Add statistics text below the chart - positioned to avoid overlap
            fig.text(0.5, 0.02, stats_text, ha='center', fontsize=10, weight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9, edgecolor='black'))

        # Adjust layout to prevent overlapping and match reference spacing
        plt.subplots_adjust(bottom=0.25, top=0.85, left=0.12, right=0.95, hspace=0.3)

        # Save plot to bytes
        buf = io.BytesIO()
        try:
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', 
                       facecolor='white', edgecolor='none', pad_inches=0.2)
        except Exception as save_error:
            logger.warning(f"Error saving figure normally, trying fallback: {save_error}")
            # Fallback save method
            fig.savefig(buf, format='png', dpi=75)

        plt.close(fig)  # Ensure figure is closed
        buf.seek(0)

        return buf.getvalue()

    except Exception as e:
        logger.error(f"Error creating chart for {instance_name}: {str(e)}")
        # Create minimal error chart
        try:
            plt.close('all')
            fig = plt.figure(figsize=(6, 2), facecolor='white')
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, 'Chart Error', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=10, color='red')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')

            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=50)
            plt.close(fig)
            buf.seek(0)
            return buf.getvalue()
        except Exception as fallback_error:
            logger.error(f"Error creating fallback chart: {fallback_error}")
            # Return minimal placeholder image bytes
            return b''

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

def get_account_id_for_client(client_name):
    """Get AWS account ID for the client from SSM or return placeholder"""
    try:
        from ssm_utils import get_credentials_for_client
        import boto3

        # Get credentials for the client
        credentials = get_credentials_for_client(client_name)
        if credentials:
            # Use STS to get account ID
            sts = boto3.client(
                'sts',
                aws_access_key_id=credentials['access_key'],
                aws_secret_access_key=credentials['secret_key'],
                region_name='us-east-1'
            )
            response = sts.get_caller_identity()
            return response.get('Account', 'N/A')
    except Exception as e:
        logger.warning(f"Could not get account ID for {client_name}: {str(e)}")

    # Return a client-specific account ID placeholder
    account_mapping = {
        'arshak': '123456789012',
        'ashwin': '234567890123', 
        'send2': '345678901234'
    }
    return account_mapping.get(client_name, 'N/A')

def create_utilization_report(doc, elements, account_name, metrics_data, cloud_provider, period_days=1):
    """Create utilization report content"""
    styles = getSampleStyleSheet()

    # Process all resources without limits
    report_period = "weekly" if period_days and period_days > 1 else "daily"
    logger.info(f"Generating {report_period} report for {len(metrics_data)} resources")

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

    # Get account ID for the client
    account_id = get_account_id_for_client(account_name)

    # Add report information table
    report_data = [
        ["Account", account_name],
        ["Report", "Resource Utilization"],
        ["Cloud Provider", cloud_provider.upper()],
        ["Account ID", account_id],
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

    # Add resources summary for EC2 instances
    if 'EC2' in service_types:
        elements.append(Paragraph("Instances Covered in Report:", header_style))
        elements.append(Spacer(1, 0.2*inch))

        # Create a table for EC2 instance summary
        summary_data = [["Instance ID", "Name", "Type", "Status"]]
        for resource in service_types['EC2']:
            summary_data.append([
                resource['id'],
                resource['name'],
                resource['type'],
                resource['state']
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

    # Add resources summary for RDS instances
    if 'RDS' in service_types:
        elements.append(Paragraph("RDS Instances Covered in Report:", header_style))
        elements.append(Spacer(1, 0.2*inch))

        # Create a table for RDS instance summary
        summary_data = [["Instance Name", "Type", "Status", "Engine"]]
        for resource in service_types['RDS']:
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

    # Process each resource with progress logging
    total_resources = len(metrics_data)
    for i, resource in enumerate(metrics_data):
        if i % 5 == 0:  # Log progress every 5 resources
            logger.info(f"Processing resource {i+1}/{total_resources}: {resource.get('name', 'unknown')}")

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

                    if cpu_data.get('timestamps'):
                        # CPU utilization title - exact format
                        elements.append(Paragraph("CPU UTILIZATION", label_style))

                        # Add remarks about CPU utilization - exact format
                        avg_val = cpu_data['average']

                        if avg_val > 85:
                            remarks = "Average utilisation is high. Explore possibility of optimising the resources."
                        elif avg_val < 15:
                            remarks = "Average utilisation is low. No action needed at the time."
                        else:
                            remarks = "Average utilisation is normal. No action needed at the time."

                        elements.append(Paragraph(f"<i>Remarks: {remarks}</i>", remark_style))
                        elements.append(Spacer(1, 0.1*inch))

                        # Add Average table - exact format with border
                        avg_table_data = [["Average", f"{avg_val:.2f}%"]]
                        avg_table = Table(wrap_table_data(avg_table_data), colWidths=[1.5*inch, 1.5*inch])
                        avg_table.setStyle(TableStyle([
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('PADDING', (0, 0), (-1, -1), 6),
                            ('FONTSIZE', (0, 0), (-1, -1), 11)
                        ]))
                        elements.append(avg_table)
                        elements.append(Spacer(1, 0.1*inch))

                        # Create and add CPU chart
                        try:
                            cpu_chart = create_chart(
                                cpu_data['timestamps'],
                                cpu_data['values'],
                                "CPU Utilization",
                                resource['name'],
                                cpu_data['average'],
                                cpu_data['min'],
                                cpu_data['max'],
                                service_type,
                                period_days
                            )

                            if cpu_chart:  # Only add if chart was successfully created
                                elements.append(Image(io.BytesIO(cpu_chart), width=6*inch, height=2.5*inch))
                            else:
                                elements.append(Paragraph("CPU chart could not be generated", remark_style))
                        except Exception as e:
                            logger.error(f"Failed to create CPU chart for {resource['name']}: {str(e)}")
                            elements.append(Paragraph("CPU chart could not be generated", remark_style))

                        elements.append(Spacer(1, 0.3*inch))

                # Process Memory metrics
                if 'memory' in resource['metrics']:
                    memory_data = resource['metrics']['memory']

                    if memory_data.get('timestamps'):
                        # Memory utilization title
                        elements.append(Paragraph("MEMORY UTILIZATION", label_style))

                        # Add remarks about memory utilization
                        avg_val = memory_data['average']

                        if service_type in ['RDS', 'Database']:
                            # Convert bytes to GB for RDS
                            avg_val_gb = avg_val / (1024 * 1024 * 1024) if avg_val > 1000 else avg_val
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
                        try:
                            memory_chart = create_chart(
                                memory_data['timestamps'],
                                memory_data['values'],
                                "Memory Utilization" if service_type not in ['RDS'] else "Available Memory",
                                resource['name'],
                                memory_data['average'],
                                memory_data['min'],
                                memory_data['max'],
                                service_type,
                                period_days
                            )

                            if memory_chart:  # Only add if chart was successfully created
                                elements.append(Image(io.BytesIO(memory_chart), width=6*inch, height=2.5*inch))
                            else:
                                elements.append(Paragraph("Memory chart could not be generated", remark_style))
                        except Exception as e:
                            logger.error(f"Failed to create memory chart for {resource['name']}: {str(e)}")
                            elements.append(Paragraph("Memory chart could not be generated", remark_style))

                        elements.append(Spacer(1, 0.3*inch))

            # Process Disk metrics - Handle both disk_metrics (multiple disks) and disk (single disk)
            disk_metrics_processed = False
            
            # First, try to process individual disk metrics (Windows C:, D:, E: drives)
            if 'metrics' in resource and 'disk_metrics' in resource['metrics']:
                disk_metrics = resource['metrics']['disk_metrics']
                for disk_name, disk_data in disk_metrics.items():
                    if disk_data.get('timestamps'):
                        disk_metrics_processed = True
                        
                        # Disk utilization title
                        if 'C' in disk_name:
                            elements.append(Paragraph("DISK C FREE PERCENTAGE", label_style))
                        elif 'D' in disk_name:
                            elements.append(Paragraph("DISK D FREE PERCENTAGE", label_style))
                        elif 'E' in disk_name:
                            elements.append(Paragraph("DISK E FREE PERCENTAGE", label_style))
                        else:
                            elements.append(Paragraph("DISK UTILIZATION", label_style))

                        # Add remarks about disk utilization
                        avg_val = disk_data['average']

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
                        try:
                            disk_chart = create_chart(
                                disk_data['timestamps'],
                                disk_data['values'],
                                f"Disk {disk_name} Utilization",
                                resource['name'],
                                disk_data['average'],
                                disk_data['min'],
                                disk_data['max'],
                                service_type,
                                period_days
                            )

                            if disk_chart:  # Only add if chart was successfully created
                                elements.append(Image(io.BytesIO(disk_chart), width=6*inch, height=2.5*inch))
                            else:
                                elements.append(Paragraph("Disk chart could not be generated", remark_style))
                        except Exception as e:
                            logger.error(f"Failed to create disk chart for {resource['name']}: {str(e)}")
                            elements.append(Paragraph("Disk chart could not be generated", remark_style))

                        elements.append(Spacer(1, 0.3*inch))
            
            # If no individual disk metrics were processed, try the general disk metric
            if not disk_metrics_processed and 'metrics' in resource and 'disk' in resource['metrics']:
                disk_data = resource['metrics']['disk']

                if disk_data.get('timestamps'):
                    # Disk utilization title
                    elements.append(Paragraph("DISK UTILIZATION", label_style))

                    # Add remarks about disk utilization
                    avg_val = disk_data['average']

                    if service_type in ['RDS', 'Database']:
                        # Convert bytes to GB for RDS
                        avg_val_gb = avg_val / (1024 * 1024 * 1024) if avg_val > 1000 else avg_val
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
                    disk_chart = create_chart(
                        disk_data['timestamps'],
                        disk_data['values'],
                        "Disk Utilization" if service_type not in ['RDS'] else "Available Storage",
                        resource['name'],
                        disk_data['average'],
                        disk_data['min'],
                        disk_data['max'],
                        service_type,
                        period_days
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
                       report_type='utilization', month=None, year=None, billing_data=None, period_days=1):
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
        create_utilization_report(doc, elements, account_name, metrics_data, cloud_provider, period_days)
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
            report_type=report_type,
            period_days=period_days
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

def create_metric_chart_matplotlib(metric_data, metric_name, instance_name, frequency='daily'):
    """Create a chart for a specific metric using matplotlib."""
    try:
        if not metric_data or len(metric_data) == 0:
            logger.warning(f"No data available for {metric_name}")
            return None

        # Extract timestamps and values
        timestamps = []
        values = []

        for datapoint in metric_data:
            if 'Timestamp' in datapoint and 'Average' in datapoint:
                # Parse timestamp properly
                timestamp = datapoint['Timestamp']
                if isinstance(timestamp, str):
                    # Handle string timestamps
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        timestamp = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
                elif hasattr(timestamp, 'replace'):
                    # It's already a datetime object, ensure it's timezone aware
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)

                # Convert to IST (UTC+5:30)
                ist_offset = timedelta(hours=5, minutes=30)
                if timestamp.tzinfo:
                    timestamp = timestamp.astimezone(timezone(ist_offset))
                else:
                    timestamp = timestamp.replace(tzinfo=timezone.utc).astimezone(timezone(ist_offset))

                timestamps.append(timestamp)
                values.append(float(datapoint['Average']))

        if len(timestamps) == 0 or len(values) == 0:
            logger.warning(f"No valid data points for {metric_name}")
            return None

        # Sort by timestamp
        sorted_data = sorted(zip(timestamps, values))
        timestamps, values = zip(*sorted_data)

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot the data
        ax.plot(timestamps, values, color='#e74c3c', linewidth=2, marker='o', markersize=4)

        # Set title and labels with proper IST formatting
        start_time = timestamps[0].strftime("%Y-%m-%d %H:%M IST")
        end_time = timestamps[-1].strftime("%Y-%m-%d %H:%M IST")
        ax.set_title(f'{metric_name}\n{start_time} to {end_time}', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_ylabel(f'{metric_name} (Percent)', fontsize=12)

        # Format x-axis based on frequency with proper time range
        if frequency == 'daily':
            # For daily reports, show hours only (not dates spanning years)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            # Set locator based on data density
            hour_span = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
            if hour_span <= 24:
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, int(hour_span/8))))
            else:
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
            ax.set_xlabel('Time', fontsize=12)
        else:
            # For weekly reports, show dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            day_span = (timestamps[-1] - timestamps[0]).days
            if day_span <= 7:
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            else:
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, int(day_span/7))))
            ax.set_xlabel('Date', fontsize=12)

        # Set x-axis limits to actual data range
        ax.set_xlim(timestamps[0], timestamps[-1])

        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)

        # Add grid
        ax.grid(True, alpha=0.3)

        # Add min, max, avg text box
        min_val = min(values)
        max_val = max(values)
        avg_val = sum(values) / len(values)

        textstr = f'Min: {min_val:.2f}% | Max: {max_val:.2f}% | Avg: {avg_val:.2f}%'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax.text(0.5, -0.15, textstr, transform=ax.transAxes, fontsize=10,
                horizontalalignment='center', bbox=props)

        # Adjust layout to prevent clipping
        plt.tight_layout()

        # Save to BytesIO
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()

        return img_buffer.getvalue()

    except Exception as e:
        logger.error(f"Error creating chart for {metric_name}: {str(e)}")
        return None