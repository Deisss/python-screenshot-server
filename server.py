#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Before using this script, refer to install here:
# https://github.com/AdamN/python-webkit2png/
#

from ConfigLoader import getCfg
from bottle import route, get, run, request, response
from datetime import datetime
import urlparse, re, os, subprocess, hashlib, json, time, logging, sys


#
# ------------------------------
#     SCRIPT VARIABLES
# ------------------------------
#
class _webkit(object):
    ''' Simple class to manipulate webkit2png configuration '''
    def __init__(self):
        self.root    = getCfg('WEBKIT2PNG', 'root')
        self.app     = getCfg('WEBKIT2PNG', 'app')
        # no need to convert to integer: only string allowed in Popen
        self.timeout = getCfg('WEBKIT2PNG', 'timeout')

webkitCfg = _webkit()

class _server(object):
    ''' Simple class to manipulate server configuration '''
    def __init__(self):
        self.url       = getCfg('APPLICATION', 'url')
        self.port      = getCfg('APPLICATION', 'port', 'int')
        self.localhost = getCfg('APPLICATION', 'localhost')

    def allowLocalhost(self):
        if self.localhost == 'true' or self.localhost == '1' or self.localhost == 'True':
            return True
        return False

serverCfg = _server()

class _cache(object):
    ''' Simple class to manipulate cache configuration '''
    def __init__(self):
        self.enable   = getCfg('CACHE', 'enable')
        self.lifetime = getCfg('CACHE', 'lifetime', 'int')
        self.path     = getCfg('CACHE', 'path')
        self.tick     = getCfg('CACHE', 'garbadge', 'float')

    def isEnabled(self):
        if self.enable == 'true' or self.enable == '1' or self.enable == 'True':
            return True
        return False

    def createCachePathIfNotExists(self):
        if self.isEnabled() and not(self.pathExists()):
            os.makedirs(self.path, 0600)

    def pathExists(self):
        return (os.path.exists(self.path) == True)

cacheCfg = _cache()

#
# ------------------------------
#     GLOBAL SCOPE
# ------------------------------
#

# Creating cache folder
cacheCfg.createCachePathIfNotExists()

# Compile the domain check
domainurl = ''
if serverCfg.allowLocalhost() == False:
    domainurl = re.compile(
        r'^(?:http)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
else:
    domainurl = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

def testurl(url):
    ''' Test if an url is valid or not (taken from django) '''
    # We refuse localhost check
    if serverCfg.allowLocalhost() == False and ('http://127' in url or 'https://127' in url):
        return False

    # Test the domain
    return domainurl.match(url)





#
# ------------------------------
#     HANDLER
# ------------------------------
#

@route('/checkhealth', method='OPTIONS')
def haproxy():
    ''' Haproxy checkhealth status check '''
    response.status = 200
    return ''

@route('/', method='GET')
def screenshot():
    ''' Create a new screenshot '''
    # Initiate an inifinite loop killer
    limit = 0

    # Get parameters
    url = request.GET.get('url', '').strip()
    if not(testurl(url)):
        logging.info('Submitted url is not valid: "%s"' % url)

    # Now we can create the final file, and return everything
    response.status = 200
    response.add_header('Content-Type', 'image/png')

    # Construct the parameters to send to user
    param = createWebkit2PngParametersStructure(url, request)
    return webkit2png(limit, param)






#
# ------------------------------
#     INTERNAL HELPERS
# ------------------------------
#
def createWebkit2PngParametersStructure(url, request):
    ''' Create the parameters base to use for using webkit2png '''
    global webkitCfg

    # Create parameters content for webkit2png
    endpath = os.path.join(webkitCfg.root, webkitCfg.app)
    param = ['python', endpath, url, '-F', 'javascript', '-t', webkitCfg.timeout];

    # We parse request to find other elements
    return extendsParam(param, request)


def extendsParam(param, request):
    ''' Parse the request to find extra parameters to apply to param '''
    for key, value in request.GET.iteritems():
        key = '--' + key

        if key == '--xvfb' or key == '--geometry' or key == '--scale':
            # We have to split dual integer
            separated = re.split('[*|x]', value)
            if len(separated) < 2:
                logging.info('the key %s is invalid, should be at least 2 parameters separated with "*" or "x"...' % key)
                continue

            if separated[0].isdigit() and separated[1].isdigit():
                param.append(key)
                param.append(separated[0])
                param.append(separated[1])

        elif key == '--transparent' or key == '--encoded-url':
            if value != 'false' and value != '0':
                param.append(key)

        elif key == '--wait' and value.isdigit():
            param.append(key)
            param.append(value)

        elif key == '--aspect-ratio' and value in ['ignore', 'keep', 'crop', 'expand']:
            param.append(key)
            param.append(value)

    # We have done parsing, we can return new param
    return param







def webkit2png(limit, param):
    ''' Perform the webkit2png request, and also take care of cache '''
    limit = limit + 1

    # If there is previous '--output' we remove
    if '--output' in param:
        # Output are always at the end
        param.pop()
        param.pop()

    if cacheCfg.isEnabled():
        # Debug
        logging.debug('Cache is enable, searching into cache')

        # Computing md5 value of param
        jsonparam = json.dumps(param, sort_keys=True)
        md5param = hashlib.md5(jsonparam).hexdigest()

        # Creating time limit and file path
        file = os.path.join(cacheCfg.path, md5param) + '.png'
        old = time.time() - cacheCfg.lifetime

        # The file exist and is still valid
        if os.path.exists(file) and os.path.getctime(file) > old:
            # Debug
            logging.debug('Serving content from cache #%s' % file)

            # We can serve that file, it's still good
            content = open(file, 'r')
            return content

        # We need to generate a new file
        else:
            # Debug
            logging.debug('Need to generate a new file')

            # If file exist, we delete
            if os.path.exists(file):
                # Debug
                logging.debug('Remove file (too old): %s' % file)
                os.remove(file)

            # We ask system to output into file (if it's not set)
            param.append('--output')
            param.append(file)

            # We can generate a new file, and call this function again
            if limit > 5:
                logging.error('Limit has been reached, system gone into infinite loop, stop processing request')
                raise Exception('Limit of calling webkit2png exceed')
            else:
                return generateImageOuput(limit, param, webkit2png)

    else:
        return generateImageOuput(limit, param, None)

def generateImageOuput(limit, param, callback):
    ''' Final image generation: sub process webkit2png and write to output '''
    # Debug
    logging.debug('Generating a new image with parameters: %s' % param)

    # Starting python-webkit2png
    proc = subprocess.Popen(param, stdout=subprocess.PIPE)

    content = ''
    # Proceed output
    while True:
        line = proc.stdout.readline()
        if line != '':
            content = content + line
        else:
            if callback is not None:
                return callback(limit, param)
            break

    return content




#
# ------------------------------
#     LOGGING
# ------------------------------
#
class stdLogger(object):
    ''' Redirect all std* to the logging plugin '''
    def __init__(self, logger, level):
        self.logger = logger
        self.level  = level

    def write(self, message):
        if message != '\n':
            self.logger.log(self.level, message)

class NoHaproxyLoggingFilter(logging.Filter):
    ''' Disable haproxy logging filter '''
    def __init__(self, name='NoHaproxyLoggingFilter'):
        logging.Filter.__init__(self, name)

    def filter(self, record):
        return not record.getMessage().startswith('200 OPTIONS /checkhealth')



def getLogLevel():
    ''' Get the current application minimum log level '''
    level = getCfg('LOG', 'level').lower()
    if level == 'info' or level == 'information':
        return logging.INFO
    elif level == 'warn' or level == 'warning':
        return logging.WARN
    elif level == 'error' or level == 'err':
        return logging.ERROR
    else:
        return logging.DEBUG


def configureLogger(_logFolder, _logFile):
    ''' Start the logger instance and configure it '''
    # Set debug level
    logger = logging.getLogger()
    logger.setLevel(getLogLevel())

    # Format
    formatter = logging.Formatter('%(asctime)s - %(levelname)s | %(name)s -> %(message)s', '%Y-%m-%d %H:%M:%S')

    # Remove default handler to keep only clean one
    for hdlr in logger.handlers:
        logger.removeHandler(hdlr)

    # Create missing folder if needed
    if not os.path.exists(_logFolder):
        os.makedirs(_logFolder, 0700)

    #
    # ----------------------------
    #   CREATE CONSOLE HANDLER
    # ----------------------------
    #

    # Create console handler
    consoleh = logging.StreamHandler()
    consoleh.setLevel(getLogLevel())
    consoleh.setFormatter(formatter)

    # Set our custom handler
    logger.addHandler(consoleh)

    #
    # ----------------------------
    #   CREATE FILE HANDLER
    # ----------------------------
    #
    fileh = logging.FileHandler(_logFile, 'a')
    fileh.setLevel(getLogLevel())
    fileh.setFormatter(formatter)

    # Set our custom handler
    logger.addHandler(fileh)

def configureTornadoHaproxyLogging():
    ''' Disable haproxy logging into default tornado element '''
    logging.getLogger('tornado.access').addFilter(NoHaproxyLoggingFilter())

def printWelcomeMessage(msg, place=10):
    ''' Print any welcome message '''
    logging.debug('*' * 30)
    welcome = ' ' * place
    welcome+= msg
    logging.debug(welcome)

    logging.debug('*' * 30 + '\n')



#
# ------------------------------
#     CACHE GARBADGE COLLECTOR
# ------------------------------
#

# On cache active, we create the garbage
if cacheCfg.isEnabled():
    from threading import Timer
    import glob

    # Initiate current to start garbadge on boot
    current = cacheCfg.tick + 1

    def cache_garbadge():
        global current, cacheCfg
        if current > cacheCfg.tick:
            current = 0
            # Clearing cache
            printWelcomeMessage('GARBADGE STARTING', 2)

            # cacheCfg.path
            fileList = glob.glob(os.path.join(cacheCfg.path, '*.png'))
            old = time.time() - cacheCfg.lifetime

            for file in fileList:
                if os.path.exists(file) and os.path.getctime(file) < old:
                    logging.debug('Removing file from cache: %s' % file)
                    os.remove(file)

        # Run forever
        # The current allow to setup a short timer
        # this help for shuting down quickly instead of waiting timer tick
        current += 1
        t = Timer(1.0, cache_garbadge)
        t.start()

    # Start first time
    cache_garbadge();





if __name__ == '__main__':
    logFile   = getCfg('LOG', 'file')
    logFolder = os.path.dirname(logFile)
    configureLogger(logFolder, logFile)

    # Print logger message
    logging.debug('\n\nSystem start at: %s\nSystem log level: %s\n' % (datetime.now(), getCfg('LOG', 'level')))

    # Configure logger for stdout and stderr
    bottleLoggerStdout = logging.getLogger('bottle')
    sys.stdout = stdLogger(bottleLoggerStdout, logging.INFO)
    sys.stderr = stdLogger(bottleLoggerStdout, logging.INFO)

    printWelcomeMessage('STARTING', 11)
    printWelcomeMessage('SETUP ROUTES', 8)

    configureTornadoHaproxyLogging()

    # Start the web server
    printWelcomeMessage('SERVER RUNNING ON PORT %i' % serverCfg.port, 1)
    run(server='tornado', host=serverCfg.url, port=serverCfg.port)
