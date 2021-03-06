from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from flask_pymongo import PyMongo
import os, json, copy, bcrypt, re
import base64
import colour
from .sample_files import incidentssample
from os.path import join
from bson.objectid import ObjectId
from functools import wraps
from flask import Flask, render_template, request, redirect, jsonify, session, abort, flash, url_for
from cleanup import app, login_manager, users, content, feed, totals, reports
from operator import itemgetter
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import configparser, logging, os, json, random, re, string, datetime, bcrypt, urllib, hashlib, bson, math
import PIL
import datetime
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS
import threading
import schedule
import time
import re
from json import dumps
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from .forms import SignupForm, LoginForm, UploadForm


def resetValues():
	for x in content.find():
		x['value'] = 10
		content.save(x)

def thread():
	while True:
		schedule.run_pending()
		time.sleep(60)
		
x = None
x = threading.Thread(target=thread)
x.daemon = True
x.start()

def job():
	print("scheduled job running...")
	aging()


def aging():
	f = open ("logs.txt", "w+")
	for x in content.find():
		f.write("Considering incident: " + str(x['_id']) + "\n")
		incidentDate = x['date_created']
		diff = datetime.datetime.now() - incidentDate
		score = x['value']
		hourDiff = math.floor(diff.seconds / 3600)
		print(hourDiff) 
		f.write(f"hour difference for incdent is {hourDiff}\n")
		if hourDiff > 0 :
			f.write(f"difference is greater than 0\n")
			print("difference exists")
			newScore = 20 + (5 * hourDiff)
			if newScore > 60:
				f.write(f"score is {newScore} this is greater than limit abort\n")
				f.close()
				return
			if score != newScore:
				f.write(f"saving new score {newScore}\n")
				print("saving new score")
				x['value'] = newScore 
				content.save(x)
	f.close()
		
#resetValues() 
schedule.every(10).minutes.do(job)

@app.route('/', methods=['GET'])
def index():
	upload_form = UploadForm()
	upload_form.image.data = ""

	total = totals.find_one()
	total_cleaned = total['total_cleaned']

	return render_template('index.html', upload_form=upload_form, total_cleaned=total_cleaned)


@app.route('/login/', methods=['POST', 'GET'])
def login():
	if session.get('logged_in'):
		result = users.find_one({'_id': ObjectId(session.get('id'))})
		if result is None:
			session.clear()
		else:
			return redirect(url_for('index'))
	
	ip = request.environ['REMOTE_ADDR']
	form = LoginForm(request.form)
	if request.method =='POST' and form.validate():
		email = form.email.data

		result = users.find_one({'email' : re.compile(email, re.IGNORECASE)})
		if result is not None:
			#if (bcrypt.checkpw(form.password.data.encode('utf-8'), result['password'])):
			if (form.password.data == result['password']):

				session['logged_in'] = True
				session['email'] = result.get('email')
				session['id'] = str(result.get('_id'))
				session['fullname'] = result.get('first_name') + " " + result.get('last_name')
				session['account_level'] = result.get('account_level')
				#flash('You are now logged in', 'success')
				print(session.get('email') + " has logged in")
				return redirect(url_for('index'))
				
			else:
				print("Failed login attempt |", email, "| IP:", ip)
				error = "wrong_password"
				return render_template('login.html', form=form, error=error)
		else:
			error = "wrong_email"
			return render_template('login.html', form=form, error=error)
	return render_template('login.html', form=form)


@app.route('/signup/', methods=['POST', 'GET'])
def signup():
	if session.get('logged_in'):
		result = users.find_one({'_id': ObjectId(session.get('id'))})
		if result is None:
			session.clear()
		else:
			return redirect(url_for('index'))
	
	form = SignupForm(request.form)
	if request.method == 'POST' and form.validate():
		# Set the user inputs
		# Force only the initial character in first name to be capitalised
		first_name = (form.firstname.data.lower()).capitalize()
		
		# Make sure the first letter is capitalised. Don't care about capitalisation on the rest
		last_name = form.lastname.data
		last_name_first_letter = last_name[0].capitalize()
		last_name_remaining_letters = last_name[1:]
		last_name = last_name_first_letter + last_name_remaining_letters

		email = form.email.data
		# Set the default inputs
		ip = request.environ['REMOTE_ADDR']
		account_level = 0

		# Check if the email address already exists
		existing_user = users.find_one({'email' : re.compile(email, re.IGNORECASE)})

		if existing_user is not None:
			flash('Account already exists', 'danger')
			return render_template('signup.html', form=form)
		if existing_user is None:
			#hashpass = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
			hashpass = request.form['password']
			users.insert({
				'first_name' : first_name,
				'last_name' : last_name,
				'email' : email,
				'password' : hashpass,
				'last_ip' : ip,
				'account_level' : account_level,
				'score' : 0,
				'badges' : []
			})

			# Retrieve the ID of the newly created user
			new_user = users.find_one({'email' : re.compile(email, re.IGNORECASE)})
			user_id = new_user['_id']

			print("INFO: New user has been created with email", email)
			flash('Account registered', 'success')
			return redirect(url_for('login'))
	else:
		return render_template('signup.html', form=form)

#Getting user data for AJAX



@app.route('/users/')
def getUsers():
	all_users =[]
	#Find user from given user id in GET arguments
	user_id = request.args.get('user')
	#If a specific user is requested
	if user_id:
		result = users.find_one({'_id': ObjectId(user_id)})
		if result:
			result['_id'] = str(result['_id'])
			result['password'] = str(result['password'])
			return jsonify(result)
		else:
			return "[]"
	else: 
		for x in users.find():
			x['_id'] = str(x['_id'])
			x['password'] = str(x['password'])
			all_users.append(x)
		return jsonify(all_users)


#Getting current user data for AJAX
@app.route('/users/current')
def get_current_user_id():
	#Find user from given user id in GET arguments
	if session.get('logged_in'):
		result = users.find_one({'_id': ObjectId(session.get('id'))})
		if result is not None:
			result['_id'] = str(result['_id'])
			result['password'] = str(result['password'])
			return jsonify(result)
		else:
			session.clear()
	return ""

@app.route('/profiles/')
@app.route('/profiles/<id>')
def profile(id=None):
	if id is not None and bson.objectid.ObjectId.is_valid(id):
		user_profile = users.find_one({'_id' : ObjectId(id)})
		user_copy = copy.deepcopy(user_profile)
		if user_copy is not None:
			user_copy['_id'] = str(user_profile['_id'])
			print("USER ID " + user_copy['_id'])
			return render_template('profile.html', user_profile=user_copy)
	elif session.get('logged_in'):
		result = users.find_one({'_id': ObjectId(session.get('id'))})
		if result is not None:
			result['_id'] = str(result['_id'])
			result['password'] = str(result['password'])
			return render_template('profile.html', user_profile=result)
	return redirect('/')
	

# Getting pin data for AJAX
@app.route('/pins/', methods=['GET'])
def pins():
	
	incidents = []
	db_content = content.find()
	for current in db_content:
		current['_id'] = str(current['_id'])
		current['uploader'] = str(current['uploader'])
		current['cleaner'] = str(current['cleaner'])
		incidents.append(current)
	# Find pin from given pin id in GET arguments or user ID
	pin_id = request.args.get('pin')
	user_id = request.args.get('user')
	# If a specific pin is requested...
	if not pin_id == None:
		# ... Search through the incidents until the right one is found
		for incident in incidents:
			if incident['_id'] == pin_id:
				return jsonify(incident)
		# If none are found return 404
		return '404'
	elif not user_id == None:
		# If a user ID is requested, return incidents related to the user
		related = []
		for incident in incidents:
			if incident["uploader"] == user_id or incident['cleaner'] == user_id:
				related.append(incident)
		return jsonify(related)
	else:
		# If no specific pin is requested, return them all
		return jsonify(incidents)



@app.route('/pins/delete/', methods=['POST'])
def pins_delete():
	incident_id = request.args.get('incident_id')
	content.delete_one({"_id" : ObjectId(incident_id)})
	feed.delete_many({"incident_id" : ObjectId(incident_id)})
	reports.delete_many({"incident_id" : ObjectId(incident_id)})
	return incident_id


@app.route('/pins/report/', methods=['POST'])
def pins_report():
	incident_id = request.args.get('incident_id')
	if session.get('logged_in'):
		result = users.find_one({'_id': ObjectId(session.get('id'))})
		if result is not None:
			prev_reported = False
			cursor = reports.find({'incident_id' : ObjectId(incident_id)})
			for record in cursor:
				if record['reporter'] == result['_id']:
					prev_reported = True
			if not prev_reported:
				new_report = {
				'incident_id' : ObjectId(incident_id),
				'reporter' : result['_id'],
				'date' : datetime.datetime.now(),
				'status' : "Unresolved"
				}
				reports.insert_one(new_report)
				flash("Reported post successfully", "success")
			else:
				flash("You already reported this post", "danger")
		return redirect('/')

	return incident_id


@app.route('/reports/', methods=['GET'])
def report_page():
	## if level 100 then allow access

	all_reports = []
	cursor = reports.find()
	for current in cursor:
		all_reports.append(current)
	
	if session.get('logged_in'):
		result = users.find_one({'_id': ObjectId(session.get('id'))})
		if result is not None:
			if result['account_level'] == 100:
				return render_template('reports.html', all_reports=all_reports)
	flash("Access denied", "danger")
	return redirect('/')

@app.route('/pins/clean/', methods=['POST'])
def clean():
	
	current_user = None
	if session.get('logged_in'):
		current_user = users.find_one({'_id' : ObjectId(session.get('id'))})
	else:
		flash('Access restricted. Please login first', 'danger')
		return redirect(url_for('login'))

	incident_id = request.args.get('incident_id')
	incident = content.find_one({'_id' : ObjectId(incident_id)})
	
	if(incident['status'] == "Available"):
		
		# Update the incident
		incident['date_cleaned'] = datetime.datetime.now()
		incident['cleaner'] = current_user['_id']
		incident['status'] = "Complete"
		content.save(incident)
		# -- would also update after image here.. not in this version

		# Give the user points
		current_user['score'] = current_user['score'] + incident['value']
		users.save(current_user)

		# Update the feed
		feedObject = {
			'type' : "clean",
			'time' : int(round(time.time() * 1000)),
			'user_first_name' : current_user['first_name'],
			'incident_id' : incident['_id'],
			'user_id' : current_user['_id']
		}
		feed.insert(feedObject)

		# Update the trash cleaned tracker
		total = totals.find_one()
		total['total_cleaned'] = total['total_cleaned'] + 1
		totals.save(total)

		flash("Cleaned trash successfully", "success")
		return redirect('/')

	return incident_id


@app.route('/feed', methods=['GET'])
def getFeed():
	user_id = request.args.get('user')
	all_feed = []
	for x in feed.find():
		x['_id'] = str(x['_id'])
		x['incident_id'] = str(x['incident_id'])
		x['user_id'] = str(x['user_id'])
		all_feed.append(x)
	if not user_id == None:
		# If a user ID is requested, return incidents related to the user
		related = []
		for feedEntry in all_feed:
			if feedEntry['user_id'] == user_id:
				related.append(feedEntry)
		return jsonify(related)
	else:
		return jsonify(all_feed)


# Redirect logged out users with error message
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Access restricted. Please login first', 'danger')
			return redirect(url_for('login'))
	return wrap


@app.route('/logout/')
def logout():
	if session.get('logged_in'):
		session.clear()
		#flash('You are now logged out', 'success')
		return redirect(url_for('index'))
	else:
		session.clear()
		return redirect(url_for('login'))



@app.route('/upload/', methods=['POST', 'GET'])
@is_logged_in
def upload():
	current_user = None
	if session.get('logged_in'):
		current_user = users.find_one({'_id' : ObjectId(session.get('id'))})
	else:
		flash('Access restricted. Please login first', 'danger')
		return redirect(url_for('login'))
	
	upload_form = UploadForm()
	id = str(current_user['_id'])
	if id is not None and bson.objectid.ObjectId.is_valid(id):
		user = users.find_one({'_id' : ObjectId(id)})
		if str(current_user['_id']) == id:
			if request.method == 'POST' and upload_form.validate():
				
				# If a file was provided by the user then upload and store it
				# Then store the name of the new file in the user profile DB
				if upload_form.image.data:
					image_data = store_uploaded_image(upload_form.image.data, str(user['_id']))

				# Create incident dictionary				
				incident = {
					'uploader' : ObjectId(id),
					'image_before' : image_data['image_before'],
					'image_after' : "",
					'status' : "Available",
					'lat' : image_data['lat'],
					'lon' : image_data['lon'],
					'date_taken' : image_data['date_taken'],
					'date_created' : datetime.datetime.now(),
					'date_cleaned' : "",
					'value' : 10,
					'cleaner' : "",
					'incident_type' : "Trash"
				}
				if incident['lat'] == 0 and incident['lon'] == 0:
					# Tell user could not find location, image was not upload
					# In future this would let them place pin manually for lat and lon
					flash("Could not retrieve image location from metadata", "danger")
				else:
					current_user['score'] = current_user['score'] + 2
					users.save(current_user)
					incidentID = content.insert(incident)
					feedObject = {
						'type' : "new_pin",
						'time' : int(round(time.time() * 1000)),
						'user_first_name' : current_user['first_name'],
						'incident_id' : incidentID,
						'user_id' : current_user['_id']
					}
					feed.insert(feedObject)
					flash("Image uploaded successfully", "success")
				return redirect('/')
			elif request.method == 'GET' and user is not None:
				upload_form.image.data = ""
			elif not upload_form.validate():
				flash("File type must be .JPG", "danger")
			return redirect('/')
		else:
			flash("Access restricted. You do not have permission to do that", 'danger')
			return redirect(url_for('index'))

	return redirect(url_for('index'))


def get_next_filename(picture_path):
	max = 0
	files = os.listdir(picture_path)
	
	for f in files:
		f_str = os.path.splitext(f)[0]
		f_num = int(f_str)
		if f_num > max:
			max = f_num
	
	return max + 1


def extract_number(f):
    s = re.findall("\d+$",f)
    return (int(s[0]) if s else -1,f)


def store_uploaded_image(form_pic, profile_user_id):
	_, ext = os.path.splitext(form_pic.filename)
	picture_fn = profile_user_id

	picture_path = os.path.join(app.root_path, 'static','resources','user-content', profile_user_id)

	


	if not os.path.exists(picture_path):
		os.makedirs(picture_path)

	next_file_name = str(get_next_filename(picture_path))

	final_location = picture_path + '/' + next_file_name + ext
	relative_path = os.path.join('static','resources','user-content', profile_user_id, (next_file_name + ext))

	img = Image.open(form_pic)
	exif_data = img._getexif()
	
	try:
		for orientation in ExifTags.TAGS.keys():
			if ExifTags.TAGS[orientation] == 'Orientation':
				break
		exif_items = dict(img._getexif().items())
		print(exif_items[orientation])
		if exif_items[orientation]== 3:
			img = img.rotate(180, expand=True)
		if exif_items[orientation]== 6:
			img = img.rotate(270, expand=True)
		if exif_items[orientation]== 8:
			img = img.rotate(90, expand=True)

	except Exception as e:
		print(e)
	a = get_exif(form_pic)

	date_taken = ""
	lat = 0
	lon = 0

	if a is not None and 'GPSInfo' in a:
		if 29 in a['GPSInfo']:
			date_taken = a['GPSInfo'][29]
		if 2 in a['GPSInfo']:

			lat = [float(x)/float(y) for x, y in a['GPSInfo'][2]]
			latref = a['GPSInfo'][1]
			lon = [float(x)/float(y) for x, y in a['GPSInfo'][4]]
			lonref = a['GPSInfo'][3]

			lat = lat[0] + lat[1]/60 + lat[2]/3600
			lon = lon[0] + lon[1]/60 + lon[2]/3600
			if latref == 'S':
				lat = -lat
			if lonref == 'W':
				lon = -lon

			# Set the image width and height to reduce large image file sizes
			file_size = (250, 250)
			img.thumbnail(file_size)

			img.save(final_location)
		else:
			print("No GPS data retrieved from image")

	img_data = {
		'image_before' : relative_path,
		'lat' : lat,
		'lon' : lon,
		'date_taken' : date_taken
	}
	return img_data

def get_exif(fn):
    ret = {}
    i = Image.open(fn)
    info = i._getexif()
    if info is not None:
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            ret[decoded] = value
        return ret
    return None