# Copyright (c) 2015 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import absolute_import

import random

import tornado.gen

from tchannel.tornado.stream import InMemStream
from tchannel.tornado.util import print_arg


@tornado.gen.coroutine
def say_hi(request, response, proxy):
    yield response.write_body("hi")


@tornado.gen.coroutine
def say_ok(request, response, proxy):
    yield print_arg(request, 1)
    yield print_arg(request, 2)

    response.set_body_s(InMemStream("world"))


@tornado.gen.coroutine
def echo(request, response, proxy):
    # stream args right back to request side
    response.set_header_s(request.get_header_s())
    response.set_body_s(request.get_body_s())


@tornado.gen.coroutine
def slow(request, response, proxy):
    yield tornado.gen.sleep(random.random())
    yield response.write_body("done")
    response.flush()


def register_example_endpoints(tchannel):
    tchannel.register(endpoint="hi", scheme="raw", handler=say_hi)
    tchannel.register(endpoint="ok", scheme="raw", handler=say_ok)
    tchannel.register(endpoint="echo", scheme="raw", handler=echo)
    tchannel.register(endpoint="slow", scheme="raw", handler=slow)

    @tchannel.register("bye", scheme="raw")
    def say_bye(request, response, proxy):
        print (yield request.get_header())
        print (yield request.get_body())

        response.write_body("world")
