from flask import Flask, render_template, request
import os.path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import datetime




def authenticate():
    # Define the path to the credentials.json file on the desktop
    desktop_path = os.path.expanduser("~/Desktop")
    credentials_path = os.path.join(desktop_path, "credentials.json")

    # The file token.json stores the user's access and refresh tokens and is created automatically when the
    # authorization flow completes for the first time.
    creds = None
    token_path = os.path.join(desktop_path, 'token.json')

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path)

    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Adjust the path to the credentials.json file
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return creds

# Function to create client ID from date of birth
def create_client_id(name, dob):
    dob_formatted = dob.replace('/', '')
    
    # Create the client ID by combining name and formatted DOB
    client_id = f"{name}_{dob_formatted}"
    
    return client_id

def get_results(values):
#Builds the client search directory
    # Assuming the first row contains headers
    headers = values[0]
    data = values[1:]
    # Create a dictionary to store the results
    result_dict = {}
    # Iterate through the rows
    for row in data:
        if row[headers.index('Choose Form Type')] == "Intake":
            last_name = row[headers.index("Parent last name")]
            first_name = row[headers.index("Parent first name")]
            name = first_name + " " + last_name
            dob = row[headers.index("Date of birth")]
            client_id = create_client_id(name, dob)
            # Create a dictionary for the current response
            if row[headers.index('Student #2 first name')]:
                response_dict = {
                'Name': name,
                'Date of Intake': row[headers.index("Date of intake")],
                'Email': row[headers.index("Email")],
                'Phone': row[headers.index("Phone number")],
                'Country of origin': row[headers.index("Country of origin")],
                'Address': row[headers.index("Address")],
                'Town': row[headers.index('Town/Village')],
                'DOB': row[headers.index('Date of birth')],
                'Students': row[headers.index('Student first name')]+" "+row[headers.index('Student last name')]+" Grade "+row[headers.index('Current grade')] + "," + row[headers.index('Student #2 first name')]+" "+row[headers.index('Student #2 last name')]+" Grade "+row[headers.index('Student #2 current grade')], 
                'Services': {}}
            else:
                response_dict = {
                'Name': name,
                'Date of Intake': row[headers.index("Date of intake")],
                'Email': row[headers.index("Email")],
                'Phone': row[headers.index("Phone number")],
                'Country of origin': row[headers.index("Country of origin")],
                'Address': row[headers.index("Address")],
                'Town': row[headers.index('Town/Village')],
                'DOB': row[headers.index('Date of birth')],
                'Students': row[headers.index('Student first name')]+" "+row[headers.index('Student last name')]+" Grade "+row[headers.index('Current grade')], 
                'Services': {}}
        # Add more fields as needed
        # Add the response dictionary to the main result dictionary
            result_dict[client_id] = response_dict
    
    
        if row[headers.index('Choose Form Type')] == "Tutoring contact":
            last_name = row[headers.index("Student's last name")]
            first_name = row[headers.index("Student's first name")]
            name = first_name + " " + last_name
            client_id = name
            if client_id not in result_dict:
                response_dict = {
                'Name': client_id,
                'District': row[headers.index("School district")],
                'Activity Log': {row[headers.index("Date of contact")]:row[headers.index("Length of session")]+" hours "+
                                 row[headers.index("Focus")]+", "+row[headers.index("Location of contact")]+". "+row[headers.index("Activity")]},
                'Advocacy Log': {},
                'Activity Hours': float(row[headers.index("Length of session")]),
                'Advocacy Hours': 0,
                }
                result_dict[client_id] = response_dict
            else:
                result_dict[client_id]['Activity Log'][row[headers.index("Date of contact")]] = row[headers.index("Length of session")]+" hours "+row[headers.index("Focus")]+", "+row[headers.index("Location of contact")]+". "+row[headers.index("Activity")]
                result_dict[client_id]['Activity Hours'] += float(row[headers.index('Length of session')])


        if row[headers.index('Choose Form Type')] == "Advocacy contact":
            last_name = row[headers.index("student last name")]
            first_name = row[headers.index("student first name")]
            name = first_name + " " + last_name
            client_id = name
            if client_id not in result_dict.keys():
                response_dict = {
                'Name': client_id,
                'District': row[headers.index("school district")],
                'Activity Log': {},
                'Advocacy Log': {row[headers.index('date of contact')]:row[headers.index('Length of contact')]+" hours, "+row[headers.index('Description of advocacy')]},
                'Activity Hours': 0,
                'Advocacy Hours': float(row[headers.index('Length of contact')])
                }
                result_dict[client_id] = response_dict
            else:
                result_dict[client_id]['Advocacy Log'][row[headers.index("date of contact")]] = row[headers.index('Length of contact')]+" hours, "+row[headers.index('Description of advocacy')]
                result_dict[client_id]['Advocacy Hours'] += float(row[headers.index('Length of contact')])
        if row[3] == "Collaboration":
            continue

         
    return result_dict


app = Flask(__name__)

# Call this function to obtain credentials
credentials = authenticate()


# Create a Google Sheets API service
service = build('sheets', 'v4', credentials=credentials)


# Specify the spreadsheet ID and range
spreadsheet_id = "1bMywF_hwWaKaWZx52B2LCR-3vlIFYDjIpEfLmOjZg10"


# Get spreadsheet information
spreadsheet_info = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

# Extract sheet names from the spreadsheet information
sheet_names = [sheet['properties']['title'] for sheet in spreadsheet_info['sheets']]

all_values = []

for sheet_name in sheet_names:
    range_name = f"{sheet_name}!A1:ZZ"
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    sheet_values = result.get('values', [])
    
    # Append the values from the current sheet to the overall list
    all_values.extend(sheet_values)


clients = get_results(all_values)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    if request.method == 'POST':
        search_query = request.form.get('search_query', '').lower()
        matching_clients = [client for client in clients.keys() if search_query == clients[client]['Name'].lower()]
        return render_template('search_results.html', matching_clients=matching_clients, clients=clients)
    return render_template('search_form.html')

@app.route('/client_info/<client_id>', methods=['GET'])
def client_info(client_id):
    client_details = clients.get(client_id)
    if not client_details:
        return "Client not found", 404
    if ord('0') <= ord(client_id[-1]) <= ord('9'):
        return render_template('adult_client_info.html', client=client_details, client_name=client_details['Name'])
    else:
        return render_template('client_info.html', client=client_details, client_id=client_id)

    

if __name__ == '__main__':
    app.run(debug=True)






