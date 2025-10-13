__all__ = ["config", "load_config", "save_config", "clear_config", "download"]

import os
import json
import requests
import re
import zipfile

moodle_api_url = "https://moodle.rwth-aachen.de/webservice/rest/server.php"

config = dict()
course_id = None
moodle_token = None
config_path = None
download_config = None
download_insight_directory = None

download_core_course_get_contents_response = None
download_mod_assign_get_assignments_response = None
download_mod_assign_get_submission_status_responses = None
download_course_files = None
download_assignment_names = None


class Progress:
    def __init__(self):
        self.progress = 0
        self.maximum = 1

    def set_maximum(self, num):
        self.maximum = max(0, num)

    def set_progress(self, num):
        self.progress = max(0, min(num, self.maximum))
        self.percentage = self.progress/self.maximum
        self.duopercentiles = int(round(50*self.percentage))

    def print(self, info=None, first_print=False):
        printee = "\r"

        if first_print:
            self.info_length = 0
            printee = ""

        if info is not None:
            self.info_length = max(self.info_length, len(info))

        printee += f"[{"=" * self.duopercentiles}{" " * (50-self.duopercentiles)}] {self.percentage:7.2%}"

        if info is not None:
            printee += f" {{: <{self.info_length}}}".format(info)
        else:
            printee += " " * (self.info_length + 1)

        print(printee, end="")


progress = Progress()


class AdvancedRecursiveSearch:
    def __init__(self, match_condition, append_as=None, kill_branch=False, kill_tree=False):
        self.match_condition = match_condition
        self.append_as = append_as
        self.kill_branch = kill_branch
        self.kill_tree = kill_tree
        self.found_match = False

        if append_as is None:
            self.append_as = lambda match, path, **kwargs: match

    def search_through(self, nested, path=[], **kwargs):
        if len(path) == 0:
            self.found_match = False

        if self.kill_tree and self.found_match:
            return []

        search_results = []

        if self.match_condition(nested, path, **kwargs):
            search_results += [self.append_as(nested, path, **kwargs)]
            self.found_match = True
            if self.kill_branch or (self.kill_tree and self.found_match):
                return search_results

        if isinstance(nested, list) or isinstance(nested, tuple):
            for step in range(len(nested)):
                search_results += self.search_through(nested[step], path + [step], **kwargs)

        if isinstance(nested, dict):
            for step in nested:
                search_results += self.search_through(nested[step], path + [step], **kwargs)

        return search_results


def download_assignment_ids_match_condition(obj, path, **kwargs):
    if not isinstance(obj, dict):
        return False

    if "modname" not in obj:
        return False

    if obj["modname"] != "assign":
        return False

    return True


def download_assignment_ids_append_as(obj, path, **kwargs):
    return obj["instance"]


download_assignment_ids_ars = AdvancedRecursiveSearch(download_assignment_ids_match_condition, download_assignment_ids_append_as)


def download_files_match_condition(obj, path, **kwargs):
    if not isinstance(obj, dict):
        return False

    if "filename" not in obj:
        return False

    if "fileurl" not in obj:
        return False

    if "mimetype" not in obj:
        return False

    return True


def download_files_append_as(obj, path, **kwargs):
    meta = sub_dict(obj, ["filename", "fileurl", "mimetype"])

    extension = meta["filename"][meta["filename"].rfind("."):]
    if extension[0] != ".":
        extension = ""
    meta["extension"] = extension

    # meta["access-path-array"] = path
    access_path_string = "\\".join([str(p) for p in path])
    meta["access-path-string"] = access_path_string

    origin = kwargs["origin"]

    if origin == "content":
        name_path = []
        for i in range(len(path)):
            nested = get_value_of_nested_at(download_core_course_get_contents_response, path[:i+1])
            if "name" in nested:
                name_path += [nested["name"]]
            else:
                name_path += [str(path[i])]

    if origin == "assignment":
        if "submission" in path:
            origin = "submission"

        if "feedback" in path:
            origin = "feedback"

        assignment = path[0]
        name_path = [assignment, origin, download_assignment_names[assignment]]

    meta["origin"] = origin

    # meta["name-path-array"] = name_path
    name_path_string = "\\".join([str(p) for p in name_path])
    meta["name-path-string"] = name_path_string

    return meta


download_files_ars = AdvancedRecursiveSearch(download_files_match_condition, download_files_append_as)


def download_assignment_names_match_condition(obj, path, **kwargs):
    if not isinstance(obj, dict):
        return False

    if (len(path) > 1) and (path[-2] != "assignments"):
        return False

    if "id" not in obj:
        return False

    if obj["id"] != kwargs["assignment_id"]:
        return False

    return True


def download_assignment_names_append_as(obj, path, **kwargs):
    if "name" in obj:
        return obj["name"]

    return path[-1]


download_assignment_names_ars = AdvancedRecursiveSearch(download_assignment_names_match_condition, download_assignment_names_append_as, kill_tree=True)


def merge_dictionaries(*dictionaries):
    resdict = dict()
    for dictionary in dictionaries:
        for key, val in dictionary.items():
            resdict[key] = val

    return resdict


def sub_dict(dictionary, keys):
    return {key: dictionary[key] for key in keys}


def check_directory_validity(path, create=False, raise_exceptions=True):
    if not isinstance(path, str):
        if not raise_exceptions:
            return False
        raise TypeError(f"Path must be of type string, got type {type(path)}.")

    if not os.path.isdir(path):
        if not create:
            if not raise_exceptions:
                return False
            raise FileNotFoundError(f"Couldn't find directory {path}.")

        os.makedirs(path, exist_ok=True)

    return True


def check_file_validity(path, suffix, create=None, raise_exceptions=True):
    if not isinstance(path, str):
        if not raise_exceptions:
            return False
        raise TypeError(f"Path must be of type string, got type {type(path)}.")

    if not isinstance(suffix, str):
        if not raise_exceptions:
            return False
        raise TypeError(f"Suffix must be of type string, got type {type(suffix)}.")

    if not path.endswith(suffix):
        if not raise_exceptions:
            return False
        raise ValueError(f"Path must point to file with suffix \"{suffix}\".")

    if not os.path.isfile(path):
        if create is None:
            if not raise_exceptions:
                return False
            raise FileNotFoundError(f"Couldn't find file {path}.")

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(create)

    return True


def check_accessibility(accessee, accessor):
    if isinstance(accessee, dict) and (accessor in accessee):
        return True

    if isinstance(accessee, list) or isinstance(accessee, tuple):
        if isinstance(accessor, int) and (0 <= accessor < len(accessee)):
            return True

    return False


def get_value_of_nested_at(nested, path):
    if not isinstance(path, list):
        path = [path]

    if len(path) == 0:
        return nested

    if check_accessibility(nested, path[0]):
        return get_value_of_nested_at(nested[path[0]], path[1:])

    return None


def ensure_alphanumeric(string):
    return "".join(re.findall("[A-Za-z0-9]+", string))


def load_config(path=None, merging_rules=None):
    global config_path, config

    if path is not None:
        check_file_validity(path, ".json", "{}", True)
        config_path = path

    else:
        if config_path is None:
            raise ValueError("Path can only be None if load_config or save_config has been called since last call of clear_config/beginning of program.")
        path = config_path

    with open(path, "r") as f:
        file_content = json.loads(f.read())

    if merging_rules is None:
        config = file_content


def save_config(path=None, merging_rules=None):
    if path is not None:
        check_file_validity(path, ".json", "{}", True)
        config_path = path

    else:
        if config_path is None:
            raise ValueError("Path can only be None if load_config or save_config has been called since last call of clear_config/beginning of program.")
        path = config_path

    with open(path, "w") as f:
        if merging_rules is None:
            json.dump(config, f, indent=4)


def clear_config():
    global config, course_id, moodle_token, config_path, download_config, download_insight_directory

    config = dict()
    course_id = None
    moodle_token = None
    config_path = None
    download_config = None
    download_insight_directory = None


def extract_essential_configs():
    global course_id, moodle_token, download_config, download_insight_directory

    course_id = get_value_of_nested_at(config, "course-id")

    moodle_token_path = get_value_of_nested_at(config, "moodle-token-path")
    check_file_validity(moodle_token_path, ".txt", None)
    with open(moodle_token_path, "r") as f:
        moodle_token = ensure_alphanumeric(f.read())

    download_config = get_value_of_nested_at(config, "download")
    download_insight_directory = get_value_of_nested_at(config, ["download", "insight-directory"])


def call_api_method(method, args=dict()):
    # this can only happen, if this method is called manually.
    if moodle_token is None:
        raise ValueError("Moodle-Token is unset.")

    if not isinstance(args, dict):
        raise Exception("Arguments need to be of type dict.")

    url = moodle_api_url + f"?wstoken={moodle_token}&wsfunction={method}&moodlewsrestformat=json"
    for key, value in args.items():
        url += f"&{key}={value}"

    response = requests.get(url)
    return response.json()


def save_insight(content, insight_directory, filename):
    if insight_directory is not None:
        with open(os.path.join(insight_directory, filename), "w") as f:
            if isinstance(content, dict) or isinstance(content, list):
                json.dump(content, f, indent=4)
            else:
                f.write(content)


def find_all_downloadable_files():
    global download_core_course_get_contents_response, download_mod_assign_get_assignments_response, download_mod_assign_get_submission_status_responses, download_course_files, download_assignment_names

    # get all course modules
    download_core_course_get_contents_response = call_api_method("core_course_get_contents", {"courseid": course_id})
    save_insight(download_core_course_get_contents_response, download_insight_directory, "download-core_course_get_contents-response.json")
    if "exception" in download_core_course_get_contents_response:
        raise ValueError("Moodle-API error:\n" + str(download_core_course_get_contents_response))

    # get all course assignments
    download_mod_assign_get_assignments_response = call_api_method("mod_assign_get_assignments", {"courseids[0]": course_id})
    save_insight(download_mod_assign_get_assignments_response, download_insight_directory, "download-mod_assign_get_assignments-response.json")
    if "exception" in download_mod_assign_get_assignments_response:
        raise ValueError("Moodle-API error:\n" + str(download_mod_assign_get_assignments_response))

    # find all assignment ids
    assign_ids = download_assignment_ids_ars.search_through(download_core_course_get_contents_response)

    # find all assignment names
    download_assignment_names = {"assignment-" + str(assign_id): download_assignment_names_ars.search_through(download_mod_assign_get_assignments_response, assignment_id=assign_id)[0] for assign_id in assign_ids}

    # get all assignments, assignment submissions and assignment feedbacks
    download_mod_assign_get_submission_status_responses = dict()
    error_responses = dict()

    for assign_id in assign_ids:
        download_mod_assign_get_submission_status_response = call_api_method("mod_assign_get_submission_status", {"assignid": assign_id})
        if "exception" in download_mod_assign_get_submission_status_response:
            error_responses["assignment-" + str(assign_id)] = download_mod_assign_get_submission_status_response
        download_mod_assign_get_submission_status_responses["assignment-" + str(assign_id)] = download_mod_assign_get_submission_status_response

    save_insight(download_mod_assign_get_submission_status_responses, download_insight_directory, "download-mod_assign_get_submission_status-responses.json")
    if bool(error_responses):
        raise ValueError("Moodle-API error(s):\n" + str(error_responses))

    # find all files in course
    download_course_files = download_files_ars.search_through(download_core_course_get_contents_response, origin="content")
    download_course_files += download_files_ars.search_through(download_mod_assign_get_submission_status_responses, origin="assignment")
    save_insight(download_course_files, download_insight_directory, "download-course_files.json")


def determine_relevant_rulesets(sub_config, ruleset_names):
    if ruleset_names is None:
        rulesets = get_value_of_nested_at(sub_config, ["rulesets"])

        if rulesets is None:
            return {}

        return rulesets

    if not isinstance(ruleset_names, list):
        ruleset_names = [ruleset_names]

    rulesets = dict()
    for ruleset_name in ruleset_names:
        ruleset = get_value_of_nested_at(sub_config, ["rulesets", ruleset_name])
        if ruleset is not None:
            rulesets[ruleset_name] = ruleset

    return ruleset_names


fvstring_pattern = re.compile(
    r'\$\('
    r'(?P<name>[a-zA-Z_]+)'
    r'(?:\:(?P<frmt>[a-zA-Z0-9_%. +\-<>\^=]*))?'
    r'\)'
)


def smart_format(strg, frmt):
    if "d" in frmt:
        strg = int(strg)
    elif ("f" in frmt) or ("e" in frmt):
        strg = float(strg)
    return f"{strg:{frmt}}"


def resolve_format_variable_string(fvstring, vardict):
    while True:
        match = fvstring_pattern.search(fvstring)
        if match is None:
            break

        name = match.groupdict()["name"]
        frmt = match.groupdict()["frmt"]
        if (name in vardict) and frmt is not None:
            fvstring = fvstring.replace(f"$({name}:{frmt})", smart_format(vardict[name], frmt))
        elif (name in vardict):
            fvstring = fvstring.replace(f"$({name})", vardict[name])
        elif frmt is not None:
            fvstring = fvstring.replace(f"$({name}:{frmt})", "")
        else:
            fvstring = fvstring.replace(f"$({name})", "")

    return fvstring


def get_download_info(filemeta, ruleset, force_dict):
    if "download-path" not in ruleset:
        return []

    # origin
    if "origin" in ruleset:
        origin_whitelist = ruleset["origin"]
        if not isinstance(origin_whitelist, list):
            origin_whitelist = [origin_whitelist]
        if filemeta["origin"] not in origin_whitelist:
            return []

    if "!origin" in ruleset:
        origin_blacklist = ruleset["!origin"]
        if not isinstance(origin_blacklist, list):
            origin_blacklist = [origin_blacklist]
        if filemeta["origin"] in origin_blacklist:
            return []

    # mimetype
    if "mimetype" in ruleset:
        mimetype_whitelist = ruleset["mimetype"]
        if not isinstance(mimetype_whitelist, list):
            mimetype_whitelist = [mimetype_whitelist]
        if filemeta["mimetype"] not in mimetype_whitelist:
            return []

    if "!mimetype" in ruleset:
        mimetype_blacklist = ruleset["!mimetype"]
        if not isinstance(mimetype_blacklist, list):
            mimetype_blacklist = [mimetype_blacklist]
        if filemeta["mimetype"] in mimetype_blacklist:
            return []

    # extension
    if "extension" in ruleset:
        extension_whitelist = ruleset["extension"]
        if not isinstance(extension_whitelist, list):
            extension_whitelist = [extension_whitelist]
        if filemeta["extension"] not in extension_whitelist:
            return []

    if "!extension" in ruleset:
        extension_blacklist = ruleset["!extension"]
        if not isinstance(extension_blacklist, list):
            extension_blacklist = [extension_blacklist]
        if filemeta["extension"] in extension_blacklist:
            return []

    vardict = {"filename": filemeta["filename"], "extension": filemeta["extension"]}

    # filename
    if "filename" in ruleset:
        filename_groupdict = dict()
        foundmatch = False
        filename_whitelist = ruleset["filename"]

        if not isinstance(filename_whitelist, list):
            filename_whitelist = [filename_whitelist]

        for filename_white in filename_whitelist:
            res = re.search(filename_white, filemeta["filename"])
            if bool(res):
                foundmatch = True
                groupdict = res.groupdict()
                filename_groupdict = merge_dictionaries(filename_groupdict, groupdict)

        if not foundmatch:
            return []

        key_intersect = list(set(vardict.keys()) & set(filename_groupdict.keys()))
        for key in key_intersect:
            if vardict[key] != filename_groupdict[key]:
                return False

        vardict = merge_dictionaries(vardict, filename_groupdict)

    if "!filename" in ruleset:
        foundmatch = False
        filename_blacklist = ruleset["!filename"]

        if not isinstance(filename_blacklist, list):
            filename_blacklist = [filename_blacklist]

        for filename_white in filename_whitelist:
            res = re.search(filename_white, filemeta["filename"])
            foundmatch |= bool(res)

        if foundmatch:
            return []

    # location
    if "location" in ruleset:
        location_groupdict = dict()
        foundmatch = False
        location_whitelist = ruleset["location"]

        if not isinstance(location_whitelist, list):
            location_whitelist = [location_whitelist]

        for location_white in location_whitelist:
            res = re.search(location_white, filemeta["name-path-string"])
            if bool(res):
                foundmatch = True
                groupdict = res.groupdict()
                location_groupdict = merge_dictionaries(location_groupdict, groupdict)

        if not foundmatch:
            return []

        key_intersect = list(set(vardict.keys()) & set(location_groupdict.keys()))
        for key in key_intersect:
            if vardict[key] != location_groupdict[key]:
                return False

        vardict = merge_dictionaries(vardict, location_groupdict)

    if "!location" in ruleset:
        foundmatch = False
        location_blacklist = ruleset["!location"]

        if not isinstance(location_blacklist, list):
            location_blacklist = [location_blacklist]

        for location_white in location_whitelist:
            res = re.search(location_white, filemeta["name-path-string"])
            foundmatch |= bool(res)

        if foundmatch:
            return []

    if bool(force_dict):
        for key in force_dict.keys():
            if (key not in vardict) or (vardict[key] != force_dict[key]):
                return []

    name = filemeta["filename"]
    url = filemeta["fileurl"]
    unzip = bool(get_value_of_nested_at(ruleset, "unzip"))
    replace = True
    if "replace" in ruleset:
        replace = ruleset["replace"]
    makedirs = True
    if "makedirs" in ruleset:
        makedirs = ruleset["makedirs"]

    download_paths = ruleset["download-path"]
    if not isinstance(download_paths, list):
        download_paths = [download_paths]
    download_paths = [resolve_format_variable_string(download_path, vardict) for download_path in download_paths]

    iszip = filemeta["extension"] == ".zip"

    info = [{"name": name, "path": download_path, "url": url, "unzip": unzip, "replace": replace, "makedirs": makedirs, "iszip": iszip} for download_path in download_paths]
    return info


def add_moodle_token_to_url(url):
    if url.find("?") != -1:
        return url + "&token=" + moodle_token
    return url + "?token=" + moodle_token


def download_file(download_info):
    name = download_info["name"]
    path = download_info["path"]
    url = download_info["url"]
    unzip = download_info["unzip"]
    replace = download_info["replace"]
    makedirs = download_info["makedirs"]
    iszip = download_info["iszip"]

    if os.path.isfile(path) and not replace:
        return

    if not os.path.isdir(os.path.dirname(path)):
        if not makedirs:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)

    progress.print(f"downloading {name}")
    res = requests.get(add_moodle_token_to_url(url))
    file_content = res.content

    with open(path, "wb") as f:
        f.write(file_content)

    if iszip and unzip:
        progress.print(f"unzipping {name}")
        with zipfile.ZipFile(path, "r") as zip_ref:
            zip_ref.extractall(os.path.dirname(path))

        try:
            os.remove(path)
        except:
            pass


def download(ruleset_names=None, print_files=False, download_files=True, force_dict=None):
    extract_essential_configs()

    if download_config is None:
        raise ValueError("No download config was found.")

    find_all_downloadable_files()
    rulesets = determine_relevant_rulesets(download_config, ruleset_names)

    download_info = []
    for filemeta in download_course_files:
        for ruleset_name, ruleset in rulesets.items():
            download_info += get_download_info(filemeta, ruleset, force_dict)

    info_without_duplicate_directories = []
    for info in download_info:
        already_exists = False
        for iwdd in info_without_duplicate_directories:
            if iwdd["path"] == info["path"]:
                already_exists = True
                break

        if not already_exists:
            info_without_duplicate_directories += [info]

    num_files = len(info_without_duplicate_directories)
    if num_files == 0:
        return

    progress.set_maximum(num_files)
    progress.set_progress(0)
    print(f"Downloading {num_files} files from Moodle.")
    progress.print(first_print=True)

    for i in range(num_files):
        info = info_without_duplicate_directories[i]
        if print_files and not download_files:
            # print(sub_dict(info, ["name", "path", "url"]))
            print(f"{info["path"]} [{info["name"]}]({info["url"]})")

        if download_files:
            download_file(info)
            progress.set_progress(i+1)
            progress.print()

    progress.print("finished")


if __name__ == "__main__":
    pass
