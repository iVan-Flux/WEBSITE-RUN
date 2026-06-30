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
    """ডাটাবেজের টাইম স্ট্রিং ক্র্যাশ ছাড়া নিরাপদে পার্স করার ফাংশন"""
    if not time_str:
        return None
    time_str = time_str.strip()
    # ফরম্যাট: "2026/07/01 16:30:00 +0000"
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
    # সরাসরি sports_live/events নোড থেকে ডেটা রিড করা হচ্ছে
    ref = db.reference('/sports_live/events')
    raw_events = ref.get()

    if not raw_events:
        raw_events = []
    elif isinstance(raw_events, dict):
        # কি-গুলো সর্ট করে লিস্টে রূপান্তর করা হচ্ছে
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
        
        # ডাটাবেজের স্ট্যাটাস টেক্সট ইগনোর করে টাইম দিয়ে স্ট্যাটাস বের করা হচ্ছে
        start_time_str = event_info.get("startTime")
        end_time_str = event_info.get("endTime")

        start_time = parse_time(start_time_str)
        end_time = parse_time(end_time_str)

        # শুরুর সময় না থাকলে সেটিকে ডিফল্ট Upcoming ধরা হচ্ছে
        if not start_time:
            status = "Upcoming"
        else:
            # শেষ হওয়ার সময় না থাকলে ৩ ঘণ্টা ম্যাচের ডিউরেশন ধরা হচ্ছে
            if not end_time:
                end_time = start_time + timedelta(hours=3)

            # বর্তমান সময়ের সাথে তুলনা করে স্ট্যাটাস নির্ধারণ করা হচ্ছে
            if utc_now > end_time:
                status = "Finish"
            elif start_time <= utc_now <= end_time:
                status = "Live"
            else:
                status = "Upcoming"

        # আপনার দেওয়া ম্যাপড ইভেন্ট কাঠামো
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
                "Status": status,  # স্বয়ংক্রিয়ভাবে হিসাব করা বাস্তব স্ট্যাটাস
                "startTime": start_time_str,
                "endTime": end_time_str
            },
            "channels_data": item.get("channels_data", [])
        }
        events_list.append(mapped_event)

    # সর্টিং লজিক নির্ধারণকারী ফাংশন
    def get_sort_key(event):
        status = event["eventInfo"]["Status"].lower()
        st_parsed = parse_time(event["eventInfo"]["startTime"])
        ts = st_parsed.timestamp() if st_parsed else 0

        if status == "live":
            # Live প্রথম পজিশনে (0) এবং যেটি সবথেকে আগে শুরু হয়েছে সেটি উপরে (Ascending order)
            return (0, ts)
        elif status == "upcoming":
            # Upcoming দ্বিতীয় পজিশনে (1) এবং যেটি সবথেকে কাছে শুরু হবে সেটি উপরে (Ascending order)
            return (1, ts)
        else:
            # Finish তৃতীয় পজিশনে (2) এবং যেটি অতি সম্প্রতি শেষ হয়েছে সেটি উপরে (Descending order)
            return (2, -ts)

    # লজিক অনুযায়ী পুরো তালিকাটি সর্ট করা হচ্ছে
    events_list.sort(key=get_sort_key)

    # সর্ট হওয়া লিস্ট থেকে কাউন্টারগুলো নির্ভুলভাবে পুনরায় গণনা করা হচ্ছে
    live_count = sum(1 for e in events_list if e["eventInfo"]["Status"] == "Live")
    upcoming_count = sum(1 for e in events_list if e["eventInfo"]["Status"] == "Upcoming")
    finish_count = sum(1 for e in events_list if e["eventInfo"]["Status"] == "Finish")

    # ভারতীয় স্থানীয় সময় (IST - UTC+5:30)
    local_time = utc_now + timedelta(hours=5, minutes=30)
    last_update_time = local_time.strftime("%I:%M:%S %p %d-%m-%Y")

    # চূড়ান্ত আউটপুট জেনারেট
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

    # 'data.json' ফাইলে রাইট করা হচ্ছে
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)
        
    print("Success: data.json created with real-time status calculations")

if __name__ == "__main__":
    fetch_and_save()
