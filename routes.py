import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from database import db
from models import User, Job, Candidate, CandidateJobMatch, JobStatus, CandidateStatus, WhatsAppContact
# Note: CV parsing, job matching, and email processing are handled externally by N8N
# This app only provides the frontend dashboard and API endpoints
import logging

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def register_routes(app):
    @app.route('/')
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        return redirect(url_for('dashboard'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Get dashboard statistics
        total_jobs = Job.query.filter_by(status=JobStatus.ACTIVE).count()
        total_candidates = Candidate.query.count()
        new_candidates = Candidate.query.filter_by(status=CandidateStatus.NEW).count()
        high_matches = CandidateJobMatch.query.filter(CandidateJobMatch.match_score >= 80).count()
        
        # Get recent candidates
        recent_candidates = Candidate.query.order_by(Candidate.created_at.desc()).limit(5).all()
        
        # Get high-scoring matches
        high_scoring_matches = db.session.query(CandidateJobMatch, Candidate, Job)\
            .join(Candidate, CandidateJobMatch.candidate_id == Candidate.id)\
            .join(Job, CandidateJobMatch.job_id == Job.id)\
            .filter(CandidateJobMatch.match_score >= 70)\
            .order_by(CandidateJobMatch.match_score.desc())\
            .limit(10).all()
        
        return render_template('dashboard.html',
                             total_jobs=total_jobs,
                             total_candidates=total_candidates,
                             new_candidates=new_candidates,
                             high_matches=high_matches,
                             recent_candidates=recent_candidates,
                             high_scoring_matches=high_scoring_matches)

    @app.route('/jobs')
    @login_required
    def jobs():
        # Get filter parameters
        status_filter = request.args.get('status', '')
        search = request.args.get('search', '')
        experience_level = request.args.get('experience_level', '')
        job_type = request.args.get('job_type', '')
        
        # Base query
        query = Job.query
        
        # Apply filters
        if status_filter and status_filter != 'all':
            if status_filter == 'active':
                query = query.filter(Job.status == JobStatus.ACTIVE)
            elif status_filter == 'paused':
                query = query.filter(Job.status == JobStatus.PAUSED)
            elif status_filter == 'closed':
                query = query.filter(Job.status == JobStatus.CLOSED)
        
        if experience_level and experience_level != 'all':
            query = query.filter(Job.experience_level == experience_level)
            
        if job_type and job_type != 'all':
            query = query.filter(Job.job_type == job_type)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Job.title.like(search_term),
                    Job.description.like(search_term),
                    Job.requirements.like(search_term),
                    Job.location.like(search_term)
                )
            )
        
        # Get jobs with pagination
        page = request.args.get('page', 1, type=int)
        jobs = query.order_by(Job.created_at.desc()).paginate(
            page=page, per_page=10, error_out=False
        )
        
        # Get statistics
        stats = {
            'total_jobs': Job.query.count(),
            'active_jobs': Job.query.filter_by(status=JobStatus.ACTIVE).count(),
            'paused_jobs': Job.query.filter_by(status=JobStatus.PAUSED).count(),
            'closed_jobs': Job.query.filter_by(status=JobStatus.CLOSED).count()
        }
        
        return render_template('jobs.html', 
                             jobs=jobs, 
                             stats=stats,
                             status_filter=status_filter,
                             search=search,
                             experience_level=experience_level,
                             job_type=job_type)

    @app.route('/jobs/create', methods=['GET', 'POST'])
    @login_required
    def create_job():
        if request.method == 'POST':
            job = Job(
                title=request.form['title'],
                description=request.form['description'],
                requirements=request.form['requirements'],
                location=request.form.get('location'),
                salary_min=request.form.get('salary_min', type=int),
                salary_max=request.form.get('salary_max', type=int),
                experience_level=request.form.get('experience_level'),
                job_type=request.form.get('job_type'),
                created_by=current_user.id
            )
            
            db.session.add(job)
            db.session.commit()
            flash('Job created successfully!', 'success')
            return redirect(url_for('jobs'))
        
        return render_template('create_job.html')

    @app.route('/jobs/<int:job_id>/toggle')
    @login_required
    def toggle_job_status(job_id):
        job = Job.query.get_or_404(job_id)
        if job.status == JobStatus.ACTIVE:
            job.status = JobStatus.PAUSED
            flash('Job paused successfully!', 'success')
        else:
            job.status = JobStatus.ACTIVE
            flash('Job activated successfully!', 'success')
        
        db.session.commit()
        return redirect(url_for('jobs'))

    @app.route('/jobs/<int:job_id>/delete', methods=['POST'])
    @login_required
    def delete_job(job_id):
        """Hard delete a job and all its associated data"""
        try:
            job = Job.query.get_or_404(job_id)
            job_title = job.title
            
            # Delete all associated candidate job matches first
            CandidateJobMatch.query.filter_by(job_id=job_id).delete()
            
            # Delete the job
            db.session.delete(job)
            db.session.commit()
            
            flash(f'Job "{job_title}" has been permanently deleted', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting job: {str(e)}', 'error')
        
        return redirect(url_for('jobs'))

    @app.route('/api/jobs/<int:job_id>', methods=['GET'])
    @login_required
    def api_job_detail(job_id):
        """API endpoint to get detailed information about a specific job"""
        try:
            job = Job.query.get_or_404(job_id)
            
            # Get candidate matches for this job
            job_matches = CandidateJobMatch.query.filter_by(job_id=job_id)\
                .order_by(CandidateJobMatch.match_score.desc()).limit(5).all()
            
            # Get candidate details for top matches
            top_matches = []
            for match in job_matches:
                candidate = Candidate.query.get(match.candidate_id)
                if candidate:
                    top_matches.append({
                        'id': candidate.id,
                        'name': candidate.name,
                        'email': candidate.email,
                        'match_score': match.match_score,
                        'matching_skills': match.matching_skills or [],
                        'missing_skills': match.missing_skills or []
                    })
            
            job_data = {
                'id': job.id,
                'title': job.title,
                'description': job.description,
                'requirements': job.requirements,
                'location': job.location,
                'salary_min': job.salary_min,
                'salary_max': job.salary_max,
                'experience_level': job.experience_level,
                'job_type': job.job_type,
                'status': job.status.value,
                'created_at': job.created_at.isoformat(),
                'required_skills': job.required_skills or [],
                'preferred_skills': job.preferred_skills or [],
                'top_matches': top_matches,
                'total_matches': len(job_matches)
            }
            
            return jsonify({
                'success': True,
                'job': job_data
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/candidates')
    @login_required
    def candidates():
        # Get filter parameters
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status', '')
        source_filter = request.args.get('source', '')
        search = request.args.get('search', '')
        experience_min = request.args.get('experience_min', type=int)
        experience_max = request.args.get('experience_max', type=int)
        
        # Base query
        query = Candidate.query
        
        # Apply filters
        if status_filter and status_filter != 'all':
            query = query.filter_by(status=CandidateStatus(status_filter))
            
        if source_filter and source_filter != 'all':
            query = query.filter_by(source=source_filter)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Candidate.name.like(search_term),
                    Candidate.email.like(search_term),
                    Candidate.location.like(search_term),
                    Candidate.summary.like(search_term)
                )
            )
            
        if experience_min is not None:
            query = query.filter(Candidate.experience_years >= experience_min)
            
        if experience_max is not None:
            query = query.filter(Candidate.experience_years <= experience_max)
        
        candidates = query.order_by(Candidate.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        # Get statistics
        stats = {
            'total_candidates': Candidate.query.count(),
            'new_candidates': Candidate.query.filter_by(status=CandidateStatus.NEW).count(),
            'reviewed_candidates': Candidate.query.filter_by(status=CandidateStatus.REVIEWED).count(),
            'shortlisted_candidates': Candidate.query.filter_by(status=CandidateStatus.SHORTLISTED).count(),
            'email_candidates': Candidate.query.filter_by(source='email').count(),
            'whatsapp_candidates': Candidate.query.filter_by(source='whatsapp').count()
        }
        
        return render_template('candidates_simplified.html', 
                             candidates=candidates, 
                             statuses=CandidateStatus,
                             stats=stats,
                             status_filter=status_filter,
                             source_filter=source_filter,
                             search=search,
                             experience_min=experience_min,
                             experience_max=experience_max)

    @app.route('/candidates/<int:candidate_id>')
    @login_required
    def candidate_detail(candidate_id):
        candidate = Candidate.query.get_or_404(candidate_id)
        
        # Get job matches with job details
        job_matches = db.session.query(CandidateJobMatch, Job)\
            .join(Job, CandidateJobMatch.job_id == Job.id)\
            .filter(CandidateJobMatch.candidate_id == candidate_id)\
            .order_by(CandidateJobMatch.match_score.desc()).all()
        
        return render_template('candidate_detail.html', 
                             candidate=candidate, 
                             job_matches=job_matches)

    @app.route('/candidates/<int:candidate_id>/status', methods=['POST'])
    @login_required
    def update_candidate_status(candidate_id):
        candidate = Candidate.query.get_or_404(candidate_id)
        new_status = request.form.get('status')
        
        if new_status in [status.value for status in CandidateStatus]:
            candidate.status = CandidateStatus(new_status)
            db.session.commit()
            flash(f'Candidate status updated to {new_status}', 'success')
        else:
            flash('Invalid status', 'error')
        
        return redirect(url_for('candidate_detail', candidate_id=candidate_id))

    # API endpoints
    @app.route('/api/jobs', methods=['GET'])
    def api_jobs():
        """API endpoint to get all active jobs"""
        try:
            jobs = Job.query.filter_by(status=JobStatus.ACTIVE).all()
            jobs_data = []
            for job in jobs:
                jobs_data.append({
                    'id': job.id,
                    'title': job.title,
                    'description': job.description,
                    'requirements': job.requirements,
                    'location': job.location,
                    'salary_min': job.salary_min,
                    'salary_max': job.salary_max,
                    'experience_level': job.experience_level,
                    'job_type': job.job_type
                })
            
            return jsonify({
                'success': True,
                'jobs': jobs_data,
                'count': len(jobs_data)
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/candidate', methods=['POST'])
    def api_candidate():
        """API endpoint to create a new candidate from external systems (N8N)"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            # Required fields validation
            required_fields = ['name', 'email']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        'success': False, 
                        'error': f'Missing required field: {field}'
                    }), 400
            
            # Check if candidate already exists
            existing_candidate = Candidate.query.filter_by(email=data.get('email')).first()
            if existing_candidate:
                return jsonify({
                    'success': False, 
                    'error': 'Candidate already exists',
                    'candidate_id': existing_candidate.id
                }), 409
            
            # Create new candidate
            candidate = Candidate(
                name=data.get('name', ''),
                email=data.get('email', ''),
                phone=data.get('phone', ''),
                location=data.get('location', ''),
                source=data.get('source', 'n8n'),
                source_reference=data.get('source_reference', ''),
                cv_filename=data.get('cv_filename', ''),  # Local filename if stored
                cv_drive_link=data.get('cv_drive_link', ''),  # Google Drive link
                cv_text=data.get('cv_text', ''),
                skills=data.get('skills', []),
                experience_years=data.get('experience_years'),
                education=data.get('education', []),
                work_experience=data.get('work_experience', []),
                summary=data.get('summary', '')
            )
            
            db.session.add(candidate)
            db.session.flush()  # Get the candidate ID for foreign keys
            
            # Process job scores if provided
            job_scores = data.get('job_scores', [])
            matches_created = 0
            
            for job_score in job_scores:
                try:
                    job_id = job_score.get('job_id')
                    score = job_score.get('score')
                    
                    if job_id is None or score is None:
                        continue
                    
                    # Create job match record
                    match = CandidateJobMatch(
                        candidate_id=candidate.id,
                        job_id=job_id,
                        match_score=score,
                        matching_skills=job_score.get('matching_skills', []),
                        missing_skills=job_score.get('missing_skills', []),
                        match_reason=job_score.get('reasons', ''),
                        status=CandidateStatus.NEW
                    )
                    
                    db.session.add(match)
                    matches_created += 1
                    
                except Exception as match_error:
                    # Log error but continue with other matches
                    print(f"Error creating match for job {job_score.get('job_id')}: {match_error}")
                    continue
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'candidate_id': candidate.id,
                'message': f'Candidate created successfully with {matches_created} job matches',
                'matches_created': matches_created,
                'total_job_scores': len(job_scores)
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/downloads/<filename>')
    @login_required
    def download_file(filename):
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

    @app.route('/api/stats')
    @login_required
    def api_stats():
        """API endpoint to get recruitment statistics"""
        try:
            total_jobs = Job.query.filter_by(status=JobStatus.ACTIVE).count()
            total_candidates = Candidate.query.count()
            new_candidates = Candidate.query.filter_by(status=CandidateStatus.NEW).count()
            high_matches = CandidateJobMatch.query.filter(CandidateJobMatch.match_score >= 80).count()
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_jobs': total_jobs,
                    'total_candidates': total_candidates,
                    'new_candidates': new_candidates,
                    'high_matches': high_matches
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/recent_activity')
    @login_required
    def api_recent_activity():
        """API endpoint to get recent recruitment activity"""
        try:
            recent_candidates = Candidate.query.order_by(Candidate.created_at.desc()).limit(10).all()
            recent_matches = CandidateJobMatch.query.order_by(CandidateJobMatch.created_at.desc()).limit(10).all()
            
            candidates_data = [{
                'id': c.id,
                'name': c.name,
                'email': c.email,
                'status': c.status.value,
                'created_at': c.created_at.isoformat()
            } for c in recent_candidates]
            
            matches_data = [{
                'id': m.id,
                'candidate_id': m.candidate_id,
                'job_id': m.job_id,
                'match_score': m.match_score,
                'created_at': m.created_at.isoformat()
            } for m in recent_matches]
            
            return jsonify({
                'success': True,
                'recent_candidates': candidates_data,
                'recent_matches': matches_data
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/notifications')
    @login_required
    def api_notifications():
        """API endpoint to get notifications for the dashboard"""
        try:
            notifications = []
            
            # Check for new candidates
            new_candidates_count = Candidate.query.filter_by(status=CandidateStatus.NEW).count()
            if new_candidates_count > 0:
                notifications.append({
                    'type': 'new_candidates',
                    'message': f'{new_candidates_count} new candidates to review',
                    'count': new_candidates_count
                })
            
            # Check for high-scoring matches
            high_matches_count = CandidateJobMatch.query.filter(CandidateJobMatch.match_score >= 80).count()
            if high_matches_count > 0:
                notifications.append({
                    'type': 'high_matches',
                    'message': f'{high_matches_count} high-scoring matches found',
                    'count': high_matches_count
                })
            
            return jsonify({
                'success': True,
                'notifications': notifications
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/test', methods=['GET'])
    def api_test():
        """Simple test endpoint to verify API is working"""
        return jsonify({
            'success': True,
            'message': 'API is working correctly',
            'timestamp': datetime.now().isoformat()
        })

    # WhatsApp webhook endpoints
    @app.route('/webhook/whatsapp', methods=['GET'])
    def whatsapp_webhook_verify():
        """WhatsApp webhook verification endpoint"""
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        # Verify token (you should set this in your environment variables)
        verify_token = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'your_verify_token')
        
        if mode == 'subscribe' and token == verify_token:
            return challenge
        else:
            return 'Forbidden', 403

    @app.route('/webhook/whatsapp', methods=['POST'])
    def whatsapp_webhook():
        """WhatsApp webhook to receive messages"""
        try:
            data = request.get_json()
            
            if data.get('object') == 'whatsapp_business_account':
                for entry in data.get('entry', []):
                    for change in entry.get('changes', []):
                        if change.get('value', {}).get('messages'):
                            for message in change['value']['messages']:
                                # Process WhatsApp message
                                process_whatsapp_message(message)
            
            return jsonify({'success': True}), 200
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def process_whatsapp_message(message):
        """Process incoming WhatsApp message"""
        try:
            # Extract message details
            phone_number = message.get('from')
            message_text = message.get('text', {}).get('body', '')
            message_id = message.get('id')
            
            # Log the message
            whatsapp_log = WhatsAppLog(
                phone_number=phone_number,
                message_id=message_id,
                status='received'
            )
            db.session.add(whatsapp_log)
            db.session.commit()
            
            # Here you would implement your WhatsApp message processing logic
            # For now, we just log the message
            
        except Exception as e:
            logging.error(f"Error processing WhatsApp message: {e}")
            db.session.rollback()

    # WhatsApp Contact Management API Endpoints
    @app.route('/api/whatsapp/contacts/upsert', methods=['POST'])
    def api_whatsapp_upsert_contact():
        """API endpoint to upsert WhatsApp contact information"""
        try:
            data = request.get_json()
            if not data or 'wa_id' not in data:
                return jsonify({
                    'success': False,
                    'error': 'wa_id is required'
                }), 400
            
            wa_id = data['wa_id']
            
            # Find existing contact or create new one
            contact = WhatsAppContact.query.filter_by(wa_id=wa_id).first()
            if not contact:
                contact = WhatsAppContact(wa_id=wa_id)
                db.session.add(contact)
            
            # Update fields if provided
            if 'eu_status' in data:
                contact.eu_status = data['eu_status']
            if 'country_code' in data:
                contact.country_code = data['country_code']
            if 'intent' in data:
                contact.intent = data['intent']
            if 'last_message_text' in data:
                contact.last_message_text = data['last_message_text']
            if 'last_message_type' in data:
                contact.last_message_type = data['last_message_type']
            if 'last_message_at' in data:
                from datetime import datetime
                contact.last_message_at = datetime.fromisoformat(data['last_message_at'].replace('Z', '+00:00'))
            if 'last_system_message_at' in data:
                from datetime import datetime
                contact.last_system_message_at = datetime.fromisoformat(data['last_system_message_at'].replace('Z', '+00:00'))
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'contact': {
                    'id': contact.id,
                    'wa_id': contact.wa_id,
                    'eu_status': contact.eu_status,
                    'country_code': contact.country_code,
                    'intent': contact.intent,
                    'last_message_text': contact.last_message_text,
                    'last_message_type': contact.last_message_type,
                    'last_message_at': contact.last_message_at.isoformat() if contact.last_message_at else None,
                    'last_system_message_at': contact.last_system_message_at.isoformat() if contact.last_system_message_at else None,
                    'created_at': contact.created_at.isoformat(),
                    'updated_at': contact.updated_at.isoformat()
                }
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/whatsapp/contacts/<wa_id>', methods=['GET'])
    def api_whatsapp_get_contact(wa_id):
        """API endpoint to get WhatsApp contact information"""
        try:
            contact = WhatsAppContact.query.filter_by(wa_id=wa_id).first()
            
            if not contact:
                return jsonify({
                    'success': False,
                    'error': 'Contact not found'
                }), 404
            
            return jsonify({
                'success': True,
                'id': contact.id,
                'wa_id': contact.wa_id,
                'eu_status': contact.eu_status,
                'country_code': contact.country_code,
                'intent': contact.intent,
                'last_message_text': contact.last_message_text,
                'last_message_type': contact.last_message_type,
                'last_message_at': contact.last_message_at.isoformat() if contact.last_message_at else None,
                'last_system_message_at': contact.last_system_message_at.isoformat() if contact.last_system_message_at else None,
                'created_at': contact.created_at.isoformat(),
                'updated_at': contact.updated_at.isoformat()
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/whatsapp/contacts/<wa_id>', methods=['PATCH'])
    def api_whatsapp_update_contact(wa_id):
        """API endpoint to update WhatsApp contact information"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
            
            contact = WhatsAppContact.query.filter_by(wa_id=wa_id).first()
            if not contact:
                return jsonify({
                    'success': False,
                    'error': 'Contact not found'
                }), 404
            
            # Update fields if provided
            if 'eu_status' in data:
                contact.eu_status = data['eu_status']
            if 'country_code' in data:
                contact.country_code = data['country_code']
            if 'intent' in data:
                contact.intent = data['intent']
            if 'last_message_text' in data:
                contact.last_message_text = data['last_message_text']
            if 'last_message_type' in data:
                contact.last_message_type = data['last_message_type']
            if 'last_message_at' in data:
                from datetime import datetime
                contact.last_message_at = datetime.fromisoformat(data['last_message_at'].replace('Z', '+00:00'))
            if 'last_system_message_at' in data:
                from datetime import datetime
                contact.last_system_message_at = datetime.fromisoformat(data['last_system_message_at'].replace('Z', '+00:00'))
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'contact': {
                    'id': contact.id,
                    'wa_id': contact.wa_id,
                    'eu_status': contact.eu_status,
                    'country_code': contact.country_code,
                    'intent': contact.intent,
                    'last_message_text': contact.last_message_text,
                    'last_message_type': contact.last_message_type,
                    'last_message_at': contact.last_message_at.isoformat() if contact.last_message_at else None,
                    'last_system_message_at': contact.last_system_message_at.isoformat() if contact.last_system_message_at else None,
                    'created_at': contact.created_at.isoformat(),
                    'updated_at': contact.updated_at.isoformat()
                }
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/whatsapp-contacts')
    @login_required
    def whatsapp_contacts():
        """WhatsApp contacts admin page"""
        try:
            # Get filter parameters
            eu_filter = request.args.get('eu_status', '')
            intent_filter = request.args.get('intent', '')
            search = request.args.get('search', '')
            
            # Base query
            query = WhatsAppContact.query
            
            # Apply filters
            if eu_filter and eu_filter != 'all':
                query = query.filter(WhatsAppContact.eu_status == eu_filter)
            
            if intent_filter and intent_filter != 'all':
                if intent_filter == 'none':
                    query = query.filter(WhatsAppContact.intent.is_(None))
                else:
                    query = query.filter(WhatsAppContact.intent == intent_filter)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    db.or_(
                        WhatsAppContact.wa_id.like(search_term),
                        WhatsAppContact.last_message_text.like(search_term),
                        WhatsAppContact.country_code.like(search_term)
                    )
                )
            
            # Get contacts with pagination
            page = request.args.get('page', 1, type=int)
            per_page = 20
            contacts = query.order_by(WhatsAppContact.updated_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # Get statistics
            stats = {
                'total_contacts': WhatsAppContact.query.count(),
                'eu_contacts': WhatsAppContact.query.filter_by(eu_status='eu').count(),
                'non_eu_contacts': WhatsAppContact.query.filter_by(eu_status='non-eu').count(),
                'unknown_location': WhatsAppContact.query.filter_by(eu_status='unknown').count(),
                'clients': WhatsAppContact.query.filter_by(intent='client').count(),
                'candidates': WhatsAppContact.query.filter_by(intent='candidate').count(),
                'no_intent': WhatsAppContact.query.filter(WhatsAppContact.intent.is_(None)).count()
            }
            
            return render_template('whatsapp_contacts.html', 
                                 contacts=contacts, 
                                 stats=stats,
                                 eu_filter=eu_filter,
                                 intent_filter=intent_filter,
                                 search=search)
            
        except Exception as e:
            flash(f'Error loading WhatsApp contacts: {str(e)}', 'error')
            return redirect(url_for('dashboard'))

    @app.route('/api/whatsapp/contacts', methods=['GET'])
    def api_whatsapp_list_contacts():
        """API endpoint to list all WhatsApp contacts for admin page"""
        try:
            contacts = WhatsAppContact.query.order_by(WhatsAppContact.updated_at.desc()).all()
            
            contacts_data = []
            for contact in contacts:
                contacts_data.append({
                    'id': contact.id,
                    'wa_id': contact.wa_id,
                    'eu_status': contact.eu_status,
                    'country_code': contact.country_code,
                    'intent': contact.intent,
                    'last_message_text': contact.last_message_text,
                    'last_message_type': contact.last_message_type,
                    'last_message_at': contact.last_message_at.isoformat() if contact.last_message_at else None,
                    'last_system_message_at': contact.last_system_message_at.isoformat() if contact.last_system_message_at else None,
                    'created_at': contact.created_at.isoformat(),
                    'updated_at': contact.updated_at.isoformat()
                })
            
            return jsonify({
                'success': True,
                'contacts': contacts_data,
                'total': len(contacts_data)
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
