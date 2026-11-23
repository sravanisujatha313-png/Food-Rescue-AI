FOODRESCUE AI - RUNNING GUIDE (WINDOWS)

1) ZIP file extract చేయండి.
2) Laptop లో Python 3.10 లేదా అంతకంటే కొత్త version install అయి ఉండాలి.
3) Project folder లో Command Prompt open చేయండి.
4) ఈ commands ఒక్కొక్కటిగా run చేయండి:

   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python app.py

5) Browser లో ఈ address open చేయండి:
   http://127.0.0.1:5000

DEMO LOGIN:
Donor:
  Email: donor@example.com
  Password: Demo@123

NGO:
  Email: ngo@example.com
  Password: Demo@123

Volunteer:
  Email: volunteer@example.com
  Password: Demo@123

DEMO FLOW:
A) Donor login చేసి Donate Food ద్వారా food listing create చేయండి.
B) Logout చేసి NGO login చేయండి.
C) Find Food page లో donation కనిపిస్తుంది.
D) Accept donation click చేయండి.
E) Dashboard లో Mark delivered click చేయండి.
F) AI Predictor లో prepared meals, expected customers enter చేసి demo estimate చూడండి.

IMPORTANT:
- ఇది college demonstration కోసం student prototype.
- AI predictor synthetic demo data తో train అవుతుంది. నిజ జీవితంలో వాడే ముందు actual, consented data తో train/test చేయాలి.
- NGO accounts ప్రస్తుతం self-registration మాత్రమే; నిజ జీవిత deployment కు identity/organization verification అవసరం.
- Food safety ని AI లేదా photo ద్వారా నిర్ధారించలేం. Donor మరియు authorized food recovery organization FSSAI rules, hygiene, storage, transport, allergen and time limits పాటించాలి.
- Demo accounts/passwords public demonstration కోసం మాత్రమే. Production లో secret key, passwords, hosting, privacy, access control and security hardening తప్పనిసరి.
- ఈ prototype ప్రస్తుతం live GPS, SMS/WhatsApp alerts, payments లేదా real government/NGO integrations చేయదు.
