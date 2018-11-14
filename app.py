from flask import Flask, request, jsonify, json, session, redirect
import requests
import os

import urllib

import firebase_admin
from firebase_admin import credentials, auth

cred = credentials.Certificate('test-a8238-firebase-adminsdk-ys4xt-e2b291045b.json') # Change this: Firebase Service Account Credential. Always keep this file secured, don't push to Github.
default_app = firebase_admin.initialize_app(cred)

client_secret = 'YOUR_CLIENT_SECRET' # Change this: your client secret with the OAuth Provider (LinkedIn). Always keep this key secured, don't push to Github.

app = Flask(__name__)

cache={}

@app.route('/')
def hello():
    return 'Hello, Feedleave World!'
	
@app.route('/oauth/redirect')
def oauthredirect():
    return redirect("https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=86a506gyjly1qs&redirect_uri=http%3A%2F%2Flocalhost:5000%2Foauth%2Fcallback&scope=r_basicprofile", code=302)

@app.route('/oauth/callback')
def callback():
	code = request.args.get('code', '')
	
	headers = {'Content-Type': 'application/x-www-form-urlencoded'}
	# r = requests.post('https://www.linkedin.com/oauth/v2/accessToken', headers=headers, data = {'grant_type':'authorization_code', 'code':code, 'redirect_uri':'http%3A%2F%2Flocalhost:5000%2Foauth%2Fcallback', 'client_id':'86a506gyjly1qs', 'client_secret':client_secret})
	r = requests.post('https://www.linkedin.com/oauth/v2/accessToken?grant_type=authorization_code&code='+code+'&redirect_uri=http%3A%2F%2Flocalhost:5000%2Foauth%2Fcallback&client_id=86a506gyjly1qs&client_secret='+client_secret, headers=headers)
	print(r.text)
	
	# return 'Signed in with Linkedin!<br/><br/>' + 'Code:<br/>' + code + '<br/>' + r.text

	if json.loads(r.text).has_key('access_token'):
		cache['authorization_code']=json.loads(r.text)['access_token']
	else:
		return "error: no access token"
	# return jsonify(json.loads(r.text))

	headers = {'Host': 'api.linkedin.com', 'Connection': 'Keep-Alive', 'Authorization': 'Bearer '+cache['authorization_code']}
	print('token: '+cache['authorization_code'])
	print(headers)
	r = requests.get('https://api.linkedin.com/v1/people/~?format=json', headers=headers)

	userInfoJson = json.loads(r.text)
	print('userInfoJson:\n')
	print(userInfoJson)
	linkedInUserId = userInfoJson['id']
	linkedInUserName = userInfoJson['firstName'] + ' ' + userInfoJson['lastName']

	firebaseUid = 'linkedIn:' + linkedInUserId
	custom_token = auth.create_custom_token(firebaseUid)
	print('generated firebase uid: '+firebaseUid)

	return signInFirebaseTemplate(custom_token, linkedInUserName,'https://media.licdn.com/dms/image/C5603AQGEYWIllW9EFQ/profile-displayphoto-shrink_200_200/0?e=1547078400&v=beta&t=dfDinhPXEijVUE5mq2L8MW3tiMn4pJNxDjXqnJDavuM','"'+cache['authorization_code']+'"')
	
def signInFirebaseTemplate(token, displayName, photoURL, linkedInAccessToken):

	signInScript = '''
	<script src="https://www.gstatic.com/firebasejs/3.4.0/firebase.js"></script>
	<script src="https://cdnjs.cloudflare.com/ajax/libs/es6-promise/4.1.1/es6-promise.min.js"></script><!-- Promise Polyfill for older browsers -->
	<script>
	(function(){
		var token = \''''+token+'''\';
		var config = {
		apiKey:  'AIzaSyCPMfH7-aMGkbqQ2JBnLy-wtkSchLEWZco', // Change this!
		databaseURL: 'https://test-a8238.firebaseio.com', // Change this!
		};
		`console.log(${token})`
		// We sign in via a temporary Firebase app to update the profile.
		var tempApp = firebase.initializeApp(config, '_temp_');
		tempApp.auth().signInWithCustomToken(token).then(function(user) {

		// Saving the linkedIn API access token in the Realtime Database.
		const tasks = [tempApp.database().ref('/linkedInAccessToken/' + user.uid)
			.set('''+linkedInAccessToken+''')];

		// Updating the displayname and photoURL if needed.
		if (\''''+displayName+'''\' !== user.displayName || \''''+photoURL+'''\' !== user.photoURL) {
			tasks.push(user.updateProfile({displayName: \''''+displayName+'''\', photoURL: \''''+photoURL+''''}));
		}

		// Wait for completion of above tasks.
		return Promise.all(tasks).then(function() {
			// Delete temporary Firebase app and sign in the default Firebase app, then close the popup.
			var defaultApp = firebase.initializeApp(config);
			Promise.all([
				defaultApp.auth().signInWithCustomToken(token),
				tempApp.delete()]).then(function() {
			// console.log('aaa')
			alert('Ahh, oauth!');
			window.close(); // We're done! Closing the popup.
			
			});
		});
		});
	}())
	</script>
	'''
	
	return signInScript
	#.format(token=token,displayName=displayName,photoURL=photoURL,linkedInAccessToken=linkedInAccessToken)

@app.route('/getinfo')
def getinfo():
	if 'authorization_code' not in cache:
		return "error: not authorized"

	headers = {'Host': 'api.linkedin.com', 'Connection': 'Keep-Alive', 'Authorization': 'Bearer '+cache['authorization_code']}
	print('token: '+cache['authorization_code'])
	print(headers)
	r = requests.get('https://api.linkedin.com/v1/people/~?format=json', headers=headers)
	# return json.loads(r.text)
	return jsonify(json.loads(r.text))
	
if __name__ == "__main__":
	# # to enable session
	# app.secret_key = os.urandom(24)                                             
    app.run()