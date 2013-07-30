#!/usr/bin/env python

#
# Before using this script, refer to install here:
#   https://github.com/AdamN/python-webkit2png/
#

from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import urlparse, re, os, subprocess, hashlib, json, time

try:
  import configparser
except ImportError:
  import ConfigParser as configparser




#
# ------------------------------
#   VAR (SEE INI FILE)
# ------------------------------
#
cfg = configparser.ConfigParser()
cfg.read("config.ini")


# webkit2png variable
webkit2png_root    = cfg.get("WEBKIT2PNG", "root")
webkit2png_app     = cfg.get("WEBKIT2PNG", "app")
# no need to convert to integer: only string allowed in Popen
webkit2png_timeout = cfg.get("WEBKIT2PNG", "timeout")

# server variable
server_url  = cfg.get("SERVER", "url")
server_port = int(cfg.get("SERVER", "port"))

# cache variable
cache_enable   = cfg.get("CACHE", "enable")
cache_lifetime = int(cfg.get("CACHE", "lifetime"))
cache_path     = cfg.get("CACHE", "path")
cache_tick     = float(cfg.get("CACHE", "garbadge"))


#
# ------------------------------
#   GLOBAL SCOPE
# ------------------------------
#


# Creating cache folder
if cache_enable == "true" and os.path.exists(cache_path) == 0:
  os.makedirs(cache_path, 0600)


# Compile the domain check
domainurl = re.compile(
     r'^(?:http)s?://' # http:// or https://
     r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
     r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
     r'(?::\d+)?' # optional port
     r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

def testurl(url):
  """ Test if an url is valid or not (taken from django) """
  # We refuse localhost check
  if "http://127" in url or "https://127" in url:
    return False

  # Test the domain
  return domainurl.match(url)





#
# ------------------------------
#   HANDLER
# ------------------------------
#

class PyQtHandler(BaseHTTPRequestHandler):
  """ Server handler for PyQt-webkit system """




  def do_GET(self):
    """ Proceed user request """
    # Initiate an infitite loop killer
    self.limit = 0

    # Parsing url query
    request = urlparse.parse_qs(urlparse.urlparse(self.path).query)
    # Debug
    print "*" * 30
    print "* New request"
    print "*" * 30
    print "Processing request: %s" % request
    # We check url does exist into parameter
    if "url" in request and testurl(request["url"][0]):
      print "Processing response"
      self.response(request["url"][0], request)
    else:
      print "ERROR: url is invalid or not existing"
      self.error()



  def extend_param(self, param, request):
    """ Parse the request to find extra parameters to apply to param """
    for key, value in request.iteritems():
      key = "--" + key
      value = value[0]

      if key == "--xvfb" or key == "--geometry" or key == "--scale":
        # We have to split dual integer
        splitted = value.split("*", 1)
        if splitted[0].isdigit() and splitted[1].isdigit():
          param.append(key)
          param.append(splitted[0])
          param.append(splitted[1])

      elif key == "--transparent" or key == "--encoded-url":
        if value != "false" and value != "0":
          param.append(key)

      elif key == "--wait" and value.isdigit():
        param.append(key)
        param.append(value)

      elif key == "--aspect-ratio" and value in ["ignore", "keep", "crop", "expand"]:
        param.append(key)
        param.append(value)

    # We have done parsing, we can return new param
    return param




  def generate(self, param, callback):
    """ Generating a new miniature """

    # Debug
    print "Generating a new image with parameters: %s" % param

    # Starting python-webkit2png
    proc = subprocess.Popen(param, stdout=subprocess.PIPE)

    # Proceed output
    while True:
      line = proc.stdout.readline()
      if line != "":
        self.wfile.write(line)
      else:
        if callback is not None:
          callback(param)
        break





  def webkit2png(self, param):
    """ Perform the webkit2png request, and also take care of cache """
    self.limit += 1

    # If there is previous "--output" we remove
    if "--output" in param:
      # Output are always at the end
      param.pop()
      param.pop()

    if cache_enable == "true":
      # Debug
      print "Cache is enable, searching into cache"

      # Computing md5 value of param
      jsonparam = json.dumps(param, sort_keys=True)
      md5param = hashlib.md5(jsonparam).hexdigest()

      # Creating time limit and file path
      file = os.path.join(cache_path, md5param) + ".png"
      old = time.time() - cache_lifetime

      # The file exist and is still valid
      if os.path.exists(file) and os.path.getctime(file) > old:
        # Debug        
        print "Serving content from cache #%s" % file

        # We can serve that file, it's still good
        content = open(file, "r")
        for line in content:
          self.wfile.write(line)

      # We need to generate a new file
      else:
        # Debug
        print "Need to generate a new file"

        # If file exist, we delete
        if os.path.exists(file):
          # Debug
          print "Remove file (too old): %s" % file
          os.remove(file)

        # We ask system to output into file (if it's not set)
        param.append("--output")
        param.append(file)

        # We can generate a new file, and call this function again
        if self.limit > 5:
          print "ERROR: Self limit is reached, system gone into infinite loop"
          raise Exception("Limit of calling webkit2png exceed")
        else:
          self.generate(param, self.webkit2png)

    else:
      self.generate(param, None)




  def error(self):
    """ Publishing a 404 error """
    self.send_response(404, "Not Found")
    self.send_header("Content-Type", "text/plain; charset=UTF-8")
    self.end_headers()
    self.wfile.write("")




  def response(self, url, request):
    """ Make default response """
    # Setting header
    self.send_response(200, "OK")
    self.send_header("Content-Type", "image/png")
    self.end_headers()

    # Default configuration option (including javascript enable, windows look & feel, and timeout to 30 sec)
    endpath = os.path.join(webkit2png_root, webkit2png_app)
    param = ["python", endpath, url, "-F", "javascript", "-t", webkit2png_timeout];

    # We parse request to find other elements
    param = self.extend_param(param, request)

    # Launching system
    self.webkit2png(param)


#
# ------------------------------
#   CACHE GARBADGE COLLECTOR
# ------------------------------
#

# On cache active, we create the garbage
if cache_enable == "true":
  from threading import Timer
  import glob

  # Initiate cache_current to start garbadge on boot
  cache_current = cache_tick + 1

  def cache_garbadge():
    global cache_current, cache_tick
    if cache_current > cache_tick:
      cache_current = 0
      # Clearing cache
      print "*" * 30
      print "* GARBADGE STARTING"
      print "*" * 30
      # cache_path
      fileList = glob.glob(os.path.join(cache_path, "*.png"))
      old = time.time() - cache_lifetime

      for file in fileList:
        if os.path.exists(file) and os.path.getctime(file) < old:
          print "Removing file from cache: %s" % file
          os.remove(file)

    # Run forever
    # The cache_current allow to setup a short timer
    # this help for shuting down quickly instead of waiting timer tick
    cache_current += 1
    t = Timer(1.0, cache_garbadge)
    t.start()

  # Start first time
  cache_garbadge();




#
# ------------------------------
#   THREAD RUNNER/STARTER
# ------------------------------
#



# Creating a dummy threaded server class
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  """ Handle request in thread """

if __name__ == "__main__":
  # Creating new server instance, and serve file from
  print "Starting server on %s, port %d" % (server_url, server_port)
  httpd = ThreadedHTTPServer((server_url, int(server_port)), PyQtHandler)
  httpd.serve_forever()
