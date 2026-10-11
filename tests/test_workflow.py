import importlib.util
import json
import tempfile
import unittest
import os
import subprocess
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1] / '.agents/skills/cleaning-image-production/scripts/workflow.py'
spec = importlib.util.spec_from_file_location('workflow', ENGINE)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)

HTML = '''<html><head><link rel="canonical" href="https://example.test/locations/darwin/commercial/office/"/></head><body>
<section><h1>Office Cleaning</h1><p>Clean hard floors professionally.</p><div class="ph" style="aspect-ratio:4/3"></div></section>
<section><h2>Results</h2><div class="ba"><div class="ba-layer"></div><div class="ba-layer ba-before" data-before></div><input class="ba-range" aria-label="Office entry"/></div><p class="cap">Entry tiles</p></section>
<section><h2>Gallery</h2><div class="job-imgs"><div class="ph"></div><div class="ph"></div></div></section></body></html>'''

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.source = self.base / 'source'; self.source.mkdir()
        (self.source / 'office.html').write_text(HTML, encoding='utf-8')
        self.output = self.base / 'output'
    def tearDown(self): self.tmp.cleanup()
    def init(self): return w.initialize(self.source, self.output, 'Darwin')
    def test_exact_roles_context_and_source_unchanged(self):
        before = (self.source/'office.html').read_bytes(); state = self.init()
        self.assertEqual(len(state['slots']), 5)
        self.assertEqual(sorted(r['role'] for r in state['slots']), ['after','before','gallery','gallery','hero'])
        self.assertTrue(all(r['dom_selector'] and r['source_sha256'] for r in state['slots']))
        pair = [r for r in state['slots'] if r['pair_id']]
        self.assertEqual(pair[0]['pair_id'],pair[1]['pair_id'])
        self.assertEqual((self.source/'office.html').read_bytes(), before)
    def test_output_under_source_rejected_before_write(self):
        with self.assertRaises(ValueError): w.initialize(self.source,self.source/'nested','Darwin')
        self.assertFalse((self.source/'nested').exists())
    def test_protected_source_rejected(self):
        prohibited=self.base/'Recovered Images - DO NOT SCAN'
        with self.assertRaises(ValueError):w.initialize(prohibited,self.output,'Darwin')
        self.assertFalse(self.output.exists())
    def test_output_ancestor_of_source_is_rejected(self):
        output=self.base/'ancestor'; source=output/'pages'/'Commercial'/'office';source.mkdir(parents=True)
        (source/'office.html').write_text(HTML,encoding='utf-8')
        (source/'source.html').write_text('OWNER ORIGINAL DO NOT OVERWRITE',encoding='utf-8')
        with self.assertRaises(ValueError):w.initialize(source,output,'Darwin')
        self.assertEqual((source/'source.html').read_text(encoding='utf-8'),'OWNER ORIGINAL DO NOT OVERWRITE')
    def test_state_symlink_into_protected_folder_rejected_before_read(self):
        protected=self.base/'Recovered Images - DO NOT SCAN';protected.mkdir()
        target=protected/'private.json';target.write_text('{}',encoding='utf-8')
        self.output.mkdir()
        try:os.symlink(target,self.output/'state.json')
        except OSError as e:self.skipTest('Symlink creation unavailable: '+str(e))
        with self.assertRaises(ValueError):w.load(self.output)
    def test_ai_registration_requires_preflight(self):
        state=self.init();asset=self.base/'asset.webp';asset.write_bytes(b'RIFF\x04\x00\x00\x00WEBP');slot=state['slots'][0]
        with self.assertRaises(ValueError):w.register(self.output,slot['slot_id'],asset,'AI_ILLUSTRATIVE')
        w.preflight(self.output,slot['slot_id'],'none','No equipment belongs in this finished surface','actual reference-check evidence')
        self.assertEqual(w.register(self.output,slot['slot_id'],asset,'AI_ILLUSTRATIVE')['provenance'],'AI_ILLUSTRATIVE')
    def test_resume_preserves_progress_and_detects_source_drift(self):
        state=self.init(); state['slots'][0]['note']='preserve me';w.save(self.output,state)
        self.assertEqual(self.init()['slots'][0]['note'],'preserve me')
        (self.source/'office.html').write_text(HTML+'<!-- changed -->',encoding='utf-8')
        with self.assertRaises(ValueError):self.init()
    def test_approval_requires_review_and_exact_asset_hash_and_locks_it(self):
        state=self.init();slot=state['slots'][0];asset=self.base/'asset.webp';asset.write_bytes(b'RIFF\x04\x00\x00\x00WEBP')
        with self.assertRaises(ValueError):w.approve(self.output,slot['slot_id'],'owner message')
        w.register(self.output,slot['slot_id'],asset)
        with self.assertRaises(ValueError):w.review(self.output,slot['slot_id'],{},'')
        checks={key:True for key in w.REVIEW_CHECKS};w.review(self.output,slot['slot_id'],checks,'test screenshot reference')
        w.approve(self.output,slot['slot_id'],'owner approved exact revision')
        with self.assertRaises(ValueError):w.register(self.output,slot['slot_id'],asset)
        self.assertTrue(w.load(self.output)['slots'][0]['owner_approved'])
    def test_retry_limit(self):
        state=self.init();slot=state['slots'][0];asset=self.base/'asset.webp';asset.write_bytes(b'RIFF\x04\x00\x00\x00WEBP')
        for _ in range(3):w.register(self.output,slot['slot_id'],asset)
        with self.assertRaises(ValueError):w.register(self.output,slot['slot_id'],asset)
    def test_incomplete_review_does_not_pass(self):
        state=self.init();slot=state['slots'][0];asset=self.base/'asset.webp';asset.write_bytes(b'RIFF\x04\x00\x00\x00WEBP');w.register(self.output,slot['slot_id'],asset)
        with self.assertRaises(ValueError):w.review(self.output,slot['slot_id'],{'realistic':True},'screenshot')
    def test_context_not_job_evidence(self):
        state=self.init();self.assertTrue(all(not r['job_verified'] and not r['owner_approved'] for r in state['slots']))
    def test_stale_save_cannot_erase_newer_progress(self):
        self.init();a=w.load(self.output);b=w.load(self.output);a['slots'][0]['note']='owner assignment';w.save(self.output,a)
        b['slots'][1]['note']='stale writer'
        with self.assertRaises(ValueError):w.save(self.output,b)
        self.assertEqual(w.load(self.output)['slots'][0]['note'],'owner assignment')
    def test_next_reviews_generated_work_and_detects_source_drift(self):
        state=self.init();slot=state['slots'][0];asset=self.base/'asset.webp';asset.write_bytes(b'RIFF\x04\x00\x00\x00WEBP');w.register(self.output,slot['slot_id'],asset)
        following=w.next_slot(self.output);self.assertEqual(following['slot_id'],slot['slot_id']);self.assertEqual(following['next_action'],'review')
        (self.source/'office.html').write_text(HTML+'<!-- drift -->',encoding='utf-8')
        with self.assertRaises(ValueError):w.next_slot(self.output)
    def test_page_records_follow_registration(self):
        state=self.init();slot=state['slots'][0];asset=self.base/'asset.webp';asset.write_bytes(b'RIFF\x04\x00\x00\x00WEBP');w.register(self.output,slot['slot_id'],asset)
        page=json.loads((Path(slot['page_folder'])/'slots.json').read_text(encoding='utf-8'))
        self.assertEqual(page[0]['status'],'generated');self.assertTrue(page[0]['asset_path'])
    def test_existing_source_image_is_not_queued_for_generation(self):
        (self.source/'office.html').write_text(HTML.replace('<div class="ph" style="aspect-ratio:4/3"></div>','<div class="ph" style="aspect-ratio:4/3"><img src="owner-image.webp"></div>'),encoding='utf-8')
        state=self.init();self.assertEqual(state['slots'][0]['status'],'existing_assignment');self.assertEqual(state['slots'][0]['existing_source'],'owner-image.webp')
        self.assertNotEqual(w.next_slot(self.output)['slot_id'],state['slots'][0]['slot_id'])
    def test_retry_reopens_only_with_explicit_evidence_and_keeps_versions(self):
        state=self.init();slot=state['slots'][0];asset=self.base/'asset.webp';asset.write_bytes(b'RIFF\x04\x00\x00\x00WEBP')
        for _ in range(3):w.register(self.output,slot['slot_id'],asset)
        with self.assertRaises(ValueError):w.authorize_retry(self.output,slot['slot_id'],'','')
        w.authorize_retry(self.output,slot['slot_id'],'Owner requested a different scene approach','Change scene, keep target and references')
        new=w.register(self.output,slot['slot_id'],asset);self.assertEqual(new['attempts'],4)
        self.assertEqual(len(list((Path(slot['page_folder'])/'images').glob('*.webp'))),4)
    def test_destination_directory_link_cannot_overwrite_source(self):
        parent=self.output/'pages'/'Commercial';parent.mkdir(parents=True);link=parent/'office'
        (self.source/'source.html').write_text('OWNER SOURCE',encoding='utf-8')
        if os.name=='nt':
            command="New-Item -ItemType Junction -Path '"+str(link).replace("'","''")+"' -Target '"+str(self.source).replace("'","''")+"' | Out-Null"
            result=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True)
            if result.returncode:self.skipTest('Directory junction creation unavailable')
        else:os.symlink(self.source,link,target_is_directory=True)
        with self.assertRaises(ValueError):w.initialize(self.source,self.output,'Darwin')
        self.assertEqual((self.source/'source.html').read_text(encoding='utf-8'),'OWNER SOURCE')
        self.assertFalse((self.source/'images').exists())
    def test_existing_assignment_can_be_imported_without_losing_source_reference(self):
        (self.source/'office.html').write_text(HTML.replace('<div class="ph" style="aspect-ratio:4/3"></div>','<div class="ph"><img src="owner.webp"></div>'),encoding='utf-8')
        state=self.init();slot=state['slots'][0];asset=self.base/'owner.webp';asset.write_bytes(b'RIFF\x04\x00\x00\x00WEBP')
        with self.assertRaises(ValueError):w.import_existing(self.output,slot['slot_id'],asset,'')
        w.import_existing(self.output,slot['slot_id'],asset,'Owner confirmed local asset matches existing source assignment')
        record=w.load(self.output)['slots'][0];self.assertEqual(record['existing_source'],'owner.webp');self.assertEqual(record['status'],'generated');self.assertFalse(record['owner_approved'])

if __name__ == '__main__': unittest.main()
