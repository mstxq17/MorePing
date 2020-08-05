#!/usr/bin/python3
# -*- coding:utf-8 -*-

import os, sys, re
import threading, gevent
import queue
import json
from argparse import ArgumentParser, RawTextHelpFormatter
from alive_progress import alive_bar

from gevent import monkey

monkey.patch_all()
import requests
import time

# global variables
task_queue = queue.Queue()
result_queue = queue.Queue()
lock = threading.Lock()


def report_result():
    cdnHost = "cdnHost_" + time.strftime("%Y%m%d", time.localtime()) + ".txt"
    realHost = "realHost_" + time.strftime("%Y%m%d", time.localtime()) + ".txt"
    errorHost = "errorHost_" + time.strftime("%Y%m%d", time.localtime()) + ".txt"
    all_result = []

    # handle output
    global STOP_THIS

    try:
        while not STOP_THIS:
            if result_queue.qsize() == 0:
                time.sleep(0.1)
                continue
            while result_queue.qsize() > 0:
                all_result.append(result_queue.get())

            cdn_text = ""
            real_text = ""
            error_text = ""
            for item in all_result:
                if item["isCdn"] is True:
                    cdn_text += item["host"] + "\n"
                    cdn_text += "ip:" + ",".join(list(item["ip"])) + "\n"
                elif item["isCdn"] is False:
                    real_text += item["host"] + "\n"
                    real_text += "ip:" + "".join(list(item["ip"])) + "\n"
                else:
                    error_text += item["host"] + "\n"

            with open(cdnHost, "w") as f1, open(realHost, "w") as f2, open(
                errorHost, "w"
            ) as f3:
                f1.write(cdn_text)
                f2.write(real_text)
                f3.write(error_text)

        if all_result:
            print(
                "[Scan report save to]:{c} {r} {e}".format(
                    c=cdnHost, r=realHost, e=errorHost
                )
            )
        else:
            print("[Error, result null]")

    except Exception as e:
        print("[Error Save Result Thread]: {}".format(e))
        sys.exit(-1)


def format_producer(args):
    lines = []
    if args.host:
        lines.append(args.host.strip())

    if args.force and args.f:
        with open(args.f, "r") as inFile:
            content = inFile.read()
        pattern = re.compile(
            r"([a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+\.[a-z]+?)\s"
        )
        resList = pattern.findall(content)
        for h in resList:
            try:
                lines.append(list(h)[0])
            except Exception as e:
                print("[Error Force Mode]:{}".format(e))

    elif args.f:
        with open(args.f, "r") as inFile:
            lines += map(lambda x: x.strip(), inFile.readlines())

    # duplicate removal
    lines = list(set(lines))
    for host in lines:
        if host:
            task_queue.put(host)

    return True


def consumer(bar):
    while True:
        try:
            target = task_queue.get(timeout=0.5)
        except:
            if task_queue.empty():
                break

        thread_worker(target)
        # show the progress...
        lock.acquire()
        bar()
        lock.release()


def thread_worker(host):
    nodes = [25, 31, 4, 19, 7, 28, 21, 14, 27, 8, 1, 15]
    my_set = set()
    try:
        jobs = [gevent.spawn(gevent_worker, host, node, my_set) for node in nodes]
        gevent.joinall(jobs, timeout=20)
        # print([job.value for job in jobs])
        if my_set:
            isCdn = True if len(my_set) > 1 else False
        else:
            isCdn = "Error"
        result = {"host": host, "isCdn": isCdn, "ip": my_set}
        print(result)
        # enter result to result_queue
        result_queue.put(result)

    except Exception as e:
        print("[Error Thread worker]: {}".format(e))


def gevent_worker(host, node, my_set):
    req_url = "https://wepcc.com:443/check-ping.html"
    req_headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
    param_body = "node={n}&host={h}".format(n=node, h=host)
    try:
        req = requests.post(url=req_url, data=param_body, headers=req_headers)
        if req.status_code == 200:
            try:
                json_data = json.loads(req.content)
                try:
                    if json_data["data"]["Error"]:
                        return False
                except:
                    pass
                ip = json_data["data"]["Ip"]
                my_set.add(ip)
                return True
            except Exception as e:
                print("[Error Gevent Worker Parse Json]: {}".format(e))
        else:
            print(req.status_code)
    except Exception as e:
        print("[Main Error Gevent Worker]: {}".format(e))
        time.sleep(0.5)

    return False


def parse_args():
    parser = ArgumentParser(
        prog="morePing",
        formatter_class=RawTextHelpFormatter,
        description="* A cdn detector with high speed *\n",
        usage="morePing.py [options]",
    )
    parser.add_argument(
        "--host",
        metavar="HOST",
        type=str,
        default="",
        help="Scan host from command line",
    )
    parser.add_argument(
        "-f",
        metavar="TargetFile",
        type=str,
        default="",
        help="Load new line delimited targets from TargetFile",
    )
    parser.add_argument(
        "-p",
        metavar="PROCESS",
        type=int,
        default=10,
        help="Number of processes running concurrently, 10 by default",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force to extract host from irregular Text"
    )
    parser.add_argument("-v", action="version", version="%(prog)s 1.0    By xq17")

    if len(sys.argv) == 1:
        sys.argv.append("-h")
    args = parser.parse_args()
    check_args(args)
    return args


def check_args(args):
    if not args.host and not args.f:
        msg = "Args missing! --host baidu.com or -f host.txt not found"
        print(msg)
        exit(-1)

    if args.f and not os.path.isfile(args.f):
        print("TargetFile not found: {file}".format(file=args.f))


def main():
    args = parse_args()
    print("* MorePing v1.0  https://github.com/xq17/MorePing *")
    print("* preparing to generate task..... *")
    format_producer(args)
    target_count = task_queue.qsize()
    print("{} targets entered Queue.".format(target_count))
    thread_count = args.p
    print("Creating {} sub Processes...".format(thread_count))
    scan_process = []
    print("Report thread running...")
    global STOP_THIS
    STOP_THIS = False

    threading.Thread(target=report_result).start()
    try:
        with alive_bar(target_count) as bar:
            for _ in range(thread_count):
                t = threading.Thread(target=consumer, args=(bar,), daemon=True)
                # t.setDaemon(true)
                t.start()
                scan_process.append(t)
            print("{} sub process successfully Running.".format(thread_count))
            for t in scan_process:
                t.join()
    except KeyboardInterrupt as e:
        time.sleep(0.5)
        print("[+] User aborted, sub scan processs exited..")

    except Exception as e:
        print("[__main__.exception]: {type} {error}".format(type=type(e), error=e))

    # output the result to file
    STOP_THIS = True

if __name__ == "__main__":
    main()
