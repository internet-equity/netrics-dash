from loguru import logger as log


def RouteErrorLogger(callback):
    return log.catch(reraise=True)(callback)
