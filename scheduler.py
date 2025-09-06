import time
import threading
import logging
import schedule
from datetime import datetime, timedelta
from email_bot import start_email_monitoring
from app import app
from database import db
from models import Candidate, Job, CandidateJobMatch, EmailLog, WhatsAppLog
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_daily_report():
    """Generate daily recruitment report"""
    with app.app_context():
        try:
            # Calculate date range
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            # Get statistics
            new_candidates_today = Candidate.query.filter(
                Candidate.created_at >= yesterday
            ).count()
            
            new_matches_today = CandidateJobMatch.query.filter(
                CandidateJobMatch.created_at >= yesterday
            ).count()
            
            high_matches_today = CandidateJobMatch.query.filter(
                CandidateJobMatch.created_at >= yesterday,
                CandidateJobMatch.match_score >= 80
            ).count()
            
            emails_processed_today = EmailLog.query.filter(
                EmailLog.processed_at >= yesterday
            ).count()
            
            whatsapp_processed_today = WhatsAppLog.query.filter(
                WhatsAppLog.processed_at >= yesterday
            ).count()
            
            # Get top matches
            top_matches = db.session.query(CandidateJobMatch, Candidate, Job)\
                .join(Candidate, CandidateJobMatch.candidate_id == Candidate.id)\
                .join(Job, CandidateJobMatch.job_id == Job.id)\
                .filter(CandidateJobMatch.created_at >= yesterday)\
                .filter(CandidateJobMatch.match_score >= 70)\
                .order_by(CandidateJobMatch.match_score.desc())\
                .limit(10).all()
            
            # Generate report
            report = {
                'date': today.strftime('%Y-%m-%d'),
                'new_candidates': new_candidates_today,
                'new_matches': new_matches_today,
                'high_matches': high_matches_today,
                'emails_processed': emails_processed_today,
                'whatsapp_processed': whatsapp_processed_today,
                'top_matches': [
                    {
                        'candidate': match.Candidate.name,
                        'job': match.Job.title,
                        'score': match.CandidateJobMatch.match_score,
                        'email': match.Candidate.email
                    }
                    for match in top_matches
                ]
            }
            
            logger.info(f"Generated daily report: {new_candidates_today} new candidates, {high_matches_today} high matches")
            
            # Send report via email if configured
            if os.getenv('SMTP_ENABLED', 'false').lower() == 'true':
                send_daily_report_email(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return None

def send_daily_report_email(report):
    """Send daily report via email"""
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        report_recipients = os.getenv('REPORT_RECIPIENTS', '').split(',')
        
        if not smtp_user or not report_recipients[0]:
            logger.warning("SMTP credentials or recipients not configured for daily reports")
            return
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = ', '.join(report_recipients)
        msg['Subject'] = f"Daily Recruitment Report - {report['date']}"
        
        # Create HTML content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #f8f9fa; padding: 20px; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat {{ text-align: center; }}
                .stat h3 {{ color: #007bff; margin: 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Daily Recruitment Report</h2>
                <p>Report Date: {report['date']}</p>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <h3>{report['new_candidates']}</h3>
                    <p>New Candidates</p>
                </div>
                <div class="stat">
                    <h3>{report['new_matches']}</h3>
                    <p>New Matches</p>
                </div>
                <div class="stat">
                    <h3>{report['high_matches']}</h3>
                    <p>High Score Matches (80+)</p>
                </div>
                <div class="stat">
                    <h3>{report['emails_processed']}</h3>
                    <p>Emails Processed</p>
                </div>
                <div class="stat">
                    <h3>{report['whatsapp_processed']}</h3>
                    <p>WhatsApp Messages</p>
                </div>
            </div>
            
            <h3>Top Matches (Score 70+)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Candidate</th>
                        <th>Job</th>
                        <th>Match Score</th>
                        <th>Email</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for match in report['top_matches']:
            html_content += f"""
                    <tr>
                        <td>{match['candidate']}</td>
                        <td>{match['job']}</td>
                        <td>{match['score']}%</td>
                        <td>{match['email']}</td>
                    </tr>
            """
        
        html_content += """
                </tbody>
            </table>
            
            <p><em>This is an automated report from the Recruitment Automation System.</em></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        logger.info(f"Daily report sent to {len(report_recipients)} recipients")
        
    except Exception as e:
        logger.error(f"Error sending daily report email: {e}")

def generate_weekly_report():
    """Generate weekly recruitment report"""
    with app.app_context():
        try:
            # Calculate date range
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)
            
            # Get weekly statistics
            new_candidates_week = Candidate.query.filter(
                Candidate.created_at >= week_ago
            ).count()
            
            total_candidates = Candidate.query.count()
            total_jobs = Job.query.count()
            total_matches = CandidateJobMatch.query.count()
            
            high_matches_week = CandidateJobMatch.query.filter(
                CandidateJobMatch.created_at >= week_ago,
                CandidateJobMatch.match_score >= 80
            ).count()
            
            # Get performance by source
            email_candidates = Candidate.query.filter_by(source='email').count()
            whatsapp_candidates = Candidate.query.filter_by(source='whatsapp').count()
            manual_candidates = Candidate.query.filter_by(source='manual').count()
            
            # Average match scores
            avg_match_score = db.session.query(db.func.avg(CandidateJobMatch.match_score)).scalar() or 0
            
            report = {
                'week_ending': today.strftime('%Y-%m-%d'),
                'new_candidates_week': new_candidates_week,
                'total_candidates': total_candidates,
                'total_jobs': total_jobs,
                'total_matches': total_matches,
                'high_matches_week': high_matches_week,
                'avg_match_score': round(avg_match_score, 1),
                'source_breakdown': {
                    'email': email_candidates,
                    'whatsapp': whatsapp_candidates,
                    'manual': manual_candidates
                }
            }
            
            logger.info(f"Generated weekly report: {new_candidates_week} new candidates this week")
            
            # Send weekly report if enabled
            if os.getenv('SMTP_ENABLED', 'false').lower() == 'true':
                send_weekly_report_email(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            return None

def send_weekly_report_email(report):
    """Send weekly report via email"""
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        report_recipients = os.getenv('REPORT_RECIPIENTS', '').split(',')
        
        if not smtp_user or not report_recipients[0]:
            logger.warning("SMTP credentials or recipients not configured for weekly reports")
            return
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = ', '.join(report_recipients)
        msg['Subject'] = f"Weekly Recruitment Report - Week Ending {report['week_ending']}"
        
        # Create HTML content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #f8f9fa; padding: 20px; }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: #fff; border: 1px solid #ddd; padding: 20px; text-align: center; }}
                .stat-card h3 {{ color: #007bff; margin: 0 0 10px 0; }}
                .source-breakdown {{ margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Weekly Recruitment Report</h2>
                <p>Week Ending: {report['week_ending']}</p>
            </div>
            
            <div class="grid">
                <div class="stat-card">
                    <h3>{report['new_candidates_week']}</h3>
                    <p>New Candidates This Week</p>
                </div>
                <div class="stat-card">
                    <h3>{report['total_candidates']}</h3>
                    <p>Total Candidates</p>
                </div>
                <div class="stat-card">
                    <h3>{report['total_jobs']}</h3>
                    <p>Active Jobs</p>
                </div>
                <div class="stat-card">
                    <h3>{report['total_matches']}</h3>
                    <p>Total Matches</p>
                </div>
                <div class="stat-card">
                    <h3>{report['high_matches_week']}</h3>
                    <p>High Score Matches This Week</p>
                </div>
                <div class="stat-card">
                    <h3>{report['avg_match_score']}%</h3>
                    <p>Average Match Score</p>
                </div>
            </div>
            
            <div class="source-breakdown">
                <h3>Candidate Sources</h3>
                <ul>
                    <li>Email Applications: {report['source_breakdown']['email']}</li>
                    <li>WhatsApp Applications: {report['source_breakdown']['whatsapp']}</li>
                    <li>Manual Uploads: {report['source_breakdown']['manual']}</li>
                </ul>
            </div>
            
            <p><em>This is an automated weekly report from the Recruitment Automation System.</em></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        logger.info(f"Weekly report sent to {len(report_recipients)} recipients")
        
    except Exception as e:
        logger.error(f"Error sending weekly report email: {e}")

def cleanup_old_logs():
    """Clean up old log entries"""
    with app.app_context():
        try:
            # Delete logs older than 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            
            old_email_logs = EmailLog.query.filter(EmailLog.processed_at < cutoff_date).count()
            old_whatsapp_logs = WhatsAppLog.query.filter(WhatsAppLog.processed_at < cutoff_date).count()
            
            EmailLog.query.filter(EmailLog.processed_at < cutoff_date).delete()
            WhatsAppLog.query.filter(WhatsAppLog.processed_at < cutoff_date).delete()
            
            db.session.commit()
            
            logger.info(f"Cleaned up {old_email_logs} email logs and {old_whatsapp_logs} WhatsApp logs")
            
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
            db.session.rollback()

def schedule_tasks():
    """Schedule all background tasks"""
    # Daily report at 8 AM
    schedule.every().day.at("08:00").do(generate_daily_report)
    
    # Weekly report on Monday at 9 AM
    schedule.every().monday.at("09:00").do(generate_weekly_report)
    
    # Clean up logs every Sunday at 2 AM
    schedule.every().sunday.at("02:00").do(cleanup_old_logs)
    
    logger.info("Scheduled tasks configured")

def run_scheduler():
    """Run the scheduler loop"""
    logger.info("Starting scheduler...")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(300)  # Wait 5 minutes before retrying

def start_background_services():
    """Start all background services"""
    logger.info("Starting background services...")
    
    # Schedule tasks
    schedule_tasks()
    
    # Start email monitoring in a separate thread
    email_thread = threading.Thread(target=start_email_monitoring, daemon=True)
    email_thread.start()
    logger.info("Email monitoring started")
    
    # Start scheduler
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Scheduler started")
    
    logger.info("All background services started successfully")

if __name__ == '__main__':
    start_background_services()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Background services stopped")
