#!/usr/bin/env python

#
# Before using this script, refer to install here:
# https://github.com/AdamN/python-webkit2png/
#

from bottle import route, get, run, request, response
import urlparse, re, os, subprocess, hashlib, json, time

try:
    import configparser
except ImportError:
    import ConfigParser as configparser




#
# ------------------------------
#     VAR (SEE INI FILE)
# ------------------------------
#
cfg = configparser.ConfigParser()
cfg.read('config.ini')


# webkit2png variable
webkit2png_root = cfg.get('WEBKIT2PNG', 'root')
webkit2png_app  = cfg.get('WEBKIT2PNG', 'app')
# no need to convert to integer: only string allowed in Popen
webkit2png_timeout = cfg.get('WEBKIT2PNG', 'timeout')

# server variable
server_url       = cfg.get('SERVER', 'url')
server_port      = int(cfg.get('SERVER', 'port'))
server_localhost = cfg.get('SERVER', 'localhost')

# cache variable
cache_enable   = cfg.get('CACHE', 'enable')
cache_lifetime = int(cfg.get('CACHE', 'lifetime'))
cache_path     = cfg.get('CACHE', 'path')
cache_tick     = float(cfg.get('CACHE', 'garbadge'))


#
# ------------------------------
#     GLOBAL SCOPE
# ------------------------------
#


# Creating cache folder
if cache_enable == 'true' and os.path.exists(cache_path) == 0:
    os.makedirs(cache_path, 0600)


# Compile the domain check
domainurl = ''
if server_localhost == 'false':
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
    if server_localhost == 'false' and ('http://127' in url or 'https://127' in url):
        return False

    # Test the domain
    return domainurl.match(url)





#
# ------------------------------
#     HANDLER
# ------------------------------
#

@route('/checkhealth')
def haproxy():
    ''' Haproxy checkhealth status check '''
    response.status = 200
    return ''

@route('/')
def screenshot():
    ''' Create a new screenshot '''
    # Initiate an inifinite loop killer
    limit = 0

    # Get parameters
    url = request.GET.get('url', '').strip()
    if not(testurl(url)):
        # TODO: use logging instead
        print 'error'

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
    # Create parameters content for webkit2png
    endpath = os.path.join(webkit2png_root, webkit2png_app)
    param = ['python', endpath, url, '-F', 'javascript', '-t', webkit2png_timeout];

    # We parse request to find other elements
    return extendsParam(param, request)


def extendsParam(param, request):
    ''' Parse the request to find extra parameters to apply to param '''
    for key, value in request.GET.iteritems():
        key = '--' + key

        if key == '--xvfb' or key == '--geometry' or key == '--scale':
            # We have to split dual integer
            separated = re.split('[*|x]', value)
            print separated
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

    if cache_enable == 'true':
        # Debug
        print 'Cache is enable, searching into cache'

        # Computing md5 value of param
        jsonparam = json.dumps(param, sort_keys=True)
        md5param = hashlib.md5(jsonparam).hexdigest()

        # Creating time limit and file path
        file = os.path.join(cache_path, md5param) + '.png'
        old = time.time() - cache_lifetime

        # The file exist and is still valid
        if os.path.exists(file) and os.path.getctime(file) > old:
            # Debug                
            print 'Serving content from cache #%s' % file

            # We can serve that file, it's still good
            content = open(file, 'r')
            return content

        # We need to generate a new file
        else:
            # Debug
            print 'Need to generate a new file'

            # If file exist, we delete
            if os.path.exists(file):
                # Debug
                print 'Remove file (too old): %s' % file
                os.remove(file)

            # We ask system to output into file (if it's not set)
            param.append('--output')
            param.append(file)

            # We can generate a new file, and call this function again
            if limit > 5:
                print 'ERROR: Limit is reached, system gone into infinite loop'
                raise Exception('Limit of calling webkit2png exceed')
            else:
                return generateImageOuput(limit, param, webkit2png)

    else:
        return generateImageOuput(limit, param, None)

def generateImageOuput(limit, param, callback):
    ''' Final image generation: sub process webkit2png and write to output '''
    # Debug
    print 'Generating a new image with parameters: %s' % param

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
#     CACHE GARBADGE COLLECTOR
# ------------------------------
#

# On cache active, we create the garbage
if cache_enable == 'true':
    from threading import Timer
    import glob

    # Initiate cache_current to start garbadge on boot
    cache_current = cache_tick + 1

    def cache_garbadge():
        global cache_current, cache_tick
        if cache_current > cache_tick:
            cache_current = 0
            # Clearing cache
            print '*' * 30
            print '* GARBADGE STARTING'
            print '*' * 30
            # cache_path
            fileList = glob.glob(os.path.join(cache_path, '*.png'))
            old = time.time() - cache_lifetime

            for file in fileList:
                if os.path.exists(file) and os.path.getctime(file) < old:
                    print 'Removing file from cache: %s' % file
                    os.remove(file)

        # Run forever
        # The cache_current allow to setup a short timer
        # this help for shuting down quickly instead of waiting timer tick
        cache_current += 1
        t = Timer(1.0, cache_garbadge)
        t.start()

    # Start first time
    cache_garbadge();







if __name__ == '__main__':
    # Start the web server
    run(host=str(server_url), port=int(server_port))
