import os,sys,subprocess,webbrowser
from pathlib import Path
root=Path(__file__).resolve().parent
os.chdir(root)
local=root/'vendor'
if local.exists(): sys.path.insert(0,str(local))
workspace_deps=root.parent/'.webdeps'
if workspace_deps.exists(): sys.path.insert(0,str(workspace_deps))
try:
    import flask
    import importlib.util
    if importlib.util.find_spec("oracledb") is None: raise ImportError()
except ImportError:
    print('Installing Flask and the Oracle driver. Internet is needed for this first launch.')
    subprocess.check_call([sys.executable,'-m','pip','install','-r',str(root/'requirements.txt')])
import threading
threading.Timer(1.5,lambda:webbrowser.open('http://127.0.0.1:5000')).start()
from app import app
app.run(host='127.0.0.1',port=5000,debug=False)
