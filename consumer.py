from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from confluent_kafka import Consumer, KafkaException, KafkaError
import threading
import json
import time

app = Flask(__name__)
socketio = SocketIO(app)

bot_statuses = {
    'mm_bot_1': {'status': 'offline', 'info': 'No contact', 'last_update': 0},
    'mm_bot_2': {'status': 'offline', 'info': 'No contact', 'last_update': 0},
    'mm_bot_3': {'status': 'offline', 'info': 'No contact', 'last_update': 0},
    'arb_bot_1': {'status': 'offline', 'info': 'No contact', 'last_update': 0},
    'arb_bot_2': {'status': 'offline', 'info': 'No contact', 'last_update': 0}
}

def process_message(msg):
    try:
        message = json.loads(msg.value().decode('utf-8'))
        bot = msg.topic()
        current_time = int(time.time())
        print(f"Received message for {bot}: {message}, Current time: {current_time}")  # Print the received message and current time
        bot_statuses[bot]['status'] = message['status']
        bot_statuses[bot]['info'] = message['info']
        bot_statuses[bot]['last_update'] = current_time  # Update the current time
        socketio.emit('update_status', {'bot': bot, 'status': message['status'], 'info': message['info'], 'ts': message['ts']})
    except Exception as e:
        print(f"Error processing message: {e}")

def consume_data():
    conf = {
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'bot_status_group',
        'auto.offset.reset': 'earliest'
    }
    consumer = Consumer(conf)
    topics = list(bot_statuses.keys())
    print(f"Subscribing to topics: {topics}")
    consumer.subscribe(topics)  # Convert dict_keys to list

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    raise KafkaException(msg.error())
            process_message(msg)
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()

@app.route('/')
def index():
    return render_template('index2.html', bot_statuses=bot_statuses)

@socketio.on('connect')
def handle_connect():
    for bot, status in bot_statuses.items():
        socketio.emit('update_status', {'bot': bot, 'status': status['status'], 'info': status['info'], 'ts': status['last_update']})

def check_bot_statuses():
    while True:
        current_time = int(time.time())
        for bot, status in bot_statuses.items():
            print(f"Checking status for {bot}. Current time: {current_time}, Last update: {status['last_update']}")  # Log the current check
            if current_time - status['last_update'] > 60:  # Adjust timeout to 60 seconds
                if status['status'] != 'offline':
                    status['status'] = 'offline'
                    status['info'] = 'No contact'
                    print(f"{bot} is now offline due to timeout.")  # Log the change to offline
                    socketio.emit('update_status', {'bot': bot, 'status': status['status'], 'info': status['info'], 'ts': status['last_update']})
        time.sleep(1)  # Reduced sleep interval for more frequent checks

if __name__ == '__main__':
    threading.Thread(target=consume_data).start()
    threading.Thread(target=check_bot_statuses).start()
    socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
