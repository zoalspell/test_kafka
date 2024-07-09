import json
import random
import time
from confluent_kafka import Producer, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
from datetime import datetime

broker = 'localhost:9092'
producer = Producer({'bootstrap.servers': broker})

admin_client = AdminClient({'bootstrap.servers': broker})

# Define the topics to be created with replication factor of 1
topics = ['mm_bot_1', 'mm_bot_2', 'mm_bot_3', 'arb_bot_1', 'arb_bot_2']
topics_to_create = []
for topic in topics:
    topics_to_create.append(NewTopic(topic, num_partitions=1, replication_factor=1))

# Create topics
try:
    admin_client.create_topics(new_topics=topics_to_create, validate_only=False)
    print(f"Topics {topics} created successfully.")
except KafkaException as e:
    print(f"Error creating topics: {e}")

bots = topics  # Using the same list for simplicity

tokens = ['BTC', 'ETH', 'USDT']
exchanges = ['Bitkub', 'Binance Thai']

# Track working status of each bot
bot_working_status = {bot: False for bot in bots}


def acked(err, msg):
    if err is not None:
        print(f"Failed to deliver message: {err}")
    else:
        print(f"Message produced: {msg.value()}")


def format_number(value):
    return "{:,.2f}".format(value)


def generate_arbitrage_messages():
    token = random.choice(tokens)
    buy_exchange = exchanges[0]
    sell_exchange = exchanges[1]

    # Generate realistic buy and sell prices in THB
    if token == 'BTC':
        base_price = round(random.uniform(2000000, 2100000), 2)
    elif token == 'ETH':
        base_price = round(random.uniform(100000, 120000), 2)
    elif token == 'USDT':
        base_price = round(random.uniform(35, 40), 2)

    buy_price = base_price
    sell_price = round(buy_price * random.uniform(1.01, 1.02), 2)  # Small profit margin
    amount = round(random.uniform(0.1, 2.0), 4) if token != 'USDT' else round(random.uniform(1000, 50000), 2)
    value_earn = round((sell_price - buy_price) * amount, 2)

    return [
        {"ts": int(datetime.utcnow().timestamp()), "status": "working",
         "info": f"🔵 Buy {token} at ฿{format_number(buy_price)} from {buy_exchange} for {amount} {token}"},
        {"ts": int(datetime.utcnow().timestamp()), "status": "working",
         "info": f"🔄 Send {amount} {token} from {buy_exchange} to {sell_exchange}"},
        {"ts": int(datetime.utcnow().timestamp()), "status": "working",
         "info": f"🟢 Sell {token} at ฿{format_number(sell_price)} on {sell_exchange} and earn ฿{format_number(value_earn)}"}
    ]


def generate_market_making_message():
    token = random.choice(tokens)
    action = random.choice(["Buy", "Sell"])

    if token == 'BTC':
        base_price = round(random.uniform(2000000, 2100000), 2)
    elif token == 'ETH':
        base_price = round(random.uniform(100000, 120000), 2)
    elif token == 'USDT':
        base_price = round(random.uniform(35, 40), 2)

    price = base_price if action == "Buy" else round(base_price * random.uniform(1.01, 1.02), 2)
    amount = round(random.uniform(0.1, 2.0), 4) if token != 'USDT' else round(random.uniform(1000, 50000), 2)

    return {"ts": int(datetime.utcnow().timestamp()), "status": "working",
            "info": f"🔵 {action} {token} at ฿{format_number(price)} for {amount} {token}"}


def send_heartbeat(bot):
    if not bot_working_status[bot]:  # Only send heartbeat if bot is not working
        heartbeat_message = {"ts": int(datetime.utcnow().timestamp()), "status": "online", "info": ""}
        print(f"Sending heartbeat for {bot}: {heartbeat_message}")
        producer.produce(bot, json.dumps(heartbeat_message), callback=acked)
        producer.flush()


while True:
    for bot in bots:
        if "arb_bot" in bot:
            bot_working_status[bot] = True
            messages = generate_arbitrage_messages()
            for message in messages:
                print(f"Producing message for {bot}: {message}")
                producer.produce(bot, json.dumps(message), callback=acked)
                producer.flush()
                # Sleep for a random time between 5 and 15 seconds to ensure messages are sent in order
                time.sleep(random.uniform(5, 15))
            bot_working_status[bot] = False
        else:
            bot_working_status[bot] = True
            # Start with an online status
            online_message = {"ts": int(datetime.utcnow().timestamp()), "status": "online", "info": ""}
            print(f"Producing message for {bot}: {online_message}")
            producer.produce(bot, json.dumps(online_message), callback=acked)
            producer.flush()
            time.sleep(random.uniform(5, 15))

            # Then send a market-making message
            message = generate_market_making_message()
            print(f"Producing message for {bot}: {message}")
            producer.produce(bot, json.dumps(message), callback=acked)
            producer.flush()
            # Sleep for a random time between 5 and 15 seconds for each bot
            sleep_time = random.uniform(5, 15)
            print(f"Sleeping for {sleep_time:.2f} seconds for {bot}")
            time.sleep(sleep_time)
            bot_working_status[bot] = False

    # Sleep for a random time between 5 and 20 seconds before starting the next cycle
    cycle_sleep_time = random.uniform(5, 20)
    print(f"Sleeping for {cycle_sleep_time:.2f} seconds before starting the next cycle")
    time.sleep(cycle_sleep_time)

    # Send heartbeats every 5 seconds if no work
    for bot in bots:
        send_heartbeat(bot)
        time.sleep(5)
