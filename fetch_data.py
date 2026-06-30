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

    # ডাটাবেজ থেকে ডাটা লিস্ট নাকি ডিকশনারি তা চেক করে ইভেন্টগুলো আলাদা করা হচ্ছে
    raw_events = []
    if isinstance(data, dict):
        if 'events' in data:
            raw_events = data['events']
        elif 'matches' in data:
            raw_events = data['matches']
        else:
            raw_events = list(data.values())
    elif isinstance(data, list):
        raw_events = data

    events_list = []
    live_count = 0
    upcoming_count = 0
    finish_count = 0

    for index, item in enumerate(raw_events):
        if not isinstance(item, dict):
            continue

        # ডাটাবেজ স্ট্রাকচার ফ্ল্যাট বা নেস্টেড যাই হোক না কেন, তা হ্যান্ডেল করার জন্য সাহায্যকারী ফাংশন
        event_info_nested = item.get("eventInfo", {}) if isinstance(item.get("eventInfo"), dict) else {}

        def get_val(key, default=None):
            # প্রথমে ফ্ল্যাট কি চেক করবে, না পেলে নেস্টেড eventInfo চেক করবে
            val = item.get(key)
            if val is None:
                val = event_info_nested.get(key)
            return val if val is not None else default

        # স্ট্যাটাস এবং টাইম সংক্রান্ত ডাটা
        status = str(get_val("Status") or get_val("status") or "Upcoming").strip()

        # স্ট্যাটাস কাউন্ট নির্ধারণ করা
        if status.lower() == "live":
            live_count += 1
        elif status.lower() == "upcoming":
            upcoming_count += 1
        elif status.lower() in ["finish", "finished", "ended"]:
            finish_count += 1

        # ডাটাবেজের প্রকৃত মানগুলোকে আপনার দেওয়া নির্দিষ্ট ফরম্যাটে সাজানো হচ্ছে
        mapped_event = {
            "id": get_val("id") or get_val("match_id") or (index + 1),
            "title": get_val("title") or get_val("match_title") or get_val("name"),
            "image": get_val("image") or get_val("logo") or get_val("tournament_logo"),
            "cat": get_val("cat") or get_val("category") or get_val("sport") or "Cricket",
            "eventInfo": {
                "teamA": get_val("teamA") or get_val("team_a") or get_val("home"),
                "teamB": get_val("teamB") or get_val("team_b") or get_val("away"),
                "teamAFlag": get_val("teamAFlag") or get_val("team_a_flag") or get_val("home_flag"),
                "teamBFlag": get_val("teamBFlag") or get_val("team_b_flag") or get_val("away_flag"),
                "eventName": get_val("eventName") or get_val("league") or get_val("tournament") or get_val("title"),
                "isHot": str(get_val("isHot") or "0"),
                "Status": status,
                "startTime": get_val("startTime") or get_val("start_time") or get_val("time"),
                "endTime": get_val("endTime") or get_val("end_time") or ""
            },
            "channels_data": item.get("channels_data") or item.get("channels") or item.get("links") or []
        }
        events_list.append(mapped_event)

    # সময় নির্ধারণ (বাংলাদেশ সময়/UTC+6)
    utc_now = datetime.now(timezone.utc)
    local_time = utc_now + timedelta(hours=6)
    last_update_time = local_time.strftime("%I:%M:%S %p %d-%m-%Y")

    # আপনার সুনির্দিষ্ট আউটপুট কাঠামো
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
        
    print("Success: data.json created with dynamic mapping")

if __name__ == "__main__":
    fetch_and_save()
