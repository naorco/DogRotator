import sys, requests, json, threading, time, argparse
import websocket
SERVER_URL = "http://127.0.0.1:8000"
children = ['עדן','שקד']
schedule = {wd:(children[wd%2] if wd!=6 else children[1],False) for wd in range(0,7)}
print(f"children new list: {children}")
print(f"new schedule: {schedule}")


r = requests.post(SERVER_URL+"/update_children", data= {'children':children})
print(f"results: {r.text}")
r = requests.post(SERVER_URL+"/update_schedule", json=schedule)
print(f"results: {r.text}")
# r = requests.get(SERVER_URL+"/today")
# print(r.text)

