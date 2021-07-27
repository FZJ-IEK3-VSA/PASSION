from . import util
from .satellite import *
from .segmentation import *
from .buildings import *
try:
  from .technical import *
except Exception as e:
  print('Error while importing RESKit. Package is not available in Windows. Continuing with the rest of submodules...')
from .economic import *