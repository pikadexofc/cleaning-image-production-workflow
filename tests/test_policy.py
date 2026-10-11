import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1]/'.agents/skills/cleaning-image-production/scripts'
sys.path.insert(0, str(SCRIPTS))
import policy

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.slot={'role':'hero','page_file':'darwin-office.html','pair_id':'',
                   'provenance':'AI_ILLUSTRATIVE','job_verified':False,'prompt_brief':'Exact source context.'}
        self.checks={k:True for k in policy.COMMON}
        self.checks.update(humans_present=False,equipment_used=False,equipment_none_reason='Finished environment')
    def test_hero_no_humans(self):
        policy.acceptance(self.slot,self.checks)
        self.checks['humans_present']=True
        with self.assertRaises(ValueError):policy.acceptance(self.slot,self.checks)
    def test_unknown_human_status_blocks(self):
        del self.checks['humans_present']
        with self.assertRaises(ValueError):policy.acceptance(self.slot,self.checks)
    def test_cropped_head_still_needs_worker(self):
        self.slot['role']='supporting';self.checks['active_cleaning']=True
        with self.assertRaises(ValueError):policy.acceptance(self.slot,self.checks)
        for k in ('worker_present','torso_arms_hands_visible','head_face_outside_frame','correct_technique','equipment_contact_correct','forest_green_uniform'):self.checks[k]=True
        policy.acceptance(self.slot,self.checks)
    def test_rug_before_requires_action(self):
        self.slot.update(role='before',page_file='darwin-rug-cleaning.html')
        with self.assertRaises(ValueError):policy.acceptance(self.slot,self.checks)
    def test_equipment_mismatch_blocks(self):
        self.checks.update(equipment_used=True,reference_geometry_and_colours_match=False)
        with self.assertRaises(ValueError):policy.acceptance(self.slot,self.checks)
    def test_pair_identity_and_result_are_required(self):
        self.slot['pair_id']='pair-01'
        with self.assertRaises(ValueError):policy.acceptance(self.slot,self.checks)
        self.checks.update(pair_identity_connected=True,result_difference_visible=True,camera_change_noticeable=True)
        policy.acceptance(self.slot,self.checks)
    def test_synthetic_job_evidence_rejected(self):
        self.slot['job_verified']=True
        with self.assertRaises(ValueError):policy.acceptance(self.slot,self.checks)
    def test_every_common_observation_required(self):
        for key in policy.COMMON:
            failed=dict(self.checks);failed[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):policy.acceptance(self.slot,failed)
    def test_ambiguous_and_missing_mapping_block(self):
        for c in ([],['a','b']):
            with self.assertRaises(ValueError):policy.unique_mapping(c)
        self.assertEqual(policy.unique_mapping(['a']),'a')
    def test_role_conflict_is_resolved(self):
        self.assertIn('No humans',policy.compose(self.slot))
        self.slot.update(role='before',page_file='darwin-rug-cleaning.html')
        self.assertIn('Mandatory active worker',policy.compose(self.slot))
    def test_real_decoding_and_extension(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'good.png';Image.new('RGB',(40,30)).save(p)
            self.assertEqual(policy.technical(p)['width'],40)
            q=Path(t)/'fake.webp';q.write_bytes(p.read_bytes())
            with self.assertRaises(ValueError):policy.technical(q)
            p.write_bytes(b'not an image')
            with self.assertRaises(Exception):policy.technical(p)
