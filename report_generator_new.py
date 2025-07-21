import io
import os
import logging
import tempfile
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

def create_comprehensive_chart(metric_data, metric_name, instance_name):
    """Create a comprehensive chart with full data visualization."""
    try:
        plt.figure(figsize=(12, 6))
        
        # Extract timestamps and values
        timestamps = []
        values = []
        
        if isinstance(metric_data, dict) and 'Datapoints' in metric_data:
            datapoints = metric_data['Datapoints']
            for point in datapoints:
                if 'Timestamp' in point and 'Average' in point:
                    timestamps.append(point['Timestamp'])
                    values.append(point['Average'])
        
        if not timestamps or not values:
            # Create placeholder chart with "No Data Available"
            plt.text(0.5, 0.5, 'No Data Available', 
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=plt.gca().transAxes,
                    fontsize=16, fontweight='bold',
                    color='gray')
            plt.title(f'{instance_name}: {metric_name}', fontweight='bold', fontsize=14)
        else:
            # Sort by timestamp
            sorted_data = sorted(zip(timestamps, values))
            timestamps, values = zip(*sorted_data)
            
            # Plot the main data line
            plt.plot(timestamps, values, color='#2E86C1', linewidth=2.5, 
                     marker='o', markersize=4, markerfacecolor='#2E86C1', 
                     label='Actual Values', alpha=0.8)
            
            # Add statistical lines
            avg_val = sum(values) / len(values)
            max_val = max(values)
            min_val = min(values)
            
            plt.axhline(y=avg_val, color='#E74C3C', linestyle='--', 
                       alpha=0.7, linewidth=2, label=f'Average ({avg_val:.2f})')
            plt.axhline(y=max_val, color='#F39C12', linestyle=':', 
                       alpha=0.6, linewidth=1.5, label=f'Maximum ({max_val:.2f})')
            plt.axhline(y=min_val, color='#27AE60', linestyle=':', 
                       alpha=0.6, linewidth=1.5, label=f'Minimum ({min_val:.2f})')
            
            # Format x-axis
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))
            plt.xticks(rotation=45)
            
            # Set labels and title
            plt.xlabel('Time (UTC)', fontweight='bold')
            
            # Determine unit based on metric name
            if 'cpu' in metric_name.lower():
                unit = 'Percent'
                plt.ylabel(f"{metric_name} (%)", fontweight='bold')
                plt.ylim(0, 100)
            elif any(word in metric_name.lower() for word in ['memory', 'disk', 'network']):
                if 'bytes' in metric_name.lower():
                    unit = 'Bytes'
                    plt.ylabel(f"{metric_name} (Bytes)", fontweight='bold')
                else:
                    unit = 'Percent'
                    plt.ylabel(f"{metric_name} (%)", fontweight='bold')
                    plt.ylim(0, 100)
            else:
                unit = 'Value'
                plt.ylabel(metric_name, fontweight='bold')
            
            # Set title with time range
            start_time = min(timestamps).strftime('%Y-%m-%d %H:%M')
            end_time = max(timestamps).strftime('%Y-%m-%d %H:%M')
            plt.title(f'{instance_name}: {metric_name}\n{start_time} to {end_time}', 
                     fontweight='bold', fontsize=12)
            
            # Add grid and legend
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.legend(loc='upper right', frameon=True, shadow=True)
            
            # Add statistics text box
            stats_text = f"Points: {len(values)} | Avg: {avg_val:.2f} | Min: {min_val:.2f} | Max: {max_val:.2f}"
            plt.figtext(0.5, 0.02, stats_text, ha='center', fontsize=10, 
                       bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.5))
        
        plt.tight_layout()
        
        # Save to bytes
        chart_buffer = io.BytesIO()
        plt.savefig(chart_buffer, format='png', dpi=300, bbox_inches='tight')
        plt.close()
        
        chart_buffer.seek(0)
        return chart_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error creating chart for {metric_name}: {str(e)}")
        plt.close()
        return None

def generate_pdf_report(account_name, data, cloud_provider='AWS', report_type='utilization', **kwargs):
    """Generate a comprehensive PDF report with full data display."""
    try:
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
        styles = getSampleStyleSheet()
        story = []
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=20
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#E74C3C'),
            spaceAfter=12,
            spaceBefore=15
        )
        
        # Report Header
        story.append(Paragraph(f"{cloud_provider} {report_type.title()} Report", title_style))
        story.append(Paragraph(f"Account: {account_name}", subtitle_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", subtitle_style))
        story.append(Spacer(1, 30))
        
        if report_type == 'utilization' and data:
            logger.info(f"Processing utilization data: {len(data)} items")
            
            # Executive Summary
            story.append(Paragraph("📊 Executive Summary", section_style))
            
            total_instances = len(data)
            total_resources = sum(1 for item in data if item.get('Metrics'))
            
            summary_data = [
                ['Metric', 'Value'],
                ['Total Resources Analyzed', str(total_instances)],
                ['Resources with Metrics', str(total_resources)],
                ['Report Period', 'Last 24 Hours'],
                ['Report Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')]
            ]
            
            summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 10)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 30))
            
            # Process each resource with comprehensive data
            for idx, item in enumerate(data):
                instance_id = item.get('InstanceId', f'Resource-{idx+1}')
                
                # Resource Header
                story.append(Paragraph(f"🖥️ Resource: {instance_id}", section_style))
                
                # Resource Information Table
                info_data = [
                    ['Property', 'Value'],
                    ['Instance ID', instance_id],
                    ['Instance Type', item.get('InstanceType', 'N/A')],
                    ['Region', item.get('Region', 'N/A')],
                    ['Availability Zone', item.get('AvailabilityZone', 'N/A')],
                    ['State', item.get('State', 'N/A')],
                    ['Launch Time', item.get('LaunchTime', 'N/A')],
                    ['Platform', item.get('Platform', 'Linux/Unix')],
                    ['Architecture', item.get('Architecture', 'x86_64')]
                ]
                
                info_table = Table(info_data, colWidths=[2*inch, 3*inch])
                info_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2980B9')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 9)
                ]))
                
                story.append(info_table)
                story.append(Spacer(1, 20))
                
                # Metrics Analysis
                metrics = item.get('Metrics', {})
                if metrics:
                    story.append(Paragraph("📈 Performance Metrics", 
                                         ParagraphStyle('MetricHeader',
                                                       parent=styles['Heading4'],
                                                       fontSize=12,
                                                       textColor=colors.HexColor('#E67E22'))))
                    
                    # Create detailed metrics table
                    metrics_data = [['Metric Name', 'Average', 'Maximum', 'Minimum', 'Data Points', 'Unit']]
                    
                    for metric_name, metric_info in metrics.items():
                        if isinstance(metric_info, dict):
                            avg = metric_info.get('Average', 0)
                            max_val = metric_info.get('Maximum', 0)
                            min_val = metric_info.get('Minimum', 0)
                            unit = metric_info.get('Unit', '')
                            data_points = len(metric_info.get('Datapoints', []))
                            
                            metrics_data.append([
                                metric_name,
                                f"{avg:.3f}",
                                f"{max_val:.3f}",
                                f"{min_val:.3f}",
                                str(data_points),
                                unit
                            ])
                    
                    metrics_table = Table(metrics_data, colWidths=[1.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.7*inch, 0.6*inch])
                    metrics_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FADBD8')),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('FONTSIZE', (0, 1), (-1, -1), 7)
                    ]))
                    
                    story.append(metrics_table)
                    story.append(Spacer(1, 20))
                    
                    # Add charts for each metric
                    for metric_name, metric_info in metrics.items():
                        if isinstance(metric_info, dict) and metric_info.get('Datapoints'):
                            chart_data = create_comprehensive_chart(metric_info, metric_name, instance_id)
                            if chart_data:
                                # Save chart to temporary file
                                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                                    tmp_file.write(chart_data)
                                    tmp_file.flush()
                                    
                                    # Add chart to PDF
                                    chart_image = Image(tmp_file.name, width=6*inch, height=3*inch)
                                    story.append(chart_image)
                                    story.append(Spacer(1, 15))
                                    
                                # Clean up temp file
                                os.unlink(tmp_file.name)
                
                # Add page break between resources (except for last one)
                if idx < len(data) - 1:
                    story.append(PageBreak())
        
        elif report_type == 'billing' and data:
            logger.info(f"Processing billing data: {len(data)} items")
            
            # Billing Overview
            story.append(Paragraph("💰 Billing Overview", section_style))
            
            month = kwargs.get('month', datetime.now().month)
            year = kwargs.get('year', datetime.now().year)
            
            total_cost = 0
            service_costs = {}
            
            # Process billing data
            for item in data:
                if isinstance(item, dict):
                    cost = float(item.get('BlendedCost', item.get('Cost', 0)))
                    service = item.get('Service', item.get('ServiceName', 'Unknown'))
                    total_cost += cost
                    
                    if service not in service_costs:
                        service_costs[service] = 0
                    service_costs[service] += cost
            
            # Billing summary
            billing_summary = [
                ['Billing Metric', 'Value'],
                ['Total Cost', f"${total_cost:.2f}"],
                ['Billing Period', f"{month:02d}/{year}"],
                ['Number of Services', str(len(service_costs))],
                ['Average Daily Cost', f"${total_cost/30:.2f}"],
                ['Report Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')]
            ]
            
            billing_table = Table(billing_summary, colWidths=[2.5*inch, 2.5*inch])
            billing_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E8F8F5')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 10)
            ]))
            
            story.append(billing_table)
            story.append(Spacer(1, 30))
            
            # Service Cost Breakdown
            story.append(Paragraph("🔍 Detailed Service Breakdown", section_style))
            
            service_breakdown = [['Service Name', 'Total Cost', 'Percentage of Total', 'Daily Average']]
            for service, cost in sorted(service_costs.items(), key=lambda x: x[1], reverse=True):
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                daily_avg = cost / 30
                service_breakdown.append([
                    service,
                    f"${cost:.2f}",
                    f"{percentage:.1f}%",
                    f"${daily_avg:.2f}"
                ])
            
            service_table = Table(service_breakdown, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch])
            service_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F39C12')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FEF9E7')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9)
            ]))
            
            story.append(service_table)
            story.append(Spacer(1, 30))
            
            # Top 5 Most Expensive Services
            if service_costs:
                story.append(Paragraph("🏆 Top 5 Most Expensive Services", section_style))
                top_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[:5]
                
                top_data = [['Rank', 'Service', 'Cost', '% of Total']]
                for i, (service, cost) in enumerate(top_services):
                    percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                    top_data.append([
                        str(i+1),
                        service,
                        f"${cost:.2f}",
                        f"{percentage:.1f}%"
                    ])
                
                top_table = Table(top_data, colWidths=[0.5*inch, 2.5*inch, 1*inch, 1*inch])
                top_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8E44AD')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F4ECF7')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 9)
                ]))
                
                story.append(top_table)
        
        else:
            # No data available
            story.append(Paragraph("⚠️ No Data Available", section_style))
            story.append(Paragraph(
                "No data was available for the selected reporting period. This could be due to:",
                styles['Normal']
            ))
            no_data_reasons = [
                "• No resources found in the specified time range",
                "• Insufficient permissions to access CloudWatch metrics",
                "• Resources may not have been active during the reporting period",
                "• CloudWatch data retention period may have expired"
            ]
            for reason in no_data_reasons:
                story.append(Paragraph(reason, styles['Normal']))
        
        # Report Footer
        story.append(Spacer(1, 50))
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#7F8C8D'),
            alignment=1,
            borderPadding=10
        )
        
        story.append(Paragraph(
            f"Report generated by Nubinix Cloud Insights | {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | "
            f"Total Pages: Generated Automatically",
            footer_style
        ))
        
        # Build PDF
        doc.build(story)
        pdf_data = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        logger.info(f"Successfully generated comprehensive PDF report: {len(pdf_data)} bytes")
        return pdf_data
        
    except Exception as e:
        logger.error(f"Error generating comprehensive PDF report: {str(e)}")
        return None