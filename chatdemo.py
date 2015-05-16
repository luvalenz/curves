#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Simplified chat demo for websockets.

Authentication, error handling, etc are left as an exercise for the reader :)
"""

import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import uuid
from curvesets import MachoCurvesSet
import motor

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/chatsocket", ChatSocketHandler),
            (r"/lightcurve/", CurveHandler),
        ]
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", messages=ChatSocketHandler.cache)

class CurveHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("lightcurve.html", curve_data=1)

class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()
    cache = []
    cache_size = 200
    curves = MachoCurvesSet("/home/lucas/Desktop/lightcurves/periodic",20,3)
    curves.load_and_index_curves()
    client = motor.MotorClient()
    db = client.curves
    responses = db.c1.find_one({"name":"responses"})

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    def open(self):
        ChatSocketHandler.waiters.add(self)

    def on_close(self):
        ChatSocketHandler.waiters.remove(self)

    @classmethod
    def update_cache(cls, chat):
        cls.cache.append(chat)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[-cls.cache_size:]

    @classmethod
    def send_updates(cls, chat):
        logging.info("sending message %s to %d waiters", chat, len(cls.waiters))
        for waiter in cls.waiters:
            try:
                waiter.write_message(chat)
            except:
                logging.error("Error sending message", exc_info=True)

    def check_response(self, chat):
        message_body = chat["body"]
        responses = ChatSocketHandler.responses.result()["values"]
        if message_body in responses:
            response_body = responses[message_body]
            self.print_message(response_body)

    def print_message(self, text):
        chat = {
            "id": str(uuid.uuid4()),
            "body": text,
            }
        chat["html"] = tornado.escape.to_basestring(
            self.render_string("message.html", message=chat))
        ChatSocketHandler.update_cache(chat)
        ChatSocketHandler.send_updates(chat)
        
    def print_plot(self):
        pass

    def start_batch(self):
        curve = ChatSocketHandler.curves.get_first(0)
        self.print_message(MachoCurvesSet.curve_tuple_to_json(curve))
        for i in range(20):
            curve = str(ChatSocketHandler.curves.get_next())
            self.print_message(MachoCurvesSet.curve_tuple_to_json(curve))
            
    def start_plot_batch(self):
        curve = ChatSocketHandler.curves.get_first(0)
        self.print_plot(MachoCurvesSet.curve_tuple_to_json(curve))
        # for i in range(20):
        #     curve = str(ChatSocketHandler.curves.get_next())
        #     self.print_message(MachoCurvesSet.curve_tuple_to_json(curve))

    def check_start(self, chat):
        message_body = chat["body"]
        if message_body == "start":
            self.start_batch()
            
    def check_start_plot(self, chat):
        message_body = chat["body"]
        if message_body == "start_plot":
            self.start_plot_batch()

    def on_message(self, message):
        logging.info("got message %r", message)
        parsed = tornado.escape.json_decode(message)
        chat = {
            "id": str(uuid.uuid4()),
            "body": parsed["body"],
            }
        chat["html"] = tornado.escape.to_basestring(
            self.render_string("message.html", message=chat))

        ChatSocketHandler.update_cache(chat)
        ChatSocketHandler.send_updates(chat)
        self.check_response(chat)
        self.check_start(chat)
        self.check_start_plot(chat)


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
