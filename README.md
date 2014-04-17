# python-screenshot-server

A web server for creating webpage screenshot or thumbnail (from url), with cache feature.




## Installation

Install git:
```sh
    # Ubuntu
    apt-get install git-core python python-setuptools
    # or Centos
    yum install git-core python python-setuptools
```

Then you can clone the repository:
```sh
    cd /opt
    mkdir python-screenshot-server
    git clone --recursive https://github.com/Deisss/python-screenshot-server.git python-screenshot-server
```

We need to install everything for making [python-webkit2png](https://github.com/adamn/python-webkit2png) working:
```sh
    # Ubuntu (as doc suggest)
    apt-get install python-qt4 libqt4-webkit xvfb flashplugin-installer
    # or Centos
    # You will need EPEL for PyQt4-webkit, here is for Centos 6 (search on internet if this link is broken):
    su -c 'rpm -Uvh http://download.fedoraproject.org/pub/epel/6/i386/epel-release-6-8.noarch.rpm'
    yum install -y python PyQt4 PyQt4-webkit xorg-x11-server-Xvfb
```

Now the system include the python-webkit2png git also (threw clone --recursive), so lets finish installation:
```sh
    cd python-screenshot-server/python-webkit2png
    python setup.py install
```

Finally, you will need python bottle (and tornado as server) to handle incomming user requests:
```sh
    pip install bottle tornado
```

The system should now be correctly setup. But you may need extra content, especially on headless server.
```sh
    # On CentOS
    yum groupinstall fonts
```
This will install most of basic fonts for rendering text on image. You will also need ```Xvfb``` to render graphics.




## Configuration

You can configure the server (port, cache, how to find [python-webkit2png](https://github.com/adamn/python-webkit2png), ...), by editing __config.ini__:
```sh
    cd /opt/python-screenshot-server
    vim config.ini
```

Here is a detailled list of available configuration:

**Section: WEBKIT2PNG**

  * **root**: the main path to find webkit2png (can be relative or absolute path)
  * **app**: From the root path, where to find webkit2png script (should not be needed to change)
  * **timeout**: Integer value to describe timeout before considering a site is not responding


**Section: SERVER**

  * **url**: The url to bind on server, leave blank should be nice
  * **port**: Integer value to specify the current port to use
  * **localhost**: Boolean, define if we allow localhost url (true) or not (false)


**Section: CACHE**

  * **enable**: boolean to indicate if cache should be working or not (strongly pro for true)
  * **lifetime**: The time an image will be consider as valid. You can put few days without trouble here
  * **path**: The folder to store cache inside
  * **garbadge**: A thread is running in parallel to clear old image, indicate how long to wait before new gargadge pass




## Start server

Just run python ```python server.py```

And that's it the server is running and ready to handle requests.

Now, you may still get blank image with the following error: 'Cannot connect to X server'. It means you need Xvfb to run before:
```sh
    Xvfb :25 -screen 0 4096x10000x24 2>/dev/null &
    export DISPLAY=127.0.0.1:25.0
```
Should correct this, even on headless server.

You may also be interested into the font packages to render font (you may see trouble with font on headless server), on CentOS:
```sh
    yum groupinstall fonts
```

Should remove blank fonts to show everything as expected!


## Usage

You can change the rendering behaviour threw parameter you pass to url:
The most basic url should looks like this: **http://localhost:9494/url=http://www.google.fr**


Parameter you can send are:
  * **url**: needed, specify the full url of the page (including http/https)
  * **xvfb**: Start and xvfb instance with the given size, example **90*60** which means 90px and 60px (width/height).
  * **geometry**: The geometry of the screenshot browser, example **250*80** wich means 250px and 80px (width/height).
  * **scale**: The image scale (to this size), example **300*200** wich means 300px and 200px (width/height).
  * **aspect-ratio**: The aspect ratio to use, can be "ignore", "keep", "crop", "expand".
  * **wait**: Any positive integer. Wait X seconds before taking the screenshot, take care of timeout limit.
  * **transparent**: Any value except "false" and "0" will be taken as true. Ask webkit2png to use transparent image (need CSS transparent in html page).
  * **encoded-url**: Any value except "false" and "0" will be taken as true. Say to webkit2png the url is encoded.


Some test you can run to check if it's working:
  * [goole thumbnail](http://localhost:9494/?url=http://www.google.com&transparent=true&scale=150*100)
  * [twitter thumbnail](http://localhost:9494/?url=http://www.twitter.com&geometry=150*300&aspect-ratio=crop)


Enjoy !
