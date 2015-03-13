#!/usr/bin/env python
from __future__ import absolute_import
import sys

import tornado.ioloop
import tornado.tcpserver

from options import get_args
from tchannel.messages import CallResponseMessage
from tchannel.tornado.connection import TornadoConnection


class MyServer(tornado.tcpserver.TCPServer):
    def handle_stream(self, stream, address):
        tchannel_connection = TornadoConnection(
            connection=stream
        )

        print("Received request from %s:%d" % address)

        print("Waiting for TChannel handshake...")
        tchannel_connection.await_handshake(headers={
            'host_port': '%s:%s' % address,
            'process_name': sys.argv[0],
        }, callback=self.handshake_complete)

    def handshake_complete(self, connection):
        print(
            "Successfully completed handshake with %s" %
            connection.remote_process_name
        )
        connection.handle_calls(self.handle_call)

    def handle_call(self, context, connection):
        """Handle a TChannel CALL_REQ message."""
        if not context:
            print("All done with connection")
            return

        print("Received message: %s" % context.message)

        if context.message.arg_1:
            response = CallResponseMessage()
            response.flags = 0
            response.code = 200
            response.span_id = 0
            response.parent_id = 0
            response.trace_id = 0
            response.traceflags = 0
            response.headers = {'currently': 'broken'}
            response.checksum_type = 0
            response.checksum = 0
            response.arg_1 = context.message.arg_1
            response.arg_2 = 'hello world'
            response.arg_3 = context.message.arg_3

            connection.frame_and_write(response)


        connection.handle_calls(self.handle_call)


if __name__ == '__main__':
    args = get_args()
    server = MyServer()
    server.listen(args.port)
    print("Listening on port %d..." % args.port)
    tornado.ioloop.IOLoop.instance().start()
