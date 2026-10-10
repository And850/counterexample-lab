"""PID 1 stays alive and reaps orphaned execution children."""
import signal
import time

signal.signal(signal.SIGCHLD, signal.SIG_IGN)
while True:
    time.sleep(3600)
