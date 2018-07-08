import sys
import time
import yaml
import pexpect
import getpass
import begin

# import pydevd
# pydevd.settrace('192.168.1.41', port=55555, stdoutToServer=True, stderrToServer=True)

ssh_connections = list()
connections = None
debug_mode = None


class Connection:
    def __init__(self, connection: dict):
        self.connection = connection
        self.server = self.connection['server']
        self.port = self.connection['port']
        self.tunnels = self.connection['tunnels']
        if 'name' in self.connection:
            self.name = self.connection['name']
        else:
            self.name = '{}:{}'.format(self.server, self.port)

        self.source_local_ports = self.get_source_local_ports()

    def get_source_local_ports(self):
        ports = list()

        for tunnel in self.connection['tunnels']:
            t = tunnel.split(',')

            if t[0] == 'L':
                ports.append(int(t[1]))

        return ports

    def get_cmd(self):
        return self.__str__()

    def __str__(self):
        data_key = ''
        if 'public_key' in self.connection.keys():
            data_key = '-i {}'.format(self.connection['public_key'])

        data_tunnels = list()

        if 'tunnels' not in self.connection.keys():
            print('Configuration error: ssh connection has no tunnels')
            return ''

        for tunnel in self.connection['tunnels']:
            t = tunnel.split(',')
            typ = t[0]
            src_port = t[1]
            ip = t[2]
            dst_port = t[3]
            data_tunnels.append('-{} {}:{}:{}'.format(typ, src_port, ip, dst_port))

        data_tunnel = ' '.join(data_tunnels)

        cmd = 'ssh -o IdentitiesOnly=yes {} {}@{} -p {} {}'.format(data_tunnel, self.connection['user'],
                                                                   self.connection['server'], self.connection['port'],
                                                                   data_key)

        return cmd

    def __repr__(self):
        return self.__str__()

def read_config(config_file: str) -> list:
    # El formato de fichero esperado con lineas con el siguiente estilo: local,puerto_origen,ip,puerto_destino

    with open(config_file, 'r') as f:
        data = yaml.load(f)

        connections = list()
        for c in data['connections']:
            conn = Connection(c)
            connections.append(conn)
        return connections

    raise FileNotFoundError('Config file not found: {}'.format(config_file))

def connect_ssh(connections: list) -> None:
    # Try to connect

    for c in connections:
        cmd = c.get_cmd()
        global ssh_connections
        ssh = pexpect.spawn(cmd)
        ssh_connections.append(ssh)

        try:
            time.sleep(0.1)
            if debug_mode: print('SSH command: {}'.format(cmd))
            ret = ssh.expect(['yes/no', 'assword: ', '[#\$] '], timeout=5)
            if debug_mode: print('RET: {} Output: {}'.format(ret, ssh.before))

            if ret == 0:
                time.sleep(0.1)
                ssh.sendline('yes')
                time.sleep(0.1)
            elif ret == 1:
                if not sys.stdin.isatty():
                    if debug_mode: print('Password echo')
                    ssh.sendline(sys.stdin.readline().rstrip())
                else:
                    ssh.sendline(getpass.getpass('Insert password for {}: '.format(c.name)))

            elif ret == 2:
                pass

        except pexpect.TIMEOUT:
            # Excepcion por tiempo de conexion
            print('Timeout error {}'.format(c.name))
        except pexpect.exceptions.EOF:
            print('Connection error {}'.format(c.name))
            continue

        if debug_mode:
            print('    - {} connected\n'.format(c.name))
        else:
            print('    - {} connected'.format(c.name))

def sleep_loop():
    '''Bucle infinito hasta pulsar control c'''
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        sys.exit(0)

def get_connections_names():
    return [c.name for c in connections]

def sort_connections():
    global connections

    connections_sorted = list()
    for c1 in connections:
        for c2 in connections:
            if c1.port in c2.source_local_ports:
                depend = True


@begin.subcommand
def connectall():
    """Connect all ssh configured ssh connections"""
    print('Connecting all ssh connections')
    connect_ssh(connections)
    print('All connected')
    sleep_loop()

@begin.subcommand
def connect(names):
    """Connect given ssh connections"""
    names_list = names.split(',')
    print('Connecting {}'.format(names))

    # Encontrar algun error en conexion pasada para informar al usuario
    connections_names = get_connections_names()
    ignored_connections = [c for c in names_list if c not in connections_names]

    if len(ignored_connections) > 0:
        print('Connections not found and ignoring: {}'.format(', '.join(ignored_connections)))

    # Filtrar conexiones y conectar
    connections_filtered = [c for c in connections if c.name in names_list]
    connect_ssh(connections_filtered)
    print('All connected')
    sleep_loop()

@begin.subcommand
def listconnections():
    """List available connections"""

    print('Available connections:')

    connections_names = get_connections_names()
    for name in connections_names:
        print('    {}'.format(name))

@begin.start(auto_convert=True)
def main(config_file: 'Config file' = 'tunnels.yaml', debug: 'Debug mode' = False):
    """Create tunnels"""
    try:
        global connections
        global debug_mode

        # Leer configuracion
        connections = read_config(config_file)

        # Ordenar conexiones jerarquicamente para que no haya ningun problema de dependencias
        # sort_connections()

        # Modo debug
        debug_mode = debug

    except FileNotFoundError:
        print('ERROR: File {} not found'.format(config_file))
        sys.exit(1)
