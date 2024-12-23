#!/usr/bin/python

# https://www.mattcrampton.com/blog/a_list_of_all_python_assert_methods/

import unittest
from importlib import util
import json
import shutil
import os, pathlib
from jsonschema import ValidationError, Draft4Validator
import re
import logging
import tempfile
from copy import deepcopy
import uuid
from pprint import pprint

##TODO: Update this reference PL priority
#Actually fix this or just jank patch it?
#veris = os.path.expanduser("~/Documents/Development/vzrisk/veris/")
veris = str(pathlib.Path(__file__).parent.resolve().parent.resolve().parent.resolve())
cfg = {
    "log_level": "error",
    "log_file": "./unittest.log",
    'provide_context': True,
    'input': "./",
    'output': "./",
    'force_analyst': False,
    'check': False,
    'update': True,
    'analyst': "unittest",
    'veris': veris,
    'version': "1.4.0",
    'countryfile': veris.rstrip("/") + "/bin/all.json",
#    'report': report,
#    'year': year,
    'test': 'BLUE',
    'vcdb': False,
    'year': 2024
}

# import rules.py
spec = util.spec_from_file_location("rules", veris.rstrip("/") + "/bin/rules.py")
rules = util.module_from_spec(spec)
spec.loader.exec_module(rules)
Rules = rules.Rules(cfg)

# import convert_1.3.7_to_1.4.0.py
spec = util.spec_from_file_location("convert", veris.rstrip("/") + "/bin/convert_1.3.7_to_1.4.0.py")
convert = util.module_from_spec(spec)
spec.loader.exec_module(convert)

# import checkValidity
spec = util.spec_from_file_location("checkValidity", cfg.get("veris", "../").rstrip("/") + "/bin/checkValidity.py")
checkValidity = util.module_from_spec(spec)
spec.loader.exec_module(checkValidity)

# create validator
with open(veris.rstrip("/") + "/verisc-merged.json") as filehandle:
    validator = Draft4Validator(json.load(filehandle))


# Used to apply convert script to json
def apply_convert(in_incident, updater, cfg=cfg):
  with tempfile.TemporaryDirectory() as tmpdirname:
    filename = os.path.join(tmpdirname, str(uuid.uuid4()).upper() + ".json")
    with open(filename, 'w') as filehandle:
        json.dump(in_incident, filehandle)
    updater.main(dict(cfg, **{'input': tmpdirname, 'output':tmpdirname}))
    with open(filename, 'r') as filehandle:
        return(json.load(filehandle))

# Import a base 1.3.6 incident
filename = str(pathlib.Path(__file__).parent.resolve())+"/veris-{}-test1.JSON".format(cfg['version'].replace(".","_"))
with open(filename, 'r') as filehandle:
  base_incident = json.load(filehandle)


class TestConvert(unittest.TestCase):

    # def test420_1(self):
    #     in_incident = deepcopy(base_incident)
    #     in_incident["schema_version"] = "1.3.6"
    #     #we skip adding the fields, since the test file has the fields required
    #     out_incident = apply_convert(in_incident, convert)
    #     self.assertNotIn('req_1', out_incident['plus']['pci'])
    #     self.assertIn('req_1', out_incident['plus']['pci']['requirements'])
    #     for error in validator.iter_errors(out_incident):
    #         raise error

    # def test451_1(self):
    #     in_incident = deepcopy(base_incident)
    #     in_incident["schema_version"] = "1.3.6"
    #
    #     #skip adding the fields, since the test file has the fields required
    #     out_incident = apply_convert(in_incident, convert)
    #     self.assertNotIn('Omission', out_incident['action']['error']['variety'])
    #     self.assertIn('Other',out_incident['action']['error']['variety'] )
    #
    #     for error in validator.iter_errors(out_incident):
    #         raise error

    # def test414_1(self):
    #     in_incident = deepcopy(base_incident)
    #     in_incident["schema_version"] = "1.3.6"
    #
    #     # skip adding the fields, since the test file has the fields required
    #     out_incident = apply_convert(in_incident, convert)
    #     self.assertIn("discovery_notes", out_incident['discovery_method'])
    #     for error in validator.iter_errors(out_incident):
    #         raise error


    # vz-risk/veris issue # 263
#    def  test263_1(self):
#        incident_in = incident0
#        incident_in['asset']['assets'].append({'variety': "U - Laptop"})
#        incident_out = Rules.addRules(incident_in)
#        self.assertIn('U - Desktop or laptop', [item.get("variety", "") for item in incident_out['asset']['assets']])
#    def  test263_2(self):
#        incident_in = incident0
#        incident_in['asset']['assets'].append({'variety': "U - Desktop"})
#        incident_out = Rules.addRules(incident_in)
#        self.assertIn('U - Desktop or laptop', [item.get("variety", "") for item in incident_out['asset']['assets']])


### This is a recommend only rule
#    def Commented_out_test_convert_400_4(self):
#        in_incident = deepcopy(base_incident)
#        in_incident["schema_version"] = "1.3.5"
#        in_incident["action"] = {"malware": {"variety": ['Trojan'], "vector": ["Unknown"]}}
#        out_incident = apply_convert(in_incident, convert)
#        self.assertIn('Trojan', out_incident['value_chain']['development']['variety'])
#        self.assertGreater(len(out_incident['value_chain']['development']['notes']), 0)
#        for error in validator.iter_errors(out_incident):
#            raise error

    def test474_1(self):
        in_incident = deepcopy(base_incident)
        in_incident["schema_version"] = "1.3.7"

        out_incident = apply_convert(in_incident, convert)
        # We need a more finessed  test if the IN JSON only has extortion action, then all social will be removed + assets
        if "Extortion" in in_incident.get('action', {}).get('social', {}).get('variety', {}) and \
                "Exploit vuln" in in_incident.get('action', {}).get('hacking', {}).get('variety', {}):
            if len(in_incident.get('action', {}).get('social', {}).get('variety', {})) > 1:
                # if there's more than one social action ,we just want ot make sure to remove the Extortin
                self.assertNotIn('Extortion', out_incident['action']['social']['variety'])
                # Verify that ransomware is added
                self.assertIn("Ransomware", out_incident['action']['malware']['variety'])

                # Verify that there is noi Obfuscation
                self.assertNotIn("Obfuscation", out_incident['attribute'].get('availability', {}).get('variety', ""))

            else:
                #if it's the only social, then we need to remove ALL of elements of associated with it
                self.assertNotIn('social', out_incident['action'])

                self.assertNotIn('P - End-user or employee',
                              [item.get("variety", "") for item in out_incident['asset']['assets']])
                self.assertNotIn("P - End-user",
                                 [item.get("variety", "") for item in out_incident['asset']['assets']])
                self.assertIn("S - Web application",
                                 [item.get("variety", "") for item in out_incident['asset']['assets']])

                #Verify that ransomware is added
                self.assertIn("Ransomware", out_incident['action']['malware']['variety'])

                #Verify that there is noi Obfuscation
                self.assertNotIn("Obfuscation", out_incident['attribute'].get('availability',{}).get('variety',""))

        for error in validator.iter_errors(out_incident):
            raise error
    def test481(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"hacking": {"variety": ["MitM"], "vector": ["Unknown"]}}
        in_incident["schema_version"] = "1.3.7"

        out_incident = apply_convert(in_incident, convert)
        self.assertNotIn('MitM', out_incident['action']['hacking']['variety'])
        self.assertIn('AitM', out_incident['action']['hacking']['variety'])
        for error in validator.iter_errors(out_incident):
            raise error

    def test480(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"malware": {"variety": ["MitM"], "vector": ["Unknown"]}}
        in_incident["schema_version"] = "1.3.7"

        out_incident = apply_convert(in_incident, convert)
        self.assertNotIn('MitM', out_incident['action']['malware']['variety'])
        self.assertIn('AitM', out_incident['action']['malware']['variety'])
        for error in validator.iter_errors(out_incident):
            raise error
class TestRules(unittest.TestCase):
#    # vz-risk/veris issue #263
#    def test263_1(self):
#        self.assertIn('U - Desktop or laptop', [item.get("variety", "") for item in incident1['asset']['assets']])

    def test_rules_271_1(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"malware": {"variety": ["DoS"], "vector":["Unknown"]}}
        in_incident["actor"] = {"internal": {"variety": ["Unknown"]}}
        out_incident = Rules.addRules(in_incident)
        motives = list(set(
            out_incident['actor'].get('external', {}).get('motive', []) +
            out_incident['actor'].get('internal', {}).get('motive', []) +
            out_incident['actor'].get('partner', {}).get('motive', [])
        ))
        #pprint(out_incident)
        self.assertIn('Secondary', motives)
        for error in validator.iter_errors(out_incident):
            raise error

class TestValidation(unittest.TestCase):
    def test_validation_180_1(self):
        regions = {
            "002": ["011", "014", "017", "018", "015"], # Africa
            "010": ["000"], # Antarctica
            "019": ["021", "005", "013", "029", "419"], # America
            "419": ["005", "013", "029"], # Latin America and Caribbean
            "142": ["030", "034", "035", "143", "145"], # Asia
            "150": ["039", "151", "154", "830", "155"], # Europe
            "009": ["053", "054", "057", "061"] # Oceania
        }
        good_regions = []
        for region in regions.keys():
            good_regions += [region + v for v in regions[region]]
        in_incident = deepcopy(base_incident)
        in_incident["victim"]['region'] = good_regions # legitimate regions
        for error in checkValidity.main(in_incident):
            raise error
    def test_validation_180_2(self):
        in_incident = deepcopy(base_incident)
        in_incident["victim"]['region'] = ["001000", "020001", "003021"] # unused super-regions
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_180_3(self):
        in_incident = deepcopy(base_incident)
        in_incident["victim"]['region'] = ["019011"] # incorrect pairing
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error

    def test_validation_407_1(self):
        in_incident = deepcopy(base_incident)
        in_incident["victim"]['secondary'] = {"victim_id": ['victim2', 'victim3', 'victim4'], "amount": 3}  # no error
        for error in checkValidity.main(in_incident):
            raise error
    def test_validation_407_2(self):
        in_incident = deepcopy(base_incident)
        in_incident["victim"]['secondary'] = {"victim_id": ['victim2', 'victim3', 'victim4'], "amount": 0}  # error
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_407_3(self):
        in_incident = deepcopy(base_incident)
        in_incident["victim"]['secondary'] = {"victim_id": ['victim2', 'victim3', 'victim4']}  # error
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error

    # Validation
    def test_validation_400_1(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"social": {"variety": ['Phishing'], "vector": ["Unknown"], "target": ["Unknown"]}}
        in_incident["value_chain"] = {"targeting": {"variety": "Email addresses"}}
        in_incident["attribute"] = {"integrity": {"variety": "Alter behavior"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_2(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"social": {"variety": ['Phishing'], "vector": ["Unknown"], "target": ["Unknown"]}}
        in_incident["value_chain"] = {"development": {"variety": "Email"}}
        in_incident["attribute"] = {"integrity": {"variety": "Alter behavior"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_3(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"malware": {"variety": ['Unknown'], "vector": ["C2"]}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_4(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"malware": {"variety": ['Ransomware'], "vector": ["Unknown"]}}
        in_incident["value_chain"] = {"development": {"variety": "Ransomware"}}
        in_incident["attribute"] = {"integrity": {"variety": "Software installation"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_5(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"malware": {"variety": ['Ransomware'], "vector": ["Unknown"]}}
        in_incident["value_chain"] = {"cash-out": {"variety": "Cryptocurrency"}}
        in_incident["attribute"] = {"integrity": {"variety": "Software installation"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_6(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"malware": {"variety": ['Trojan'], "vector": ["Unknown"]}}
        in_incident["attribute"] = {"integrity": {"variety": "Software installation"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_7(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"social": {"variety": ['Unknown'], "vector": ["Email"]}}
        in_incident["value_chain"] = {"distribution": {"variety": "Email"}}
        in_incident["attribute"] = {"integrity": {"variety": "Alter behavior"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_8(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"social": {"variety": ['Unknown'], "vector": ["Email"]}}
        in_incident["value_chain"] = {"targeting": {"variety": "Email addresses"}}
        in_incident["attribute"] = {"integrity": {"variety": "Alter behavior"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    # Recommend only
    def test_validation_400_9(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"malware": {"variety": ['Unknown'], "vector": ["Unknown"]}}
        in_incident["attribute"] = {"integrity": {"variety": "Software installation"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_10(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"malware": {"variety": ['Trojan'], "vector": ["Unknown"]}}
        in_incident["value_chain"] = {"development": {"variety": ["Unknown"]}}
        in_incident["attribute"] = {"integrity": {"variety": "Software installation"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_11(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"social": {"variety": ['Pretexting'], "vector": ["Unknown"]}}
        in_incident["value_chain"] = {"targeting": {"variety": "Email addresses"}}
        in_incident["attribute"] = {"integrity": {"variety": "Alter behavior"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_12(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"hacking": {"variety": ['Use of stolen creds'], "vector": ["Unknown"]}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_13(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"hacking": {"variety": ['Exploit vuln'], "vector": ["Unknown"]}}
        in_incident["value_chain"] = {"targeting": {"variety": "Vulnerabilities"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_14(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"hacking": {"variety": ['Exploit vuln'], "vector": ["Unknown"]}}
        in_incident["value_chain"] = {"development": {"variety": "Exploit"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_15(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"malware": {"variety": ['Downloader'], "vector": ["Unknown"]}}
        in_incident["value_chain"] = {"development": {"variety": ["Unknown"]}}
        in_incident["attribute"] = {"integrity": {"variety": "Software installation"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_16(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"hacking": {"variety": ['Exploit misconfig'], "vector": ["Unknown"]}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_17(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"malware": {"variety": ['Exploit misconfig'], "vector": ["Unknown"]}}
        in_incident["value_chain"] = {"development": {"variety": ["Unknown"]}}
        in_incident["attribute"] = {"integrity": {"variety": "Software installation"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_18(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"malware": {"variety": ['Unknown'], "vector": ["Web application"]}}
        in_incident["value_chain"] = {"development": {"variety": ["Unknown"]}}
        in_incident["attribute"] = {"integrity": {"variety": "Software installation"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error
    def test_validation_400_19(self):
        in_incident = deepcopy(base_incident)
        in_incident["action"] = {"social": {"variety": ['Unknown'], "vector": ["Web application"]}}
        in_incident["attribute"] = {"integrity": {"variety": "Alter behavior"}}
        with self.assertRaises(ValidationError):
            for error in checkValidity.main(in_incident):
                raise error

    def test_validation_429_1(self):
        in_incident = deepcopy(base_incident)

# if True: #





if __name__ == '__main__':
    ## Test Validations
    logging.info("Review the following errors to ensure there are none unexpected. (In the future maybe we can catch all these with unit tests.")

    # Test Cases
    logging.info("Beginning test cases")
    unittest.main()