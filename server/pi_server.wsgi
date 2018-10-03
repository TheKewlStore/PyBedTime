import sys

sys.path.insert(0, '/var/www/pybedtime')

from server import pi_server

pi_server.initialize()

application = pi_server.app
