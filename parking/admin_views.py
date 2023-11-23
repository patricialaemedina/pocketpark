import matplotlib
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta, date
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, HRFlowable, Image, PageBreak
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from django.utils import timezone
from django.db.models import Count
from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import *
matplotlib.use('Agg')

@staff_member_required
def generate_report(request):
    if request.method == 'POST':
        report_type = request.POST.get('report-type')
        period = request.POST.get('period')
        period_date_start = request.POST.get('periodDateStart')
        end_date = None

        if report_type == 'revenue':
            if period == 'daily':
                start_date = datetime.strptime(period_date_start, '%Y-%m-%d').date()
                end_date = start_date

                paid_payments = Payment.objects.filter(payment_status='Paid', creation_datetime__date__range=(start_date, end_date))

                total_revenue = sum(payment.amount_paid for payment in paid_payments)

            elif period == 'weekly':
                start_date = datetime.strptime(period_date_start, '%Y-%m-%d').date()
                end_date = start_date + timedelta(days=7)

                paid_payments = Payment.objects.filter(payment_status='Paid', creation_datetime__date__range=(start_date, end_date))

                total_revenue = sum(payment.amount_paid for payment in paid_payments)
                
            elif period == 'monthly':
                selected_year, selected_month = period_date_start.split('-')
                selected_month = int(selected_month)
                selected_year = int(selected_year)

                start_date = datetime(selected_year, selected_month, 1).date()
                end_date = start_date.replace(day=1, month=selected_month + 1) - timedelta(days=1)

                paid_payments = Payment.objects.filter(payment_status='Paid', creation_datetime__date__range=(start_date, end_date))

                total_revenue = sum(payment.amount_paid for payment in paid_payments)

            elif period == 'yearly':
                selected_year = int(period_date_start)

                start_date = datetime(selected_year, 1, 1).date()
                end_date = datetime(selected_year, 12, 31).date()

                paid_payments = Payment.objects.filter(payment_status='Paid', creation_datetime__date__range=(start_date, end_date))

                total_revenue = sum(payment.amount_paid for payment in paid_payments)
            
            response = HttpResponse(content_type='application/pdf')
            filename = f"{period}_sales_report.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            doc = SimpleDocTemplate(response, pagesize=letter)
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Title'],
                fontSize=12,
                spaceAfter=3,
                textColor=colors.black,
                leading=18,
            )

            story = []

            report_title = (
                "Mayflower Parking Sales and Revenue Report<br/>"
                "Greenfield District Mandaluyong<br/>"
            )

            if period == 'daily':
                report_title += f"Date: {datetime.strptime(period_date_start, '%Y-%m-%d').date().strftime('%B %d, %Y')}"
            elif period == 'weekly':
                report_title += f"Date: {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
            elif period == 'monthly':
                year, month = period_date_start.split('-')
                month = datetime.strptime(period_date_start, '%Y-%m').date().strftime('%B')
                report_title += f"Date: {month} {year}"
            elif period == 'yearly':
                report_title += f"Date: {period_date_start}"

            story.append(Paragraph(report_title, title_style))

            table_data = [['ID', 'Date & Time', 'Amount Paid', 'Fee Type']]

            for payment in paid_payments:
                payment_details = [
                    payment.booking.id,
                    timezone.localtime(payment.booking.start_time).strftime('%B %d, %Y, %I:%M %p'),
                    f'PHP {payment.amount_paid}',
                    payment.fee_type,
                ]
                table_data.append(payment_details)

            col_widths = [170, 150, 80, 80]

            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor("#3B5D50")),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#CFCFCF")),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'), 
                ('BOTTOMPADDING', (0, 0), (-1, 0), 3), 
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#CFCFCF")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, 0), 8), 
                ('LEADING', (0, 0), (-1, 0), 8),  
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),  
                ('LEFTPADDING', (0, 0), (-1, -1), 3),  
                ('RIGHTPADDING', (0, 0), (-1, -1), 3), 
                ('LEFT', (0, 0), (-1, -1), 0),
            ]))

            story.append(table)
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"Total Revenue: PHP {total_revenue}\n\n\n", styles["Normal"]))

            doc.build(story)

            return response
            
        elif report_type == 'occupancy':

            if period == 'realtime':
                
                total_slots = Slot.objects.count()
                occupied_slots = Slot.objects.filter(status='Occupied').count()
                vacant_slots = Slot.objects.filter(status='Vacant').count()
                reserved_slots = Slot.objects.filter(status='Reserved').count()

                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="occupancy_report.pdf"'
                doc = SimpleDocTemplate(response, pagesize=letter)
                styles = getSampleStyleSheet()
                story = []
                
                current_time = timezone.now()

                title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=12, spaceBefore=1, spaceAfter=1, textColor=colors.black, leading=18)

                subheading_style = ParagraphStyle(name='CenteredSubheading', alignment=1)

                report_title = ("Mayflower Parking Occupancy Report<br/>")

                subheading = (
                    "Greenfield District Mandaluyong<br/>"
                    f"(Taken on {timezone.localtime(current_time).strftime('%B %d, %Y, %I:%M %p')})"
                )


                story.append(Paragraph(report_title, title_style))
                story.append(Paragraph(subheading, subheading_style))        
                story.append(Spacer(1, 1)) 

                labels = ['Occupied', 'Vacant', 'Reserved']
                sizes = [occupied_slots, vacant_slots, reserved_slots]
                mpl_colors = ['#F9BF29', '#DA6A00', '#3B5D50'] 
                explode = (0.1, 0, 0) 

                fig, ax = plt.subplots()
                ax.pie(sizes, explode=explode, labels=labels, colors=mpl_colors, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')

                buffer = BytesIO()
                canvas = FigureCanvas(fig)
                canvas.print_png(buffer)
                plt.close(fig)
                buffer.seek(0)

                image = Image(buffer, width=280, height=220)

                table_data = [
                    [image, f"Total Slots: {total_slots}\nOccupied Slots: {occupied_slots}\nVacant Slots: {vacant_slots}\nReserved Slots: {reserved_slots}"]
                ]

                table = Table(table_data, colWidths=[200, 220])
                table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                    ('LEFTPADDING', (1, 0), (1, 0), 10),
                    ('RIGHTPADDING', (0, 0), (0, 0), 10),
                ]))

                story.append(Paragraph("Slot and Occupancy Information", styles["Heading4"]))
                story.append(Spacer(0, 0))
                story.append(table)

                # HOURLY PEAKS  
                current_time = timezone.localtime(current_time).date()
                start_time = datetime.combine(current_time, datetime.min.time())
                end_time = datetime.combine(current_time, datetime.max.time())

                daily_peaks = (Booking.objects.filter(created_at__range=(start_time, end_time)).values('created_at__hour').annotate(bookings_count=Count('id')).order_by('-bookings_count')[:3])

                daily_peaks_data = [['Ranking', 'Time Interval', 'Number of Bookings']]
                for rank, peak in enumerate(daily_peaks, start=1):
                    start_hour = peak['created_at__hour']
                    end_hour = (start_hour + 1) % 24
                    peak_count = peak['bookings_count']

                    start_time_formatted = datetime.strptime(f"{start_hour:02d}:00", "%H:%M").strftime("%I:%M %p")
                    end_time_formatted = datetime.strptime(f"{end_hour:02d}:00", "%H:%M").strftime("%I:%M %p")

                    peak_interval = f"{start_time_formatted} - {end_time_formatted}"
                    daily_peaks_data.append([rank, peak_interval, peak_count])

                daily_peaks_col_widths = [156, 156, 156] 

                daily_peaks_table = Table(daily_peaks_data, colWidths=daily_peaks_col_widths)
                daily_peaks_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor("#3B5D50")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#CFCFCF")),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 1, HexColor("#CFCFCF")),
                ]))

                story.append(Paragraph("Hourly Peak", styles["Heading4"]))
                story.append(Spacer(0, 0))
                story.append(daily_peaks_table)

                # WEEKLY PEAKS
                current_date = timezone.localtime(timezone.now()).date()
                start_of_week = current_date - timedelta(days=(current_date.weekday() + 1) % 7)
                end_of_week = start_of_week + timedelta(days=6)

                daily_peaks = []

                for day in range((current_date - start_of_week).days + 1):
                    date_of_peak = start_of_week + timedelta(days=day)
                    peak_count = (Booking.objects.filter(created_at__date=date_of_peak).count())
                    daily_peaks.append({'date': date_of_peak, 'count': peak_count})

                daily_peaks.sort(key=lambda x: x['count'], reverse=True)

                weekly_peaks_data = [['Ranking', 'Day', 'Number of Bookings']]

                for rank, peak in enumerate(daily_peaks[:3], start=1):
                    day_name = peak['date'].strftime("%A") 
                    peak_interval = [rank, day_name, peak['count']]
                    weekly_peaks_data.append(peak_interval)

                weekly_peaks_col_widths = [156, 156, 156] 

                weekly_peaks_table = Table(weekly_peaks_data, colWidths=weekly_peaks_col_widths)
                weekly_peaks_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor("#3B5D50")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#CFCFCF")),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 1, HexColor("#CFCFCF")),
                ]))

                story.append(Paragraph("Weekly Peak", styles["Heading4"]))
                story.append(Spacer(0, 0))
                story.append(weekly_peaks_table)

                # MONTHLY PEAKS
                current_date = timezone.localtime(timezone.now()).date()
                start_of_year = datetime(current_date.year, 1, 1)
                end_of_year = datetime(current_date.year, 12, 31)

                yearly_peaks = (Booking.objects.filter(created_at__range=(start_of_year, end_of_year)).values('created_at__month').annotate(bookings_count=Count('id')).order_by('-bookings_count')[:3])

                yearly_peaks_data = [['Ranking', 'Month', 'Number of Bookings']]

                for rank, peak in enumerate(yearly_peaks, start=1):
                    month_number = peak['created_at__month']
                    month_name = datetime(2000, month_number, 1).strftime('%B')
                    peak_count = peak['bookings_count']
                    yearly_peak_interval = [rank, month_name, peak_count]
                    yearly_peaks_data.append(yearly_peak_interval)

                yearly_peaks_col_widths = [156, 156, 156]
                yearly_peaks_table = Table(yearly_peaks_data, colWidths=yearly_peaks_col_widths)
                yearly_peaks_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor("#3B5D50")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#CFCFCF")),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 1, HexColor("#CFCFCF")),
                ]))

                story.append(Paragraph("Monthly Peak", styles["Heading4"]))
                story.append(Spacer(0, 0))
                story.append(yearly_peaks_table)

                if len(yearly_peaks) > 1:
                    conclusion_text = "The analysis indicates a variance in booking trends across different months within the year."
                else:
                    conclusion_text = "The analysis shows consistent booking patterns across the months in the year."

                # ACTIVE USERS
                active_users = CustomUser.objects.exclude(is_staff=True).annotate(num_bookings=Count('booking')).order_by('-num_bookings')[:5]

                active_users_data = [['Ranking', 'Name', 'Number of Bookings']]

                for rank, user in enumerate(active_users, start=1):
                    name = user.first_name + ' ' + user.last_name
                    user_info = [rank, name, user.num_bookings]
                    active_users_data.append(user_info)

                active_users_col_widths = [156, 156, 156]
                active_users_table = Table(active_users_data, colWidths=active_users_col_widths)
                active_users_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor("#3B5D50")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#CFCFCF")),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 1, HexColor("#CFCFCF")),
                ]))

                story.append(Paragraph("Most Active Users", styles["Heading4"]))
                story.append(Spacer(0, 0))
                story.append(active_users_table)

                # USER STATISTICS
                total_users = CustomUser.objects.filter(is_staff=False).count()
                total_bookings = Booking.objects.filter(user__in=CustomUser.objects.all()).count()
                average_bookings_per_user = total_bookings / total_users if total_users > 0 else 0

                story.append(Spacer(1, 10))
                story.append(Paragraph(f"Total Users: {total_users}\n"))
                story.append(Paragraph(f"Average Bookings per user: {average_bookings_per_user:.2f}\n"))


                # LINE CHART
                all_months_abbr = [datetime(2000, month, 1).strftime('%b') for month in range(1, 13)]

                monthly_peak_data_dict = {month_abbr: 0 for month_abbr in all_months_abbr}

                for peak in yearly_peaks:
                    month_number = peak['created_at__month']
                    month_abbr = datetime(2000, month_number, 1).strftime('%b')
                    monthly_peak_data_dict[month_abbr] = peak['bookings_count']

                monthly_peak_data = [{'month': month_abbr, 'count': monthly_peak_data_dict[month_abbr]} for month_abbr in all_months_abbr]

                plt.figure(figsize=(6, 3))
                plt.plot([item['month'] for item in monthly_peak_data], [item['count'] for item in monthly_peak_data], marker='o', color='#F9BF29')
                plt.xlabel('Months', fontweight='bold', fontsize=8)
                plt.ylabel('Number of Bookings', fontweight='bold', fontsize=8)
                plt.grid(True)
                plt.xticks(color='#3B5D50', weight='bold', fontsize=8)
                plt.yticks(color='#3B5D50', weight='bold', fontsize=8)

                ax = plt.gca()
                ax.xaxis.grid(False)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)

                plt.margins(x=0.1)

                buffer = BytesIO()
                plt.savefig(buffer, format='png')
                plt.close()
                buffer.seek(0)

                image = Image(buffer, width=300, height=150)

                combined_table_data = [
                    [image]
                ]

                combined_table_col_widths = [250, 250]
                combined_table = Table(combined_table_data, colWidths=combined_table_col_widths)
                combined_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),  
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'), 
                ]))

                story.append(PageBreak())
                story.append(Paragraph("Monthly Performance Chart", styles["Heading4"]))
                story.append(Spacer(0, 0))
                story.append(combined_table)
                story.append(Spacer(1, 12))
                centered_style = ParagraphStyle(name='Centered', alignment=TA_CENTER)
                story.append(Spacer(1, 8))
                story.append(Paragraph(conclusion_text, centered_style))

                doc.build(story)

                return response
                
    return render(request, 'admin/generate_report.html')

@staff_member_required
def scan_qr(request):
    return render(request, 'admin/scan_qr.html', {})

@staff_member_required
def surveillance(request):
    return render(request, 'admin/surveillance.html', {})
