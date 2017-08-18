@app.route('/')
@login_required
def hello_world():
    return flask.redirect(flask.url_for('admin'))