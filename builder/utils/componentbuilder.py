#!/usr/bin/python3

import shutil, json, hashlib, glob

from pathlib import Path

from utils.common import log, runCMD, getFileDirectory, getFilename
from utils.containerclient import ContainerClient
from utils.artifactory import ArtifactoryClient
from utils.makeclient import MakeClient

class ComponentBuilder:

    def __init__(self, config):
        self.root = config["root"]
        self.version = config["version"]
        self.default_registry = config["default_registry"]
        self.target_path = config["target_path"]
        self.component_path = config["component_path"]
        self.build_path = config["build_path"]
        self.containerclient= ContainerClient(config["container_client_config"])
        self.artifactoryclient = ArtifactoryClient(config["artifactory_config"])
        self.makeClient = MakeClient(config["make_client_config"])
        self.components = []
        self.build_components = []
        self.images = []
        self.artifacts = []
        self.helm_charts = []

    def set(self, components, images, artifacts, helm_charts, cleanonly=False):
        '''
        Sort components
            1) build first components
            2) non dependend components
            3) components with dependencies in correct order

        Update image tags to have hash if they are locally build
        '''
        self.components = self.__sortComponents(components)
        self.images = images
        self.artifacts = artifacts
        self.helm_charts = helm_charts

        if not cleanonly:
            for component in self.components:
                hash = self.getComponentHash(component)
                component["hash"] = hash
                for image_name in component["images"]:
                    image = self.__mapImage(image_name)
                    if not image["external"]:
                        image["tag"] = "{}-{}".format(image["tag"], hash[:10])

                for artifact_name in component["artifacts"]:
                    artifact = self.__mapArtifact(artifact_name)
                    artifact["hash"] = hash

    def build(self, force=False):
        '''
        force: will build everything and it ignores cache and
               any data from armdocker or from artifactory

        Check if component images are found from armdocker and if artifacts
        are found from artifactory.

        If not then check cache if we have build this already.
        Then just fetch it.
        Else execute "make"

        Last copy component to target directory
        '''
        path= "{}/{}/container-list.json".format(self.root, self.component_path)
        self.__createContainerList(path)

        self.__initTarget()

        index_file= open("{}/docker-images-index".format(self.target_path), "w")

        self.containerclient.updateLocalImages()
        for component in self.components:
            log("Building component {}".format(component["name"]))
            if self.__componentNeedsBuilding(component) or force:
                if not force and self.__componentFoundFromCache(component):
                    self.__fetchFromCache(component, index_file)
                else:
                    if len(component["build_source"]) > 0:
                        self.__makeMetadata(component)
                        path = "{}/{}".format(self.component_path,
                                component["build_source"])
                        self.makeClient.make(path)
                        self.build_components.append(component)
                        self.__moveComponentToTarget(component, index_file)
                    elif self.__imagesBuildAndNoArtifacts(component):
                        self.build_components.append(component)
                        self.__moveComponentToTarget(component, index_file)
                    else:
                        self.build_components.append(component)
                        self.__moveComponentToTarget(component, index_file)
            else:
                self.__moveComponentToTarget(component, index_file)

        index_file.close()

    def clean(self):
        '''
        Clean all components. I.e run "make clean"
        Do not fail even command would fail
        '''
        for component in self.components:
            path= "{}/{}".format(self.component_path, component["build_source"])
            self.makeClient.make(path,cmd="clean", nofail=True)

            path = "{}/{}/meta-data.json".format(self.root, path)
            try:
                Path(path).unlink()
            except:
                pass

        if Path(self.target_path).exists():
            shutil.rmtree(self.target_path)

        p = Path("{}/{}/container-list.json".format(self.root,
                    self.component_path))
        if p.exists():
            p.unlink()

    def publish(self, force=False):
        '''
        Update Cache
        Publish Images and Artifacts of build components
        '''
        for component in self.build_components:
            log("Publishing component {}".format(component["name"]))
            for image_tag in component["images"]:
                image = self.__mapImage(image_tag)
                log("Publishing image {}".format(image["name"]))
                if force or not self.containerclient.imageExists(image):
                    log("Push container {}:{}".format(image["name"],
                        image["tag"]))
                    self.containerclient.push(image)
                else:
                    raise Exception("image {}:{} exists! Can not push!".format(
                                    image["name"], image["tag"]))

            for artifact_name in component["artifacts"]:
                artifact = self.__mapArtifact(artifact_name)
                path = self.__getFullArtifactTargetPath(artifact, component)
                target = self.__getArtifactArtifactoryPath(artifact)
                log("Publishing Artifact {}".format(artifact["name"]))
                if force or not self.artifactoryclient.findOneFile(path):
                    if Path(path).is_file():
                        log("Put Artifact {} file".format(artifact["name"]))
                        self.artifactoryclient.putFile(path, target)
                    else:
                        log("Put Artifact {} directory".format(
                            artifact["name"]))
                        self.artifactoryclient.putDirectory(path, target)
                else:
                    raise Exception("Artifact {} exists! Can not push!".format(
                                    artifact["name"]))

            self.__pushToCache(component, force)

    def getComponentHash(self, component):
        '''
        Hash includes:
        1) build_source directory hash
        2) component info
        3) list of image infos
        4) list of artifact infos
        5) version
        '''
        dir_hash = self.__getDirHash(component)
        component_str = json.dumps(component)
        image_str = ""
        for image_name in component["images"]:
            image = self.__mapImage(image_name)
            image_str += json.dumps(image)

        artifact_str = ""
        for artifact_name in component["artifacts"]:
            artifact = self.__mapArtifact(artifact_name)
            artifact_str += json.dumps(artifact)

        hash_str = "{} {} {} {} {}".format(component_str, image_str,
                                        artifact_str, dir_hash, self.version)
        return hashlib.sha256(hash_str.encode('utf-8')).hexdigest()

    ############################################################################
    # Cache functions
    ############################################################################

    def __componentFoundFromCache(self, component):
        '''
        Return false if component do not use cache
        Calculate hash for component
        Check if mathing build is found from cache
        '''
        if not ("use_cache" in component and component["use_cache"]):
            return False
        path = self.__getComponentCachePath(component)
        return self.artifactoryclient.findOneFile(path)

    def __fetchFromCache(self, component, index_file):
        '''
        Download component from cache
        Retag image during loading
        Copy Artifacts to their build locations
        '''
        path = self.__getComponentCachePath(component)
        output_path = "{}/{}".format(self.target_path,
                        self.__getComponentTargetPath(component))
        self.artifactoryclient.getTar(path, output_path)

        images_path = "{}/images/*.tar.gz".format(output_path)

        for image_tar in glob.glob(images_path):
            log("loading {}".format(image_tar))
            full_tag = image_tar.split('/')[-1][:-7]
            parts = full_tag.split('_')
            self.containerclient.loadImageTarToLocalDaemon(image_tar, parts[0],
                                                            parts[1])

            container_tag = "{}:{}".format(parts[0], parts[1])
            container_tar = "{}/{}/images/{}_{}.tar.gz".format(
                            self.component_path, component["name"], parts[0],
                            parts[1])
            index_file.write("{} {}\n".format(container_tag, container_tar))

    def __pushToCache(self, component, force=False):
        '''
        Creates temporarry tar file to base level of components directory.
        This is then uploaded to artifactory and temporarry archive is deleted.

        This will never upload archive if it is found from cache. As if it is
        found there then this archive is actually same as in build stage
        components are fetched from cache or from permanent location and if
        directory hash is same the it should match.
        '''
        if len(component["build_source"]) < 1:
            log("Skipping! {} has empty build_source.".format(
                component["name"]))
            return

        if "use_cache" in component and not component["use_cache"]:
            log("Skipping! {} cache dissabled for this component.".format(
                component["name"]))
            return

        if not force:
            if self.__componentFoundFromCache(component):
                log("Component already in cache! Skipping!")
                return

        source_path = self.__getFullComponentTargetPath(component)
        path = self.__getComponentCachePath(component)
        log("Put Component {} to cache!".format(component["name"]))
        self.artifactoryclient.putDirectory(source_path, path)

    ############################################################################
    # Move functions
    ############################################################################

    def __moveComponentToTarget(self, component, index_file):
        '''
        Moves build or fetched containers and artifacts to target direcotry
        1) move docker images
        2) move artifacts
        '''
        if "exclude_from_tar" in component and component["exclude_from_tar"]:
            # Add exclude tag to component
            path_base = self.__getFullComponentTargetPath(component)
            path = "{}/exclude_from_tar".format(path_base)
            try:
                Path(getFileDirectory(path)).mkdir(parents=True)
            except:
                pass
            Path(path).touch()

        self.containerclient.updateLocalImages()
        for image_tag in component["images"]:
            image = self.__mapImage(image_tag)
            if not self.containerclient.imageFoundLocally(image):
                self.containerclient.copyImageToLocalDaemon(image)
            self.__moveImageToTarget(image, component, index_file)

        for artifact_name in component["artifacts"]:
            artifact = self.__mapArtifact(artifact_name)
            if not self.__moveArtifactsFromBuildToTarget(artifact, component):
                self.__moveArtifactFromExternalToTarget(artifact, component)

    def __moveArtifactsFromBuildToTarget(self, artifact, component):
        '''
        Moves build artifact from build source to target directory.
        Can copy files or directories.
        '''
        paths = self.__getArtifactBuildPaths(artifact, component)
        for _from in paths:
            if not Path(_from).exists():
                return False

            _to = self.__getFullArtifactTargetPath(artifact, component)
            try:
                Path(getFileDirectory(_to)).mkdir(parents=True)
            except:
                pass

            if Path(_from).is_dir():
                shutil.copytree(_from, _to)
            else:
                shutil.copy(_from, _to)
        return True

    def __moveArtifactFromExternalToTarget(self, artifact, component):
        """
        Download artifact from artifactory and untar it to target direcotry.

        So end result will be same as after builder
        """
        path = self.__getArtifactArtifactoryPath(artifact)
        target_path = self.__getFullArtifactTargetPath(artifact, component)
        self.artifactoryclient.getTar(path, target_path)

    def __moveImageToTarget(self, image, component, index_file):
        '''
        Append index_file if component do not have exclude_from_tar flag
        Archive image from local docker to target path
        '''
        target_file = self.__getFullImageTargetPath(image, component)

        if not ("exclude_from_tar" in component and
                component["exclude_from_tar"]):
            filename = self.__getImageTargetPath(image, component)
            index_file.write("{} {}\n".format(getFilename(filename),filename))

        try:
            Path(getFileDirectory(target_file)).mkdir(parents=True)
        except:
            pass

        self.containerclient.archiveImage(image, target_file)

    ############################################################################
    # Utils
    ############################################################################

    def __makeMetadata(self,component):
        path = "{}/{}/{}/meta-data.json".format(self.root, self.component_path,
                                            component["build_source"])
        with open(path, "w") as f:
            if "meta_data_json" in component:
                f.write(json.dumps(component["meta_data_json"]))
            else:
                f.write("")

    def __initTarget(self):
        '''
        Create new directory and cleaned container-list.json in it.
        '''
        Path(self.target_path).mkdir(parents=True)

        path = "{}/container-list.json".format(self.target_path)
        self.__createContainerList(path, for_tar=True)

    def __getDirHash(self, component):
        '''
        Calculate sha256 hash for directory from where component is build.
        '''
        if len(component["build_source"]) < 1:
            return None
        hashes=[]
        path = "{}/{}/{}/**".format(self.root, self.component_path,
                                    component["build_source"])
        for filename in sorted(glob.glob(path, recursive=True)):
            hash_sha256 = hashlib.sha256()
            if Path(filename).is_file():
                with open(filename, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_sha256.update(chunk)
                hashes.append(hash_sha256.hexdigest())
        return hashlib.sha256(" ".join(hashes).encode('utf-8')).hexdigest()

    def __getGitHash(self, component):
        '''
        Get git hash of directory where component is stored to know if we need
        to build it or if we can just fetch its components from external source.
        '''
        tmp_path = "{}/{}/{}".format(self.root, self.component_path,
                                     component["build_source"])
        cmd = ["git", "log", "--pretty=tformat:\"%h\"", "-n", "1", tmp_path]
        output = runCMD(cmd)
        return output.stdout.strip()

    def __sortComponents(self, components):
        '''
        First set build_first components to be build first
        Then get all non dependend components and last sort components with
        dependencies so that they can be build.
        max_loops is only for exiting when we hit infinite loop
        '''
        return_components = list(filter(lambda x: "build_first" in x and
                                            x["build_first"], components))
        return_components.extend(list(filter(lambda x: len(x["dependency"]) < 1
                                and not ("build_first" in x and
                                         x["build_first"]), components)))

        dependend = list(filter(lambda x: len(x["dependency"]) > 0 and
                                not ("build_first" in x and x["build_first"]),
                                     components))

        def _inList(item_name, item_list):
            for item in item_list:
                if item["key"] == item_name:
                    return True
            return False

        counter = 0
        max_loops = len(dependend)*10
        while True:
            if len(dependend) < 1:
                return return_components
            comp = dependend.pop(0)
            if all(_inList(i, return_components) for i in comp["dependency"]):
                return_components.append(comp)
            else:
                dependend.append(comp)
            counter += 1
            if counter > max_loops:
                raise Exception("Too many loops: {}".format(counter))

    def __createContainerList(self, target, for_tar=False):
        '''
        Generate container-list.json for building or for tar.

        for_tar flag will remove all build spesific infromation and also
        it do not setup containers that should not be uploaded to tar archive.
        '''
        container_dict = {}
        container_dict["erikube_version"] = self.version
        container_dict["default_registry"] = self.default_registry
        container_dict["helm_charts"] = {}
        for helm_chart in self.helm_charts:
            helm_chart_tmp = {"name": helm_chart["name"]}
            if "tarball" in helm_chart:
                helm_chart_tmp["tarball"] = helm_chart["tarball"]
            if "version" in helm_chart:
                helm_chart_tmp["version"] = helm_chart["version"]
            container_dict["helm_charts"][helm_chart["key"]] = helm_chart_tmp

        container_dict["containers"] = {}

        def appendImage(_dict, _img):
            if not _img["namespace"] in _dict["containers"]:
                _dict["containers"][_img["namespace"]] = {}
            tag = "{}:{}".format(_img["name"], _img["tag"])
            container_dict["containers"][_img["namespace"]][_img["key"]] = tag

        for component in self.components:
            for image_name in component["images"]:
                image = self.__mapImage(image_name)
                tmp_image = {}
                if for_tar:
                    if not ("include_in_tar" in image and
                            not image["include_in_tar"]):
                        appendImage(container_dict, image)
                else:
                    appendImage(container_dict, image)

        with open(target, 'w') as output:
            output.write(json.dumps(container_dict, indent=4))

    def __mapArtifact(self, artifact_name):
        for art in self.artifacts:
            if art["key"] == artifact_name:
                return art
        raise Exception("Could not find artifact: {} from {}".format(
                        artifact_name, self.artifacts))

    def __mapImage(self, target):
        items = target.split('.')
        if len(items) != 2:
            msg = "Image tag isn't in correct form: <namespace>.<name> ({})"
            raise Exception(msg.format(target))
        ns = items[0]
        key = items[1]

        for image in self.images:
            if image["key"] == key and image["namespace"] == ns:
                return image

        raise Exception("Wasn't able to find image for {}.{} from {}".format(
                        ns,key, self.images))

    def __imagesBuildAndNoArtifacts(self, component):
        if len(component["artifacts"]) > 0:
            return False
        for image_tag in component["images"]:
            image = self.__mapImage(image_tag)
            if not self.containerclient.imageFoundLocally(image):
                return False
        return True

    def __componentNeedsBuilding(self, component):
        '''
        Check if all containers are found from armdocker.
        Check if all artifacts are found from artifactory.

        Note: During patchset changes this will return false as
              git hash changes. However the cache will take care of
              that situation.
        '''
        for image_tag in component["images"]:
            image = self.__mapImage(image_tag)
            log("Check component {}, image {}".format(component["name"],
                                                      image["name"]))
            if not self.containerclient.imageExists(image):
                return True
        for artifact_name in component["artifacts"]:
            artifact = self.__mapArtifact(artifact_name)
            log("Check component {}, artifact {}".format(component["name"],
                                                         artifact["name"]))
            path = self.__getArtifactArtifactoryPath(artifact)
            if not self.artifactoryclient.findOneFile(path):
                return True
        return False

    ############################################################################
    # Path generation
    ############################################################################
    def __getComponentCachePath(self,component):
        '''
        Generates path for cached component in artifactory

        <build_path>/cache/<name>/<dir_hash>/<name>-<dir_hash>.tgz

        example:
        erikube/build/build-v5/cache/kubernetes/XXX/kubernetes-XXX.tgz
        '''
        return "{0}/cache/{1}/{2}/{1}-{2}.tgz".format(self.build_path,
                component["name"], component["hash"])

    def __getArtifactArtifactoryPath(self, artifact):
        '''
        Generates path for artifact in artifactory.

        <path_to_artifact>/<version>/artifacts/<artifact_name>/
                    <artifact_name>-<component_directory_hash>.tgz
        example:
        erikube/build/build-v5/<version>/artifacts/kubelet/
                    kubelet-XXXXXXXX.tar.gz
        '''
        return "{0}/{1}/artifacts/{2}/{2}-{3}.tgz".format(self.build_path,
                self.version, artifact["name"], artifact["hash"])

    def __getFullComponentTargetPath(self, component):
        target = self.__getComponentTargetPath(component)
        return "{}/{}".format(self.target_path, target)

    def __getFullArtifactTargetPath(self, artifact, component):
        target = self.__getArtifactTargetPath(artifact, component)
        return "{}/{}".format(self.target_path, target)

    def __getFullImageTargetPath(self, image, component):
        target = self.__getImageTargetPath(image, component)
        return "{}/{}".format(self.target_path, target)

    def __getArtifactTargetPath(self, artifact, component):
        '''
        Returns directory path where artifact should be stored.
        The directory that will generate tar file.
        '''
        path_base = self.__getComponentTargetPath(component)
        return "{}/artifacts/{}".format(path_base, artifact["name"])

    def __getImageTargetPath(self, image, component):
        path_base = self.__getComponentTargetPath(component)
        container_tar = "{}_{}.tar.gz".format(image["name"],image["tag"])
        return "{}/images/{}".format(path_base, container_tar)

    def __getComponentTargetPath(self, component):
        return "components/{}".format(component["name"])

    def __getArtifactBuildPaths(self, artifact, component):
        path = "{}/{}/{}".format(self.root, self.component_path,
                                        component["build_source"])
        return_paths = []
        for artifact_path in artifact["publish_artifacts"]:
            return_paths.append("{}/{}".format(path, artifact_path))
        return return_paths
