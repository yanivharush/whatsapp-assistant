from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime
import os

app = Flask(__name__)

# Configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID') 
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', 'whatsapp:+14155238886')

def detect_intent(message):
    """זיהוי כוונת המשתמש"""
    message = message.lower().strip()
    
    # מזג אוויר
    if any(word in message for word in ['מזג', 'אוויר', 'טמפרטורה', 'גשם', 'שמש']):
        return 'weather'
    
    # יומן ופגישות  
    if any(word in message for word in ['פגישה', 'יומן', 'תוסיף', 'קבע', 'תזכורת']):
        return 'calendar'
    
    # חיפוש
    if any(word in message for word in ['חפש', 'מידע', 'מה זה', 'ספר לי']):
        return 'search'
    
    # תרגום
    if any(word in message for word in ['תרגם', 'תרגום', 'אנגלית', 'עברית']):
        return 'translate'
        
    # חדשות
    if any(word in message for word in ['חדשות', 'מה קורה', 'עדכונים']):
        return 'news'
    
    return 'general'

def get_openai_response(message, intent='general'):
    """קבלת תשובה מ-OpenAI"""
    
    if intent == 'weather':
        system_prompt = """אתה עוזר מזג אוויר. ענה בעברית על שאלות מזג אוויר. 
        אם לא צוין מיקום, שאל על המיקום. תן מידע כללי ומועיל."""
        
    elif intent == 'calendar':
        system_prompt = """אתה עוזר יומן אישי. עזור למשתמש לנהל פגישות ותזכורות.
        ענה בעברית. תן הצעות מועילות לניהול זמן."""
        
    elif intent == 'search':  
        system_prompt = """אתה עוזר חיפוש מידע. ספק מידע מדויק ורלוונטי בעברית.
        אם אתה לא יודע משהו, תגיד זאת בכנות."""
        
    elif intent == 'translate':
        system_prompt = """אתה מתרגם מקצועי. תרגם בין עברית לאנגלית ולהפך.
        תן תרגומים מדויקים וטבעיים."""
        
    elif intent == 'news':
        system_prompt = """אתה עוזר חדשות. ספק עדכונים כלליים ואקטואליים.
        ענה בעברית בצורה ברורה ומסודרת."""
        
    else:
        system_prompt = """אתה עוזר חכם ואדיב בשם 'עוזר וואטסאפ'. ענה תמיד בעברית.
        עזור למשתמש בכל שאלה או בקשה בצורה מועילת וידידותית."""

    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': message}
                ],
                'max_tokens': 500,
                'temperature': 0.7
            }
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"מצטער, יש בעיה טכנית. קוד שגיאה: {response.status_code}"
            
    except Exception as e:
        return f"מצטער, אירעה שגיאה: {str(e)}"

def send_whatsapp_message(to_number, message):
    """שליחת הודעה בווטסאפ דרך Twilio"""
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
        
        data = {
            'From': TWILIO_PHONE_NUMBER,
            'To': to_number,  
            'Body': message
        }
        
        response = requests.post(
            url,
            data=data,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        )
        
        return response.status_code == 201
        
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

@app.route('/', methods=['GET'])
def health_check():
    """בדיקת תקינות השרת"""
    return jsonify({
        'message': 'WhatsApp Smart Assistant is running',
        'status': 'active',
        'endpoints': {
            'health': '/',
            'webhook': '/whatsapp-bot',
            'send_message': '/send-message (requires API key)'
        }
    })

@app.route('/webhook', methods=['POST', 'GET'])  
def old_webhook():
    print("🚨 OLD WEBHOOK STILL BEING CALLED!")
    print("Twilio is still using the old URL!")
    
    try:
        # Let's handle it anyway
        message = request.values.get('Body', '')
        from_number = request.values.get('From', '')
        
        print(f"📱 From: {from_number}")
        print(f"💬 Message: {message}")
        
        if message and from_number:
            if 'שלום' in message or 'היי' in message:
                response_text = "שלום! אני העוזר החכם שלך! 🤖 איך אוכל לעזור לך היום?"
            else:
                intent = detect_intent(message)
                response_text = get_openai_response(message, intent)
            
            success = send_whatsapp_message(from_number, response_text)
            
            if success:
                print(f"✅ Sent: {response_text}")
            else:
                print("❌ Failed to send message")
        
        return '', 200
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return '', 200

@app.route('/whatsapp-bot', methods=['POST', 'GET'])
def whatsapp_webhook():
    """עוזר וואטסאפ - נקודת קבלה חדשה"""
    
    print("🔥 NEW WHATSAPP BOT HIT!")
    
    try:
        message = request.values.get('Body', '')
        from_number = request.values.get('From', '')
        
        print(f"📱 From: {from_number}")
        print(f"💬 Message: {message}")
        
        if message and from_number:
            if 'שלום' in message or 'היי' in message:
                response_text = "שלום! אני העוזר החכם שלך! 🤖 איך אוכל לעזור לך היום?"
            else:
                intent = detect_intent(message)
                response_text = get_openai_response(message, intent)
            
            success = send_whatsapp_message(from_number, response_text)
            
            if success:
                print(f"✅ Sent: {response_text}")
            else:
                print("❌ Failed to send message")
        
        return '', 200
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return '', 200

@app.route('/send-message', methods=['POST'])
def send_message():
    """API לשליחת הודעות"""
    
    api_key = request.headers.get('Authorization')
    if not api_key or api_key != f"Bearer {os.environ.get('API_KEY')}":
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    to_number = data.get('to')
    message = data.get('message')
    
    if not to_number or not message:
        return jsonify({'error': 'Missing to or message parameter'}), 400
        
    success = send_whatsapp_message(to_number, message)
    
    if success:
        return jsonify({'status': 'sent'})
    else:
        return jsonify({'error': 'Failed to send message'}), 500

if __name__ == '__main__':
    print("🚀 Starting WhatsApp Smart Assistant...")
    print("🔗 Webhook URLs: /webhook AND /whatsapp-bot")
    print("💡 Health Check: /")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )
