#!/usr/bin/python3

import threading
import pprint
import queue
import sys
from tqdm import tqdm
import randstr
import subprocess
import os
import time

THREADS_LIMIT = os.cpu_count()
ROUTES_PER_STEP = 100

files = []
params = []
for param in sys.argv[1:]:
    params.append(param) if "--" in param else files.append(param)

if len(files) != 3:
    print("{0} [options]... basechars-file keymap-file routes-file".format(sys.argv[1]))
    exit(0)

basechars_file, keymap_file, routes_file = files
results_q = queue.Queue()

def process_queue(routes_q, results_q, counter):
    while True:
        try:
            routes = routes_q.get(False)
        except queue.Empty:
            # print("Queue is empty!")
            # print("QSize: {0}".format(routes_q.qsize()))
            break
        result = process_route(params, basechars_file, keymap_file, routes)
        results_q.put(result)
        counter.update()



def process_route(params, basechars_file, keymap_file, routes):
    tmpfile = "/tmp/kwpmt-" + randstr.randstr(10)
    with open(tmpfile, "w") as fh:
        fh.write(routes)

    cmd = ["./kwp"]
    cmd += params
    cmd.append(basechars_file)
    cmd.append(keymap_file)
    cmd.append(tmpfile)
    output = subprocess.check_output(cmd)

    os.unlink(tmpfile)

    return output.decode()

tmp_content = ""
tmp_countent_cnt = 0
routes_q = queue.Queue()
with open(routes_file) as fh:
    for line in fh:
        if not len(line.strip()):
            continue

        tmp_content += line
        tmp_countent_cnt += 1

        if tmp_countent_cnt == ROUTES_PER_STEP:
            routes_q.put(tmp_content)
            tmp_content = ""
            tmp_countent_cnt = 0
if len(tmp_content) > 0:
    routes_q.put(tmp_content)
    tmp_content = ""
    tmp_countent_cnt = 0

print("We got {0} routes".format(routes_q.qsize()))

results_file_name = os.path.basename(keymap_file).replace(".keymap", "") + "__" + \
                    os.path.basename(basechars_file).replace(".base", "") + "__" + \
                    os.path.basename(routes_file).replace(".route", "") + \
                    ("_" + "_".join(params)).replace("--", '').replace('-', "_") + \
                    ".results"
print("Put results in " + results_file_name)


counter = tqdm(range(routes_q.qsize()))


class Worker(threading.Thread):
    daemon = True

    def run(self) -> None:
        while True:
            try:
                routes = routes_q.get(False)
                result = process_route(params, basechars_file, keymap_file, routes)
                results_q.put(result)
                counter.update()
            except queue.Empty:
                # print("Queue is empty!")
                # print("QSize: {0}".format(routes_q.qsize()))
                break

class Writer(threading.Thread):
    daemon = True
    may_work = True

    def run(self) -> None:
        with open(results_file_name, "w") as fh:
            while self.may_work:
                try:
                    result = results_q.get(False)
                    fh.write(result)
                except queue.Empty:
                    time.sleep(1)
                    continue



writer = Writer()
writer.start()

pool = []
for _ in range(THREADS_LIMIT):
    w = Worker()
    w.start()
    pool.append(w)


isAlive = True
while isAlive:
    isAlive = False

    for w in pool:
        if w.is_alive():
            isAlive = True
            break

    time.sleep(1)

writer.may_work = False
while writer.is_alive():
    time.sleep(1)


