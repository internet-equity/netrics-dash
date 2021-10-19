from loguru import logger as log


class RouteErrorLogger:

    name = 'error-logger'
    api = 2

    def apply(self, callback, route):
        return log.catch(
            message=f"Error in function {route.callback.__name__}() for {route.method} {route.rule}:",
            reraise=True,
        )(callback)
