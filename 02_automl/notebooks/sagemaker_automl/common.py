"""SageMaker AutoPilot Helpers.

This package contains helper classes and functions that are used in the candidates definition notebook.
"""

import json
import logging
import random
import threading
from time import gmtime, sleep, strftime

from botocore.exceptions import ClientError


def uid():
    """Returns an identifier that can be used when creating SageMaker entities like training jobs.
    Currently returns a formatted string representation of the current time"""
    return strftime("%d-%H-%M-%S", gmtime())


class AutoMLLocalCandidateStep:
    """Helper class to execute a callable which is decorated with some metadata like name action.
    """

    def __init__(self, name, action, description=""):
        self.name = name
        self.action = action
        self.description = description

    def run(self, context):
        self.action(context)

    def to_dict(self):
        return {"name": self.name, "description": self.description}

    def __repr__(self):
        json.dumps(self.to_dict(), indent=4)


def execute_steps(execution_name, steps, context, start_jitter_seconds=5):
    """Execute steps sequentially
    Args:
        execution_name (str): the execution name, used for logging
        steps (List[AutoMLLocalCandidateStep]): steps to run
        context (dict): a dictionary that contains shared context for the steps
        start_jitter_seconds (int): delay the execution on each steps to avoid throttling issues
    """

    # Add a bit jitter to avoid throttling API when many job starts
    start_jitter_seconds = random.randint(0, start_jitter_seconds)

    wait_seconds = 1
    max_wait_seconds = 64

    for step in steps:
        sleep(start_jitter_seconds)
        thread_name = threading.current_thread().name
        logging.info(
            "[{}:{}]Executing step: {}".format(thread_name, execution_name, step.name)
        )

        while True:
            try:
                step.run(context)
                break
            except ClientError as e:
                if (
                    e.response["Error"]["Code"] == "ThrottlingException"
                    and wait_seconds < max_wait_seconds
                ):
                    logging.info(
                        "We are getting throttled, retrying in {}s".format(wait_seconds)
                    )
                    sleep(wait_seconds)
                    wait_seconds = wait_seconds * 2
                    continue
                else:
                    raise e


class AutoMLLocalRunBaseError(RuntimeError):
    """Base class for all known exceptions raised by AutoML Locall runner"""


class AutoMLLocalCandidateNotPrepared(AutoMLLocalRunBaseError):
    """Raised when AutoML Local Candidate is not prepared for training"""


class AutoMLLocalCandidateNotTrained(AutoMLLocalRunBaseError):
    """Raised when AutoML Local Candidate is not trained"""
