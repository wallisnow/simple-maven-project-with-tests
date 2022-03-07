#!/usr/bin/python3

from utils.common import log
from utils.makeclient import MakeClient

################################################################################
# Helmbuilder
################################################################################

class Helmbuilder:

    def __init__(self, config):
        self.makeClient = MakeClient(config["make_client_config"])

    def build(self):
        self.__helmMake("build")

    def publish(self):
        self.__helmMake("install")

    def clean(self):
        self.__helmMake("clean")

    def getImages(self, helm_charts):
        images = []
        for chart in helm_charts:
            if "images" in chart:
                for ns in chart["images"]:
                    for image in chart["images"][ns]:
                        chart["images"][ns][image]["key"] = image
                        chart["images"][ns][image]["namespace"] = ns
                        images.append(chart["images"][ns][image])

        return images, self.__makeHelmComponent(images)

    # Private functions
    def __helmMake(self, cmd):
        self.makeClient.make("helm-charts", cmd=cmd)

    def __makeHelmComponent(self, images):
        component = {"name": "helm_images","artifacts":[],"build_source":"",
                    "dependency":[],"version":1,"images":[], "use_cache":False}
        for image in images:
            component["images"].append("{}.{}".format(image["namespace"],
                                                      image["key"]))
        return component
