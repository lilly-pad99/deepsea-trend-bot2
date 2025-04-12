from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import tweepy

app = Flask(__name__)

# --------- 환경 변수 ---------
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
CREDENTIAL_FILE = "credentials.json"

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

keywords = ["deep sea creature", "rare jellyfish", "심해생물", "해양생물", "정체불명 해파리"]

# 트위터 인증
auth = tweepy.OAuth1UserHandler(
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
)
api = tweepy.API(auth)

def scrape_twitter(keyword, limit=3):
    results = []
    for tweet in tweepy.Cursor(api.search_tweets, q=keyword, lang="en", tweet_mode="extended").items(limit):
        results.append({
            "platform": "Twitter",
            "keyword": keyword,
            "date": tweet.created_at.strftime("%Y-%m-%d %H:%M"),
            "content": tweet.full_text,
            "url": f"https://twitter.com/user/status/{tweet.id}"
        })
    return results

def save_to_sheets(data_list):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIAL_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1

    for data in data_list:
        sheet.append_row([data["date"], data["platform"], data["keyword"], data["content"], data["url"]])

def send_email(data_list):
    if not data_list:
        return
    body = f"📡 심해 트렌드 자동 요약 ({datetime.now().strftime('%Y-%m-%d')})\n\n"
    for d in data_list:
        body += f"🔹 [{d['platform']}] {d['keyword']}\n"
        body += f"{d['content'][:100]}...\n{d['url']}\n\n"

    msg = MIMEText(body)
    msg["Subject"] = "🌊 심해 트렌드 요약 자동 보고서"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_RECEIVER

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

def run_trend_task():
    print("🔄 트렌드 수집 작업 실행 중...")
    all_data = []
    for kw in keywords:
        all_data.extend(scrape_twitter(kw, limit=2))

    if all_data:
        save_to_sheets(all_data)
        send_email(all_data)
        print(f"✅ {len(all_data)}개 저장 및 이메일 전송 완료")
    else:
        print("❌ 새 트렌드 없음")

# --------- APScheduler 설정 ---------
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(run_trend_task, 'interval', hours=1)  # 1시간마다 실행
scheduler.start()

# --------- 웹 루트 ---------
@app.route("/")
def home():
    return "DeepSea Flask Bot (Tweepy version) is running!"

# 수동 실행 라우트
@app.route("/run-now")
def manual_run():
    run_trend_task()
    return "✅ 수동 실행 완료!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
