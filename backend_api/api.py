import flask

from flask import Flask, jsonify, request
from flask_sock import Sock
import json
import data_handling
from data_handling import application_exists
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__) #Create the Flask object
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
sock = Sock(app) #Setting up the socket object

users = [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"}
]

#Dummy API endpoint
@app.route('/users', methods=['GET'])
def get_users():
    return jsonify(users)

#Manually adds job statuses based on company, job, email link, and status 
@app.route('/jobstatuses', methods=['POST'])
def jobstatus_manual():
    #Check if the request is JSON
    if request.is_json:
        #Get the JSON data from the request
        data = request.get_json()

        #Extract the parameters from the JSON
        company = data.get('company')
        date = data.get('date')
        user_email = 'name@example.com'
        company_email = data.get('user_email')
        status = data.get('status')

        #Validate that all required parameters are provided
        if not company or not date or not status or not company_email:
            return jsonify({"error": "Missing required parameters"}), 400
                
        #Obtain the JSON object from the json file
        with open('data.json') as f:
            database = json.load(f)
            f.close()
            #If the user does not exist
            if user_email not in database["users"]:
                #Add the user into a separate list of dictionaries.
                database["users"][user_email] = []
            #If there exists an application for the user with the same company and role name
            index = application_exists(company, database["users"][user_email])
            if index != -1:
                #Update the status and email link using the index for the user
                database["users"][user_email][index]["status"] = status
            #Else
            else:
                #Insert a new record into the user's list of applications (application = dictionary)
                new_application = {"date": date, "company": company, "company_email": company_email, "status": status}
                database["users"][user_email].append(new_application)
            #Dump it back into the json file
            new_json_file = json.dumps(database)
            with open('data.json', 'w') as f:
                f.write(new_json_file)
                f.close()
            return jsonify(database["users"][user_email]), 200
    else:
        return jsonify({"error": "Request must be JSON"}), 400


email_list = []  # Define global variable at top of file
        
active_connections = set()

@socketio.on('connect')
def handle_connect():
    active_connections.add(request.sid)
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    active_connections.remove(request.sid)
    print(f"Client disconnected: {request.sid}")

import traceback

@app.route('/emails', methods=['POST'])
def add_emails():
    global email_list
    try:
        email_data = request.get_json()
        email_list = email_data
        
        # Emit to all connected clients
        socketio.emit('email_update', email_data, to=None)
        
        return jsonify({"message": "Emails saved and broadcast successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400


#Start the Flask app
if __name__ == '__main__':
    socketio.run(app, debug=True, port=8080)