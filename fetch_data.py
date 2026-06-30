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

def parse_time(time_str):
    """টাইম স্ট্রিং নিরাপদে পার্স করার ফাংশন"""
    if not time_str:
        return None
    time_str = time_str.strip()
    for fmt in ("%Y/%m/%d %H:%M:%S %z", "%Y/%m/%d %H:%M:%S"):
        try:
            dt = datetime.strptime(time_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None

def fetch_and_save():
    ref = db.reference('/sports_live/events')
    raw_events = ref.get()

    if not raw_events:
        raw_events = []
    elif isinstance(raw_events, dict):
        sorted_keys = sorted(raw_events.keys(), key=lambda x: int(x) if x.isdigit() else x)
        raw_events = [raw_events[k] for k in sorted_keys]

    events_list = []
    utc_now = datetime.now(timezone.utc)

    # প্রতিটি ইভেন্ট প্রসেস করা হচ্ছে
    for index, item in enumerate(raw_events):
        if not isinstance(item, dict):
            continue

        event_id = item.get("id")
        title = item.get("title")
        league_logo = item.get("league_logo")
        cat = item.get("cat")
        
        event_info = item.get("eventInfo", {})
        
        start_time_str = event_info.get("startTime")
        end_time_str = event_info.get("endTime")

        start_time = parse_time(start_time_str)
        end_time = parse_time(end_time_str)

        if not start_time:
            status = "Upcoming"
        else:
            if not end_time:
                end_time = start_time + timedelta(hours=3)

            # জেনুইন সিস্টেম টাইমের সাথে তুলনা করে রিয়েল-টাইম স্ট্যাটাস নির্ধারণ
            if utc_now > end_time:
                status = "Finish"
            elif start_time <= utc_now <= end_time:
                status = "Live"
            else:
                status = "Upcoming"

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
                "startTime": start_time_str,
                "endTime": end_time_str
            },
            "channels_data": item.get("channels_data", [])
        }
        events_list.append(mapped_event)

    # সর্টিং লজিক: Live (0) -> Upcoming (1) -> Finish (2)
    def get_sort_key(event):
        status = event["eventInfo"]["Status"].lower()
        st_parsed = parse_time(event["eventInfo"]["startTime"])
        ts = st_parsed.timestamp() if st_parsed else 0

        if status == "live":
            return (0, ts)
        elif status == "upcoming":
            return (1, ts)
        else:
            return (2, -ts)

    # সর্ট করা হচ্ছে
    events_list.sort(key=get_sort_key)

    # সর্ট করা লিস্ট থেকে সঠিক কাউন্টার পুনরায় গণনা করা
    live_count = sum(1 for e in events_list if e["eventInfo"]["Status"] == "Live")
    upcoming_count = sum(1 for e in events_list if e["eventInfo"]["Status"] == "Upcoming")
    finish_count = sum(1 for e in events_list if e["eventInfo"]["Status"] == "Finish")

    # ভারতীয় সময় নির্ধারণ (IST - UTC+5:30)
    local_time = utc_now + timedelta(hours=5, minutes=30)
    last_update_time = local_time.strftime("%I:%M:%S %p %d-%m-%Y")

    # আপনার সুনির্দিষ্ট আউটপুট কাঠামো
    final_output = {
        "NAME": "FluX-oW Live event ( Auto updated)",
        "AUTHOR": "iVan_Flux",
        "CONTACT (OWNER)": "https://t.me/iVan_flux",
        "TELEGRAM CHANNEL": "https://t.me/api_hub_by_ivan",
        "Last update time": last_update_time,
        "Live": f"{live_count:02d}",
        "Upcoming": f"{upcoming_count:02d}",
        "Finish": f"{finish_count:02d}",
        "events": events_list
    }

    # ফাইলটি ivan-web.json নামে সংরক্ষণ করা হচ্ছে
    with open('ivan-web.json', 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)
        
    print("Success: ivan-web.json created")

if __name__ == "__main__":
    fetch_and_save()
