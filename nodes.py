"""Schema-backed ComfyUI nodes for the current MidjourneyDify catalog.

Model and action selectors are first-class. Remaining Dify parameters use JSON,
which is validated by the copied published API contract before any request.
"""

from __future__ import annotations

import json
import os

from .client import AceDataMidjourneyClient

SERVICE = 'Midjourney'
MEDIA_TYPES = ('IMAGE', 'VIDEO')
TOOL_SPECS = {'midjourney_describe': {'models': [],
                         'actions': [],
                         'operation': 'describe',
                         'label': 'Midjourney Describe',
                         'description': 'Get descriptions for an image via Ace Data Cloud Midjourney '
                                        'Describe API.',
                         'required': ['image_url'],
                         'fields': ['image_url']},
 'midjourney_edits': {'models': [],
                      'actions': [],
                      'operation': 'edit',
                      'label': 'Midjourney Edits',
                      'description': 'Edit an image via Ace Data Cloud Midjourney Edits API.',
                      'required': [],
                      'fields': ['mask', 'mode', 'prompt', 'image_url', 'callback_url', 'split_images']},
 'midjourney_get_seed': {'models': [],
                         'actions': [],
                         'operation': 'request',
                         'label': 'Midjourney Get Seed',
                         'description': 'Get Seed through the Ace Data Cloud Midjourney API.',
                         'required': ['image_id'],
                         'fields': ['image_id']},
 'midjourney_imagine': {'models': [],
                        'actions': [],
                        'operation': 'generate',
                        'label': 'Midjourney Imagine',
                        'description': 'Generate or transform images via Ace Data Cloud Midjourney '
                                       'Imagine API.',
                        'required': [],
                        'fields': ['mask',
                                   'mode',
                                   'prompt',
                                   'timeout',
                                   'image_id',
                                   'translation',
                                   'callback_url',
                                   'split_images',
                                   'version',
                                   'hd',
                                   'quality',
                                   'style_reference',
                                   'moodboard']},
 'midjourney_shorten': {'models': [],
                        'actions': [],
                        'operation': 'request',
                        'label': 'Midjourney Shorten',
                        'description': 'Shorten through the Ace Data Cloud Midjourney API.',
                        'required': ['prompt'],
                        'fields': ['prompt']},
 'midjourney_task_retrieve': {'models': [],
                              'actions': [],
                              'operation': 'task',
                              'label': 'Midjourney Retrieve Task',
                              'description': 'Retrieve one task, optionally waiting up to 240 seconds.',
                              'required': [],
                              'fields': ['trace_id']},
 'midjourney_tasks_retrieve_batch': {'models': [],
                                     'actions': [],
                                     'operation': 'batch',
                                     'label': 'Midjourney Retrieve Tasks',
                                     'description': 'Retrieve existing tasks by ID without repeating '
                                                    'generation.',
                                     'required': [],
                                     'fields': ['trace_id', 'trace_ids', 'offset', 'limit']},
 'midjourney_translate': {'models': [],
                          'actions': [],
                          'operation': 'translate',
                          'label': 'Midjourney Translate',
                          'description': 'Translate Chinese prompt to English via Ace Data Cloud '
                                         'Midjourney Translate API.',
                          'required': ['content'],
                          'fields': ['content']},
 'midjourney_videos': {'models': [],
                       'actions': ['generate', 'extend'],
                       'operation': 'video',
                       'label': 'Midjourney Videos',
                       'description': 'Generate or extend videos via Ace Data Cloud Midjourney Videos '
                                      'API.',
                       'required': [],
                       'fields': ['mode',
                                  'resolution',
                                  'prompt',
                                  'video_id',
                                  'video_index',
                                  'loop',
                                  'image_url',
                                  'end_image_url',
                                  'callback_url']}}
SENTINEL = '(from JSON/default)'


def _credential() -> str:
    token = os.environ.get('ACEDATACLOUD_API_KEY') or os.environ.get('ACEDATACLOUD_API_TOKEN')
    if not token or not token.strip():
        raise RuntimeError('Set ACEDATACLOUD_API_KEY in the ComfyUI process environment and restart.')
    return token.strip()


class _ToolNode:
    RETURN_TYPES = ('STRING', 'STRING', 'STRING', 'STRING', 'STRING', 'STRING')
    RETURN_NAMES = ('status', 'task_id', 'media_urls_json', 'first_media_url', 'result_json', 'trace_id')
    FUNCTION = 'run'
    CATEGORY = 'Ace Data Cloud/' + SERVICE
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        spec = cls.SPEC
        required = {'parameters_json': ('STRING', {'multiline': True, 'default': '{}'})}
        if spec['models']:
            required['model'] = ([SENTINEL, *spec['models']], {'default': SENTINEL})
        if spec['actions']:
            required['action'] = ([SENTINEL, *spec['actions']], {'default': SENTINEL})
        for name in spec['fields']:
            if name == 'confirm':
                required[name] = ('BOOLEAN', {'default': False})
            else:
                required[name] = ('STRING', {'multiline': name in {'prompt', 'lyric', 'lyrics',
                    'image_urls', 'audio_urls', 'video_urls', 'negative_prompt'} or name.endswith('_json'),
                    'default': ''})
        if spec['operation'] == 'task':
            required['task_id'] = ('STRING', {'default': ''})
            required['wait_seconds'] = ('INT', {'default': 0, 'min': 0, 'max': 240})
        if spec['operation'] == 'batch':
            required['ids_json'] = ('STRING', {'multiline': True, 'default': ''})
        return {'required': required}

    def run(self, parameters_json: str, model: str = SENTINEL, action: str = SENTINEL,
            task_id: str = '', wait_seconds: int = 0, ids_json: str = '', **fields):
        try:
            parameters = json.loads(parameters_json)
        except (TypeError, ValueError):
            raise ValueError('parameters_json must contain a JSON object.') from None
        if not isinstance(parameters, dict):
            raise ValueError('parameters_json must contain a JSON object.')
        if model != SENTINEL:
            parameters['model'] = model
        if action != SENTINEL:
            parameters['action'] = action
        for name, value in fields.items():
            if value is not None and value != '':
                parameters[name] = value
        if task_id.strip():
            parameters['task_id'] = task_id.strip()
        if self.SPEC['operation'] == 'task':
            parameters['wait_seconds'] = wait_seconds
        if ids_json.strip():
            try:
                ids = json.loads(ids_json)
            except ValueError:
                raise ValueError('ids_json must be a JSON array of task IDs.') from None
            if not isinstance(ids, list) or not ids:
                raise ValueError('ids_json must be a nonempty JSON array of task IDs.')
            parameters['ids'] = ids
        result = AceDataMidjourneyClient(_credential()).invoke(self.TOOL, parameters)
        urls = result.get('media_urls') or []
        if not isinstance(urls, list):
            urls = []
        status = str(result.get('status') or 'unknown')
        resolved_task_id = str(result.get('task_id') or '')
        trace_id = str(result.get('trace_id') or '')
        return {
            'ui': {'text': [f'{SERVICE} status: {status}',
                            f'Task ID: {resolved_task_id or "completed synchronously"}',
                            f'Media URLs: {len(urls)}']},
            'result': (status, resolved_task_id, json.dumps(urls), urls[0] if urls else '',
                       json.dumps(result, ensure_ascii=False, default=str), trace_id),
        }


NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
for tool, spec in TOOL_SPECS.items():
    class_name = 'Ace' + ''.join(part.title() for part in SERVICE.split()) + ''.join(
        part.title() for part in tool.split('_')
    )
    node = type(class_name, (_ToolNode,), {'TOOL': tool, 'SPEC': spec,
                                          'DESCRIPTION': spec['description']})
    NODE_CLASS_MAPPINGS[class_name] = node
    NODE_DISPLAY_NAME_MAPPINGS[class_name] = spec['label'] + ' (Ace Data Cloud)'


if MEDIA_TYPES:
    from .media import as_audio, as_image, as_video, download_media


class _LoadImage:
    RETURN_TYPES = ('IMAGE',)
    RETURN_NAMES = ('image',)
    FUNCTION = 'run'
    CATEGORY = 'Ace Data Cloud/' + SERVICE
    DESCRIPTION = 'Load a completed Ace CDN image into ComfyUI IMAGE.'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'media_url': ('STRING', {'default': ''})}}

    def run(self, media_url: str):
        if not media_url:
            raise ValueError('Task is pending; retrieve the same task ID again.')
        return (as_image(download_media(media_url)),)


class _LoadVideo:
    RETURN_TYPES = ('VIDEO',)
    RETURN_NAMES = ('video',)
    FUNCTION = 'run'
    CATEGORY = 'Ace Data Cloud/' + SERVICE
    DESCRIPTION = 'Load a completed Ace CDN video into native ComfyUI VIDEO.'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'media_url': ('STRING', {'default': ''})}}

    def run(self, media_url: str):
        if not media_url:
            raise ValueError('Task is pending; retrieve the same task ID again.')
        return (as_video(download_media(media_url)),)


class _LoadAudio:
    RETURN_TYPES = ('AUDIO',)
    RETURN_NAMES = ('audio',)
    FUNCTION = 'run'
    CATEGORY = 'Ace Data Cloud/' + SERVICE
    DESCRIPTION = 'Load a completed Ace CDN audio file into ComfyUI AUDIO.'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'media_url': ('STRING', {'default': ''})}}

    def run(self, media_url: str):
        if not media_url:
            raise ValueError('Task is pending; retrieve the same task ID again.')
        return (as_audio(download_media(media_url)),)


for media_type, base in {'IMAGE': _LoadImage, 'VIDEO': _LoadVideo, 'AUDIO': _LoadAudio}.items():
    if media_type in MEDIA_TYPES:
        class_name = 'Ace' + ''.join(part.title() for part in SERVICE.split()) + 'Load' + media_type.title()
        NODE_CLASS_MAPPINGS[class_name] = type(class_name, (base,), {})
        NODE_DISPLAY_NAME_MAPPINGS[class_name] = SERVICE + ' Load ' + media_type.title() + ' (Ace Data Cloud)'

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'TOOL_SPECS']
