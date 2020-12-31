
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from collections import OrderedDict
from dataclasses import dataclass

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GLib

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class Vertex:
    name: str = None
    factory_name: str = None
    elem: Gst.Element = None
    linkable: bool = True
    enabled: bool = True

class StreamGraph():
    def __init__(self, *args, **kwargs):
        logger.info("Initializing StreamGraph...")
        self.vmap = OrderedDict()
        self.parse_launch = False
        self.callbacks = dict()

    def register_callback(self, name, callback):
        self.callbacks[name] = callback

    def add(self, factory_name, name, throw=True):
        if self.parse_launch:
            elem = None
        else:
            elem = Gst.ElementFactory.make(factory_name, name)
            if elem is None:
                msg = "Failed to make element %s of type %s" % (name, factory_name)
                logger.error(msg)
                if throw:
                    raise Exception(msg)
                return
        self.vmap[name] = Vertex(name, factory_name, elem)

    def add_pipeline(self, pipeline: dict):
        for k,v in pipeline.items():
            self.add(v, k)

    def get(self, name):
        return self.vmap[name]

    def keys(self):
        return self.vmap.keys()

    def items(self):
        return self.vmap.items()

    def contains(self, key : str):
        return key in self.vmap

    def contains_plugin(self, keylist : list):
        for k,v in self.vmap.items():
            if v.factory_name in keylist:
                return True
        return False

    def next_key(self, key):
        return list(self.vmap)[list(self.vmap.keys()).index(key) + 1]

    def __getitem__(self, key):
        return self.vmap[key].elem

    def __setitem__(self, key, value):
        self.vmap[key] = value

    def compile(self, pipeline):
        '''
        Compiles the graph to the pipeline: adds elements from the graph and links them
        '''
        # Add elements
        for k,v in self.items():
            if not v.enabled:
                logger.info("Disabled: %s" % k)
                continue
            logger.info("Adding: %s" % k)
            pipeline.add(v.elem)

        # Link elements
        prev = None
        graph_str = ""
        for k,v in self.items():
            if not v.enabled:
                continue
            if prev is not None:
                if prev.linkable is None:
                    logger.info("Not linking plugin '%s'. Do so manually." % prev.name)
                    graph_str += " \n\t%s-> " % u'\u2514'
                elif prev.linkable:
                    prev.elem.link(v.elem)
                    graph_str += " --> "
                    if isinstance(prev.linkable, str):
                        prev.elem.link(self[prev.linkable])
                        graph_str += " \n\t%s-> " % u'\u2514'
                else:
                    logger.info("Plugin '%s' will be linked to '%s' on new pad added." % (prev.name, k))
                    prev.elem.connect("pad-added", self.callbacks["on_pad_added"], v.elem)
                    graph_str += " ~~> "
            prev = v
            graph_str += "%s [%s]" % (k, v.factory_name)
        logger.info(graph_str)

    def configure(self, k, v):
        '''
        Configure plugin k with values from dictionary v
        '''
        if k in list(self.keys()) and isinstance(v, dict):
            config_params = v.keys()
            plugin = self[k]

            # Set linkable property
            if "linkable" in v:
                logger.info("Setting property 'linkable' for plugin '%s' to a value: %s" % (k, v["linkable"]))
                self.get(k).linkable = v["linkable"]

            # Set enabled property
            if "enabled" in v:
                logger.info("Setting property 'enabled' for plugin '%s' to a value: %s" % (k, v["enabled"]))
                self.get(k).enabled = v["enabled"]

            # Connect signals
            if "signals" in v:
                logger.info("signals:")
                for signal, args in v["signals"].items():
                    logger.info("Connecting signal '%s' for plugin '%s' with args: %s" % (signal, k, args))
                    self[k].connect(signal, *args)

            # Add probes
            if "probes" in v:
                logger.info("probes:")
                for pad_name, callback in v["probes"].items():
                    logger.info("Connecting buffer probe for plugin '%s' to the pad: %s" % (k, pad_name))
                    pad = plugin.get_static_pad(pad_name)
                    if not pad:
                        logger.error("Unable to get %s pad of %s\n" % (pad_name, k))
                    else:
                        pad.add_probe(Gst.PadProbeType.BUFFER, self.callbacks["buffer_probe_callback"], callback)

            # Set plug-in properties
            if plugin is not None:
                props = plugin.list_properties()
                for p in props:
                    if p.name == "name":
                        continue
                    if p.name in config_params:
                        logger.info("Setting property '%s' for plugin '%s' to a value: %s" % (p.name, k, v[p.name]))
                        if p.name == "caps" and isinstance(v[p.name], str):
                            caps = Gst.caps_from_string(v[p.name])
                            plugin.set_property(p.name, caps)
                        else:
                            plugin.set_property(p.name, v[p.name])

    def get_gst_launch_str(self, config=dict(), parse_launch=False):
        '''
        Returns gst-launch-1.0 string to use with command line or Gst.parse_launch()
        '''
        gst_launch_str = ""
        first = True
        tee = None
        for k,v in self.items():
            if not v.enabled:
                continue

            # Separator
            sep = " " if first else " ! "
            gst_launch_str += sep
            first = False

            # Next plug-in
            if v.factory_name != "capsfilter":
                gst_launch_str += v.factory_name

            # Plug-in's parameters
            plugin = self[k]
            config_params = config[k] if k in config else {}

            if plugin is None:
                # For dummy plug-ins, we just assume that what's in config is going to the params,
                # as there is no plug-in instance (yet), no cross-check
                for p,q in config_params.items():
                    prefix = " "
                    if p != "caps":
                        prefix += p + "="
                    decorator = "'" if not parse_launch and p == "caps" else ""
                    gst_launch_str += prefix + decorator + str(q) + decorator
            else:
                props = plugin.list_properties()
                for p in props:
                    if p.name == "name":
                        if v.factory_name == "tee":
                            tee = plugin.get_property(p.name)
                            gst_launch_str += " name=" + tee
                        continue
                    if p.name in config_params:
                        prefix = " "
                        if p.name != "caps":
                            prefix += p.name + "="
                        decorator = "'" if not parse_launch and p.name == "caps" else ""
                        gst_launch_str += prefix + decorator + str(config_params[p.name]) + decorator

            if v.linkable is None and tee is not None:
                gst_launch_str += " %s." % tee

        return gst_launch_str.strip()


