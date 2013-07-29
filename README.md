python-screenshot-server
========================

A web server for creating webpage screenshot or thumbnail (from url), with cache feature.




Installation
============

First you need to follow [python-webkit2png setup](https://github.com/adamn/python-webkit2png).


You have two type of installation, the zip version (basic one) or the git version (better if you have access to git).

**Basic one**
Just grab the zip of this project, and uncompress it somewhere, __the system does not need any installation__...


**Git one**
Install git:

**Ubuntu:**

    apt-get install git-core

**Centos:**

    yum install git-core

Clone the repository:

    cd /opt
    mkdir python-screenshot-server
    git clone https://github.com/Deisss/python-screenshot-server.git .




Configuration
=============

You can configure the server (port, cache, how to find [python-webkit2png](https://github.com/adamn/python-webkit2png), by editing __config.ini__:

    vim config.ini


Here is a detailled list of available configuration:

**[WEBKIT2PNG]**

    root | the main path to find webkit2png (can be relative or absolute path)
    app  | From the root path, where to find webkit2png script (should not be needed to change)
    timeout | Integer value to describe timeout before considering a site is not responding


**[SERVER]**

    url | The url to bind on server, leave blank should be nice
    port | Integer value to specify the current port to use


**[CACHE]**

    enable | boolean to indicate if cache should be working or not (strongly pro for true)
    lifetime | The time an image will be consider as valid. You can put few days without trouble here
    path | The folder to store cache inside
    garbadge | A thread is running in parallel to clear old image, indicate how long to wait before new gargadge pass




Start server
============

Just run python:

    python server.py

And that's it the server is running.




Usage
=====

You can change the rendering behaviour threw parameter you pass to url:
The default url should looks like this: **http://localhost:9494/url=http://www.google.fr**

Parameter you can send
  * **url**: needed, specify the full url of the page (including http/https)
  * **xvfb**: Start and xvfb instance with the given size, example **90*60** which means 90px and 60px (width/height).
  * **geometry**: The geometry of the screenshot browser, example **250*80** wich means 250px and 80px (width/height).
  * **scale**: The image scale (to this size), example **300*200** wich means 300px and 200px (width/height).
  * **aspect-ratio**: The aspect ratio to use, can be "ignore", "keep", "crop", "expand".
  * **wait**: Any positive integer. Wait X seconds before taking the screenshot, take care of timeout limit.
  * **transparent**: Any value except "false" and "0" will be taken as true. Ask webkit2png to use transparent image (need CSS transparent in html page).
  * **encoded-url**: Any value except "false" and "0" will be taken as true. Say to webkit2png the url is encoded.

Some test you can run:
  * __http://localhost:9494/?url=http://www.google.com&transparent=true&scale=150*100__
  * __http://localhost:9494/?url=http://www.twitter.com&geometry=150*300&aspect-ratio=crop__

  
Enjoy !
