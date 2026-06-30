import firebase_admin
from firebase_admin import credentials, db
import json
import os
from datetime import datetime, timedelta, timezone

# ফায়ারবেস কনফিগারেশন এবং ডাটাবেজ ইউআরএল লোড করা হচ্ছে
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

    # ডাটাবেজ থেকে প্রাপ্ত ডাটা লিস্ট নাকি ডিকশনারি তা চেক করে ইভেন্টগুলো আলাদা করা হচ্ছে
    raw_events = []
    if isinstance(data, dict):
        if 'events' in data:
            raw_events = data['events']
        else:
            raw_events = list(data.values())
    elif isinstance(data, list):
        raw_events = data

    events_list = []
    live_count = 0
    upcoming_count = 0
    finish_count = 0

    # প্রতিটি ইভেন্টকে নির্দিষ্ট ফরম্যাটে রূপান্তর করা এবং গণনা করা
    for item in raw_events:
        if not isinstance(item, dict):
            continue

        event_info = item.get("eventInfo", {})
        status = str(event_info.get("Status", "Upcoming")).strip()

        # স্ট্যাটাস অনুযায়ী কাউন্টার বৃদ্ধি করা
        if status.lower() == "live":
            live_count += 1
        elif status.lower() == "upcoming":
            upcoming_count += 1
        elif status.lower() in ["finish", "finished"]:
            finish_count += 1

        # আপনার দেওয়া সুনির্দিষ্ট কাঠামো অনুযায়ী সিঙ্গেল ইভেন্ট ম্যাপ করা হচ্ছে
        mapped_event = {
            "id": item.get("id"),
            "title": item.get("title"),
            "image": item.get("image"),
            "cat": item.get("cat"),
            "eventInfo": {
                "teamA": event_info.get("teamA"),
                "teamB": event_info.get("teamB"),
                "teamAFlag": event_info.get("teamAFlag"),
                "teamBFlag": event_info.get("teamBFlag"),
                "eventName": event_info.get("eventName"),
                "isHot": str(event_info.get("isHot", "0")),
                "Status": status,
                "startTime": event_info.get("startTime"),
                "endTime": event_info.get("endTime")
            },
            "channels_data": item.get("channels_data", [])
        }
        events_list.append(mapped_event)

    # সময় নির্ধারণ (এখানে বাংলাদেশ সময়/UTC+6 ব্যবহার করা হয়েছে, প্রয়োজন হলে পরিবর্তন করতে পারেন)
    utc_now = datetime.now(timezone.utc)
    local_time = utc_now + timedelta(hours=6)
    last_update_time = local_time.strftime("%I:%M:%S %p %d-%m-%Y")

    # আপনার দেওয়া সম্পূর্ণ ফাইনাল জেএসন ফরম্যাট
    final_output = {
        "NAME": "FluX-oW Live event ( Auto updated)",
        "AUTHOR": "iVan_FluX",
        "CONTACT (OWNER)": "https://t.me/iVan_flux",
        "TELEGRAM CHANNEL": "https://t.me/api_hub_by_ivan",
        "Last update time": last_update_time,
        "Live": f"{live_count:02d}",
        "Upcoming": f"{upcoming_count:02d}",
        "Finish": f"{finish_count:02d}",
        "events": events_list
    }

    # ফাইলটি 'data.json' নামে রাইট করা হচ্ছে
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)
        
    print("Success: data.json created with custom format")

if __name__ == "__main__":
    fetch_and_save()
