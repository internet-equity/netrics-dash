## Dashboard for Local Performance

* **dash**: html file with a bunch of spans etc that get replaced by javascript
* **scripts/** is javascript, the `ndt7-*` scripts are modified from [ndt7-server](https://github.com/m-lab/ndt-server/tree/master/html) 
* **assets/** is the css and there are also some cutesy `img/`
* **pyscripts/** is the python code and this needs to get placed wherever you like to keep wsgi scripts.  I keep them in `/var/www/scripts/`.

You will have to set up WSGI, which mostly means:
```
sudo apt install apache2 apache2-utils ssl-cert libapache2-mod-wsgi-py3
```

You must also be running the docker container on the raspberry pi.
That means following [these instructions](https://www.measurementlab.net/blog/run-your-own-ndt-server/#setup-and-run-an-ndt-server-on-ubuntu-1804-lts) from M-Lab; however, you must clone and `docker build .` the package from scratch, since it is ARM.
Then you can launch it with `docker/launch-ndt`

Put your python functions ("microservices") in `/etc/apache2/conf-available/mod-wsgi.conf`:
```
WSGIScriptAlias /current_stats       /var/www/scripts/current_stats.py
WSGIScriptAlias /submit_subjective   /var/www/scripts/submit_subjective.py
WSGIScriptAlias /plots               /var/www/scripts/plots.py
```
and then restart apache.

