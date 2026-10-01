#!/usr/bin/env python3
"""Vendored dependency resolution must work from a clean shell, not only via Makefile PYTHONPATH."""
from __future__ import annotations
import os
import subprocess
import sys

ROOT=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
code=r'''
import os,sys
root=os.getcwd()
sys.path.insert(0, os.path.join(root,'code','physics'))
import mountain_lora_link
import itmlogic
actual=os.path.realpath(itmlogic.__file__)
expected=os.path.realpath(os.path.join(root,'libs','pylibs')) + os.sep
assert actual.startswith(expected), (actual, expected)
from itmlogic.preparatory_subroutines.qlrpfl import qlrpfl
print(actual)
'''
env=dict(os.environ)
env.pop('PYTHONPATH',None)
p=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,capture_output=True,text=True)
if p.returncode:
    print('FAIL vendored dependency clean-shell resolution')
    print(p.stdout)
    print(p.stderr)
    raise SystemExit(p.returncode)
print('PASS vendored itmlogic clean-shell resolution:',p.stdout.strip())
