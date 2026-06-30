import firebase_admin
from firebase_admin import credentials, db
import json
import os

firebase_json = os.environ.get('FIREBASE_CONFIG')
database_url = os.environ.get('DATABASE_URL')

if not firebase_admin._apps:
    cred_dict = json.loads(firebase_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {
        'databaseURL': database_url
    })

def fetch_and_save():
    ref = db.reference('/')
    data = ref.get()
    # ব্যবহারকারীর অনুরোধ অনুযায়ী ফাইলের নাম data.json করা হলো
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("Success: data.json created")

if __name__ == "__main__":
    fetch_and_save()
