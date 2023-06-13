"""

"""
import traceback
from sys import argv

from module.log import logger
from module.task_manager import TaskManager

bidTaskManager = TaskManager()

def main(argv: list):
    argv = argv[1:] if len(argv) > 1 else argv
    try:
        if argv[0] == "-r":
            logger.hr("task restart", 3)
            bidTaskManager.restart = True
        bidTaskManager.loop()
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.error(traceback.format_exc())
    finally:
        bidTaskManager.exit()


if __name__ == "__main__":
    main(argv)
