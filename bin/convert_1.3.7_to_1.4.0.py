import json as sj
import argparse
import logging
from glob import glob
import os
from fnmatch import fnmatch
import configparser
from tqdm import tqdm
# import imp
from importlib import util
import pprint

# from distutils.version import LooseVersion
script_dir = os.path.dirname(os.path.realpath(__file__))
try:
    spec = util.spec_from_file_location("veris_logger", script_dir + "/veris_logger.py")
    veris_logger = util.module_from_spec(spec)
    spec.loader.exec_module(veris_logger)
    # veris_logger = imp.load_source("veris_logger", script_dir + "/veris_logger.py")
except:
    print("Script dir: {0}.".format(script_dir))
    raise

cfg = {
    'log_level': 'warning',
    'log_file': None,
    'countryfile': './all.json'
}


def getCountryCode(countryfile):
    # country_codes = sj.loads(open(countryfile).read())
    with open(countryfile, 'r') as filehandle:
        country_codes = sj.load(filehandle)
    country_code_remap = {'Unknown': '000000'}
    for eachCountry in country_codes:
        try:
            country_code_remap[eachCountry['alpha-2']] = \
                eachCountry['region-code']
        except:
            country_code_remap[eachCountry['alpha-2']] = "000"
        try:
            country_code_remap[eachCountry['alpha-2']] += \
                eachCountry['sub-region-code']
        except:
            country_code_remap[eachCountry['alpha-2']] += "000"
    return country_code_remap


def getField(current, txt):
    tsplit = txt.split('.', 1)
    if tsplit[0] in current:
        result = current[tsplit[0]]
        if len(tsplit) > 1:
            result = getField(result, tsplit[1])
    else:
        result = None
    return result


def grepText(incident, searchFor):
    txtFields = ['summary', "notes", "victim.notes", "actor.external.notes",
                 "actor.internal.notes", "actor.partner.notes",
                 "actor.unknown.notes", "action.malware.notes",
                 "action.hacking.notes", "action.social.notes",
                 "action.misuse.notes", "action.physical.notes",
                 "action.error.notes", "action.environmental.notes",
                 "asset.notes", "attribute.confidentiality.notes",
                 "attribute.integrity.notes", "attribute.availability.notes",
                 "impact.notes", "plus.analyst_notes", "plus.pci.notes"]
    foundAny = False
    for txtField in txtFields:
        curText = getField(incident, txtField)
        if isinstance(curText, str):  # replaced basestr with str per 2to3. - GDB 181109
            if searchFor.lower() in curText:
                foundAny = True
                break
        # could be extended to look for fields in lists
    return foundAny


def main(cfg):
    veris_logger.updateLogger(cfg)

    last_version = "1.3.7"
    version = "1.4.0"

    if cfg.get('log_level', '').lower() == "debug":
        pprint.pprint(cfg)  # DEBUG

    logging.info("Converting files from {0} to {1}.".format(cfg["input"], cfg["output"]))
    for root, dirnames, filenames in tqdm(os.walk(cfg['input'])):
        logging.info("starting parsing of directory {0}.".format(root))
        # filenames = filter(lambda fname: fnmatch(fname, "*.json"), filenames)
        filenames = [fname for fname in filenames if fnmatch(fname.lower(), "*.json")]  # per 2to3. - GDB 181109
        if filenames:
            dir_ = os.path.join(cfg['output'], root[len(cfg['input']):].lstrip(
                "/"))  # if we don't strip the input, we get duplicate directories
            logging.info("Output directory is {0}.".format(dir_))
            if not os.path.isdir(dir_):
                os.makedirs(dir_)
            for fname in filenames:
                in_fname = os.path.join(root, fname)
                out_fname = os.path.join(dir_, fname)

                logging.info("Now processing %s" % in_fname)
                try:
                    # incident = sj.loads(open(in_fname).read())
                    with open(in_fname, 'r') as filehandle:
                        incident = sj.load(filehandle)
                except sj.JSONDecodeError:
                    logging.warning(
                        "ERROR: %s did not parse properly. Skipping" % in_fname)
                    continue

                if 'assets' not in incident.get('asset', {}):
                    raise KeyError("Asset missing from assets in incident {0}.".format(fname))

                # if the record is already version 1.3.6, skip it. This can happen if there are mixed records
                if incident.get('schema_version', last_version) != last_version:
                    if incident.get('schema_version', '') != version:
                        logging.warning(
                            "Incident {0} is version {1} instead of {2} and can therefore not be updated.".format(fname,
                                                                                                                  incident.get(
                                                                                                                      'schema_version',
                                                                                                                      'NONE'),
                                                                                                                  last_version))
                    continue

                # Update the schema version
                incident['schema_version'] = version

                # EXAMPLE UPDATE
                #             # Replace asset S - SCADA with S - ICS
                #             # Issue 104, Commit f8b7387
                #             # if "S - SCADA" in incident.get("asset", {}).get("assets", []):
                #                 # incident["asset"]["assets"] = [e.replace("S - SCADA", "S - ICS") for e in incident["asset"]["assets"]]
                #             incident["asset"]["assets"] = [dict(e, **{u"variety": u"S - ICS"}) if e.get(u"variety", "") ==  u"S - SCADA" else e for e in incident["asset"]["assets"]]

                # Per https://github.com/vz-risk/veris/issues/271
                # infer actor.*.motive.Secondary if malware.variety.DoS
                # Now to save the incident


                ##ISSUE 420 (lol) Update PCI standard to the new version which requires adding additional fields and moving over the fields
                # if 'pci' in incident.get("plus", {}):
                #
                #     # start the dictionary of PCI values
                #     pci_dict = {"In Place": "Yes",
                #                 "Not Applicable": "Not Assessed",
                #                 "Not In Place": "No",
                #                 "Unknown":"Not Assessed"
                #     }
                #
                #     # Need to create the new hierarchy to add the subvalues to
                #     # Do a check before we accidentally remove this field
                #     if 'requirements' not in incident.get('plus',{}).get('pci',{}):
                #         incident['plus']['pci']['requirements'] = {}
                #
                #     # loop through the values that have "req_" and iterate through those [extract out the ones that start with req
                #     # with those values you can know look up and transfer the values
                #     for y in [x for x in incident.get('plus',{}).get('pci', {}) if x.startswith('req_')]:
                #         old_value = incident.get('plus', {}).get('pci', {}).get(y)
                #         incident['plus']['pci']['requirements'][y] = {}
                #         incident['plus']['pci']['requirements'][y]['in_place'] = pci_dict.get(old_value)
                #         incident['plus']['pci'].pop(y, None)

                #Issue https://github.com/vz-risk/veris/issues/414 Discovery_notes is found in the root of the incident
                # it should really be at the root  of discovery_method, this update will make that happen
                #: do we need to ensure we capture if there's a discovery_note BUT no discovery?? seems unlikely considerng discovery_method is required
                # if incident.get("discovery_notes", {}) and incident.get('discovery_method', {}):
                #     incident['discovery_method']['discovery_notes'] = incident.get('discovery_notes')
                #     incident.pop('discovery_notes', None)

                ##https://github.com/vz-risk/veris/issues/451 Removes omission from the error variety and reassigns them as Other



                #https://github.com/vz-risk/veris/issues/481 Change man in the middle to adversary in the middle for hacking

                if "MitM" in incident.get('action', {}).get('hacking', {}).get('variety',{}):
                    incident['action']['hacking']['variety'] = [e.replace("MitM", "AitM") for e in
                                                                incident['action']['hacking']['variety']]
                    notes = incident['action']['hacking'].get('notes', '')
                    notes = notes + "\n" + "VERIS 1_3_7 to 1_4_0 Migration script, to change MiTM to AiTM"
                    incident['action']['hacking']['notes'] = notes

                # https://github.com/vz-risk/veris/issues/480 Change man in the middle to adversary in the middle for malware
                if "MitM" in incident.get('action', {}).get('malware', {}).get('variety',{}):
                    incident['action']['malware']['variety'] = [e.replace("MitM", "AitM") for e in
                                                                incident['action']['malware']['variety']]

                    notes = incident['action']['malware'].get('notes', '')
                    notes = notes + "\n" + "VERIS 1_3_7 to 1_4_0 Migration script, to change MiTM to AiTM"
                    incident['action']['malware']['notes'] = notes


                #Stop using Social.Extortion for Ransomware - transfer 2023/2024 caseload over
                # https://github.com/vz-risk/veris/issues/474
                # Remove the action social extortion associated with ransomware attacks

                if "Extortion" in incident.get('action', {}).get('social', {}).get('variety',{}) and \
                    "Exploit vuln" in incident.get('action', {}).get('hacking', {}).get('variety',{}):
                    #remove extortion + remove alter behavior + remove

                    #Add Ransomware
                    if 'Ransomware' not in incident.get('action', {}).get('malware', {}).get('variety',{}):
                        #if theres no malware
                        if 'malware' not in incident['action']:
                            incident['action']['malware'] = {"variety": ['Ransomware'], "vector": ["Remote injection"]}
                        else:
                            incident['action']['malware']['variety'].append('Ransomware')
                            incident['action']['malware']['vector'].append('Remote injection')
                        notes = incident['action']['malware'].get('notes',"")
                        notes = notes + "\n" + "VERIS 1_3_7 to 1_4_0 Migration script, to fix extortion and ransomware attacks"
                        incident['action']['malware']['notes'] = notes

                    # if there's only one social action, clear out everything social related
                    if len(incident.get('action', {}).get('social', {}).get('variety',{})) == 1:
                        #fix attribute
                        attribute = incident['attribute']['integrity'].get('variety', [])
                        attribute.remove("Alter behavior")
                        incident['attribute']['integrity']['variety'] = attribute

                        # if there's no integrity left, remove integrity
                        if len(incident['attribute']['integrity']['variety'])<1:
                            incident['attribute'].pop('integrity')

                        # dealing with assets

                        #incident['asset']['assets'] = [
                            #enum.pop() if enum.get(u"variety", "") == "P - End-user" else enum for enum in incident['asset']['assets']]
                        varieties = [item for item in incident['asset']['assets'] if item.get('variety', "") != "P - End-user"]
                        varieties = [item for item in varieties if item.get('variety', "") != 'P - End-user or employee']
                        incident['asset']['assets'] = varieties

                        incident['action']['social']['target'] = None
                        incident['action']['social']['result'] = None
                        incident['action'].pop('social')
                    else:
                        incident['action']['social']['variety'].remove("Extortion")

                    notes = incident['action']['hacking'].get('notes', '')
                    notes = notes + "\n" + "VERIS 1_3_7 to 1_4_0 Migration script, to fix extortion and ransomware attacks"
                    incident['action']['hacking']['notes'] = notes

                # There's some floating privleged access physical vectors that shouldn't exist, so cleaning those up
                if "Privileged access" in incident.get('action', {}).get('physical', {}).get('vector',{}):
                    incident['action']['physical']['vector'] = [e.replace("Privileged access", "Victim secure area") for e in
                                                                incident['action']['physical']['vector']]

                logging.info("Writing new file to %s" % out_fname)
                with open(out_fname, 'w') as outfile:
                    sj.dump(incident, outfile, indent=2, sort_keys=True, separators=(',', ': '))


if __name__ == '__main__':
    descriptionText = "Converts VERIS 1.3.7 incidents to v1.4.0"
    helpText = "output directory to write new files. Default is to overwrite."
    parser = argparse.ArgumentParser(description=descriptionText)
    parser.add_argument("-l", "--log_level", choices=["critical", "warning", "info", "debug"],
                        help="Minimum logging level to display")
    parser.add_argument('--log_file', help='Location of log file')
    parser.add_argument("-i", "--input", required=True,
                        help="top level folder to search for incidents")
    parser.add_argument("-o", "--output",
                        help=helpText)
    # parser.add_argument('--countryfile', help='The json file holdering the country mapping.')
    parser.add_argument('--conf', help='The location of the config file', default="../user/data_flow.cfg")
    args = parser.parse_args()
    args = {k: v for k, v in vars(args).items() if v is not None}

    # logging_remap = {'warning':logging.WARNING, 'critical':logging.CRITICAL, 'info':logging.INFO, 'debug':logging.DEBUG} # defined above. - gdb 080716

    # Parse the config file
    try:
        config = configparser.ConfigParser()
        # config.readfp(open(args["conf"]))
        with open(args['conf'], 'r') as filehandle:
            config.readfp(filehandle)
        cfg_key = {
            'GENERAL': ['report', 'input', 'output', 'analysis', 'year', 'force_analyst', 'version', 'database',
                        'check'],
            'LOGGING': ['log_level', 'log_file'],
            'REPO': ['veris', 'dbir_private'],
            'VERIS': ['mergedfile', 'enumfile', 'schemafile', 'labelsfile', 'countryfile']
        }
        for section in cfg_key.keys():
            if config.has_section(section):
                for value in cfg_key[section]:
                    if value.lower() in config.options(section):
                        cfg[value] = config.get(section, value)
        veris_logger.updateLogger(cfg)
        logging.debug("config import succeeded.")
    except Exception as e:
        logging.warning("config import failed with error {0}.".format(e))
        # raise e
        pass
    # place any unique config file parsing here
    if "input" in cfg:
        cfg["input"] = [l.strip() for l in cfg["input"].split(" ,")]  # spit to list

    cfg.update(args)

    if "output" not in cfg:
        cfg["output"] = cfg["input"]

    veris_logger.updateLogger(cfg)

    # country_region = getCountryCode(cfg['countryfile'])

    # assert args.path != args.output, "Source and destination must differ"

    main(cfg)
