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

    if not raw_events:
        raw_events = []
    elif isinstance(raw_events, dict):
        # কি-গুলো সর্ট করে লিস্টে রূপান্তর
        sorted_keys = sorted(raw_events.keys(), key=lambda x: int(x) if x.isdigit() else x)
        raw_events = [raw_events[k] for k in sorted_keys]

    events_list = []
    live_count = 0
    upcoming_count = 0
    finish_count = 0

    # প্রতিটি ইভেন্ট রিড করে সাজানো হচ্ছে
    for item in raw_events:
        if not isinstance(item, dict):
            continue

        event_id = item.get("id")
        title = item.get("title")
        league_logo = item.get("league_logo")  # league_logo অপরিবর্তিত রাখা হলো
        cat = item.get("cat")
        
        event_info = item.get("eventInfo", {})
        status = str(event_info.get("Status", "Upcoming")).strip()

        # চূড়ান্ত তালিকায় পাঠানোর জন্য অবজেক্ট ম্যাপ করা হচ্ছে
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

    # সর্টিং লজিক: Live (১ম) -> Upcoming (২য়) -> Finish (৩য়) এবং প্রতি ক্যাটাগরিতে সময়ের ক্রমানুসারে সাজানো
    def get_sort_key(event):
        status = event["eventInfo"]["Status"].lower()
        if status == "live":
            status_order = 0
        elif status == "upcoming":
            status_order = 1
        elif status in ["finish", "finished", "ended"]:
            status_order = 2
        else:
            status_order = 3  # অন্য কোনো স্ট্যাটাস থাকলে তা শেষে যাবে
            
        start_time_str = event["eventInfo"]["startTime"]
        if not start_time_str:
            start_time_str = "9999/12/31 23:59:59 +0000"  # সময় না থাকলে তা শেষে দেখাবে
            
        return (status_order, start_time_str)

    # সম্পূর্ণ তালিকাটি সর্ট করা হচ্ছে
    events_list.sort(key=get_sort_key)

    # সর্ট হওয়া চূড়ান্ত তালিকা থেকে কাউন্টারগুলো নির্ভুলভাবে পুনরায় গণনা করা হচ্ছে
    for event in events_list:
        status = event["eventInfo"]["Status"].lower()
        if status == "live":
            live_count += 1
        elif status == "upcoming":
            upcoming_count += 1
        elif status in ["finish", "finished", "ended"]:
            finish_count += 1

    # ভারতীয় সময় নির্ধারণ (IST - UTC+5:30)
    utc_now = datetime.now(timezone.utc)
    local_time = utc_now + timedelta(hours=5, minutes=30)
    last_update_time = local_time.strftime("%I:%M:%S %p %d-%m-%Y")

    # চূড়ান্ত আউটপুট জেনারেট
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

    # ফাইল সংরক্ষণ
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)
        
    print("Success: data.json updated and sorted")

if __name__ == "__main__":
    fetch_and_save()
