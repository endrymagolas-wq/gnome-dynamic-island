#!/usr/bin/env python3
"""Explicit user controls; no model, shell interpolation, or arbitrary commands."""
import argparse,json,subprocess,sys
from pathlib import Path
import preferences
from diagnostics import diagnose
p=argparse.ArgumentParser();p.add_argument('action',choices=['status','on','off','economy-on','economy-off','mute','unmute','diagnose']);p.add_argument('kind',nargs='?',choices=sorted(preferences.KINDS));args=p.parse_args()
settings=preferences.read()
if args.action in ['mute','unmute']:
    if args.kind is None:p.error('kind required')
    values=set(settings['muted_kinds'])
    if args.action=='mute':values.add(args.kind)
    else:values.discard(args.kind)
    settings['muted_kinds']=sorted(values);preferences.write(settings)
elif args.action.startswith('economy-'):settings['economy']=args.action=='economy-on';preferences.write(settings)
elif args.action in ['on','off']:
    if args.action=='on' and not ((Path(__file__).resolve().parent/'venv/bin/python').is_file() and (Path(__file__).resolve().parent/'model/multilingual/model.safetensors').is_file()):
        print(json.dumps({'ok':False,'error':'Спочатку виконай setup_assistant.py для моделі Laya'},ensure_ascii=False));sys.exit(1)
    old=settings.copy();settings['enabled']=args.action=='on';preferences.write(settings)
    try:
        r=subprocess.run(['systemctl','--user','enable' if settings['enabled'] else 'disable','--now','island-assistant.service'],capture_output=True,text=True,timeout=12)
        if r.returncode:preferences.write(old);print(json.dumps({'ok':False,'error':'Не вдалося змінити стан помічника'}));sys.exit(1)
    except (OSError,subprocess.TimeoutExpired):
        # Keep requested preference: a delayed systemd job may still complete.
        print(json.dumps({'ok':False,'error':'Перевір стан служби помічника','preferences':settings},ensure_ascii=False));sys.exit(1)
if args.action=='diagnose':print(json.dumps({'ok':True,'diagnosis':diagnose()},ensure_ascii=False))
else:print(json.dumps({'ok':True,'preferences':settings},ensure_ascii=False))
