import bottle
import waitress


class WaitressServer(bottle.ServerAdapter):

    # bottle's adapter fails to pass options in v0.12.19 (fixed in master)
    def run(self, handler):
        waitress.serve(handler, host=self.host, port=self.port, _quiet=self.quiet, **self.options)
