import random
import time


def date_time_original(localtime):
    # return time.strftime("%Y:%m:%d+%H:%M:%S", localtime)
    return time.strftime("%Y%m%dT%H%M%S.000Z", localtime)


def random_delay(delay_range: list):
    """Trigger sleep of a random floating number in range min_sleep to max_sleep"""
    return time.sleep(random.uniform(delay_range[0], delay_range[1]))
