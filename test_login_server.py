import socket
import threading
import json
import psycopg2
import datetime
import random
from uuid import uuid4

conn_uri = "GET FROM SOMEWHERE ELSE!!!"

def connect_to_db():
    conn = psycopg2.connect(conn_uri)
    conn.set_session(autocommit=True)
    cur = conn.cursor()
    return cur

cur = connect_to_db()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("localhost", 5000))

print("Server up!")
print("Running on " + str(s.getsockname()[0]) + ":" + str(s.getsockname()[1]))

connections = {}

def handle_message(data, conn):
    send = json.dumps(data).encode()
    print("New message:", data["data"])
    for addr2 in connections:
        if addr2 != data["from"]:
            try:
                connections[addr2].sendall(send)
            except:
                print(f"Error sending to {addr2}, removing...")
                del connections[addr2]

def handle_account_creation(data, conn):
    account_data = data["data"] # {"user": str (username), "password": str (password HASH)}
    
    uuid = str(uuid4())
    symbol = random.choice("☀☁★☾♥♠♦♣♫☘☉☠")
    color = "#ffffff"
    timestamp = str(datetime.datetime.now())
    user = account_data["user"]
    password = account_data["password"]



    send_query='''insert into "Discord"."UserInfo" (user_id, user_name, user_password, user_color, user_symbol, user_creation_timestamp) values (%s, %s, %s, %s, %s, %s)'''
    cur.execute(send_query, (uuid, user, password, color, symbol, timestamp))

def handle_username_check(data, conn):
    user = data["data"]

    send_query = """select 1 from "Discord"."UserInfo" where user_name = %s"""
    cur.execute(send_query, (user,)) # weird tuple hack
    records = cur.fetchall()
    if len(records) > 0:
        conn.sendall("False".encode("utf-8"))
    else:
        conn.sendall("True".encode("utf-8"))

def handle_token_bypass(data, conn):
    data = data["data"]
    token = data["token"]
    sys_uuid = data["uuid"]

    f = Fernet(key + str(sys_uuid).encode())
    try:
        token = f.decrypt(token.encode("utf-8")).decode("utf-8")
    except:
        conn.sendall("False".encode("utf-8"))
        return
    else:
        conn.sendall(token.encode("utf-8"))


def pin_message(message_id, channel_id):
    send_query = '''select pinned_message_ids from "Discord"."ChatInfo" where chat_id = %s'''
    cur.execute(send_query, (channel_id,))
    records = cur.fetchall()
    if len(records) == 0:
        return False
    
    pinned_message_ids = records[0][0]
    if pinned_message_ids == None:
        pinned_message_ids = []

    if message_id in pinned_message_ids:
        return False
    
    pinned_message_ids.append(message_id)
    send_query = '''update "Discord"."ChatInfo" set pinned_message_ids = %s where chat_id = %s'''
    try:
        cur.execute(send_query, (pinned_message_ids, channel_id))
        return True
    except Exception as e:
        return False

def pin_message_endpoint(data, conn):
    data = data["data"]
    message_id = data["message_id"]
    channel_id = data["channel_id"]

    if pin_message(message_id, channel_id):
        if conn:
            conn.sendall("True".encode("utf-8"))
    else:
        if conn:
            conn.sendall("False".encode("utf-8"))



def handle_login(data, conn):
    account_data = data["data"]
    user = account_data["user"]
    password = account_data["password"]
    
    sys_uuid = account_data["sys_uuid"]

    send_query = """select 1 from "Discord"."UserInfo" where user_name = %s and user_password = %s"""
    cur.execute(send_query, (user, password))
    records = cur.fetchall()
    if len(records) > 0:
        token = str(uuid4())
        tokens[token] = user
        conn.sendall(token.encode("utf-8"))
    else:   
        
        conn.recv(1024)

        f = Fernet(key + str(sys_uuid).encode())
        conn.sendall(f.encrypt(token.encode("utf-8")))

''' 
def handle_recent_messages(data, conn):
    server_id = data["data"]

    send_query = """
    SELECT message_id, user_id, chat_id, server_id, replied_to_id, message_content, message_timestamp, pinged_user_ids
    FROM "Discord"."MessageInfo"
    WHERE server_id = %s
    ORDER BY message_timestamp DESC
    LIMIT 15
    """
    cur.execute(send_query, (server_id,))
    messages = cur.fetchall()
    messages_data = [{"message_id": msg[0], "user_id": msg[1], "chat_id": msg[2], "server_id": msg[3],
                      "replied_to_id": msg[4], "message_content": msg[5], "message_timestamp": msg[6].isoformat(),
                      "pinged_user_ids": msg[7]} for msg in messages]
    conn.sendall(json.dumps(messages_data).encode("utf-8"))

def handle_scroll_messages(data, conn):
    scroll_data = data["data"]
    server_id = scroll_data["server_id"]
    current_position = scroll_data.get("current_position", 0)
    direction = scroll_data["direction"]

    if direction == "up":
        current_position -= 1
        if current_position < 0:
            current_position = 0
    else:  # direction == "down"
        current_position += 1

    send_query = """
    SELECT message_id, user_id, chat_id, server_id, replied_to_id, message_content, message_timestamp, pinged_user_ids
    FROM "Discord"."MessageInfo"
    WHERE server_id = %s
    ORDER BY message_timestamp DESC
    OFFSET %s
    LIMIT 15
    """
    cur.execute(send_query, (server_id, current_position))
    messages = cur.fetchall()
    messages_data = [{"message_id": msg[0], "user_id": msg[1], "chat_id": msg[2], "server_id": msg[3],
                      "replied_to_id": msg[4], "message_content": msg[5], "message_timestamp": msg[6].isoformat(),
                      "pinged_user_ids": msg[7]} for msg in messages]
    conn.sendall(json.dumps({"messages": messages_data, "current_position": current_position}).encode("utf-8"))
'''
tokens = {}
handlers = {
    "msg": handle_message,
    "account_create": handle_account_creation,
    "username_check": handle_username_check,
    "login": handle_login,
#    "recent_messages": handle_recent_messages,
#    "scroll_messages": handle_scroll_messages
    "token_bypass": handle_token_bypass,
    "pin_message": pin_message_endpoint

}

def handle_connection(conn, addr):
    print("New connection:", addr)
    connections[addr] = conn
    while True:
        try:
            data = conn.recv(1024)
        except:
            pass
        else:
            if not data:
                print("Disconnect:", addr)
                del connections[addr]
                return
            parsed = json.loads(data.decode())
            for label in handlers:
                if "type" in parsed and parsed["type"] == label:
                    parsed["from"] = addr
                    print("Endpoint " + label + " called by " )
                    handlers[label](parsed, conn)
                    break


while True:
    s.listen()
    conn, addr = s.accept()
    threading.Thread(target=handle_connection, args=(conn, addr)).start()