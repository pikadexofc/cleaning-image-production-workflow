import json,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'.agents/skills/cleaning-image-production/scripts'))
import workflow as w
import policy
import recovery

HTML='<section><h1>Office</h1><div class="ph"></div></section><section><div class="ba"><div class="ba-layer"></div><div class="ba-layer ba-before" data-before></div></div></section>'

class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=self.root/'source';self.source.mkdir();(self.source/'office.html').write_text(HTML)
        self.output=self.root/'output';self.state=w.initialize(self.source,self.output,'Darwin')
        self.slot=self.state['slots'][0];self.asset=self.root/'image.png';Image.new('RGB',(40,30)).save(self.asset)
        w.register(self.output,self.slot['slot_id'],self.asset)
        self.proof=self.root/'review.txt';self.proof.write_text('Actual test fixture observations, not production pixel evidence')
        self.observed={k:True for k in policy.COMMON};self.observed.update(humans_present=False,equipment_used=False,equipment_none_reason='Finished office')
    def tearDown(self):self.tmp.cleanup()
    def test_legacy_review_cannot_be_approved_by_gateway(self):
        w.review(self.output,self.slot['slot_id'],{k:True for k in w.REVIEW_CHECKS},'old review')
        with self.assertRaises(ValueError):recovery.approve(self.output,self.slot['slot_id'],self.proof)
    def test_real_review_and_exact_approval(self):
        recovery.record_review(self.output,self.slot['slot_id'],self.observed,self.proof)
        owner=self.root/'owner.txt';owner.write_text('Owner exact test approval: '+w.load(self.output)['slots'][0]['asset_sha256'])
        recovery.approve(self.output,self.slot['slot_id'],owner)
        self.assertTrue(w.load(self.output)['slots'][0]['owner_approved'])
        with self.assertRaises(ValueError):w.register(self.output,self.slot['slot_id'],self.asset)
    def test_missing_and_changed_review_evidence_block(self):
        with self.assertRaises(ValueError):recovery.record_review(self.output,self.slot['slot_id'],self.observed,self.root/'missing.txt')
        recovery.record_review(self.output,self.slot['slot_id'],self.observed,self.proof)
        self.proof.write_text('Changed')
        with self.assertRaises(ValueError):recovery.approve(self.output,self.slot['slot_id'],self.proof)
    def test_opposite_pair_missing_blocks(self):
        slot=self.state['slots'][1];w.register(self.output,slot['slot_id'],self.asset)
        observations=dict(self.observed,pair_identity_connected=True,result_difference_visible=True,camera_change_noticeable=True)
        with self.assertRaises(ValueError):recovery.record_review(self.output,slot['slot_id'],observations,self.proof)
    def test_identical_pair_bytes_block(self):
        for slot in self.state['slots'][1:]:w.register(self.output,slot['slot_id'],self.asset)
        observations=dict(self.observed,pair_identity_connected=True,result_difference_visible=True,camera_change_noticeable=True)
        with self.assertRaises(ValueError):recovery.record_review(self.output,self.state['slots'][1]['slot_id'],observations,self.proof)
    def test_blocked_state_visible_and_progress_preserved(self):
        s=w.load(self.output);s['slots'][0].update(status='blocked',blocked_reason='Equipment reference missing');w.save(self.output,s)
        item=recovery.next_item(self.output)
        self.assertEqual(item['next_action'],'resolve_block');self.assertTrue(item['asset_path'])
    def test_resume_reviews_existing_batch_first(self):
        self.assertEqual(recovery.next_item(self.output)['next_action'],'review')
        self.assertEqual(w.initialize(self.source,self.output,'Darwin')['slots'][0]['attempts'],1)
