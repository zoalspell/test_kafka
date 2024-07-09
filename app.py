from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from confluent_kafka import Consumer, KafkaException, KafkaError
import threading
import json
import uuid

app = Flask(__name__)
socketio = SocketIO(app)

def process_message(msg):
    try:
        message = json.loads(msg.value().decode('utf-8'))
        role = message.get('role')
        tokens_count = len(message.get('message').split(" "))
        socketio.emit('new_data', {'role': role, 'tokens_count': tokens_count})
    except Exception as e:
        print(f"Error processing message: {e}")

def consume_data():
    conf = {
        'bootstrap.servers': 'publickafka.quix.io:9092',
        'group.id': str(uuid.uuid4()),
        'auto.offset.reset': 'earliest'
    }
    consumer = Consumer(conf)
    consumer.subscribe(['demo-onboarding-prod-chat'])

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
    return render_template('index.html')

if __name__ == '__main__':
    threading.Thread(target=consume_data).start()
    socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
