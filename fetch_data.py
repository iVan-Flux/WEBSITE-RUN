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
    # সরাসরি sports_live/events পাথ থেকে ডেটা রিড করা হচ্ছে
    ref = db.reference('/sports_live/events')
    raw_events = ref.get()

    # ডাটাবেজে কোনো ডেটা না থাকলে খালি লিস্ট ধরা হবে
    if not raw_events:
        raw_events = []
    # ডাটাবেজ ডিকশনারি ফরম্যাটে থাকলে তা সিরিয়াল অনুযায়ী ০, ১, ২ সাজানো হচ্ছে
    elif isinstance(raw_events, dict):
        sorted_keys = sorted(raw_events.keys(), key=lambda x: int(x) if x.isdigit() else x)
        raw_events = [raw_events[k] for k in sorted_keys]

    events_list = []
    live_count = 0
    upcoming_count = 0
    finish_count = 0

    # প্রতিটি ইভেন্ট পর পর রিড করে সাজানো হচ্ছে
    for item in raw_events:
        if not isinstance(item, dict):
            continue

        # ইভেন্টের মূল তথ্যগুলো নেওয়া হচ্ছে
        event_id = item.get("id")
        title = item.get("title")
        league_logo = item.get("league_logo")  # আপনার নির্দেশনা অনুযায়ী league_logo অপরিবর্তিত রাখা হলো
        cat = item.get("cat")
        
        # eventInfo নোড রিড করা হচ্ছে
        event_info = item.get("eventInfo", {})
        status = str(event_info.get("Status", "Upcoming")).strip()

        # স্ট্যাটাস কাউন্ট
        if status.lower() == "live":
            live_count += 1
        elif status.lower() == "upcoming":
            upcoming_count += 1
        elif status.lower() in ["finish", "finished", "ended"]:
            finish_count += 1

        # ফাইনাল আউটপুটের জন্য প্রতিটি ইভেন্টের কাঠামো
        mapped_event = {
            "id": event_id,
            "title": title,
            "league_logo": league_logo,
            "cat": cat,
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

    # সময় আপডেট (বাংলাদেশ সময়/UTC+6)
    utc_now = datetime.now(timezone.utc)
    local_time = utc_now + timedelta(hours=6)
    last_update_time = local_time.strftime("%I:%M:%S %p %d-%m-%Y")

    # চূড়ান্ত ফাইল স্ট্রাকচার
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

    # 'data.json' ফাইলে রাইট করা হচ্ছে
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)
        
    print("Success: data.json created with correct database path")

if __name__ == "__main__":
    fetch_and_save()
