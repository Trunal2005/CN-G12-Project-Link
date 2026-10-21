import json,hashlib,math
from .config import MODELS
from ml.features import NAMES

def read_model():
    m=json.loads((MODELS/'forest.json').read_text())
    if m.get('schema')!='forest-v1' or m.get('feature_names')!=NAMES:raise ValueError('Incompatible feature schema')
    trees=m.get('trees')
    if not isinstance(trees,list) or not 1<=len(trees)<=64:raise ValueError('Invalid ensemble')
    for t in trees:
        size=len(t['left'])
        if not 1<=size<=1024 or any(len(t[k])!=size for k in ['right','feature','threshold','value']):raise ValueError('Invalid tree arrays')
        for i,l in enumerate(t['left']):
            if not all(isinstance(t[k][i],(float,int)) and math.isfinite(t[k][i]) for k in ['threshold','value']):raise ValueError('Nonfinite tree')
            if l==-1:
                if t['right'][i]!=-1:raise ValueError('Invalid leaf')
            elif not (isinstance(l,int) and i<l<size and isinstance(t['right'][i],int) and i<t['right'][i]<size and isinstance(t['feature'][i],int) and 0<=t['feature'][i]<len(NAMES)):raise ValueError('Invalid child index')
    checksum=hashlib.sha256(json.dumps(trees,sort_keys=True).encode()).hexdigest()
    if m.get('checksum')!=checksum:raise ValueError('Model checksum mismatch')
    return m

def status():
    try:
        m=read_model();return {'ready':True,**{k:v for k,v in m.items() if k!='trees'}}
    except (OSError,ValueError,KeyError,TypeError) as e:return {'ready':False,'fallback':'historical','reason':str(e)}
