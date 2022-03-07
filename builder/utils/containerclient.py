#!/usr/bin/python3

import json

from utils.common import log, runCMD, runCMDRetry

from utils.artifactory import ArtifactoryClient

class ContainerClient:

    def __init__(self, config):
        self.reg_url = config["armdocker_config"]["url"]
        self.path_reg = config["armdocker_config"]["project"]
        self.art_cache_path = config["cache_path_art"]
        self.policy = ""
        if config["insecure_policy"]:
            self.policy = "--insecure-policy"
        self.updateLocalImages()
        self.artClient = ArtifactoryClient(config["artifactory_config"])

    def updateLocalImages(self):
        '''
        Load image infromation from local docker repository
        '''
        cmd = ["docker", "images", "--format", "'{{json . }}'"]
        output = runCMD(cmd, output=False)
        if output.returncode:
            raise Exception("Can not check image locally: error code: {}".format(output.returncode))

        data = list(filter(None,output.stdout.split('\n')))
        self.local_json = json.loads('[{}]'.format(','.join(data)))

    def imageFoundLocally(self, image):
        '''
        Check if matching container is found from local registry
        '''
        image_name = "{}:{}".format(image["name"],image["tag"])
        for item in self.local_json:
            if image_name == "{}:{}".format(item["Repository"], item["Tag"]):
                return True
        return False

    def copyImageToLocalDaemon(self, image):
        '''
        If image is external download it from its source.
        Othervice assume it is build image and it can be found from
        armdocker
        '''
        if "external_source" in image:
            source = image["external_source"]
        else:
            source = self.__genArmImageUrl(image)

        cmd = ["skopeo", "--insecure-policy", "copy",
               "docker://{}".format(source),
               "docker-daemon:{}:{}".format(image["name"],image["tag"])]
        runCMDRetry(cmd)

    def archiveImage(self, image, target_filename):
        container_tag = "{}:{}".format(image["name"],image["tag"])
        cmd = ["skopeo", "copy",
               "docker-daemon:{}".format(container_tag),
               "docker-archive:{}".format(target_filename)]
        runCMD(cmd)

    def loadImageTarToLocalDaemon(self, tar_file, name, tag):
        cmd = ["skopeo", "--insecure-policy", "copy",
               "docker-archive:{}".format(tar_file),
               "docker-daemon:{}:{}".format(name,tag)]
        runCMD(cmd)

    def imageExists(self, image):
        '''
        Check if image is found from Armdocker
        '''
        image_url = "{}/{}/{}:{}".format(self.reg_url, self.path_reg,
                                         image["name"], image["tag"])
        cmd = ["skopeo", self.policy, "inspect",
               "docker://{}".format(image_url)]
        output = runCMD(cmd,nofail=True)
        if output.returncode == 0:
            return True
        else:
            return False

    def imageIsExternal(self, image):
        return "external_source" in image and len(image["external_source"]) > 0

    def push(self, image):
        '''
        Copy container from local docker daemon to remote registry (Armdocker)
        '''
        image_tag = "{}:{}".format(image["name"], image["tag"])
        image_url = self.__genArmImageUrl(image)
        cmd = ["skopeo", self.policy, "copy",
               "docker-daemon:{}".format(image_tag),
               "docker://{}".format(image_url)]
        log("Pushing Container {}".format(image_tag))
        output = runCMD(cmd)
        if output.returncode != 0:
            raise Exception("Failed to push image: {}, stderr: {}".format(
                            image_url, output.stderr))
        else:
            log("Container {} stored at {}".format(image_tag, image_url))

    def __genArmImageUrl(self, image):
        image_tag = "{}:{}".format(image["name"], image["tag"])
        return "{}/{}/{}".format(self.reg_url, self.path_reg, image_tag)
