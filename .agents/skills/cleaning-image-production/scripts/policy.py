"""Evidence-backed acceptance gates. Visual observations remain human attestations."""
from pathlib import Path
import hashlib
from PIL import Image

POLICY_VERSION = 'darwin-recovery-2'
COMMON = ('service_correct', 'target_clear', 'physical_realism', 'scene_diverse',
          'crop_readable', 'no_graphics_or_fake_logos', 'natural_documentary_finish')

def acceptance(slot, observed):
    """Reject absent/failed observations, including scoped human composition."""
    for key in COMMON:
        if observed.get(key) is not True:
            raise ValueError('Missing or failed observation: ' + key)
    if slot['role'] == 'hero':
        if observed.get('humans_present') is not False:
            raise ValueError('Heroes must contain no humans, partial bodies, reflections or shadows')
    elif observed.get('active_cleaning') is True:
        for key in ('worker_present', 'torso_arms_hands_visible', 'head_face_outside_frame',
                    'correct_technique', 'equipment_contact_correct', 'forest_green_uniform'):
            if observed.get(key) is not True:
                raise ValueError('Active process requirement failed: ' + key)
    if slot['role'] == 'before' and 'rug' in slot['page_file'].lower():
        if observed.get('active_cleaning') is not True:
            raise ValueError('Rug BEFORE requires a worker actively cleaning the clearly visible rug')
    if slot.get('pair_id'):
        for key in ('pair_identity_connected', 'result_difference_visible'):
            if observed.get(key) is not True:
                raise ValueError('Comparison requirement failed: ' + key)
    if observed.get('equipment_used') is True:
        if observed.get('reference_geometry_and_colours_match') is not True:
            raise ValueError('Actual referenced equipment must match')
    elif not observed.get('equipment_none_reason', '').strip():
        raise ValueError('No equipment requires a task-specific reason')
    if slot.get('provenance') == 'AI_ILLUSTRATIVE' and slot.get('job_verified'):
        raise ValueError('Synthetic imagery is not verified customer-job proof')
    return True

def technical(asset):
    path = Path(asset)
    from workflow import safe
    path = safe(path)
    with Image.open(path) as im:
        fmt, size = im.format, im.size
        im.verify()
    with Image.open(path) as im:
        im.load()
    valid = {'PNG': {'.png'}, 'JPEG': {'.jpg', '.jpeg'}, 'WEBP': {'.webp'}}
    if path.suffix.lower() not in valid.get(fmt, set()):
        raise ValueError('Image bytes and extension disagree')
    return {'format': fmt, 'width': size[0], 'height': size[1],
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

def unique_mapping(candidates):
    if len(candidates) != 1:
        raise ValueError('Missing or ambiguous assignment; explicit owner slot mapping required')
    return candidates[0]

def compose(slot):
    rule = ('No humans, partial bodies, people in reflections or human shadows. Show the service '
            'through the target, environment and appropriate equipment, never a worker.') if slot['role']=='hero' else (
            'If this depicts active cleaning, retain a physical worker with torso, arms, hands and '
            'correct tool contact; naturally crop head and face outside the frame. Plain dark '
            'forest-green polo, practical dark trousers and suitable PPE. A cropped head is not a missing worker.')
    if slot['role']=='before' and 'rug' in slot['page_file'].lower():
        rule += ' Mandatory active worker with professional tools; rug boundaries and treatment clearly visible.'
    if slot['role']=='after':
        rule += ' Finished result, no forced worker or machinery.'
    if slot.get('pair_id'):
        rule += ' Same identifiable environment and item. Camera angle may differ; no angle change required if identity and cleaning result are clear. Crop or tiny zoom alone is not a cleaning result. Visible believable dirt removal at card size.'
    return (slot['prompt_brief'] + '\nAUTHORITATIVE ROLE RULE: ' + rule +
            '\nFlagship-smartphone documentary character, natural daylight or credible commercial light, '
            'neutral-to-warm white balance, restrained contrast, real microtextures and ordinary imperfections. '
            'No CGI gloss, excessive HDR, stock posing, artificial blur, slogans, watermarks or fabricated logos. '
            'Physical machine colours and geometry follow originals. Source claims are unverified context.')
