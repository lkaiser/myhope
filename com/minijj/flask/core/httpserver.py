#!/usr/bin/python
# coding=utf-8
import logging.handlers
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

import time

starttime = time.time()
logger = logging.getLogger('root')  # 获取名为tst的logger
class TradeHTTPServer(HTTPServer):
    def server_bind(self):
        HTTPServer.server_bind(self)
        self.trade = None

    def setTrade(self,trade):
        self.trade = trade


class MyHandler(BaseHTTPRequestHandler):
    #    '''Definition of the request handler.'''

    def _writeheaders(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _getdoc(self, filename):
        '''Handle a request for a document,returning one of two different page as as appropriate.'''
        if filename == '/':
            return '''
                <html>
                    <head>
                        <title>Samlle Page</title>
                        <script type="text/javascript">
                            //alert("hello");
                        </script>
                    </head>

                    <body>
                        This is a sample page.You can also look at the
                        <a href="stats.html">Server statistics</a>.
                    </body>
                </html>
                '''
        elif filename == '/stats.html':
            return ''' 
                <html>
                    <head>
                        <title>Statistics</title>
                    </head>

                    <body>
                        this server has been running for %d seconds.
                    </body>
                </html>
                ''' % int(time.time() - starttime)
        else:
            return None

    def do_HEAD(self):
        '''Handle a request for headers only'''
        doc = self._getdoc(self.path)
        self._writeheaders()

    def execcmd(self,path):
        logger.info("################## 查询 path="+path)
        if "/hserver/" == path:
            logger.info("################## I'm switing Hserver" + path)
            self.server.trade.switchHserver()
        if "/lserver/" == path:
            logger.info("################## I'm switing Hserver" + path)
            self.server.trade.switchLserver()
        if "/hopen/" == path:
            self.server.trade.switchHOpen()
        if "/hliquid/" == path:
            self.server.trade.switchHLiquid()
        if "/lopen/" == path:
            self.server.trade.switchLOpen()
        if "/lliquid/" == path:
            self.server.trade.switchLLiquid()
        if "/hsetting/" == path:
            self.server.trade.hsetting()
        if "/lsetting/" == path:
            self.server.trade.lsetting()


    def do_GET(self):
        '''Handle a request for headers and body'''
        print "Get path is:%s" % self.path
        self._writeheaders()
        self.execcmd(self.path)
        # if doc is None:
        #     self.wfile.write('''
        #                         <html>
        #                             <head>
        #                                 <title>Not Found</title>
        #                                 <body>
        #                                     The requested document '%s' was not found.
        #                                 </body>
        #                             </head>
        #                         </html>
        #                         ''' % (self.path))
        #
        # else:
        #     self.wfile.write(doc)


# Create the pbject and server requests

