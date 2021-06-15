from bottle import route, redirect


@route('/', method='GET')
def redirect_to_dashboard():
    return redirect('/dashboard/', 302)
