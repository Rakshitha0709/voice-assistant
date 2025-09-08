import speech_recognition as sr
import pyttsx3
import requests
import time
import schedule
import threading
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 160)  
tts_engine.setProperty('volume', 1.0)

def speak(text):
    """Speak the provided text using pyttsx3."""
    print("Assistant:", text)
    tts_engine.say(text)
    tts_engine.runAndWait()

recognizer = sr.Recognizer()

def listen(timeout=5, phrase_time_limit=6):
    """Listen and return recognized text (or None on failure)."""
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.7)
        print("Listening...")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            text = recognizer.recognize_google(audio)  
            print("You:", text)
            return text.lower()
        except sr.WaitTimeoutError:
            print("No speech detected (timeout).")
            return None
        except sr.UnknownValueError:
            print("Could not understand audio.")
            return None
        except sr.RequestError as e:
            print("Speech recognition service error:", e)
            return None

# --- Weather ---
def get_weather_by_city(city):
    if not OPENWEATHER_KEY:
        return "OpenWeather API key not set. Put OPENWEATHER_API_KEY in .env."
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        return f"Could not get weather for {city} (status {resp.status_code})."
    data = resp.json()
    temp = data['main']['temp']
    desc = data['weather'][0]['description']
    humidity = data['main']['humidity']
    return f"The weather in {city} is {desc} with temperature {temp}°C and humidity {humidity}%."

# --- News ---
def get_top_headlines(source='us'):
    if not NEWSAPI_KEY:
        return ["News API key not set. Add NEWSAPI_KEY in .env or use RSS."]

    url = ("https://newsapi.org/v2/top-headlines?"
           f"country={source}&apiKey={NEWSAPI_KEY}")
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        return [f"Could not fetch news (status {resp.status_code})."]
    items = resp.json().get('articles', [])[:5]
    headlines = [f"{i+1}. {a['title']}" for i,a in enumerate(items)]
    return headlines or ["No top headlines found."]


def schedule_reminder(text, when_seconds):
    def reminder_job():
        speak(f"Reminder: {text}")

    run_at = datetime.now() + timedelta(seconds=when_seconds)
    schedule_time = run_at.strftime("%Y-%m-%d %H:%M:%S")
   
    def waiter():
        time.sleep(when_seconds)
        reminder_job()
    t = threading.Thread(target=waiter, daemon=True)
    t.start()
    return f"Reminder scheduled at {schedule_time}."


def run_scheduler_loop():
    while True:
        schedule.run_pending()
        time.sleep(1)

scheduler_thread = threading.Thread(target=run_scheduler_loop, daemon=True)
scheduler_thread.start()


def handle_command(cmd):
    if not cmd:
        return

    if "time" in cmd:
        now = datetime.now().strftime("%I:%M %p")
        speak(f"The time is {now}")

    elif "weather" in cmd:
        words = cmd.split()
        if "in" in words:
            city = " ".join(words[words.index("in")+1:])
        else:
            speak("Which city?")
            city = listen() or ""
        if city:
            resp = get_weather_by_city(city)
            speak(resp)
        else:
            speak("City not provided.")

    elif "news" in cmd:
        speak("Fetching top headlines.")
        headlines = get_top_headlines('us') 
        for h in headlines:
            speak(h)

    elif "set reminder" in cmd or "remind me" in cmd:
        import re
       
        m = re.search(r'in (\d+)\s*(second|seconds|minute|minutes|hour|hours)', cmd)
        if m:
            val = int(m.group(1))
            unit = m.group(2)
            seconds = val * (60 if 'minute' in unit else 3600 if 'hour' in unit else 1)
            text = cmd.split(' in ')[0].replace('remind me to', '').replace('set reminder to', '').strip()
            if not text:
                speak("What should I remind you about?")
                text = listen() or "your task"
            res = schedule_reminder(text, seconds)
            speak(res)
        else:
            speak("When should I remind you? Say, for example, 'in 10 seconds' or 'in 2 minutes'.")
            when = listen()
            speak("What should I remind you about?")
            what = listen()
            if when and what:
                m2 = re.search(r'(\d+)', when)
                if m2:
                    number = int(m2.group(1))
                    if 'minute' in when:
                        seconds = number * 60
                    elif 'hour' in when:
                        seconds = number * 3600
                    else:
                        seconds = number
                    res = schedule_reminder(what, seconds)
                    speak(res)
                else:
                    speak("Sorry, I couldn't understand the time.")
            else:
                speak("Insufficient information for a reminder.")

    elif "open" in cmd:
        if "youtube" in cmd:
            speak("Opening YouTube")
            import webbrowser
            webbrowser.open("https://www.youtube.com")
        elif "google" in cmd:
            speak("Opening Google")
            import webbrowser
            webbrowser.open("https://www.google.com")
        else:
            speak("What would you like me to open?")
            site = listen() or ""
            if site:
                url = "https://www." + site.replace(" ", "") + ".com"
                speak(f"Opening {site}")
                import webbrowser
                webbrowser.open(url)
            else:
                speak("No site provided.")

    elif "stop" in cmd or "exit" in cmd or "quit" in cmd:
        speak("Goodbye!")
        raise SystemExit

    else:
        speak("I can help with time, weather, news, reminders, opening websites, or say 'stop' to exit.")

def main_loop():
    speak("Hello! I am your personal assistant. How can I help you today?")
    try:
        while True:
            text = listen()
            if text:
                handle_command(text)
           
            time.sleep(0.5)
    except KeyboardInterrupt:
        speak("Shutting down. Bye.")

if __name__ == "__main__":
    main_loop()
